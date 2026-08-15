"""Behavioral tests for project utility commands."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from owlbear_tools.megalinter import MegaLinterImage, load_megalinter_image
from owlbear_tools.project import deps_status, deps_sync, doctor, megalint_clean, target_branch


def _git_result(command: list[str], *, cwd: Path | None = None) -> int:  # noqa: ARG001
    return 0 if command[:2] == ["git", "check-ref-format"] or "show-ref" in command else 1


def test_megalinter_image_loads_from_workspace_config(tmp_path: Path) -> None:
    config = tmp_path / ".mega-linter.yml"
    config.write_text(
        "MEGALINTER_FLAVOR: cupcake\nMEGALINTER_VERSION: v10.0.0\n",
        encoding="utf-8",
    )

    image = load_megalinter_image(config)

    assert image.repository == "ghcr.io/oxsecurity/megalinter-cupcake"
    assert image.tag == "v10.0.0"


def test_megalinter_image_matches_workspace_config() -> None:
    image = load_megalinter_image()

    assert re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+", image.tag)


@pytest.mark.parametrize(
    "config_text",
    [
        'MEGALINTER_VERSION: "v10.0.0"\nMEGALINTER_FLAVOR: "cupcake"\n',
        "MEGALINTER_FLAVOR: cupcake  # selected image flavor\nMEGALINTER_VERSION: v10.0.0  # pinned release\n",
    ],
)
def test_megalinter_image_accepts_stable_yaml_variants(tmp_path: Path, config_text: str) -> None:
    config = tmp_path / ".mega-linter.yml"
    config.write_text(config_text, encoding="utf-8")

    image = load_megalinter_image(config)

    assert image.reference == "ghcr.io/oxsecurity/megalinter-cupcake:v10.0.0"


def test_megalinter_image_uses_base_repository_for_all_flavor(tmp_path: Path) -> None:
    config = tmp_path / ".mega-linter.yml"
    config.write_text("MEGALINTER_VERSION: v10.0.0\n", encoding="utf-8")

    image = load_megalinter_image(config)

    assert image.reference == "ghcr.io/oxsecurity/megalinter:v10.0.0"


@pytest.mark.parametrize(
    ("config_text", "message"),
    [
        ("MEGALINTER_FLAVOR: cupcake\n", "invalid MEGALINTER_VERSION"),
        (
            "MEGALINTER_FLAVOR: cupcake\nMEGALINTER_VERSION: v10/unsafe\n",
            "invalid MEGALINTER_VERSION",
        ),
        (
            "MEGALINTER_FLAVOR: cupcake/unsafe\nMEGALINTER_VERSION: v10.0.0\n",
            "invalid MEGALINTER_FLAVOR",
        ),
        (
            "MEGALINTER_FLAVOR: cupcake\nMEGALINTER_VERSION: latest\n",
            "invalid MEGALINTER_VERSION",
        ),
        (
            "MEGALINTER_FLAVOR: cupcake\nMEGALINTER_VERSION: 10.0.0\n",
            "invalid MEGALINTER_VERSION",
        ),
        (
            "MEGALINTER_FLAVOR: cupcake\nMEGALINTER_VERSION: v10.0.0-beta\n",
            "invalid MEGALINTER_VERSION",
        ),
    ],
)
def test_megalinter_image_rejects_invalid_native_config(
    tmp_path: Path,
    config_text: str,
    message: str,
) -> None:
    config = tmp_path / ".mega-linter.yml"
    config.write_text(config_text, encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        load_megalinter_image(config)


def test_megalinter_image_rejects_non_mapping_config(tmp_path: Path) -> None:
    config = tmp_path / ".mega-linter.yml"
    config.write_text("- MEGALINTER_VERSION: v10.0.0\n", encoding="utf-8")

    with pytest.raises(TypeError, match="must contain a YAML mapping"):
        load_megalinter_image(config)


def test_renovate_megalinter_manager_tracks_independent_native_fields(tmp_path: Path) -> None:
    """Use Python regex as a syntax approximation; RE2 compatibility needs separate validation."""
    root = Path(__file__).resolve().parents[3]
    config = json.loads((root / ".github/renovate.json").read_text(encoding="utf-8"))
    manager = next(
        item for item in config["customManagers"] if item["managerFilePatterns"] == ["/^\\.mega-linter\\.yml$/"]
    )
    flavor_pattern, version_pattern = manager["matchStrings"]
    flavor_pattern = flavor_pattern.replace("(?<flavor>", "(?P<flavor>")
    version_pattern = version_pattern.replace("(?<currentValue>", "(?P<currentValue>")
    extract_pattern = manager["extractVersionTemplate"].replace("(?<version>", "(?P<version>")
    version_match_index = manager["matchStrings"].index(
        "MEGALINTER_VERSION:[ \\t]*(?:\\x22|')?v(?<currentValue>[0-9]+\\.[0-9]+\\.[0-9]+)(?:\\x22|')?"
    )

    reordered = 'MEGALINTER_VERSION: "v10.0.0"\n# keep fields independently matchable\nMEGALINTER_FLAVOR: "cupcake"\n'
    flavor_match = re.search(flavor_pattern, reordered)
    version_match = re.search(version_pattern, reordered)
    all_flavor_match = re.search(flavor_pattern, "MEGALINTER_FLAVOR: all\n")
    next_version_match = re.search(version_pattern, "MEGALINTER_VERSION: v10.1.0")
    native_config = (root / ".mega-linter.yml").read_text(encoding="utf-8")
    native_flavor_match = re.search(flavor_pattern, native_config)
    native_version_match = re.search(version_pattern, native_config)
    extracted_version_match = re.fullmatch(extract_pattern, "v10.1.0")
    native_image = load_megalinter_image(root / ".mega-linter.yml")
    base_config = tmp_path / ".mega-linter-all.yml"
    base_config.write_text(f"MEGALINTER_FLAVOR: all\nMEGALINTER_VERSION: {native_image.tag}\n", encoding="utf-8")
    base_image = load_megalinter_image(base_config)
    template = manager["depNameTemplate"]
    flavor_template = "{{#if flavor}}-{{{flavor}}}{{/if}}"
    rendered_flavored_repository = template.replace(
        flavor_template,
        f"-{native_flavor_match.group('flavor')}" if native_flavor_match is not None else "",
    )
    rendered_base_repository = template.replace(flavor_template, "")
    allowed_manager_fields = {
        "customType",
        "description",
        "fileFormat",
        "managerFilePatterns",
        "matchStrings",
        "matchStringsStrategy",
        "depNameTemplate",
        "packageNameTemplate",
        "datasourceTemplate",
        "versioningTemplate",
        "registryUrlTemplate",
        "currentValueTemplate",
        "extractVersionTemplate",
        "autoReplaceStringTemplate",
        "depTypeTemplate",
    }

    assert manager["matchStringsStrategy"] == "combination"
    assert set(manager).issubset(allowed_manager_fields)
    assert version_match_index == len(manager["matchStrings"]) - 1
    assert flavor_match is not None
    assert native_flavor_match is not None
    assert flavor_match.group("flavor") == native_flavor_match.group("flavor")
    assert version_match is not None
    assert version_match.group("currentValue") == "10.0.0"
    assert all_flavor_match is not None
    assert all_flavor_match.groupdict()["flavor"] is None
    assert next_version_match is not None
    assert next_version_match.group("currentValue") == "10.1.0"
    assert native_version_match is not None
    assert native_version_match.group("currentValue") == native_image.tag.removeprefix("v")
    assert extracted_version_match is not None
    assert extracted_version_match.group("version") == "10.1.0"
    assert rendered_flavored_repository == native_image.repository
    assert rendered_base_repository == base_image.repository
    for invalid_tag in ("latest", "v10", "v10.0", "v10.0.0-beta", "v10.0.0-alpha.1"):
        assert re.fullmatch(extract_pattern, invalid_tag) is None


def test_target_branch_prints_current_value(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: object) -> None:
    config = tmp_path / ".owlbear/delivery/config.json"
    config.parent.mkdir(parents=True)
    config.write_text(
        '{"schema_version":2,"remote":"origin","target_branch":"dev","github_repository":"example/project"}\n',
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["target-branch"])

    target_branch()

    assert capsys.readouterr().out == "dev\n"


def test_target_branch_atomically_changes_idle_project(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: object,
) -> None:
    config = tmp_path / ".owlbear/delivery/config.json"
    config.parent.mkdir(parents=True)
    config.write_text(
        '{"schema_version":2,"remote":"origin","target_branch":"dev","github_repository":"example/project"}\n',
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["target-branch", "release"])

    with patch("owlbear_tools.project._run", side_effect=_git_result):
        target_branch()

    assert json.loads(config.read_text(encoding="utf-8"))["target_branch"] == "release"
    assert "dev -> release" in capsys.readouterr().out


def test_target_branch_rejects_unfinished_delivery_work(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = tmp_path / ".owlbear/delivery/config.json"
    config.parent.mkdir(parents=True)
    config.write_text(
        '{"schema_version":2,"remote":"origin","target_branch":"dev","github_repository":"example/project"}\n',
        encoding="utf-8",
    )
    frontier = tmp_path / ".owlbear/delivery/runtime/changes/example/frontier.json"
    frontier.parent.mkdir(parents=True)
    frontier.write_text('{"bindings": []}\n', encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["target-branch", "release"])

    with patch("owlbear_tools.project._run", side_effect=_git_result), pytest.raises(SystemExit, match="2"):
        target_branch()

    assert json.loads(config.read_text(encoding="utf-8"))["target_branch"] == "dev"


def test_target_branch_accepts_acceptance_completed_delivery_work(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: object,
) -> None:
    config = tmp_path / ".owlbear/delivery/config.json"
    config.parent.mkdir(parents=True)
    config.write_text(
        '{"schema_version":2,"remote":"origin","target_branch":"dev","github_repository":"example/project"}\n',
        encoding="utf-8",
    )
    frontier = tmp_path / ".owlbear/delivery/runtime/changes/example/frontier.json"
    frontier.parent.mkdir(parents=True)
    frontier.write_text('{"bindings": [], "change_completion": {"completion_id": "receipt"}}\n', encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["target-branch", "release"])

    with patch("owlbear_tools.project._run", side_effect=_git_result):
        target_branch()

    assert json.loads(config.read_text(encoding="utf-8"))["target_branch"] == "release"
    assert "dev -> release" in capsys.readouterr().out


def test_target_branch_accepts_abandoned_delivery_work(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: object,
) -> None:
    config = tmp_path / ".owlbear/delivery/config.json"
    config.parent.mkdir(parents=True)
    config.write_text(
        '{"schema_version":2,"remote":"origin","target_branch":"dev","github_repository":"example/project"}\n',
        encoding="utf-8",
    )
    frontier = tmp_path / ".owlbear/delivery/runtime/changes/example/frontier.json"
    frontier.parent.mkdir(parents=True)
    frontier.write_text(
        '{"bindings": [], "change_abandonment": {"abandonment_id": "receipt"}}\n',
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["target-branch", "release"])

    with patch("owlbear_tools.project._run", side_effect=_git_result):
        target_branch()

    assert json.loads(config.read_text(encoding="utf-8"))["target_branch"] == "release"
    assert "dev -> release" in capsys.readouterr().out


def test_target_branch_accepts_legacy_integration_completed_delivery_work(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: object,
) -> None:
    config = tmp_path / ".owlbear/delivery/config.json"
    config.parent.mkdir(parents=True)
    config.write_text(
        '{"schema_version":2,"remote":"origin","target_branch":"dev","github_repository":"example/project"}\n',
        encoding="utf-8",
    )
    frontier = tmp_path / ".owlbear/delivery/runtime/changes/example/frontier.json"
    frontier.parent.mkdir(parents=True)
    frontier.write_text(
        json.dumps(
            {
                "bindings": [],
                "integration_result_id": "a" * 64,
                "integration_completion": {"completion_id": "a" * 64},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["target-branch", "release"])

    with patch("owlbear_tools.project._run", side_effect=_git_result):
        target_branch()

    assert json.loads(config.read_text(encoding="utf-8"))["target_branch"] == "release"
    assert "dev -> release" in capsys.readouterr().out


def test_target_branch_rejects_idle_change_coordination_without_frontier(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = tmp_path / ".owlbear/delivery/config.json"
    config.parent.mkdir(parents=True)
    config.write_text(
        '{"schema_version":2,"remote":"origin","target_branch":"dev","github_repository":"example/project"}\n',
        encoding="utf-8",
    )
    coordination = tmp_path / ".owlbear/delivery/runtime/claims/changes/example.json"
    coordination.parent.mkdir(parents=True)
    coordination.write_text('{"writer": null}\n', encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["target-branch", "release"])

    with patch("owlbear_tools.project._run", side_effect=_git_result), pytest.raises(SystemExit, match="2"):
        target_branch()

    assert json.loads(config.read_text(encoding="utf-8"))["target_branch"] == "dev"


@pytest.mark.parametrize(
    "unfinished_path",
    [
        ".owlbear/delivery/runtime/changes/example/contract.json",
        ".owlbear/delivery/packages/example/manifest.json",
    ],
)
def test_target_branch_rejects_partial_change_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    unfinished_path: str,
) -> None:
    config = tmp_path / ".owlbear/delivery/config.json"
    config.parent.mkdir(parents=True)
    config.write_text(
        '{"schema_version":2,"remote":"origin","target_branch":"dev","github_repository":"example/project"}\n',
        encoding="utf-8",
    )
    authority = tmp_path / unfinished_path
    authority.parent.mkdir(parents=True)
    authority.write_text("{}\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["target-branch", "release"])

    with patch("owlbear_tools.project._run", side_effect=_git_result), pytest.raises(SystemExit, match="2"):
        target_branch()

    assert json.loads(config.read_text(encoding="utf-8"))["target_branch"] == "dev"


@pytest.mark.parametrize("legacy_root", [".owlbear/target", ".owlbear/worktrees"])
def test_target_branch_rejects_unmigrated_delivery_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    legacy_root: str,
) -> None:
    config = tmp_path / ".owlbear/delivery/config.json"
    config.parent.mkdir(parents=True)
    config.write_text(
        '{"schema_version":2,"remote":"origin","target_branch":"dev","github_repository":"example/project"}\n',
        encoding="utf-8",
    )
    state = tmp_path / legacy_root / "state"
    state.parent.mkdir(parents=True)
    state.write_text("unmigrated\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["target-branch", "release"])

    with patch("owlbear_tools.project._run", side_effect=_git_result), pytest.raises(SystemExit, match="2"):
        target_branch()

    assert json.loads(config.read_text(encoding="utf-8"))["target_branch"] == "dev"


def test_doctor_accepts_canonical_workspace_without_cutover_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: object,
) -> None:
    config = tmp_path / ".owlbear/delivery/config.json"
    config.parent.mkdir(parents=True)
    config.write_text(
        '{"schema_version":2,"remote":"origin","target_branch":"dev","github_repository":"example/project"}\n',
        encoding="utf-8",
    )
    mcp = tmp_path / ".vscode/mcp.json"
    mcp.parent.mkdir(parents=True)
    mcp.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["doctor", str(tmp_path)])

    with (
        patch("owlbear_tools.project.shutil.which", return_value="/usr/bin/tool"),
        patch("owlbear_tools.project._remote_target_exists", return_value=True),
        patch("owlbear_tools.project._remote_github_repository", return_value="example/project"),
        pytest.raises(SystemExit, match="0"),
    ):
        doctor()

    output = capsys.readouterr().out
    assert "target-cutover" not in output


def test_doctor_reports_only_unsupported_config_schema(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: object,
) -> None:
    config = tmp_path / ".owlbear/delivery/config.json"
    config.parent.mkdir(parents=True)
    config.write_text('{"schema_version":1,"integration_target":"dev"}\n', encoding="utf-8")
    mcp = tmp_path / ".vscode/mcp.json"
    mcp.parent.mkdir(parents=True)
    mcp.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["doctor", str(tmp_path)])

    with (
        patch("owlbear_tools.project.shutil.which", return_value="/usr/bin/tool"),
        pytest.raises(SystemExit, match="1"),
    ):
        doctor()

    output = capsys.readouterr().out
    assert "FAIL  unsupported Delivery config schema: 1" in output
    assert "None/None" not in output


def test_doctor_rejects_unmigrated_delivery_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: object,
) -> None:
    config = tmp_path / ".owlbear/delivery/config.json"
    config.parent.mkdir(parents=True)
    config.write_text(
        '{"schema_version":2,"remote":"origin","target_branch":"dev","github_repository":"example/project"}\n',
        encoding="utf-8",
    )
    legacy = tmp_path / ".owlbear/target/runtime.json"
    legacy.parent.mkdir(parents=True)
    legacy.write_text("{}\n", encoding="utf-8")
    mcp = tmp_path / ".vscode/mcp.json"
    mcp.parent.mkdir(parents=True)
    mcp.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["doctor", str(tmp_path)])

    with (
        patch("owlbear_tools.project.shutil.which", return_value="/usr/bin/tool"),
        patch("owlbear_tools.project._remote_target_exists", return_value=True),
        patch("owlbear_tools.project._remote_github_repository", return_value="example/project"),
        pytest.raises(SystemExit, match="1"),
    ):
        doctor()

    assert "FAIL  unmigrated Delivery state: .owlbear/target" in capsys.readouterr().out


def test_deps_status_distinguishes_available_updates_from_sync(tmp_path, monkeypatch, capsys) -> None:
    web = tmp_path / "serve/cockpit/web"
    web.mkdir(parents=True)
    (web / "package-lock.json").write_text("{}\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    with patch("owlbear_tools.project._run", side_effect=[0, 1, 1]), pytest.raises(SystemExit, match="0"):
        deps_status()

    output = capsys.readouterr().out
    assert "Dependency status is informational" in output
    assert "Wanted is the newest version allowed by package.json" in output
    assert "does not update locks or manifest ranges" in output


def test_deps_sync_explains_that_it_reproduces_existing_locks(tmp_path, monkeypatch, capsys) -> None:
    web = tmp_path / "serve/cockpit/web"
    web.mkdir(parents=True)
    (web / "package-lock.json").write_text("{}\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    with patch("owlbear_tools.project._run", return_value=0), pytest.raises(SystemExit, match="0"):
        deps_sync()

    output = capsys.readouterr().out
    assert "versions and manifest ranges will not be updated" in output
    assert "remaining deps-status entries require a lock or manifest update" in output


def test_megalint_clean_preserves_current_and_removes_only_obsolete_images(
    monkeypatch: pytest.MonkeyPatch,
    capsys: object,
) -> None:
    image = MegaLinterImage(reference="registry.example/megalinter-main:v-current")
    listing = f"{image.repository}\t{image.tag}\tcurrent\t1GB\n{image.repository}\tv-old\tobsolete\t900MB\n"
    monkeypatch.setattr(sys, "argv", ["megalint-clean", "--yes"])
    completed = type("Result", (), {"returncode": 0, "stdout": listing, "stderr": ""})()

    with (
        patch("owlbear_tools.project.load_megalinter_image", return_value=image),
        patch("owlbear_tools.project.subprocess.run", return_value=completed),
        patch("owlbear_tools.project._run", return_value=0) as remove,
        pytest.raises(SystemExit, match="0"),
    ):
        megalint_clean()

    remove.assert_called_once_with(["docker", "image", "rm", "obsolete"])
    assert "v-old" in capsys.readouterr().out


def test_pds_sync_replaces_assets_only_after_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from owlbear_tools.project import pds_sync

    web = tmp_path / "serve/cockpit/web"
    target = web / "public/porsche-design-system"
    target.mkdir(parents=True)
    (target / "old.txt").write_text("old", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    def populate(_command: list[str], *, cwd: Path, env: dict[str, str], check: bool) -> object:  # noqa: ARG001
        output = Path(env["PDS_OUTPUT_DIR"])
        (output / "components").mkdir()
        (output / "components/new.js").write_text("new", encoding="utf-8")
        return type("Result", (), {"returncode": 0})()

    with patch("owlbear_tools.project.subprocess.run", side_effect=populate), pytest.raises(SystemExit, match="0"):
        pds_sync()

    assert not (target / "old.txt").exists()
    assert (target / "components/new.js").read_text(encoding="utf-8") == "new"


def test_pds_sync_preserves_assets_when_download_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from owlbear_tools.project import pds_sync

    web = tmp_path / "serve/cockpit/web"
    target = web / "public/porsche-design-system"
    target.mkdir(parents=True)
    (target / "old.txt").write_text("old", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    failed = type("Result", (), {"returncode": 1})()

    with patch("owlbear_tools.project.subprocess.run", return_value=failed), pytest.raises(SystemExit, match="1"):
        pds_sync()

    assert (target / "old.txt").read_text(encoding="utf-8") == "old"
