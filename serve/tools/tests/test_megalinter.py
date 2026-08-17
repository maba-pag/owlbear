"""Behavioral tests for MegaLinter configuration and commands."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from owlbear_tools.megalinter import (
    DockerRuntimeApp,
    FixMode,
    MegaLinterImage,
    _wait_for_docker,
    load_megalinter_image,
    megalint,
    megalint_clean,
    run_megalint,
)

_TEST_IMAGE = MegaLinterImage(reference="registry.example/megalinter-main:v-current")


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


def test_run_megalint_uses_ready_docker_without_starting_runtime() -> None:
    with (
        patch("owlbear_tools.megalinter.load_megalinter_image", return_value=_TEST_IMAGE),
        patch("owlbear_tools.megalinter._find_docker_binary", return_value="docker"),
        patch("owlbear_tools.megalinter._docker_is_ready", return_value=True),
        patch("owlbear_tools.megalinter._start_docker_app") as start_app,
        patch("owlbear_tools.megalinter._call", return_value=0) as call,
    ):
        assert run_megalint(FixMode.NONE) == 0

    start_app.assert_not_called()
    assert call.call_args.args[0][:2] == ["docker", "run"]


def test_run_megalint_starts_runtime_and_leaves_it_running_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = DockerRuntimeApp(name="OrbStack", process_name="OrbStack")
    monkeypatch.delenv("OWLBEAR_DOCKER_STOP_RUNTIME", raising=False)

    with (
        patch("owlbear_tools.megalinter.sys.platform", "darwin"),
        patch("owlbear_tools.megalinter.load_megalinter_image", return_value=_TEST_IMAGE),
        patch("owlbear_tools.megalinter._find_docker_binary", return_value=None),
        patch("owlbear_tools.megalinter._installed_docker_apps", return_value=(app,)),
        patch("owlbear_tools.megalinter._app_is_running", return_value=False),
        patch("owlbear_tools.megalinter._start_docker_app") as start_app,
        patch("owlbear_tools.megalinter._wait_for_docker", return_value="docker"),
        patch("owlbear_tools.megalinter._stop_docker_app") as stop_app,
        patch("owlbear_tools.megalinter._call", return_value=0),
    ):
        assert run_megalint(FixMode.NONE) == 0

    start_app.assert_called_once_with(app)
    stop_app.assert_not_called()


def test_run_megalint_stops_runtime_started_by_invocation_when_requested(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = DockerRuntimeApp(name="OrbStack", process_name="OrbStack")
    monkeypatch.setenv("OWLBEAR_DOCKER_STOP_RUNTIME", "1")

    with (
        patch("owlbear_tools.megalinter.sys.platform", "darwin"),
        patch("owlbear_tools.megalinter.load_megalinter_image", return_value=_TEST_IMAGE),
        patch("owlbear_tools.megalinter._find_docker_binary", return_value=None),
        patch("owlbear_tools.megalinter._installed_docker_apps", return_value=(app,)),
        patch("owlbear_tools.megalinter._app_is_running", return_value=False),
        patch("owlbear_tools.megalinter._start_docker_app"),
        patch("owlbear_tools.megalinter._wait_for_docker", return_value="docker"),
        patch("owlbear_tools.megalinter._stop_docker_app") as stop_app,
        patch("owlbear_tools.megalinter._call", return_value=0),
    ):
        assert run_megalint(FixMode.NONE) == 0

    stop_app.assert_called_once_with(app)


def test_run_megalint_does_not_stop_a_preexisting_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    app = DockerRuntimeApp(name="OrbStack", process_name="OrbStack")
    monkeypatch.setenv("OWLBEAR_DOCKER_STOP_RUNTIME", "1")

    with (
        patch("owlbear_tools.megalinter.sys.platform", "darwin"),
        patch("owlbear_tools.megalinter.load_megalinter_image", return_value=_TEST_IMAGE),
        patch("owlbear_tools.megalinter._find_docker_binary", return_value="docker"),
        patch("owlbear_tools.megalinter._docker_is_ready", return_value=False),
        patch("owlbear_tools.megalinter._installed_docker_apps", return_value=(app,)),
        patch("owlbear_tools.megalinter._app_is_running", return_value=True),
        patch("owlbear_tools.megalinter._wait_for_docker", return_value="docker"),
        patch("owlbear_tools.megalinter._stop_docker_app") as stop_app,
        patch("owlbear_tools.megalinter._call", return_value=0),
    ):
        assert run_megalint(FixMode.NONE) == 0

    stop_app.assert_not_called()


def test_run_megalint_cleans_started_runtime_after_readiness_timeout() -> None:
    app = DockerRuntimeApp(name="OrbStack", process_name="OrbStack")

    with (
        patch("owlbear_tools.megalinter.sys.platform", "darwin"),
        patch("owlbear_tools.megalinter.load_megalinter_image", return_value=_TEST_IMAGE),
        patch("owlbear_tools.megalinter._find_docker_binary", return_value=None),
        patch("owlbear_tools.megalinter._installed_docker_apps", return_value=(app,)),
        patch("owlbear_tools.megalinter._app_is_running", return_value=False),
        patch("owlbear_tools.megalinter._start_docker_app"),
        patch("owlbear_tools.megalinter._wait_for_docker", return_value=None),
        patch("owlbear_tools.megalinter._stop_docker_app") as stop_app,
        pytest.raises(RuntimeError, match="did not make Docker ready"),
    ):
        run_megalint(FixMode.NONE)

    stop_app.assert_called_once_with(app)


def test_run_megalint_reports_cleanup_failure(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    app = DockerRuntimeApp(name="OrbStack", process_name="OrbStack")
    monkeypatch.setenv("OWLBEAR_DOCKER_STOP_RUNTIME", "yes")

    with (
        patch("owlbear_tools.megalinter.load_megalinter_image", return_value=_TEST_IMAGE),
        patch("owlbear_tools.megalinter._acquire_docker_runtime", return_value=("docker", app)),
        patch("owlbear_tools.megalinter._stop_docker_app", side_effect=RuntimeError("quit failed")),
        patch("owlbear_tools.megalinter._call", return_value=0),
    ):
        assert run_megalint(FixMode.NONE) == 0

    assert "Warning: Docker runtime cleanup failed: quit failed" in capsys.readouterr().err


def test_run_megalint_rejects_unavailable_runtime_on_non_macos() -> None:
    with (
        patch("owlbear_tools.megalinter.sys.platform", "linux"),
        patch("owlbear_tools.megalinter.load_megalinter_image", return_value=_TEST_IMAGE),
        patch("owlbear_tools.megalinter._find_docker_binary", return_value=None),
        patch("owlbear_tools.megalinter._installed_docker_apps") as installed_apps,
        pytest.raises(RuntimeError, match="unavailable on this platform"),
    ):
        run_megalint(FixMode.NONE)

    installed_apps.assert_not_called()


def test_wait_for_docker_retries_until_engine_is_ready() -> None:
    with (
        patch("owlbear_tools.megalinter._find_docker_binary", return_value="docker"),
        patch("owlbear_tools.megalinter._docker_is_ready", side_effect=[False, True]) as is_ready,
        patch("owlbear_tools.megalinter.time.monotonic", side_effect=[0.0, 1.0]),
        patch("owlbear_tools.megalinter.time.sleep"),
    ):
        assert _wait_for_docker() == "docker"

    assert is_ready.call_count == 2


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
    all_prefixed_flavor_match = re.search(flavor_pattern, "MEGALINTER_FLAVOR: all-cupcake\n")
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
    assert all_prefixed_flavor_match is not None
    assert all_prefixed_flavor_match.group("flavor") == "all-cupcake"
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


def test_megalint_clean_preserves_current_and_removes_only_obsolete_images(
    monkeypatch: pytest.MonkeyPatch,
    capsys: object,
) -> None:
    image = MegaLinterImage(reference="registry.example/megalinter-main:v-current")
    stale_base = "ghcr.io/oxsecurity/megalinter"
    listing = (
        f"{image.repository}\t{image.tag}\tcurrent\t1GB\n"
        f"{image.repository}\tv-old\tobsolete\t900MB\n"
        f"{stale_base}\t{image.tag}\tbase\t900MB\n"
    )
    monkeypatch.setattr(sys, "argv", ["megalint-clean", "--yes"])
    completed = type("Result", (), {"returncode": 0, "stdout": listing, "stderr": ""})()

    with (
        patch("owlbear_tools.megalinter.load_megalinter_image", return_value=image),
        patch("owlbear_tools.megalinter.subprocess.run", return_value=completed) as list_images,
        patch("owlbear_tools.megalinter._run", return_value=0) as remove,
        pytest.raises(SystemExit, match="0"),
    ):
        megalint_clean()

    remove.assert_called_once_with(["docker", "image", "rm", "obsolete", "base"])
    assert "reference=ghcr.io/oxsecurity/megalinter*:*" in list_images.call_args.args[0]
    assert "v-old" in capsys.readouterr().out


def test_megalint_clean_reports_invalid_configuration(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(sys, "argv", ["megalint-clean"])

    with (
        patch("owlbear_tools.megalinter._require_development"),
        patch("owlbear_tools.megalinter.load_megalinter_image", side_effect=ValueError("invalid image")),
        pytest.raises(SystemExit, match="2"),
    ):
        megalint_clean()

    assert "Error: invalid image" in capsys.readouterr().err


def test_megalint_help_is_available_outside_development_checkout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["megalint", "--help"])

    with pytest.raises(SystemExit, match="0"):
        megalint()
