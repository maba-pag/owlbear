"""OwlBear workspace initialiser — setup/init.py.

Usage (CLI):
    python ../owlbear/setup/init.py [--replace-hooks] [--refresh-configs | --check-configs | --uninstall]
        [--yes] [--dry-run]

Run from the target project directory.  owlbear_dir is auto-detected from
the location of this script.
"""

from __future__ import annotations

import difflib
import hashlib
import importlib.util
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import warnings
from collections import Counter
from contextlib import suppress
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from types import ModuleType


def _load_workspace_git() -> ModuleType:
    """Load the sibling Git-exclude helper whether run as a script or loaded by path."""
    spec = importlib.util.spec_from_file_location(
        "owlbear_setup_workspace_git", Path(__file__).with_name("workspace_git.py")
    )
    if spec is None or spec.loader is None:
        message = "setup/workspace_git.py is missing next to setup/init.py"
        raise ImportError(message)
    module = importlib.util.module_from_spec(spec)
    caching, sys.dont_write_bytecode = sys.dont_write_bytecode, True  # no write in the runtime before consent
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = caching
    return module


_workspace_git = _load_workspace_git()

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
        ".yamllint.yml",
    }
)
_REFRESHABLE_CONFIG_REL = frozenset(
    {
        ".editorconfig",
        ".markdownlint-cli2.jsonc",
        ".markdownlint.json",
        ".markdownlintignore",
        ".yamllint.yml",
    }
)

_MERGED_REL = frozenset({".vscode/settings.json", ".vscode/mcp.json"})
_ACTION_LABELS = {"create": "create", "merge": "merge into existing", "replace": "replace"}
_TRACKED_NOTE = " (tracked: your change will show as modified)"

# Older installs wrote this section into the project's .gitignore; uninstall still removes it.
_OWLBEAR_GITIGNORE_MARKER = "# --- OwlBear managed paths ---"
_HOOKS_REL_PREFIX = ".owlbear/hooks/"
_INSTALL_MANIFEST_PATH = Path(".owlbear/install-manifest.json")
_INSTALL_MANIFEST_SCHEMA_VERSION = 1
_DEFAULT_PROFILE_ASSOCIATION = "__default__profile__"
_COPILOT_REASONING_SETTINGS = {
    "gpt-6-luna": "max",
    "gpt-6-sol": "high",
    "claude-opus-5.5": "medium",
}

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
        if _is_mergeable_settings_key(key):
            owlbear_inner = owlbear.get(key, {})
            user_inner = existing.get(key, {})
            merged[key] = {**owlbear_inner, **user_inner}
        else:
            merged[key] = existing[key] if key in existing else owlbear[key]
    return merged


def _settings_claims(seed: dict, existing: dict) -> dict:
    """Return the settings values that installation added to *existing*."""
    claims: dict = {"keys": {}, "nested": {}}
    for key, seed_value in seed.items():
        if _is_mergeable_settings_key(key) and isinstance(seed_value, dict):
            existing_value = existing.get(key)
            existing_inner = existing_value if isinstance(existing_value, dict) else {}
            added_values = {
                nested_key: _json_value_digest(nested_value)
                for nested_key, nested_value in seed_value.items()
                if nested_key not in existing_inner
            }
            if added_values:
                claims["nested"][key] = {
                    "parent_created": key not in existing,
                    "values": added_values,
                }
        elif key not in existing:
            claims["keys"][key] = _json_value_digest(seed_value)
    return claims


def _replace_placeholders(content: str, replacements: dict[str, str]) -> str:
    """Replace all {{key}} tokens in content with the corresponding values."""
    for key, value in replacements.items():
        content = content.replace("{{" + key + "}}", value)
    return content


def _build_replacements(owlbear_dir: Path, target_dir: Path) -> dict[str, str]:
    """Build the placeholder replacement dict for seed templates."""
    return {
        "owlbear_rel_path": Path(os.path.relpath(owlbear_dir, target_dir)).as_posix(),
        "owlbear_abs_path": str(owlbear_dir.absolute()),
        "target_abs_path": str(target_dir.resolve()),
    }


def _is_mergeable_settings_key(key: str) -> bool:
    """Return whether settings installation merges values below *key*."""
    return key in _DICT_MERGE_KEYS or (key.startswith("[") and key.endswith("]"))


def _sha256_bytes(value: bytes) -> str:
    """Return the SHA-256 digest for one byte sequence."""
    return hashlib.sha256(value).hexdigest()


def _json_value_digest(value: object) -> str:
    """Return a stable digest for one JSON value."""
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return _sha256_bytes(encoded)


def _new_install_manifest() -> dict[str, object]:
    """Return an empty install receipt."""
    return {
        "schema_version": _INSTALL_MANIFEST_SCHEMA_VERSION,
        "files": {},
        "created_directories": [],
    }


def _load_install_manifest(path: Path) -> tuple[dict[str, object] | None, bytes | None]:
    """Read a valid install receipt and its original bytes."""
    try:
        raw = path.read_bytes()
        manifest = json.loads(raw)
    except OSError, UnicodeDecodeError, json.JSONDecodeError:
        return None, None
    if (
        not isinstance(manifest, dict)
        or manifest.get("schema_version") != _INSTALL_MANIFEST_SCHEMA_VERSION
        or not isinstance(manifest.get("files"), dict)
        or not isinstance(manifest.get("created_directories"), list)
    ):
        return None, None
    return manifest, raw


def _write_install_manifest(path: Path, manifest: dict[str, object]) -> None:
    """Write an install receipt atomically."""
    content = json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            delete=False,
        ) as temporary:
            temporary.write(content)
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_path = Path(temporary.name)
        temporary_path.replace(path)
    finally:
        if temporary_path is not None:
            with suppress(FileNotFoundError):
                temporary_path.unlink()


def _ensure_parent_dirs(path: Path, target_dir: Path, manifest: dict[str, object]) -> None:
    """Create missing destination parents and retain exactly those directories."""
    missing: list[Path] = []
    current = path
    while current != target_dir and not current.exists():
        missing.append(current)
        current = current.parent
    for directory in reversed(missing):
        directory.mkdir()
        relative = directory.relative_to(target_dir).as_posix()
        created = manifest.setdefault("created_directories", [])
        if isinstance(created, list) and relative not in created:
            created.append(relative)


def _merge_manifest_record(
    manifest: dict[str, object],
    relative: str,
    record: dict[str, object],
) -> None:
    """Merge one install action into the durable receipt."""
    files = manifest.setdefault("files", {})
    if not isinstance(files, dict):
        files = {}
        manifest["files"] = files
    previous = files.get(relative)
    if isinstance(previous, dict):
        record["created"] = bool(previous.get("created", False))
        for key in ("claims", "added_lines"):
            old_value = previous.get(key)
            new_value = record.get(key)
            if isinstance(old_value, dict) and isinstance(new_value, dict):
                merged = {**old_value, **new_value}
                if key == "claims":
                    merged = _merge_claims(old_value, new_value)
                record[key] = merged
            elif isinstance(old_value, list) and isinstance(new_value, list):
                record[key] = [*old_value, *new_value]
    files[relative] = record


