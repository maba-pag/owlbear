"""OwlBear workspace initialiser — setup/init.py.

Usage (CLI):
    python ../owlbear/setup/init.py [--name NAME]

Run from the target project directory.  owlbear_dir is auto-detected from
the location of this script.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
import warnings
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_LOCATION_KEYS = frozenset(
    {
        "chat.agentFilesLocations",
        "chat.agentSkillsLocations",
        "chat.hookFilesLocations",
        "chat.instructionsFilesLocations",
        "chat.promptFilesLocations",
    }
)

# Keys whose values are dicts that should be union-merged (owlbear defaults
# first, user values win on conflict) rather than replaced wholesale.
_DICT_MERGE_KEYS = _LOCATION_KEYS | frozenset(
    {
        "chat.tools.edits.autoApprove",
        "chat.tools.terminal.autoApprove",
        "chat.tools.urls.autoApprove",
        "extensions.experimental.affinity",
        "files.exclude",
        "github.copilot.enable",
        "search.exclude",
    }
)

_SKIP_NAMES = frozenset({"scratch-pad.txt"})
_SKIP_IF_EXISTS_REL = frozenset(
    {
        ".editorconfig",
        ".gitattributes",
        ".markdownlint-cli2.jsonc",
        ".markdownlint.json",
        ".markdownlintignore",
        "owlbear-project.json",
    }
)

_OWLBEAR_GITIGNORE_MARKER = "# --- OwlBear managed paths ---"
_HOOKS_REL_PREFIX = ".owlbear/hooks/"

# Regex: match // line-comments outside of strings.  Handles the common JSONC
# patterns VS Code uses (trailing comments like `true, // old value`).  Does
# NOT attempt to handle every edge case — just enough for settings.json files.
_JSONC_LINE_COMMENT_RE = re.compile(r"(?<!:)//.*$", re.MULTILINE)


def _strip_jsonc_comments(text: str) -> str:
    """Strip ``//``-style line comments so stdlib ``json.loads`` can parse JSONC."""
    return _JSONC_LINE_COMMENT_RE.sub("", text)


def _merge_settings(owlbear: dict, existing: dict) -> dict:
    """Merge owlbear defaults with existing user settings.

    - Dict-valued keys (chat.*Locations, *.autoApprove, files.exclude, etc.):
      union of inner dicts; user value wins on conflict.
    - Language-scoped keys (e.g. ``[json]``, ``[yaml]``): same dict-union logic.
    - All other keys: owlbear value as default; existing user value overrides.
    """
    all_keys = set(owlbear) | set(existing)
    merged: dict = {}
    for key in all_keys:
        is_dict_key = key in _DICT_MERGE_KEYS or (key.startswith("[") and key.endswith("]"))
        if is_dict_key:
            owlbear_inner = owlbear.get(key, {})
            user_inner = existing.get(key, {})
            merged[key] = {**owlbear_inner, **user_inner}
        else:
            merged[key] = existing[key] if key in existing else owlbear[key]
    return merged


def _replace_placeholders(content: str, replacements: dict[str, str]) -> str:
    """Replace all {{key}} tokens in content with the corresponding values."""
    for key, value in replacements.items():
        content = content.replace("{{" + key + "}}", value)
    return content


def _write_gitignore(src: Path, dest: Path) -> None:
    """Write .gitignore, appending owlbear-managed section to existing file.

    If the destination file does not exist, copies the full seed .gitignore.
    If it exists but has no owlbear marker, appends the owlbear-managed section.
    If the marker is already present, does nothing (idempotent).
    """
    seed_content = src.read_text(encoding="utf-8")

    if not dest.exists():
        dest.write_text(seed_content, encoding="utf-8")
        return

    existing = dest.read_text(encoding="utf-8")
    if _OWLBEAR_GITIGNORE_MARKER in existing:
        return  # already has the owlbear section

    # Extract the owlbear-managed section from the seed
    marker_pos = seed_content.find(_OWLBEAR_GITIGNORE_MARKER)
    if marker_pos < 0:
        return  # seed has no marker — nothing to append
    owlbear_section = seed_content[marker_pos:]

    # Append with a blank line separator
    separator = "" if existing.endswith("\n") else "\n"
    dest.write_text(existing + separator + "\n" + owlbear_section, encoding="utf-8")


