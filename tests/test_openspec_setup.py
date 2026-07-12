"""Tests for the OwlBear OpenSpec setup integration."""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path
from unittest.mock import call, patch

import yaml


_REPO_ROOT = Path(__file__).parent.parent
_SETUP_PATH = _REPO_ROOT / "setup" / "openspec.py"
_SPEC = importlib.util.spec_from_file_location("owlbear_openspec_setup", _SETUP_PATH)
assert _SPEC is not None
assert _SPEC.loader is not None
_SETUP = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_SETUP)


def test_cli_install_is_skipped_when_pinned_version_is_available() -> None:
    completed = subprocess.CompletedProcess(["openspec", "--version"], 0, stdout="1.6.0\n")

    with (
        patch.object(_SETUP.shutil, "which", side_effect=lambda command: f"/bin/{command}"),
        patch.object(_SETUP.subprocess, "run", return_value=completed) as run,
    ):
        executable = _SETUP._ensure_openspec_cli()

    assert executable == "/bin/openspec"
    run.assert_called_once_with(
        ["/bin/openspec", "--version"],
        check=True,
        capture_output=True,
        text=True,
    )


def test_cli_install_uses_pinned_npm_package_when_missing() -> None:
    commands = {"openspec": [None, "/bin/openspec"], "npm": ["/bin/npm"]}

    def which(command: str) -> str | None:
        return commands[command].pop(0)

    completed = subprocess.CompletedProcess(["openspec", "--version"], 0, stdout="1.6.0\n")
    with (
        patch.object(_SETUP.shutil, "which", side_effect=which),
        patch.object(_SETUP.subprocess, "run", side_effect=[None, completed]) as run,
    ):
        executable = _SETUP._ensure_openspec_cli()

    assert executable == "/bin/openspec"
    assert run.call_args_list == [
        call(["/bin/npm", "install", "--global", _SETUP.OPEN_SPEC_PACKAGE], check=True, env=_SETUP._openspec_env()),
        call(["/bin/openspec", "--version"], check=True, capture_output=True, text=True),
    ]


def test_install_configures_stock_schema_and_preserves_project_context(tmp_path: Path) -> None:
    config_path = tmp_path / "openspec" / "config.yaml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        "schema: custom\ncontext: existing context\nrules:\n  design:\n    - Existing project rule\n",
        encoding="utf-8",
    )
    legacy_schema = tmp_path / "openspec" / "schemas" / "owlbear"
    legacy_schema.mkdir(parents=True)
    (legacy_schema / "schema.yaml").write_text("name: owlbear\n", encoding="utf-8")

    _SETUP.install(tmp_path, initialize=False)

    config_text = config_path.read_text(encoding="utf-8")
    config = yaml.safe_load(config_text)
    assert config_text.startswith("---\n")
    assert "\n    - '[OwlBear]" in config_text
    assert max(map(len, config_text.splitlines())) <= 100
    assert config["schema"] == "spec-driven"
    assert config["context"].startswith("existing context\n\n")
    assert "shaper reads the complete native change package" in config["context"]
    assert config["rules"]["design"][0] == "Existing project rule"
    assert not legacy_schema.exists()
    assert not legacy_schema.parent.exists()
    assert not (tmp_path / ".github" / "skills" / "grill-me").exists()


def test_install_removes_speckit_tooling_without_removing_feature_specs(tmp_path: Path) -> None:
    specify_dir = tmp_path / ".specify"
    specify_dir.mkdir()
    (specify_dir / "feature.json").write_text("{}", encoding="utf-8")
    speckit_skill = tmp_path / ".github" / "skills" / "speckit-plan"
    speckit_skill.mkdir(parents=True)
    (speckit_skill / "SKILL.md").write_text("legacy", encoding="utf-8")
    openspec_skill = tmp_path / ".github" / "skills" / "openspec-propose"
    openspec_skill.mkdir(parents=True)
    (openspec_skill / "SKILL.md").write_text("stock", encoding="utf-8")
    feature_spec = tmp_path / "specs" / "keep.md"
    feature_spec.parent.mkdir()
    feature_spec.write_text("preserved", encoding="utf-8")

    _SETUP.install(tmp_path, initialize=False)

    assert not specify_dir.exists()
    assert not speckit_skill.exists()
    assert (openspec_skill / "SKILL.md").read_text(encoding="utf-8") == "stock"
    assert feature_spec.read_text(encoding="utf-8") == "preserved"


def test_rules_add_value_without_replacing_native_artifacts(tmp_path: Path) -> None:
    _SETUP.install(tmp_path, initialize=False)

    config_text = (tmp_path / "openspec" / "config.yaml").read_text(encoding="utf-8")
    config = yaml.safe_load(config_text)
    assert max(map(len, config_text.splitlines())) <= 100
    assert set(config["rules"]) == {"proposal", "specs", "design", "tasks"}
    assert any("Decision Register" in rule for rule in config["rules"]["proposal"])
    assert any("full Product Promise" in rule for rule in config["rules"]["proposal"])
    assert any("concrete behaviors" in rule for rule in config["rules"]["proposal"])
    assert any("explicit user agreement" in rule for rule in config["rules"]["proposal"])
    assert any("every active Product Promise outcome" in rule for rule in config["rules"]["specs"])
    assert "investment tier" not in config_text
    assert "First Useful Step" not in config_text
    assert any("independent adversarial review" in rule for rule in config["rules"]["design"])
    assert any("normal assembled proof boundary" in rule for rule in config["rules"]["design"])
    assert any("advisory input" in rule for rule in config["rules"]["tasks"])
    assert any("Do not add OwlBear-specific YAML" in rule for rule in config["rules"]["tasks"])


def test_install_is_idempotent_for_context_and_rules(tmp_path: Path) -> None:
    _SETUP.install(tmp_path, initialize=False)
    _SETUP.install(tmp_path, initialize=False)

    config = yaml.safe_load((tmp_path / "openspec" / "config.yaml").read_text(encoding="utf-8"))
    assert config["context"].count("shaper reads the complete native change package") == 1
    decision_rules = [rule for rule in config["rules"]["proposal"] if "Decision Register" in rule]
    assert len(decision_rules) == 1


def test_install_is_idempotent_for_gitignore(tmp_path: Path) -> None:
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text(
        ".env\n\n# --- OwlBear OpenSpec generated commands ---\n"
        ".github/skills/openspec-*/\n"
        ".github/prompts/opsx-*.prompt.md\n"
        ".github/skills/grill-me/\n",
        encoding="utf-8",
    )

    _SETUP.install(tmp_path, initialize=False)
    _SETUP.install(tmp_path, initialize=False)

    content = gitignore.read_text(encoding="utf-8")
    assert content.count("# --- OwlBear OpenSpec generated commands ---") == 1
    assert content.startswith(".env\n")
    assert ".github/skills/grill-me/" not in content