def _merge_claims(old: dict, new: dict) -> dict:
    """Merge settings or MCP ownership claims without losing prior claims."""
    merged: dict = {**old, **new}
    old_keys = old.get("keys")
    new_keys = new.get("keys")
    if isinstance(old_keys, dict) and isinstance(new_keys, dict):
        merged["keys"] = {**old_keys, **new_keys}
    old_nested = old.get("nested")
    new_nested = new.get("nested")
    if isinstance(old_nested, dict) and isinstance(new_nested, dict):
        nested = {**old_nested}
        for key, value in new_nested.items():
            if isinstance(nested.get(key), dict) and isinstance(value, dict):
                existing = nested[key]
                combined = {**existing, **value}
                if isinstance(existing.get("values"), dict) and isinstance(value.get("values"), dict):
                    combined["values"] = {**existing["values"], **value["values"]}
                nested[key] = combined
            else:
                nested[key] = value
        merged["nested"] = nested
    return merged


def _write_settings(
    src: Path,
    dest: Path,
    replacements: dict[str, str],
    *,
    manifest: dict[str, object] | None = None,
) -> None:
    """Write .vscode/settings.json, merging with existing file if present (AC12)."""
    template = src.read_text(encoding="utf-8")
    json_replacements = {key: json.dumps(value)[1:-1] for key, value in replacements.items()}
    template = _replace_placeholders(template, json_replacements)
    owlbear_settings: dict = json.loads(template)

    existed_before = dest.exists()
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
    if manifest is not None:
        _merge_manifest_record(
            manifest,
            ".vscode/settings.json",
            {
                "kind": "settings",
                "created": not existed_before,
                "installed_sha256": _sha256_bytes(dest.read_bytes()),
                "claims": _settings_claims(owlbear_settings, existing),
            },
        )


def _write_mcp(
    src: Path,
    dest: Path,
    replacements: dict[str, str],
    *,
    manifest: dict[str, object] | None = None,
) -> None:
    """Write .vscode/mcp.json, merging with existing file if present.

    Owlbear servers are added as defaults; existing user entries are preserved
    and win on key conflict (same logic as settings merge for non-Location
    keys).
    """
    template = src.read_text(encoding="utf-8")
    template = _replace_placeholders(template, replacements)
    owlbear_mcp: dict = json.loads(template)

    existed_before = dest.exists()
    existing: dict = {}
    if dest.exists():
        raw = dest.read_text(encoding="utf-8")
        try:
            existing = json.loads(_strip_jsonc_comments(raw))
        except json.JSONDecodeError:
            warnings.warn(
                f"Could not parse existing {dest} as JSON(C); owlbear MCP servers will be written without merging.",
                stacklevel=2,
            )

    # Merge servers: owlbear defaults first, user entries override on conflict
    owlbear_servers = owlbear_mcp.get("servers", {})
    user_servers = existing.get("servers", {})
    merged_servers = {**owlbear_servers, **user_servers}

    result = {**owlbear_mcp, **existing, "servers": merged_servers}
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    if manifest is not None:
        _merge_manifest_record(
            manifest,
            ".vscode/mcp.json",
            {
                "kind": "mcp",
                "created": not existed_before,
                "installed_sha256": _sha256_bytes(dest.read_bytes()),
                "claims": {
                    name: _json_value_digest(server)
                    for name, server in owlbear_servers.items()
                    if name not in user_servers
                },
                "servers_created": "servers" not in existing,
            },
        )


def _write_seed_file(src: Path, dest: Path, replacements: dict[str, str]) -> None:
    """Write a generic seed file with placeholder replacement when needed."""
    if src.suffix in (".json", ".yml"):
        content = src.read_text(encoding="utf-8")
        content = _replace_placeholders(content, replacements)
        dest.write_text(content, encoding="utf-8")
        return

    shutil.copy2(src, dest)


def _render_seed_file(src: Path, replacements: dict[str, str]) -> bytes:
    """Return the bytes that *src* would write to a consumer project."""
    if src.suffix in (".json", ".yml"):
        content = src.read_text(encoding="utf-8")
        return _replace_placeholders(content, replacements).encode("utf-8")
    return src.read_bytes()


def _record_seed_install(
    manifest: dict[str, object],
    relative: str,
    dest: Path,
    *,
    created: bool,
) -> None:
    """Record one copied seed surface after installation."""
    record: dict[str, object] = {
        "kind": "file",
        "created": created,
        "installed_sha256": _sha256_bytes(dest.read_bytes()),
    }
    _merge_manifest_record(manifest, relative, record)


class UninstallResult:
    """Describe one completed or cancelled uninstall operation."""

    __slots__ = ("actions", "completed")

    def __init__(self, *, completed: bool, actions: tuple[str, ...]) -> None:
        self.completed = completed
        self.actions = actions

    def __bool__(self) -> bool:
        """Retain natural truthiness for callers checking completion."""
        return self.completed


class UninstallError(RuntimeError):
    """Report an uninstall failure together with actions already performed."""

    def __init__(self, message: str, actions: tuple[str, ...]) -> None:
        super().__init__(message)
        self.actions = actions


class _UninstallOptions:
    """Carry uninstall reporting and mutation options through helper calls."""

    __slots__ = ("actions", "created_directories", "dry_run", "manifest", "target_dir", "target_root")

    def __init__(
        self,
        target_dir: Path,
        *,
        target_root: Path,
        dry_run: bool = False,
        manifest: dict[str, object] | None = None,
    ) -> None:
        self.target_dir = target_dir
        self.target_root = target_root
        self.dry_run = dry_run
        self.manifest = manifest
        created = manifest.get("created_directories", []) if manifest is not None else []
        self.created_directories = {value for value in created if isinstance(value, str)}
        self.actions: list[str] = []


def _safe_uninstall_destination(path: Path, options: _UninstallOptions) -> bool:
    """Return whether a destination resolves below the consumer root."""
    try:
        resolved = path.resolve(strict=False)
    except OSError:
        _record_uninstall_action(options, "preserve (unresolvable path)", path)
        return False
    if not resolved.is_relative_to(options.target_root):
        _record_uninstall_action(options, "preserve (outside target)", path)
        return False
    return True


def _remove_created_parent_dirs(path: Path, options: _UninstallOptions) -> None:
    """Remove only empty directories recorded as created during installation."""
    parent = path.parent
    while parent != options.target_dir:
        try:
            relative = parent.relative_to(options.target_dir).as_posix()
        except ValueError:
            return
        if relative not in options.created_directories:
            return
        if parent.is_symlink() or not parent.is_dir():
            return
        try:
            if not parent.resolve().is_relative_to(options.target_root):
                return
            parent.rmdir()
        except OSError:
            return
        _record_uninstall_action(options, "removed directory", parent)
        parent = parent.parent


def _record_uninstall_action(
    options: _UninstallOptions,
    action: str,
    path: Path,
) -> None:
    """Append one relative uninstall action to the result."""
    options.actions.append(f"{action}: {path.relative_to(options.target_dir).as_posix()}")


def _manifest_record(manifest: dict[str, object] | None, relative: str) -> dict | None:
    """Return one validated file record from an optional install receipt."""
    if manifest is None:
        return None
    files = manifest.get("files")
    if not isinstance(files, dict):
        return None
    record = files.get(relative)
    return record if isinstance(record, dict) else None


def _manifest_file_is_unchanged(dest: Path, record: dict) -> bool:
    """Return whether a recorded file still has its installed bytes."""
    expected = record.get("installed_sha256")
    if not isinstance(expected, str) or not dest.is_file() or dest.is_symlink():
        return False
    try:
        return _sha256_bytes(dest.read_bytes()) == expected
    except OSError:
        return False