def _write_settings(src: Path, dest: Path, owlbear_path: str) -> None:
    """Write .vscode/settings.json, merging with existing file if present (AC12)."""
    template = src.read_text(encoding="utf-8")
    template = _replace_placeholders(template, {"owlbear_path": owlbear_path})
    owlbear_settings: dict = json.loads(template)

    existing: dict = {}
    if dest.exists():
        raw = dest.read_text(encoding="utf-8")
        try:
            existing = json.loads(_strip_jsonc_comments(raw))
        except json.JSONDecodeError:
            # Unparseable even after stripping comments — treat as empty but
            # warn so the user notices rather than silently losing settings.
            warnings.warn(
                f"Could not parse existing {dest} as JSON(C); owlbear settings will be written without merging.",
                stacklevel=2,
            )

    merged = _merge_settings(owlbear_settings, existing)
    dest.write_text(json.dumps(merged, indent=2), encoding="utf-8")


def _write_project_json(
    src: Path,
    dest: Path,
    owlbear_path: str,
    name: str,
) -> None:
    """Write owlbear-project.json with computed fields.  Skips if dest already exists."""
    if dest.exists():
        return
    template = src.read_text(encoding="utf-8")
    template = _replace_placeholders(template, {"name": name})
    data: dict = json.loads(template)
    data["owlbear_path"] = owlbear_path
    data["created_at"] = datetime.now(tz=UTC).isoformat()
    dest.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _write_mcp(src: Path, dest: Path, owlbear_path: str) -> None:
    """Write .vscode/mcp.json, merging with existing file if present.

    Owlbear servers are added as defaults; existing user entries are preserved
    and win on key conflict (same logic as settings merge for non-Location
    keys).
    """
    template = src.read_text(encoding="utf-8")
    template = _replace_placeholders(template, {"owlbear_path": owlbear_path})
    owlbear_mcp: dict = json.loads(template)

    existing: dict = {}
    if dest.exists():
        raw = dest.read_text(encoding="utf-8")
        with suppress(json.JSONDecodeError):
            existing = json.loads(_strip_jsonc_comments(raw))

    # Merge servers: owlbear defaults first, user entries override on conflict
    owlbear_servers = owlbear_mcp.get("servers", {})
    user_servers = existing.get("servers", {})
    merged_servers = {**owlbear_servers, **user_servers}

    result = {**owlbear_mcp, **existing, "servers": merged_servers}
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(result, indent=2), encoding="utf-8")


def _write_seed_file(src: Path, dest: Path, owlbear_path: str) -> None:
    """Write a generic seed file with placeholder replacement when needed."""
    if src.suffix in (".json", ".yml"):
        content = src.read_text(encoding="utf-8")
        content = _replace_placeholders(content, {"owlbear_path": owlbear_path})
        dest.write_text(content, encoding="utf-8")
        return

    shutil.copy2(src, dest)


def _hook_files_match(src: Path, dest: Path) -> bool:
    """Return True when the existing hook file already matches the seed file."""
    return dest.exists() and src.read_bytes() == dest.read_bytes()


def _is_interactive_session() -> bool:
    """Return True when both stdin and stdout are attached to a TTY."""
    return sys.stdin.isatty() and sys.stdout.isatty()


def _should_replace_hook_file(
    dest: Path,
    *,
    src: Path,
    replace_hooks: bool,
    interactive: bool,
) -> bool:
    """Decide whether a differing existing hook file should be overwritten."""
    if replace_hooks:
        return True

    if not interactive:
        warnings.warn(
            (
                f"Existing hook file differs and was left unchanged: {dest}. "
                "Re-run with replace_hooks=True or --replace-hooks to overwrite it."
            ),
            stacklevel=2,
        )
        return False

    diff = _hook_diff(src, dest)
    if diff:
        print(f"\nDiff for {dest} (seed -> existing):")
        print(diff)

    prompt = (
        f"Hook file '{dest}' differs from the OwlBear seed. "
        "Choose replace, skip, or cancel: "
    )
    while True:
        choice = input(prompt).strip().lower()
        if choice in {"replace", "r"}:
            return True
        if choice in {"skip", "s"}:
            return False
        if choice in {"cancel", "c"}:
            raise RuntimeError("Hook seeding cancelled by user.")
        print("Enter replace, skip, or cancel.")


def _hook_diff(src: Path, dest: Path) -> str:
    """Return a short unified diff between src (seed) and dest (existing)."""
    import difflib

    try:
        seed_lines = src.read_text(encoding="utf-8").splitlines(keepends=True)
        existing_lines = dest.read_text(encoding="utf-8").splitlines(keepends=True)
    except (OSError, UnicodeDecodeError):
        return ""
    diff_lines = list(
        difflib.unified_diff(
            seed_lines,
            existing_lines,
            fromfile=f"seed/{src.name}",
            tofile=str(dest),
            n=2,
        )
    )
    if len(diff_lines) > 40:
        diff_lines = diff_lines[:40] + ["... (diff truncated)\n"]
    return "".join(diff_lines)


