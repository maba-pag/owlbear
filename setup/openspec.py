"""Install the pinned OwlBear OpenSpec workflow into a target repository."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path

import yaml

OPEN_SPEC_PACKAGE = "@fission-ai/openspec@1.6.0"
OPEN_SPEC_VERSION = OPEN_SPEC_PACKAGE.rsplit("@", maxsplit=1)[1]
_GITIGNORE_MARKER = "# --- OwlBear OpenSpec generated commands ---"
_GITIGNORE_BLOCK = """# --- OwlBear OpenSpec generated commands ---
.github/skills/openspec-*/
.github/prompts/opsx-*.prompt.md
"""
_REPO_ROOT = Path(__file__).resolve().parent.parent
_CONFIG_PATH = _REPO_ROOT / "seed" / "openspec" / "config.yaml"
_CONTEXT_START = "# --- OwlBear OpenSpec context ---"
_CONTEXT_END = "# --- End OwlBear OpenSpec context ---"
_RULE_PREFIX = "[OwlBear] "


class _IndentedSafeDumper(yaml.SafeDumper):
    def increase_indent(
        self,
        flow: bool = False,  # noqa: FBT001, FBT002
        indentless: bool = False,  # noqa: ARG002, FBT001, FBT002
    ) -> None:
        return super().increase_indent(flow, indentless=False)


def _openspec_env() -> dict[str, str]:
    return {**os.environ, "OPENSPEC_TELEMETRY": "0"}


def _has_pinned_version(executable: str) -> bool:
    try:
        result = subprocess.run(  # noqa: S603
            [executable, "--version"],
            check=True,
            capture_output=True,
            text=True,
        )
    except OSError, subprocess.CalledProcessError:
        return False
    return result.stdout.strip() == OPEN_SPEC_VERSION


def _ensure_openspec_cli() -> str:
    executable = shutil.which("openspec")
    if executable is not None and _has_pinned_version(executable):
        return executable

    npm = shutil.which("npm")
    if npm is None:
        msg = f"npm is required to install {OPEN_SPEC_PACKAGE}"
        raise RuntimeError(msg)
    subprocess.run(  # noqa: S603
        [npm, "install", "--global", OPEN_SPEC_PACKAGE],
        check=True,
        env=_openspec_env(),
    )
    executable = shutil.which("openspec")
    if executable is None or not _has_pinned_version(executable):
        msg = f"installed {OPEN_SPEC_PACKAGE}, but the openspec executable is unavailable or has the wrong version"
        raise RuntimeError(msg)
    return executable


def _run_openspec_init(target: Path) -> None:
    openspec = _ensure_openspec_cli()
    subprocess.run(  # noqa: S603
        [
            openspec,
            "init",
            str(target),
            "--tools",
            "github-copilot",
            "--force",
        ],
        check=True,
        env=_openspec_env(),
    )


def _remove_legacy_schema(target: Path) -> None:
    schemas_dir = target / "openspec" / "schemas"
    shutil.rmtree(schemas_dir / "owlbear", ignore_errors=True)
    if schemas_dir.exists() and not any(schemas_dir.iterdir()):
        schemas_dir.rmdir()


def _without_managed_context(context: str, managed_context: str) -> str:
    start = context.find(_CONTEXT_START)
    end = context.find(_CONTEXT_END)
    if start != -1 and end >= start:
        end += len(_CONTEXT_END)
        return f"{context[:start]}{context[end:]}".strip()
    legacy_context = "\n".join(
        line for line in managed_context.splitlines() if line not in {_CONTEXT_START, _CONTEXT_END}
    )
    return context.replace(legacy_context, "").strip()


def _configure_schema(target: Path) -> None:
    config_path = target / "openspec" / "config.yaml"
    config: dict[str, object] = {}
    if config_path.exists():
        loaded = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            config = loaded
    defaults = yaml.safe_load(_CONFIG_PATH.read_text(encoding="utf-8"))
    config["schema"] = defaults["schema"]
    default_context = defaults["context"]
    existing_context = config.get("context")
    preserved_context = (
        _without_managed_context(existing_context, default_context) if isinstance(existing_context, str) else ""
    )
    config["context"] = f"{preserved_context}\n\n{default_context}".strip()

    existing_rules = config.get("rules")
    rules = dict(existing_rules) if isinstance(existing_rules, dict) else {}
    for artifact, additions in defaults["rules"].items():
        current = rules.get(artifact)
        existing = list(current) if isinstance(current, list) else []
        legacy_additions = {rule.removeprefix(_RULE_PREFIX) for rule in additions}
        preserved = [
            rule
            for rule in existing
            if isinstance(rule, str) and not rule.startswith(_RULE_PREFIX) and rule not in legacy_additions
        ]
        rules[artifact] = [*preserved, *additions]
    config["rules"] = rules
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        yaml.dump(
            config,
            Dumper=_IndentedSafeDumper,
            explicit_start=True,
            sort_keys=False,
            width=80,
        ),
        encoding="utf-8",
    )


def _remove_legacy_grill_skill(target: Path) -> None:
    shutil.rmtree(target / ".github" / "skills" / "grill-me", ignore_errors=True)


def _remove_legacy_speckit(target: Path) -> None:
    shutil.rmtree(target / ".specify", ignore_errors=True)
    for pattern in (".github/skills/speckit-*", ".github/prompts/speckit-*"):
        for path in target.glob(pattern):
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()


def _update_gitignore(target: Path) -> None:
    gitignore = target / ".gitignore"
    existing = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
    if _GITIGNORE_MARKER in existing:
        migrated = existing.replace(".github/skills/grill-me/\n", "")
        if migrated != existing:
            gitignore.write_text(migrated, encoding="utf-8")
        return
    separator = "" if not existing or existing.endswith("\n") else "\n"
    prefix = "" if not existing else "\n"
    gitignore.write_text(f"{existing}{separator}{prefix}{_GITIGNORE_BLOCK}", encoding="utf-8")


def install(target: Path, *, initialize: bool = True) -> None:
    """Install or refresh the OwlBear OpenSpec integration in ``target``."""
    resolved_target = target.resolve()
    if initialize:
        _run_openspec_init(resolved_target)
    _remove_legacy_schema(resolved_target)
    _configure_schema(resolved_target)
    _remove_legacy_grill_skill(resolved_target)
    _remove_legacy_speckit(resolved_target)
    _update_gitignore(resolved_target)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", nargs="?", type=Path, default=Path.cwd())
    parser.add_argument("--skip-init", action="store_true", help="Install local assets without running OpenSpec init")
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    args = _build_parser().parse_args(argv)
    install(args.target, initialize=not args.skip_init)
    print(f"Configured stock OpenSpec workflow in {args.target.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