def _read_json_mapping(path: Path, description: str) -> dict | None:
    """Read one JSON or JSONC object, warning instead of mutating malformed input."""
    try:
        raw = path.read_text(encoding="utf-8")
        value = json.loads(_strip_jsonc_comments(raw))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        warnings.warn(f"Could not inspect existing {description} during uninstall: {path}: {exc}", stacklevel=2)
        return None
    if not isinstance(value, dict):
        warnings.warn(f"Existing {description} must contain a JSON object; left unchanged: {path}", stacklevel=2)
        return None
    return value


def _remove_manifest_file(dest: Path, record: dict | None, options: _UninstallOptions) -> None:
    """Remove one receipt-owned file when its installed bytes are unchanged."""
    if not dest.exists():
        return
    if not _safe_uninstall_destination(dest, options):
        return
    if record is None or record.get("created") is not True:
        _record_uninstall_action(options, "preserve", dest)
        return
    if not _manifest_file_is_unchanged(dest, record):
        _record_uninstall_action(options, "preserve", dest)
        return
    if dest.is_symlink() or not dest.is_file():
        _record_uninstall_action(options, "preserve", dest)
        return
    if options.dry_run:
        _record_uninstall_action(options, "would remove", dest)
        return
    try:
        dest.unlink()
    except OSError as exc:
        message = f"Could not remove seeded file during uninstall: {dest}"
        raise RuntimeError(message) from exc
    _remove_created_parent_dirs(dest, options)
    _record_uninstall_action(options, "removed", dest)


def _remove_settings_key_claims(current: dict, claims: dict) -> bool:
    """Remove top-level receipt-claimed settings whose values still match."""
    changed = False
    keys = claims.get("keys", {})
    if not isinstance(keys, dict):
        return False
    for key, digest in keys.items():
        if key in current and _json_value_digest(current[key]) == digest:
            del current[key]
            changed = True
    return changed


def _remove_settings_nested_claims(current: dict, claims: dict) -> bool:
    """Remove nested receipt-claimed settings whose values still match."""
    changed = False
    nested = claims.get("nested", {})
    if not isinstance(nested, dict):
        return False
    for key, claim in nested.items():
        if not isinstance(claim, dict) or not isinstance(current.get(key), dict):
            continue
        current_inner = current[key]
        values = claim.get("values", {})
        if not isinstance(values, dict):
            continue
        for nested_key, digest in values.items():
            if nested_key in current_inner and _json_value_digest(current_inner[nested_key]) == digest:
                del current_inner[nested_key]
                changed = True
        if not current_inner and claim.get("parent_created") is True:
            del current[key]
    return changed


def _remove_settings_claims(current: dict, claims: dict) -> bool:
    """Remove receipt-claimed settings whose values still match."""
    changed = _remove_settings_key_claims(current, claims)
    return _remove_settings_nested_claims(current, claims) or changed


def _json_text_with_newline(value: dict, original: str) -> str:
    """Serialize JSON using the installed file's trailing-newline convention."""
    content = json.dumps(value, ensure_ascii=False, indent=2)
    if original.endswith("\n"):
        content += "\n"
    return content


def _write_uninstalled_json(
    path: Path,
    value: dict,
    options: _UninstallOptions,
    *,
    remove_when_empty: bool,
    original: str,
) -> None:
    """Write a changed merged JSON object or remove it when no values remain."""
    if options.dry_run:
        action = "would remove" if not value and remove_when_empty else "would update"
        _record_uninstall_action(options, action, path)
        return
    try:
        if not value and remove_when_empty:
            path.unlink()
        else:
            path.write_text(_json_text_with_newline(value, original), encoding="utf-8")
    except OSError as exc:
        message = f"Could not update {path} during uninstall"
        raise RuntimeError(message) from exc
    if not value and remove_when_empty:
        _remove_created_parent_dirs(path, options)
    _record_uninstall_action(options, "removed" if not value and remove_when_empty else "updated", path)


def _remove_settings_seed_values(
    dest: Path,
    record: dict | None,
    options: _UninstallOptions,
) -> None:
    """Remove receipt-claimed settings without touching later file edits."""
    if not dest.exists():
        return
    if not _safe_uninstall_destination(dest, options):
        return
    if record is None or not _manifest_file_is_unchanged(dest, record):
        _record_uninstall_action(options, "preserve", dest)
        return
    if dest.is_symlink() or not dest.is_file():
        _record_uninstall_action(options, "preserve", dest)
        return
    original = dest.read_text(encoding="utf-8")
    current = _read_json_mapping(dest, "VS Code settings")
    if current is None:
        return
    claims = record.get("claims")
    if not isinstance(claims, dict) or not _remove_settings_claims(current, claims):
        _record_uninstall_action(options, "preserve", dest)
        return
    _write_uninstalled_json(
        dest,
        current,
        options,
        remove_when_empty=record.get("created") is True,
        original=original,
    )


def _remove_mcp_seed_servers(
    dest: Path,
    record: dict | None,
    options: _UninstallOptions,
) -> None:
    """Remove receipt-claimed MCP servers without touching later file edits."""
    if not dest.exists():
        return
    if not _safe_uninstall_destination(dest, options):
        return
    if record is None or not _manifest_file_is_unchanged(dest, record) or dest.is_symlink() or not dest.is_file():
        _record_uninstall_action(options, "preserve", dest)
        return
    original = dest.read_text(encoding="utf-8")
    current = _read_json_mapping(dest, "MCP configuration")
    if current is None:
        return
    current_servers = current.get("servers")
    claims = record.get("claims")
    if not isinstance(current_servers, dict) or not isinstance(claims, dict):
        _record_uninstall_action(options, "preserve", dest)
        return

    if not _remove_mcp_claimed_servers(current_servers, claims):
        _record_uninstall_action(options, "preserve", dest)
        return
    if not current_servers and record.get("servers_created") is True:
        del current["servers"]
    _write_uninstalled_json(
        dest,
        current,
        options,
        remove_when_empty=record.get("created") is True,
        original=original,
    )


def _remove_mcp_claimed_servers(current_servers: dict, claims: dict) -> bool:
    """Remove MCP servers whose receipt digests still match."""
    changed = False
    for name, digest in claims.items():
        if name in current_servers and _json_value_digest(current_servers[name]) == digest:
            del current_servers[name]
            changed = True
    return changed


def _remove_created_gitignore(dest: Path, record: dict, options: _UninstallOptions) -> bool:
    """Remove a newly created unchanged gitignore and report whether handled."""
    if record.get("created") is not True or not _manifest_file_is_unchanged(dest, record):
        return False
    if options.dry_run:
        _record_uninstall_action(options, "would remove", dest)
        return True
    try:
        dest.unlink()
    except OSError as exc:
        message = f"Could not remove gitignore during uninstall: {dest}"
        raise RuntimeError(message) from exc
    _remove_created_parent_dirs(dest, options)
    _record_uninstall_action(options, "removed", dest)
    return True