def create_mcp_config(target_dir: Path, owlbear_dir: Path) -> None:
    """Write .vscode/mcp.json, merging owlbear servers with existing entries.

    Writes five MCP server entries from the seed template:
      - owlbear-kanban (owlbear_mcp_kanban)
      - owlbear-knowledge (owlbear_mcp_knowledge)
      - owlbear-memory (owlbear_mcp_memory)
      - ddgs (DuckDuckGo search)
      - microsoft/markitdown

    Standalone entry point for callers that only need the MCP config written.
    Delegates to ``_write_mcp``.

    Args:
        target_dir: Destination project directory.
        owlbear_dir: Root of the owlbear installation (contains ``seed/``).
    """
    mcp_dest = target_dir / ".vscode" / "mcp.json"
    mcp_src = owlbear_dir / "seed" / ".vscode" / "mcp.json"
    owlbear_path = Path(os.path.relpath(owlbear_dir, target_dir)).as_posix()
    _write_mcp(mcp_src, mcp_dest, owlbear_path)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def init(
    target_dir: Path,
    owlbear_dir: Path,
    *,
    name: str | None = None,
    replace_hooks: bool = False,
    interactive: bool | None = None,
) -> None:
    """Initialise an OwlBear workspace in *target_dir*.

    Walks the seed/ tree inside *owlbear_dir*, copies static files, and
    replaces ``{{placeholder}}`` tokens in ``.json`` / ``.yml`` templates.
    Computed fields (owlbear_path, created_at) are generated here rather than
    stored as template placeholders.

    Idempotent: ``owlbear-project.json`` is skipped when it already exists.
    ``settings.json`` and ``mcp.json`` are deep-merged with existing files.

    Args:
        target_dir: Destination project directory.
        owlbear_dir: Root of the owlbear installation (contains ``seed/``).
        name: Project name.  Defaults to *target_dir.name*.
        replace_hooks: Overwrite differing existing hook runtime files.
        interactive: Whether hook conflicts may prompt. Defaults to TTY detect.
    """
    seed_dir = owlbear_dir / "seed"
    owlbear_path = Path(os.path.relpath(owlbear_dir, target_dir)).as_posix()
    resolved_name = name if name is not None else target_dir.name
    interactive_mode = _is_interactive_session() if interactive is None else interactive

    for src in sorted(seed_dir.rglob("*")):
        if src.is_dir():
            continue

        rel = src.relative_to(seed_dir)
        rel_posix = rel.as_posix()

        if src.name in _SKIP_NAMES:
            continue

        dest = target_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)

        # --- per-file dispatch ---

        if rel_posix == ".vscode/settings.json":
            _write_settings(src, dest, owlbear_path)
            continue

        if rel_posix == ".vscode/mcp.json":
            _write_mcp(src, dest, owlbear_path)
            continue

        if rel_posix == ".gitignore":
            _write_gitignore(src, dest)
            continue

        if rel_posix == "owlbear-project.json":
            _write_project_json(src, dest, owlbear_path, resolved_name)
            continue

        if rel_posix in _SKIP_IF_EXISTS_REL and dest.exists():
            continue

        if rel_posix.startswith(_HOOKS_REL_PREFIX) and dest.exists():
            if _hook_files_match(src, dest):
                continue
            if not _should_replace_hook_file(
                dest,
                src=src,
                replace_hooks=replace_hooks,
                interactive=interactive_mode,
            ):
                continue

        _write_seed_file(src, dest, owlbear_path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":  # pragma: no cover
    import argparse

    parser = argparse.ArgumentParser(description="Initialise an OwlBear workspace in the current directory.")
    parser.add_argument("--name", default=None, help="Project name (default: directory name)")
    parser.add_argument(
        "--replace-hooks",
        action="store_true",
        help="Overwrite differing existing .owlbear/hooks files instead of skipping or prompting.",
    )
    args = parser.parse_args()

    _target = Path.cwd()
    _owlbear = Path(__file__).resolve().parent.parent
    try:
        init(_target, _owlbear, name=args.name, replace_hooks=args.replace_hooks)
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc
    print(f"OwlBear workspace initialised in '{_target.name}'.")
