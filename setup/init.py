"""OwlBear workspace initialiser — setup/init.py.

Usage (CLI):
    python ../owlbear/setup/init.py [--name NAME]

Run from the target project directory.  owlbear_dir is auto-detected from
the location of this script.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import os
import re
import shutil
import sys
import warnings
from contextlib import suppress
from pathlib import Path

from owlbear_delivery import (
    TargetAdapterRef,
    TargetAuthorityRegistry,
    TargetCutoverReadiness,
    TargetCutoverRequest,
    TargetCutoverSource,
    cut_over_target_runtime,
    inventory_legacy_source,
    target_authority_digest,
)

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
        ".github/copilot-instructions.md",
        ".editorconfig",
        ".gitattributes",
        ".markdownlint-cli2.jsonc",
        ".markdownlint.json",
        ".markdownlintignore",
    }
)

_OWLBEAR_GITIGNORE_MARKER = "# --- OwlBear managed paths ---"
_HOOKS_REL_PREFIX = ".owlbear/hooks/"
_TARGET_REQUEST_PATH = Path(".owlbear/target-cutover-request.json")
_TARGET_RECEIPT_PATH = Path(".owlbear/target-cutover.json")
_DELIVERY_CONFIG_PATH = Path(".owlbear/delivery/config.json")

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


def _build_replacements(owlbear_dir: Path, target_dir: Path) -> dict[str, str]:
    """Build the placeholder replacement dict for seed templates."""
    return {
        "owlbear_rel_path": Path(os.path.relpath(owlbear_dir, target_dir)).as_posix(),
        "owlbear_abs_path": str(owlbear_dir.resolve()),
        "target_abs_path": str(target_dir.resolve()),
    }


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


def _write_settings(src: Path, dest: Path, replacements: dict[str, str]) -> None:
    """Write .vscode/settings.json, merging with existing file if present (AC12)."""
    template = src.read_text(encoding="utf-8")
    template = _replace_placeholders(template, replacements)
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


def _write_mcp(src: Path, dest: Path, replacements: dict[str, str]) -> None:
    """Write .vscode/mcp.json, merging with existing file if present.

    Owlbear servers are added as defaults; existing user entries are preserved
    and win on key conflict (same logic as settings merge for non-Location
    keys).
    """
    template = src.read_text(encoding="utf-8")
    template = _replace_placeholders(template, replacements)
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
    dest.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


def _write_seed_file(src: Path, dest: Path, replacements: dict[str, str]) -> None:
    """Write a generic seed file with placeholder replacement when needed."""
    if src.suffix in (".json", ".yml"):
        content = src.read_text(encoding="utf-8")
        content = _replace_placeholders(content, replacements)
        dest.write_text(content, encoding="utf-8")
        return

    shutil.copy2(src, dest)


def _write_delivery_config(target_dir: Path) -> None:
    """Create the workspace-local Delivery policy once."""
    path = target_dir / _DELIVERY_CONFIG_PATH
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    content = {"schema_version": 1, "integration_target": "main"}
    path.write_text(json.dumps(content, indent=2) + "\n", encoding="utf-8")


def _target_code_revision(owlbear_dir: Path) -> str:
    """Identify the installed target runtime and agent distribution."""
    serve_root = owlbear_dir / "serve"
    package_sources = (
        tuple(path / "src" for path in sorted(serve_root.iterdir()) if path.is_dir()) if serve_root.exists() else ()
    )
    roots = (
        owlbear_dir / "seed",
        owlbear_dir / "setup",
        owlbear_dir / "share" / "agents",
        owlbear_dir / "share" / "instructions",
        owlbear_dir / "share" / "prompts",
        owlbear_dir / "share" / "skills",
        owlbear_dir / "serve" / "cockpit" / "dist",
        *package_sources,
    )
    files = [path for name in ("pyproject.toml", "uv.lock") if (path := owlbear_dir / name).is_file()]
    files.extend(path for root in roots if root.exists() for path in root.rglob("*") if path.is_file())
    digest = hashlib.sha256()
    for path in sorted(files):
        relative = path.relative_to(owlbear_dir).as_posix().encode()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        content = path.read_bytes()
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def _activate_fresh_target(target_dir: Path, owlbear_dir: Path) -> None:
    """Publish a receipt-authorized empty target runtime for a fresh workspace."""
    request_path = target_dir / _TARGET_REQUEST_PATH
    if (target_dir / _TARGET_RECEIPT_PATH).exists():
        return
    if (target_dir / ".owlbear/target").exists():
        message = "target store exists without its activation receipt"
        raise RuntimeError(message)

    if request_path.exists():
        request = TargetCutoverRequest.model_validate_json(request_path.read_bytes())
    else:
        source = target_dir / ".owlbear/bootstrap/target-runtime"
        source.mkdir(parents=True)
        revision = _target_code_revision(owlbear_dir)
        (source / "distribution-revision").write_text(revision + "\n", encoding="utf-8")
        source_digest = inventory_legacy_source(source, (), {}).source_digest
        request = TargetCutoverRequest(
            sources=(
                TargetCutoverSource(
                    source_path=".owlbear/bootstrap/target-runtime",
                    snapshot_name="bootstrap",
                    expected_source_digest=source_digest,
                ),
            ),
            snapshot_path=".owlbear/legacy/target-cutover",
            target_path=".owlbear/target",
            receipt_path=_TARGET_RECEIPT_PATH.as_posix(),
            adapter_refs=(TargetAdapterRef(relative_path=".owlbear/adapters/delivery", target="target"),),
            authorities=(),
            classifications=(),
            expected_authority_digest=target_authority_digest(()),
            actual_code_revision=revision,
            expected_code_revision=revision,
            readiness=TargetCutoverReadiness(),
            approval="ACTIVATE_TARGET_RUNTIME",
        )
        request_path.write_text(request.model_dump_json(indent=2) + "\n", encoding="utf-8")

    def smoke(workspace: Path, cutover_request: TargetCutoverRequest) -> None:
        authorities = TargetAuthorityRegistry(workspace / cutover_request.target_path).list_authorities()
        if authorities:
            message = "fresh target runtime contains unexpected authority"
            raise RuntimeError(message)

    cut_over_target_runtime(target_dir, request, smoke=smoke)


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

    prompt = f"Hook file '{dest}' differs from the OwlBear seed. Choose replace, skip, or cancel: "
    while True:
        choice = input(prompt).strip().lower()
        if choice in {"replace", "r"}:
            return True
        if choice in {"skip", "s"}:
            return False
        if choice in {"cancel", "c"}:
            msg = "Hook seeding cancelled by user."
            raise RuntimeError(msg)
        print("Enter replace, skip, or cancel.")


def _hook_diff(src: Path, dest: Path) -> str:
    """Return a short unified diff between src (seed) and dest (existing)."""
    max_diff_lines = 40

    try:
        seed_lines = src.read_text(encoding="utf-8").splitlines(keepends=True)
        existing_lines = dest.read_text(encoding="utf-8").splitlines(keepends=True)
    except OSError, UnicodeDecodeError:
        return ""
    diff_lines = list(
        difflib.unified_diff(
            existing_lines,
            seed_lines,
            fromfile=str(dest),
            tofile=f"seed/{src.name}",
            n=2,
        )
    )
    if len(diff_lines) > max_diff_lines:
        diff_lines = [*diff_lines[:max_diff_lines], "... (diff truncated)\n"]
    return "".join(diff_lines)


def create_mcp_config(target_dir: Path, owlbear_dir: Path) -> None:
    """Write .vscode/mcp.json, merging owlbear servers with existing entries.

    Writes five MCP server entries from the seed template:
            - owlbear-delivery (owlbear_delivery_mcp)
            - owlbear-knowledge (owlbear_knowledge_mcp)
            - owlbear-memory (owlbear_memory_mcp)
        - owlbear-browser (owlbear_browser_mcp)
      - microsoft/markitdown

    Standalone entry point for callers that only need the MCP config written.
    Delegates to ``_write_mcp``.

    Args:
        target_dir: Destination project directory.
        owlbear_dir: Root of the owlbear installation (contains ``seed/``).
    """
    mcp_dest = target_dir / ".vscode" / "mcp.json"
    mcp_src = owlbear_dir / "seed" / ".vscode" / "mcp.json"
    replacements = _build_replacements(owlbear_dir, target_dir)
    _write_mcp(mcp_src, mcp_dest, replacements)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def init(  # noqa: C901
    target_dir: Path,
    owlbear_dir: Path,
    *,
    replace_hooks: bool = False,
    interactive: bool | None = None,
) -> None:
    """Initialise an OwlBear workspace in *target_dir*.

    Walks the seed/ tree inside *owlbear_dir*, copies static files, and
    replaces ``{{placeholder}}`` tokens in ``.json`` / ``.yml`` templates.
    ``settings.json`` and ``mcp.json`` are deep-merged with existing files.
    Also receipt-activates an empty target authority store for fresh workspaces.
    Existing pre-cutover stores remain untouched until ``setup/finalize.py``
    activates them.

    Args:
        target_dir: Destination project directory.
        owlbear_dir: Root of the owlbear installation (contains ``seed/``).
        replace_hooks: Overwrite differing existing hook runtime files.
        interactive: Whether hook conflicts may prompt. Defaults to TTY detect.
    """
    seed_dir = owlbear_dir / "seed"
    replacements = _build_replacements(owlbear_dir, target_dir)
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
            _write_settings(src, dest, replacements)
            continue

        if rel_posix == ".vscode/mcp.json":
            _write_mcp(src, dest, replacements)
            continue

        if rel_posix == ".gitignore":
            _write_gitignore(src, dest)
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

        _write_seed_file(src, dest, replacements)

    _write_delivery_config(target_dir)
    ops_root = target_dir / ".owlbear"
    if not (ops_root / "kanban").exists():
        _activate_fresh_target(target_dir, owlbear_dir)


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
        init(_target, _owlbear, replace_hooks=args.replace_hooks)
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc
    print(f"OwlBear workspace initialised in '{_target.name}'.")