def _recorded_gitignore_update(current: str, record: dict) -> str | None:
    """Return a gitignore with recorded additions removed, if it changed."""
    added_lines = record.get("added_lines")
    if _OWLBEAR_GITIGNORE_MARKER not in current or not isinstance(added_lines, list) or not added_lines:
        return None
    prefix, _, suffix = current.partition(_OWLBEAR_GITIGNORE_MARKER)
    counts = Counter(line for line in added_lines if isinstance(line, str))
    remaining: list[str] = []
    for line in suffix.splitlines(keepends=True):
        stripped = line.strip()
        if stripped and counts[stripped]:
            counts[stripped] -= 1
            continue
        remaining.append(line)
    if record.get("marker_added") is True:
        prefix_text = prefix.rstrip("\r\n")
        remaining_text = "".join(remaining).lstrip("\r\n")
        if prefix_text and remaining_text:
            updated = f"{prefix_text}\n{remaining_text}"
        elif prefix_text:
            updated = f"{prefix_text}\n"
        else:
            updated = remaining_text
    else:
        updated = prefix + _OWLBEAR_GITIGNORE_MARKER + "".join(remaining)
    return None if updated == current else updated


def _write_gitignore_update(
    dest: Path,
    updated: str,
    record: dict,
    options: _UninstallOptions,
) -> None:
    """Apply or preview one recorded gitignore cleanup."""
    if record.get("created") is True and not updated.strip():
        if options.dry_run:
            _record_uninstall_action(options, "would remove", dest)
            return
        try:
            dest.unlink()
        except OSError as exc:
            message = f"Could not remove gitignore during uninstall: {dest}"
            raise RuntimeError(message) from exc
        _remove_created_parent_dirs(dest, options)
        _record_uninstall_action(options, "removed", dest)
        return
    if options.dry_run:
        _record_uninstall_action(options, "would update", dest)
        return
    try:
        dest.write_text(updated, encoding="utf-8")
    except OSError as exc:
        message = f"Could not update gitignore during uninstall: {dest}"
        raise RuntimeError(message) from exc
    _record_uninstall_action(options, "updated", dest)


def _remove_managed_gitignore(
    dest: Path,
    record: dict | None,
    options: _UninstallOptions,
) -> None:
    """Remove only gitignore lines recorded as installation additions."""
    if not dest.exists():
        return
    if not _safe_uninstall_destination(dest, options):
        return
    if record is None or dest.is_symlink() or not dest.is_file():
        _record_uninstall_action(options, "preserve", dest)
        return
    try:
        current = dest.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        warnings.warn(f"Could not inspect gitignore during uninstall: {dest}: {exc}", stacklevel=2)
        return

    if _remove_created_gitignore(dest, record, options):
        return

    updated = _recorded_gitignore_update(current, record)
    if updated is None:
        _record_uninstall_action(options, "preserve", dest)
        return
    _write_gitignore_update(dest, updated, record, options)


def _confirm_uninstall(target_dir: Path) -> bool:
    """Ask for confirmation before an interactive uninstall."""
    print(f"This will remove unchanged receipt-owned OwlBear files from '{target_dir.resolve()}'.")
    print("Pre-existing consumer editor and lint configuration files will be preserved.")
    print("Customized files, project Delivery state, and other user files will be preserved.")
    try:
        answer = input("Continue with OwlBear uninstall? [y/N] ").strip().lower()
    except EOFError:
        return False
    return answer in {"y", "yes"}


def config_drift(target_dir: Path, owlbear_dir: Path) -> dict[str, str]:
    """Return missing or customized refreshable consumer configs."""
    seed_dir = owlbear_dir / "seed"
    replacements = _build_replacements(owlbear_dir, target_dir)
    drift: dict[str, str] = {}
    for rel_posix in sorted(_REFRESHABLE_CONFIG_REL):
        src = seed_dir / rel_posix
        dest = target_dir / rel_posix
        if not dest.exists():
            drift[rel_posix] = "missing"
        elif dest.read_bytes() != _render_seed_file(src, replacements):
            drift[rel_posix] = "different"
    return drift


def _hook_files_match(src: Path, dest: Path) -> bool:
    """Return True when the existing hook file already matches the seed file."""
    return dest.exists() and src.read_bytes() == dest.read_bytes()


def _is_interactive_session() -> bool:
    """Return True when both stdin and stdout are attached to a TTY."""
    return sys.stdin.isatty() and sys.stdout.isatty()


class _CopilotProfileTarget:
    """Identify one VS Code profile settings file."""

    __slots__ = ("associated", "profile_id", "settings_path", "user_data_root")

    def __init__(
        self,
        user_data_root: Path,
        settings_path: Path,
        profile_id: str | None,
        *,
        associated: bool,
    ) -> None:
        self.user_data_root = user_data_root
        self.settings_path = settings_path
        self.profile_id = profile_id
        self.associated = associated


def _unique_paths(paths: list[Path]) -> list[Path]:
    """Return paths in order without duplicate resolved locations."""
    unique: list[Path] = []
    seen: set[Path] = set()
    for path in paths:
        resolved = path.expanduser().resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique.append(resolved)
    return unique


def _vscode_app_from_command(command: str) -> Path | None:
    """Extract a VS Code application path from one macOS process command."""
    for app_name in ("Visual Studio Code - Insiders.app", "Visual Studio Code.app"):
        marker = f"/{app_name}/"
        marker_start = command.find(marker)
        if marker_start >= 0:
            return Path(command[: marker_start + 1] + app_name)
    return None


def _user_data_roots_for_vscode_app(app_path: Path) -> list[Path]:
    """Return standard or portable user-data roots for a VS Code app."""
    is_insiders = "Insiders" in app_path.name
    standard_name = "Code - Insiders" if is_insiders else "Code"
    portable_name = "code-insiders-portable-data" if is_insiders else "code-portable-data"
    portable_root = app_path.parent / portable_name / "user-data"
    if portable_root.is_dir():
        return [portable_root]
    return [Path.home() / "Library" / "Application Support" / standard_name]


def _user_data_paths_from_tokens(tokens: list[str]) -> list[Path]:
    """Extract existing user-data paths from one tokenized process command."""
    paths: list[Path] = []
    for index, argument in enumerate(tokens):
        if argument == "--user-data-dir" and index + 1 < len(tokens):
            path_parts = tokens[index + 1 :]
        elif argument.startswith("--user-data-dir="):
            path_parts = [argument.partition("=")[2], *tokens[index + 1 :]]
        else:
            continue
        stop = next(
            (position for position, part in enumerate(path_parts) if part.startswith("--")),
            len(path_parts),
        )
        path_parts = path_parts[:stop]
        if path_parts:
            paths.append(Path(" ".join(path_parts)))
    return paths


def _running_macos_vscode_user_data_roots() -> list[Path]:
    """Discover user-data roots from running VS Code processes when possible."""
    if sys.platform != "darwin":
        return []
    try:
        completed = subprocess.run(
            ["ps", "-axo", "command="],  # noqa: S607
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return []
    if completed.returncode != 0:
        return []

    roots: list[Path] = []
    for command in completed.stdout.splitlines():
        try:
            tokens = shlex.split(command)
        except ValueError:
            continue
        app_path = _vscode_app_from_command(command)
        if app_path is None:
            continue
        roots.extend(_user_data_paths_from_tokens(tokens))
        roots.extend(_user_data_roots_for_vscode_app(app_path))
    return [root for root in _unique_paths(roots) if root.is_dir()]


def _macos_vscode_user_data_roots() -> list[Path]:
    """Return discoverable stable, Insiders, and portable macOS user-data roots."""
    if sys.platform != "darwin":
        return []

    support_dir = Path.home() / "Library" / "Application Support"
    roots = [*_running_macos_vscode_user_data_roots()]
    roots.extend((support_dir / "Code", support_dir / "Code - Insiders"))
    for app_parent in (Path("/Applications"), Path.home() / "Applications"):
        for app_name, portable_name in (
            ("Visual Studio Code.app", "code-portable-data"),
            ("Visual Studio Code - Insiders.app", "code-insiders-portable-data"),
        ):
            portable_root = app_parent / portable_name / "user-data"
            if (app_parent / app_name).is_dir() and portable_root.is_dir():
                roots.append(portable_root)
    return _unique_paths(roots)


def _workspace_profile_association(
    user_data_root: Path,
    target_dir: Path,
) -> tuple[bool, str | None] | None:
    """Read a workspace profile association from VS Code's local state."""
    state_path = user_data_root / "User" / "globalStorage" / "storage.json"
    if not state_path.is_file():
        return None
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except OSError, json.JSONDecodeError:
        return None
    association: tuple[bool, str | None] | None = None
    if isinstance(state, dict):
        profile_associations = state.get("profileAssociations")
        if isinstance(profile_associations, dict):
            workspaces = profile_associations.get("workspaces")
            if isinstance(workspaces, dict):
                workspace_uri = target_dir.resolve().as_uri()
                profile_id = workspaces.get(workspace_uri)
                if profile_id == _DEFAULT_PROFILE_ASSOCIATION:
                    association = True, None
                elif isinstance(profile_id, str) and profile_id:
                    association = True, profile_id
    return association


def _make_copilot_profile_target(
    user_data_root: Path,
    profile_id: str | None,
    *,
    associated: bool,
) -> _CopilotProfileTarget:
    """Build and validate a profile settings target."""
    user_dir = user_data_root / "User"
    if profile_id is None:
        settings_path = user_dir / "chatLanguageModels.json"
    else:
        profile_dir = user_dir / "profiles" / profile_id
        if not profile_dir.is_dir():
            message = f"VS Code profile association points to missing profile '{profile_id}' under {profile_dir}."
            raise RuntimeError(message)
        settings_path = profile_dir / "chatLanguageModels.json"
    return _CopilotProfileTarget(user_data_root, settings_path, profile_id, associated=associated)


def _find_associated_copilot_profile(
    roots: list[Path],
    target_dir: Path,
) -> _CopilotProfileTarget | None:
    """Find the unique profile associated with the target project."""
    matches: list[_CopilotProfileTarget] = []
    for root in roots:
        association = _workspace_profile_association(root, target_dir)
        if association is None:
            continue
        _, profile_id = association
        matches.append(_make_copilot_profile_target(root, profile_id, associated=True))
    if len(matches) > 1:
        locations = ", ".join(str(match.settings_path) for match in matches)
        message = f"Multiple VS Code profile associations were found for this project: {locations}"
        raise RuntimeError(message)
    return matches[0] if matches else None


def _select_default_copilot_profile(
    roots: list[Path],
    target_dir: Path,
) -> _CopilotProfileTarget:
    """Select one safe default-profile target when no association exists."""
    del target_dir
    active_roots = _running_macos_vscode_user_data_roots()
    if len(active_roots) == 1:
        return _make_copilot_profile_target(active_roots[0], None, associated=False)
    if len(active_roots) > 1:
        locations = ", ".join(str(root) for root in active_roots)
        message = f"Multiple running VS Code user-data roots were found: {locations}"
        raise RuntimeError(message)

    existing_roots = [root for root in roots if (root / "User").is_dir()]
    if len(existing_roots) == 1:
        return _make_copilot_profile_target(existing_roots[0], None, associated=False)
    if len(existing_roots) > 1:
        locations = ", ".join(str(root) for root in existing_roots)
        message = f"Multiple VS Code user-data roots were found: {locations}"
        raise RuntimeError(message)

    standard_root = Path.home() / "Library" / "Application Support" / "Code"
    return _make_copilot_profile_target(standard_root, None, associated=False)


def _profile_display_path(path: Path) -> str:
    """Render a profile path compactly for an interactive prompt."""
    try:
        return f"~/{path.relative_to(Path.home()).as_posix()}"
    except ValueError:
        return str(path)


def _profile_display_name(target: _CopilotProfileTarget) -> str:
    """Return the stable profile label available to the setup script."""
    if target.profile_id is None:
        return "Default Profile"
    return f"profile ID {target.profile_id}"


def _profile_json_indent(raw: str | None) -> int | str:
    """Preserve the existing profile file's common indentation when possible."""
    if raw is not None:
        for line in raw.splitlines()[1:]:
            stripped = line.lstrip()
            if stripped:
                return line[: len(line) - len(stripped)]
    return 2


def _update_copilot_reasoning_settings(path: Path) -> tuple[object, bool, str | None]:
    """Return updated profile JSON, whether it changed, and its original text."""
    raw = path.read_text(encoding="utf-8") if path.exists() else None
    data: object = json.loads(raw) if raw is not None else []
    if not isinstance(data, list):
        message = f"Copilot profile settings must be a JSON array: {path}"
        raise TypeError(message)

    copilot_entries = [entry for entry in data if isinstance(entry, dict) and entry.get("vendor") == "copilot"]
    if len(copilot_entries) > 1:
        message = f"Multiple Copilot entries were found in profile settings: {path}"
        raise RuntimeError(message)
    if not copilot_entries:
        copilot_entry: dict[str, object] = {
            "name": "GitHub Copilot Chat",
            "vendor": "copilot",
            "settings": {},
        }
        data.append(copilot_entry)
    else:
        copilot_entry = copilot_entries[0]

    settings = copilot_entry.get("settings")
    if settings is None:
        settings = {}
        copilot_entry["settings"] = settings
    if not isinstance(settings, dict):
        message = f"Copilot profile settings must contain an object-valued 'settings': {path}"
        raise TypeError(message)

    changed = False
    for model_id, reasoning_effort in _COPILOT_REASONING_SETTINGS.items():
        model_settings = settings.get(model_id)
        if model_settings is None:
            model_settings = {}
            settings[model_id] = model_settings
        if not isinstance(model_settings, dict):
            message = f"Model settings for '{model_id}' must be an object: {path}"
            raise TypeError(message)
        if model_settings.get("reasoningEffort") != reasoning_effort:
            model_settings["reasoningEffort"] = reasoning_effort
            changed = True
    return data, changed, raw


def _write_copilot_profile_atomically(
    path: Path,
    data: object,
    *,
    original_text: str | None,
) -> None:
    """Write profile JSON atomically while retaining its existing file mode."""
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(data, ensure_ascii=False, indent=_profile_json_indent(original_text)) + "\n"
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            delete=False,
        ) as temporary:
            temporary.write(content)
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_path = Path(temporary.name)
        if path.exists():
            temporary_path.chmod(path.stat().st_mode & 0o777)
        temporary_path.replace(path)
    finally:
        if temporary_path is not None:
            with suppress(FileNotFoundError):
                temporary_path.unlink()


def _confirm_copilot_profile_update(target: _CopilotProfileTarget) -> bool:
    """Ask for confirmation before changing one profile's reasoning settings."""
    association_text = (
        "associated with this project"
        if target.associated
        else "selected as the default profile because no profile is associated with this project"
    )
    print(
        "\nOwlBear model thinking settings (Luna: max, Sol: high, Opus 5: medium) "
        f"will be written to the VS Code profile {association_text}:"
    )
    print(f"  Profile: {_profile_display_name(target)}")
    print(f"  File: {_profile_display_path(target.settings_path)}")
    print("These settings are required for OwlBear's minimum performance and cost-efficiency standard.")
    print("No other profile settings will be changed.")
    if not target.associated:
        print(
            "To target a named profile instead, use 'Profiles: Switch Profile' in VS Code for this project, "
            "then run setup/init.py again."
        )
    try:
        answer = input("Implement these settings? [Y/n] ").strip().lower()
    except EOFError:
        return False
    return answer not in {"n", "no"}


def _print_profile_association_help(target_dir: Path) -> None:
    """Explain how to associate a different VS Code profile with the project."""
    print(
        f"\nNo VS Code profile was changed for {target_dir.resolve()}. "
        "To configure a named profile, open this project in VS Code, switch to the intended "
        "profile with 'Profiles: Switch Profile', then run setup/init.py again."
    )


def _configure_copilot_profile(target_dir: Path, *, interactive: bool) -> None:
    """Configure the associated or default macOS VS Code Copilot profile."""
    if sys.platform != "darwin":
        return
    if not interactive:
        warnings.warn(
            "VS Code Copilot profile settings were not changed because setup is non-interactive.",
            stacklevel=2,
        )
        return

    roots = _macos_vscode_user_data_roots()
    try:
        target = _find_associated_copilot_profile(roots, target_dir)
        if target is None:
            target = _select_default_copilot_profile(roots, target_dir)
    except RuntimeError as exc:
        warnings.warn(f"Could not determine a unique VS Code profile target: {exc}", stacklevel=2)
        _print_profile_association_help(target_dir)
        return

    try:
        data, changed, original_text = _update_copilot_reasoning_settings(target.settings_path)
    except (OSError, RuntimeError, json.JSONDecodeError) as exc:
        warnings.warn(f"Could not inspect VS Code Copilot profile settings: {exc}", stacklevel=2)
        return
    if not changed:
        print(f"VS Code profile {_profile_display_name(target)} already has the required Copilot settings.")
    elif not _confirm_copilot_profile_update(target):
        _print_profile_association_help(target_dir)
    else:
        try:
            _write_copilot_profile_atomically(target.settings_path, data, original_text=original_text)
        except OSError as exc:
            warnings.warn(f"Could not write VS Code Copilot profile settings: {exc}", stacklevel=2)
        else:
            print(f"Updated VS Code profile settings: {_profile_display_path(target.settings_path)}")


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

    Writes four MCP server entries from the seed template:
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


class _PlannedFile(NamedTuple):
    """One seed file and what installing it does to the target."""

    src: Path
    relative: str
    dest: Path
    action: str


class _InstallPlan(NamedTuple):
    """Everything one setup run would create, merge or replace, computed before writing."""

    files: list[_PlannedFile]
    directories: list[str]
    tracked: set[str]
    manifest_exists: bool
    exclude_path: Path | None
    exclude_lines: list[str]


def _planned_action(
    src: Path,
    relative: str,
    dest: Path,
    replacements: dict[str, str],
    *,
    refresh_configs: bool,
) -> str | None:
    """Return create, merge, replace, replace-hook or unchanged; None when setup leaves the file."""
    if not dest.exists():
        return "create"
    if relative in _MERGED_REL:
        return "merge"
    if relative in _SKIP_IF_EXISTS_REL and not (refresh_configs and relative in _REFRESHABLE_CONFIG_REL):
        return None
    if relative.startswith(_HOOKS_REL_PREFIX):
        return None if _hook_files_match(src, dest) else "replace-hook"
    return "unchanged" if dest.read_bytes() == _render_seed_file(src, replacements) else "replace"


def _plan_seed_files(
    seed_dir: Path,
    target_dir: Path,
    replacements: dict[str, str],
    *,
    refresh_configs: bool,
) -> list[_PlannedFile]:
    """Walk the seed tree in install order and plan each file."""
    plan: list[_PlannedFile] = []
    for src in sorted(seed_dir.rglob("*")):
        if src.is_dir() or src.name in _SKIP_NAMES:
            continue
        relative = src.relative_to(seed_dir).as_posix()
        dest = target_dir / relative
        action = _planned_action(src, relative, dest, replacements, refresh_configs=refresh_configs)
        if action is not None:
            plan.append(_PlannedFile(src, relative, dest, action))
    return plan


def _missing_directories(paths: list[Path], target_dir: Path) -> list[str]:
    """Return the target-relative directories that writing *paths* would create."""
    missing: set[str] = set()
    for path in paths:
        current = path.parent
        while current != target_dir and not current.exists():
            missing.add(current.relative_to(target_dir).as_posix())
            current = current.parent
    return sorted(missing)


def _created_paths(manifest: dict[str, object]) -> tuple[set[str], set[str]]:
    """Return the directories and files the install receipt records as created by setup."""
    created_directories = manifest.get("created_directories")
    directories = {value for value in created_directories or [] if isinstance(value, str)}
    records = manifest.get("files")
    files = {
        relative
        for relative, record in (records.items() if isinstance(records, dict) else ())
        if isinstance(record, dict) and record.get("created") is True
    }
    files.add(_INSTALL_MANIFEST_PATH.as_posix())
    return directories, files


def _exclude_lines_for(target_dir: Path, prefix: str, directories: set[str], files: set[str]) -> list[str]:
    """Return the exclude block for created paths, leaving out files Git already tracks."""
    tracked = _workspace_git.tracked_paths(target_dir, sorted(files))
    return _workspace_git.exclude_lines(prefix, directories, files - tracked)


def _build_install_plan(
    seed_dir: Path,
    target_dir: Path,
    replacements: dict[str, str],
    manifest: dict[str, object],
    *,
    refresh_configs: bool,
) -> _InstallPlan:
    """Compute every path setup would write and how it would be hidden from Git."""
    files = _plan_seed_files(seed_dir, target_dir, replacements, refresh_configs=refresh_configs)
    manifest_dest = target_dir / _INSTALL_MANIFEST_PATH
    directories = _missing_directories([*(item.dest for item in files), manifest_dest], target_dir)
    existing = [item.relative for item in files if item.action not in {"create", "unchanged"}]
    if manifest_dest.exists():
        existing.append(_INSTALL_MANIFEST_PATH.as_posix())
    tracked = _workspace_git.tracked_paths(target_dir, existing)
    location = _workspace_git.locate(target_dir)
    exclude_lines: list[str] = []
    if location is not None:
        created_directories, created_files = _created_paths(manifest)
        created_files |= {item.relative for item in files if item.action == "create"}
        exclude_lines = _exclude_lines_for(
            target_dir, location[1], created_directories | set(directories), created_files
        )
    exclude_path = location[0] if location is not None else None
    return _InstallPlan(files, directories, tracked, manifest_dest.exists(), exclude_path, exclude_lines)


def _hook_label(*, replace_hooks: bool, interactive: bool) -> str:
    """Describe what setup does with an existing hook file that differs from the seed."""
    if replace_hooks:
        return "replace"
    if interactive:
        return "replace if you choose (differs from seed)"
    return "keep (differs from seed; --replace-hooks replaces it)"


def _inventory_lines(target_dir: Path, plan: _InstallPlan, *, replace_hooks: bool, interactive: bool) -> list[str]:
    """Render the paths setup would create, merge or replace, and what it hides from Git."""
    lines = [f"OwlBear agent workspace setup for {target_dir.resolve()}:"]
    lines.extend(f"  create directory: {directory}/" for directory in plan.directories)
    entries = [(item.relative, item.action) for item in plan.files if item.action != "unchanged"]
    entries.append((_INSTALL_MANIFEST_PATH.as_posix(), "replace" if plan.manifest_exists else "create"))
    for relative, action in entries:
        label = _ACTION_LABELS.get(action) or _hook_label(replace_hooks=replace_hooks, interactive=interactive)
        note = _TRACKED_NOTE if relative in plan.tracked and not label.startswith("keep") else ""
        lines.append(f"  {label}: {relative}{note}")
    if plan.exclude_path is None:
        lines.append("Not a Git repository: setup hides nothing from Git.")
    else:
        lines.append(f"Hidden from Git in {plan.exclude_path} (one OwlBear block):")
        lines.extend(f"  {line}" for line in plan.exclude_lines)
    return lines


def _confirm_install(target_dir: Path, *, yes: bool, dry_run: bool, interactive: bool) -> bool:
    """Return whether setup may write, asking once in an interactive session."""
    if dry_run:
        print("OwlBear setup dry-run; no files changed.")
        return False
    if yes:
        return True
    if not interactive:
        message = "Refusing non-interactive setup without consent; rerun with --yes or use --dry-run."
        raise RuntimeError(message)
    try:
        answer = input(f"Write the OwlBear agent workspace into {target_dir.resolve()}? [y/N] ").strip().lower()
    except EOFError:
        answer = ""
    if answer in {"y", "yes"}:
        return True
    print("OwlBear setup cancelled; nothing was written.")
    return False


def _install_seed_files(  # noqa: PLR0913 - the plan, its target and receipt, and the two hook-conflict choices
    files: list[_PlannedFile],
    target_dir: Path,
    replacements: dict[str, str],
    manifest: dict[str, object],
    *,
    replace_hooks: bool,
    interactive: bool,
) -> None:
    """Write each planned seed file and record it in the install receipt."""
    for item in files:
        _ensure_parent_dirs(item.dest.parent, target_dir, manifest)
        if item.relative == ".vscode/settings.json":
            _write_settings(item.src, item.dest, replacements, manifest=manifest)
        elif item.relative == ".vscode/mcp.json":
            _write_mcp(item.src, item.dest, replacements, manifest=manifest)
        elif item.action != "replace-hook" or _should_replace_hook_file(
            item.dest, src=item.src, replace_hooks=replace_hooks, interactive=interactive
        ):
            created = not item.dest.exists()
            _write_seed_file(item.src, item.dest, replacements)
            _record_seed_install(manifest, item.relative, item.dest, created=created)


def _hide_from_git(target_dir: Path, manifest: dict[str, object]) -> None:
    """Write the OwlBear block into the local exclude file and record it in the receipt."""
    location = _workspace_git.locate(target_dir)
    if location is None:
        manifest.pop("git_exclude", None)
        return
    exclude_path, prefix = location
    lines = _exclude_lines_for(target_dir, prefix, *_created_paths(manifest))
    previous = manifest.get("git_exclude")
    try:
        _workspace_git.write_block(exclude_path, prefix, lines, previous if isinstance(previous, list) else None)
    except OSError as exc:
        message = f"Could not update the Git exclude file {exclude_path}: {exc}"
        raise RuntimeError(message) from exc
    manifest["git_exclude"] = lines


def init(  # noqa: PLR0913 - one keyword per command-line flag
    target_dir: Path,
    owlbear_dir: Path,
    *,
    replace_hooks: bool = False,
    refresh_configs: bool = False,
    interactive: bool | None = None,
    yes: bool = False,
    dry_run: bool = False,
) -> bool:
    """Initialise an OwlBear workspace in *target_dir* after one consent.

    Plans every path the seed/ tree inside *owlbear_dir* would create, merge or
    replace, prints that inventory and asks once before the first write
    (``yes`` consents, ``dry_run`` only prints). Copies static files and
    replaces ``{{placeholder}}`` tokens in ``.json`` / ``.yml`` templates;
    ``settings.json`` and ``mcp.json`` are deep-merged with existing files.
    Existing refreshable consumer configs are preserved unless
    ``refresh_configs`` is true. Created paths are hidden from Git in one
    block of the repository's local exclude file. A successful run records
    its copied and merged surfaces and that block in
    ``.owlbear/install-manifest.json`` for conservative uninstall.

    Args:
        target_dir: Destination project directory.
        owlbear_dir: Root of the owlbear installation (contains ``seed/``).
        replace_hooks: Overwrite differing existing hook runtime files.
        refresh_configs: Replace existing refreshable consumer configs from seed/.
        interactive: Whether setup may prompt. Defaults to TTY detect.
        yes: Consent to writing without the prompt.
        dry_run: Print the inventory and write nothing.

    Returns:
        Whether setup wrote the workspace.
    """
    seed_dir = owlbear_dir / "seed"
    replacements = _build_replacements(owlbear_dir, target_dir)
    interactive_mode = _is_interactive_session() if interactive is None else interactive
    manifest_path = target_dir / _INSTALL_MANIFEST_PATH
    manifest, _ = _load_install_manifest(manifest_path)
    if manifest is None:
        manifest = _new_install_manifest()

    plan = _build_install_plan(seed_dir, target_dir, replacements, manifest, refresh_configs=refresh_configs)
    for line in _inventory_lines(target_dir, plan, replace_hooks=replace_hooks, interactive=interactive_mode):
        print(line)
    if not _confirm_install(target_dir, yes=yes, dry_run=dry_run, interactive=interactive_mode):
        return False

    _install_seed_files(
        plan.files, target_dir, replacements, manifest, replace_hooks=replace_hooks, interactive=interactive_mode
    )
    _ensure_parent_dirs(manifest_path.parent, target_dir, manifest)
    _hide_from_git(target_dir, manifest)
    _configure_copilot_profile(target_dir, interactive=interactive_mode)
    _write_install_manifest(manifest_path, manifest)
    return True


def _has_owlbear_surface(target_dir: Path) -> bool:
    """Return whether a target has a receipt or recognizable OwlBear surface."""
    if (target_dir / _INSTALL_MANIFEST_PATH).is_file():
        return True
    return any(
        (target_dir / relative).exists()
        for relative in (
            ".owlbear/hooks/deny-src-writes.py",
            ".owlbear/.gitignore",
            ".vscode/mcp.json",
        )
    )


def _remove_install_manifest(
    path: Path,
    original: bytes | None,
    options: _UninstallOptions,
) -> None:
    """Remove the unchanged receipt after uninstalling its owned surfaces."""
    if original is None or not path.exists():
        return
    if not _safe_uninstall_destination(path, options):
        return
    if path.is_symlink() or not path.is_file():
        _record_uninstall_action(options, "preserve", path)
        return
    try:
        unchanged = path.read_bytes() == original
    except OSError:
        unchanged = False
    if not unchanged:
        _record_uninstall_action(options, "preserve", path)
        return
    if options.dry_run:
        _record_uninstall_action(options, "would remove", path)
        return
    try:
        path.unlink()
    except OSError as exc:
        message = f"Could not remove install receipt during uninstall: {path}"
        raise RuntimeError(message) from exc
    _remove_created_parent_dirs(path, options)
    _record_uninstall_action(options, "removed", path)


def _remove_seed_surfaces(seed_dir: Path, options: _UninstallOptions) -> None:
    """Remove each receipt-backed seed surface from one consumer project."""
    relative_paths = {
        src.relative_to(seed_dir).as_posix()
        for src in seed_dir.rglob("*")
        if not src.is_dir() and src.name not in _SKIP_NAMES
    }
    manifest_files = options.manifest.get("files") if isinstance(options.manifest, dict) else None
    if isinstance(manifest_files, dict):
        relative_paths.update(relative for relative in manifest_files if isinstance(relative, str))

    for relative in sorted(relative_paths):
        dest = options.target_dir / relative
        record = _manifest_record(options.manifest, relative)

        if relative == ".vscode/settings.json":
            _remove_settings_seed_values(dest, record, options)
        elif relative == ".vscode/mcp.json":
            _remove_mcp_seed_servers(dest, record, options)
        elif relative in {".gitignore", ".owlbear/.gitignore"}:
            _remove_managed_gitignore(dest, record, options)
        else:
            _remove_manifest_file(dest, record, options)


def _remove_git_exclude(options: _UninstallOptions) -> None:
    """Remove the OwlBear exclude block when it still holds the lines the receipt records."""
    recorded = options.manifest.get("git_exclude") if isinstance(options.manifest, dict) else None
    if not isinstance(recorded, list):
        return
    location = _workspace_git.locate(options.target_dir)
    if location is None:
        return
    try:
        action = _workspace_git.remove_block(location[0], location[1], recorded, dry_run=options.dry_run)
    except OSError as exc:
        message = f"Could not update the Git exclude file during uninstall: {location[0]}"
        raise RuntimeError(message) from exc
    if action is not None:
        options.actions.append(f"{action}: OwlBear block in {location[0]}")


def uninstall(
    target_dir: Path,
    owlbear_dir: Path,
    *,
    confirm: bool | None = None,
    dry_run: bool = False,
) -> UninstallResult:
    """Remove unchanged OwlBear-managed seed surfaces from *target_dir*.

    The install receipt records what this setup run actually created or merged.
    Only receipt-owned surfaces whose post-install bytes remain unchanged are
    removed. Customized files, project Delivery state, and user-local profile
    settings are preserved.

    Args:
        target_dir: Destination project directory.
        owlbear_dir: Root of the owlbear installation (contains ``seed/``).
        confirm: Whether to skip confirmation (``False``), require it (``True``),
            or infer it from the current TTY (``None``).
        dry_run: Report planned changes without modifying files.

    Returns:
        A structured result containing completion state and all recorded actions.
    """
    target_root = target_dir.resolve()
    owlbear_root = owlbear_dir.resolve()
    if target_root == owlbear_root or target_root.is_relative_to(owlbear_root):
        message = (
            "Refusing to uninstall the OwlBear checkout itself or one of its descendants; "
            "run this from a consumer project."
        )
        raise RuntimeError(message)

    seed_dir = owlbear_dir / "seed"
    if not seed_dir.is_dir():
        message = f"OwlBear seed directory does not exist: {seed_dir}"
        raise RuntimeError(message)

    if not _has_owlbear_surface(target_dir):
        message = "No OwlBear install receipt or recognizable managed surface was found in the target project."
        raise RuntimeError(message)

    if not dry_run and confirm is not False and not _is_interactive_session():
        message = "Refusing non-interactive uninstall; rerun with --yes or use --dry-run."
        raise RuntimeError(message)
    if not dry_run and confirm is not False and not _confirm_uninstall(target_dir):
        print("OwlBear uninstall cancelled.")
        return UninstallResult(completed=False, actions=())

    manifest_path = target_dir / _INSTALL_MANIFEST_PATH
    manifest, manifest_bytes = _load_install_manifest(manifest_path)
    options = _UninstallOptions(
        target_dir,
        target_root=target_root,
        dry_run=dry_run,
        manifest=manifest,
    )
    try:
        _remove_seed_surfaces(seed_dir, options)
        _remove_git_exclude(options)
        _remove_install_manifest(manifest_path, manifest_bytes, options)
    except RuntimeError as exc:
        raise UninstallError(str(exc), tuple(options.actions)) from exc
    return UninstallResult(completed=True, actions=tuple(options.actions))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":  # pragma: no cover
    if sys.platform == "win32":
        print(
            "Windows is unsupported. OwlBear supports macOS only; Linux and Windows are not supported yet.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    import argparse

    parser = argparse.ArgumentParser(description="Initialise an OwlBear workspace in the current directory.")
    parser.add_argument(
        "--replace-hooks",
        action="store_true",
        help="Overwrite differing existing .owlbear/hooks files instead of skipping or prompting.",
    )
    config_mode = parser.add_mutually_exclusive_group()
    config_mode.add_argument(
        "--uninstall",
        action="store_true",
        help="Remove receipt-owned OwlBear files and configuration from the current project.",
    )
    config_mode.add_argument(
        "--refresh-configs",
        action="store_true",
        help="Replace existing consumer lint/editor configs from the owlbear seed.",
    )
    config_mode.add_argument(
        "--check-configs",
        action="store_true",
        help="Report consumer lint/editor config drift without changing files.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Consent to setup or uninstall without prompting.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what setup or uninstall would change without modifying files.",
    )
    args = parser.parse_args()

    _target = Path.cwd()
    # Not resolved: run from the ~/.owlbear/runtime alias, seeded paths keep the alias across updates.
    _owlbear = Path(__file__).absolute().parent.parent
    if (args.yes or args.dry_run) and args.check_configs:
        parser.error("--yes and --dry-run cannot be combined with --check-configs")
    if args.replace_hooks and args.uninstall:
        parser.error("--replace-hooks cannot be combined with --uninstall")
    if args.uninstall:
        try:
            result = uninstall(
                _target,
                _owlbear,
                confirm=False if args.yes else None,
                dry_run=args.dry_run,
            )
        except UninstallError as exc:
            print(f"OwlBear uninstall failed: {exc}", file=sys.stderr)
            for action in exc.actions:
                print(f"  {action}", file=sys.stderr)
            raise SystemExit(1) from exc
        except RuntimeError as exc:
            raise SystemExit(str(exc)) from exc
        if result.completed:
            if args.dry_run:
                print(f"OwlBear uninstall dry-run for '{_target.name}'; no files changed.")
            else:
                print(f"OwlBear workspace uninstalled from '{_target.name}'.")
            if result.actions:
                for action in result.actions:
                    print(f"  {action}")
            else:
                print("  No unchanged OwlBear-managed files found.")
            print("  Preserved by design: Delivery state and user-local VS Code profile settings.")
        raise SystemExit(0)
    if args.check_configs:
        drift = config_drift(_target, _owlbear)
        if drift:
            print("Consumer config drift detected:")
            for path, reason in drift.items():
                print(f"  {reason}: {path}")
            raise SystemExit(1)
        print("Consumer lint/editor configs are aligned with the owlbear seed.")
        raise SystemExit(0)
    try:
        completed = init(
            _target,
            _owlbear,
            replace_hooks=args.replace_hooks,
            refresh_configs=args.refresh_configs,
            yes=args.yes,
            dry_run=args.dry_run,
        )
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc
    if completed:
        print(f"OwlBear workspace initialised in '{_target.name}'.")
