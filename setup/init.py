"""OwlBear workspace initialiser — setup/init.py.

Usage (CLI):
    python ../owlbear/setup/init.py [--replace-hooks] [--refresh-configs | --check-configs | --uninstall]
        [--yes] [--dry-run]

Run from the target project directory.  owlbear_dir is auto-detected from
the location of this script.
"""

from __future__ import annotations

import sys

# Runtime floor shared with every serve/* requires-python declaration and with
# .python-version; kept aligned by .github/scripts/check_python_runtime.py.
#
# This module is the one entry point documented to run before a managed
# environment exists, so it must stay parseable by older interpreters in order
# to report the floor instead of failing with a SyntaxError. `ruff`'s
# per-file-target-version setting pins that constraint for both linter and
# formatter; do not introduce newer-only syntax here.
_MINIMUM_PYTHON = (3, 14, 6)


def _check_python_version(version_info: tuple[int, ...] | None = None) -> None:
    """Abort setup when the active interpreter is below the supported minimum.

    Missing components in an injected ``version_info`` are treated as zero so
    callers and tests may supply only the major and minor versions.
    """
    raw_version = sys.version_info if version_info is None else version_info
    current = tuple(raw_version[:3])
    current += (0,) * (3 - len(current))
    if current < _MINIMUM_PYTHON:
        required = ".".join(str(part) for part in _MINIMUM_PYTHON)
        found = ".".join(str(part) for part in current)
        message = (
            f"OwlBear requires Python {required} or newer; found Python {found}. "
            "Run setup through uv so the pinned runtime is used, for example: "
            "uv run --project ../owlbear python ../owlbear/setup/init.py"
        )
        raise SystemExit(message)


_check_python_version()

import difflib  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
import os  # noqa: E402
import re  # noqa: E402
import shlex  # noqa: E402
import shutil  # noqa: E402
import subprocess  # noqa: E402
import tempfile  # noqa: E402
import warnings  # noqa: E402
from collections import Counter  # noqa: E402
from contextlib import suppress  # noqa: E402
from pathlib import Path  # noqa: E402

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

_OWLBEAR_GITIGNORE_MARKER = "# --- OwlBear managed paths ---"
_RETIRED_OWLBEAR_GITIGNORE_LINES = frozenset(
    {
        "# Brief drafts (transient template directory)",
        "# Host-local Delivery startup configuration",
        "/.owlbear/delivery/config.json",
        ".owlbear/briefs/draft-new/",
        "# Scratch / ad-hoc workspace",
        ".owlbear/scratch/*",
        "!.owlbear/scratch/.gitkeep",
        "!.owlbear/scratch/.instructions.md",
        "# Knowledge and memory databases",
        ".owlbear/knowledge/*.db",
        ".owlbear/knowledge/vectors/",
        ".owlbear/memory/*.db",
        "# Host-local Delivery worktrees and mutable capacity ledger",
        "/.owlbear/delivery/runtime/",
        "/.owlbear/delivery/worktrees/",
        "/.owlbear/worktrees/",
        "/.owlbear/delivery/migration.json",
        "/.owlbear/delivery/integration-retirement.json",
        "/.owlbear/scratch/delivery-integration-retirement/",
        "/.owlbear/target/target-runtime/capacity.json",
        "/.owlbear/target/target-runtime/integration-verification/",
        "# Lock files (transient runtime artifacts)",
        "**/.storage.lock",
        ".owlbear/target/**/.storage.lock",
        ".owlbear/kanban/activity.jsonl",
    }
)
_HOOKS_REL_PREFIX = ".owlbear/hooks/"
_DELIVERY_CONFIG_PATH = Path(".owlbear/delivery/config.json")
_DELIVERY_CONFIG_SCHEMA_VERSION = 2
_INSTALL_MANIFEST_PATH = Path(".owlbear/install-manifest.json")
_INSTALL_MANIFEST_SCHEMA_VERSION = 1
_DEFAULT_PROFILE_ASSOCIATION = "__default__profile__"
_COPILOT_REASONING_SETTINGS = {
    "gpt-5.6-luna": "max",
    "gpt-5.6-sol": "high",
    "claude-opus-5": "medium",
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
        "owlbear_abs_path": str(owlbear_dir.resolve()),
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
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
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


def _write_gitignore(src: Path, dest: Path, *, retired_lines: frozenset[str] | None = None) -> None:
    """Write .gitignore, appending owlbear-managed section to existing file.

    If the destination file does not exist, copies the full seed .gitignore.
    If it exists but has no owlbear marker, appends the owlbear-managed section.
    If the marker is already present, removes retired rules and adds missing current rules.
    """
    seed_content = src.read_text(encoding="utf-8")
    retired = _RETIRED_OWLBEAR_GITIGNORE_LINES if retired_lines is None else retired_lines

    if not dest.exists():
        dest.write_text(seed_content, encoding="utf-8")
        return

    existing = dest.read_text(encoding="utf-8")
    if _OWLBEAR_GITIGNORE_MARKER in existing:
        prefix, marker, managed = existing.partition(_OWLBEAR_GITIGNORE_MARKER)
        retained = [line for line in managed.splitlines() if line.strip() not in retired]
        while retained and not retained[0].strip():
            retained.pop(0)
        seed_managed = seed_content.partition(_OWLBEAR_GITIGNORE_MARKER)[2].splitlines()
        retained_values = {line.strip() for line in retained}
        additions = [
            line
            for line in seed_managed
            if line.strip() and line.strip() not in retained_values and line.strip() not in retired
        ]
        merged = "\n".join((*retained, *additions)).rstrip()
        updated = prefix + marker + ("\n" + merged + "\n" if merged else "\n")
        if updated != existing:
            dest.write_text(updated, encoding="utf-8")
        return

    # Extract the owlbear-managed section from the seed
    marker_pos = seed_content.find(_OWLBEAR_GITIGNORE_MARKER)
    if marker_pos < 0:
        return  # seed has no marker — nothing to append
    owlbear_section = seed_content[marker_pos:]

    # Append with a blank line separator
    separator = "" if existing.endswith("\n") else "\n"
    dest.write_text(existing + separator + "\n" + owlbear_section, encoding="utf-8")


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
    kind: str = "file",
    **extra: object,
) -> None:
    """Record one copied seed surface after installation."""
    record: dict[str, object] = {
        "kind": kind,
        "created": created,
        "installed_sha256": _sha256_bytes(dest.read_bytes()),
        **extra,
    }
    _merge_manifest_record(manifest, relative, record)


def _gitignore_section_lines(content: str) -> list[str]:
    """Return non-empty managed-section lines from one gitignore document."""
    if _OWLBEAR_GITIGNORE_MARKER not in content:
        return []
    return [line.strip() for line in content.partition(_OWLBEAR_GITIGNORE_MARKER)[2].splitlines() if line.strip()]


def _gitignore_added_lines(before: str, after: str) -> list[str]:
    """Return the managed lines added by one installation pass."""
    before_counts = Counter(_gitignore_section_lines(before))
    after_counts = Counter(_gitignore_section_lines(after))
    return list((after_counts - before_counts).elements())


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


def _current_branch(target_dir: Path) -> str | None:
    """Return the checked-out local branch when the target is a Git repository."""
    result = subprocess.run(
        ["git", "branch", "--show-current"],  # noqa: S607
        cwd=target_dir,
        check=False,
        capture_output=True,
        text=True,
    )
    branch = result.stdout.strip()
    return branch or None


def _valid_branch_name(target_dir: Path, branch: str) -> bool:
    """Return whether *branch* is a valid unqualified Git branch name."""
    syntax = subprocess.run(  # noqa: S603
        ["git", "check-ref-format", f"refs/heads/{branch}"],  # noqa: S607
        cwd=target_dir,
        check=False,
        capture_output=True,
    )
    return syntax.returncode == 0


def _select_target_branch(target_dir: Path, requested: str | None, *, interactive: bool) -> str:
    """Resolve a fresh project's target from an option, prompt, or stable fallback."""
    if requested is not None:
        if not _valid_branch_name(target_dir, requested):
            msg = f"Target branch name is invalid: {requested}"
            raise RuntimeError(msg)
        return requested
    if not interactive:
        return "main"
    suggested = _current_branch(target_dir) or "main"
    selected = input(f"Target branch [{suggested}]: ").strip() or suggested
    if not _valid_branch_name(target_dir, selected):
        msg = f"Target branch name is invalid: {selected}"
        raise RuntimeError(msg)
    return selected


def _github_repository_from_remote(target_dir: Path, remote: str) -> str | None:
    """Infer an exact GitHub ``owner/name`` identity from one remote URL."""
    completed = subprocess.run(  # noqa: S603
        ["git", "remote", "get-url", remote],  # noqa: S607
        cwd=target_dir,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return None
    match = re.fullmatch(
        r"(?:https://github\.com/|git@github\.com:|ssh://git@github\.com/)([^\s/]+/[^\s/]+?)(?:\.git)?",
        completed.stdout.strip(),
    )
    return match.group(1) if match else None


def _select_github_repository(
    target_dir: Path,
    remote: str,
    requested: str | None,
    *,
    interactive: bool,
) -> str:
    """Resolve an exact GitHub repository identity without placeholders."""
    selected = requested or _github_repository_from_remote(target_dir, remote)
    if selected is None and interactive:
        selected = input("GitHub repository (owner/name): ").strip()
    if selected is None or re.fullmatch(r"[^\s/]+/[^\s/]+", selected) is None:
        msg = "GitHub repository must be provided as owner/name or inferred from the configured remote"
        raise RuntimeError(msg)
    return selected


def _write_delivery_config(
    target_dir: Path,
    remote: str,
    target_branch: str | None,
    github_repository: str | None,
    *,
    interactive: bool,
) -> None:
    """Create or migrate the tracked project Delivery policy."""
    path = target_dir / _DELIVERY_CONFIG_PATH
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            msg = f"Delivery configuration cannot be migrated: {path}"
            raise RuntimeError(msg) from exc
        if isinstance(existing, dict) and existing.get("schema_version") == _DELIVERY_CONFIG_SCHEMA_VERSION:
            return
        if (
            not isinstance(existing, dict)
            or set(existing) != {"schema_version", "integration_target"}
            or existing.get("schema_version") != 1
            or not isinstance(existing.get("integration_target"), str)
            or not existing["integration_target"]
        ):
            msg = f"Delivery configuration schema cannot be migrated: {path}"
            raise RuntimeError(msg)
        target_branch = existing["integration_target"]
    path.parent.mkdir(parents=True, exist_ok=True)
    content = {
        "schema_version": _DELIVERY_CONFIG_SCHEMA_VERSION,
        "remote": remote,
        "target_branch": _select_target_branch(
            target_dir,
            target_branch,
            interactive=interactive,
        ),
        "github_repository": _select_github_repository(
            target_dir,
            remote,
            github_repository,
            interactive=interactive,
        ),
    }
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        delete=False,
    ) as temporary:
        temporary.write(json.dumps(content, indent=2) + "\n")
        temporary.flush()
        os.fsync(temporary.fileno())
        temporary_path = Path(temporary.name)
    temporary_path.replace(path)


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
    except (OSError, json.JSONDecodeError):
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
    except (OSError, UnicodeDecodeError):
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


def init(  # noqa: C901, PLR0913
    target_dir: Path,
    owlbear_dir: Path,
    *,
    replace_hooks: bool = False,
    refresh_configs: bool = False,
    interactive: bool | None = None,
    remote: str = "origin",
    target_branch: str | None = None,
    github_repository: str | None = None,
) -> None:
    """Initialise an OwlBear workspace in *target_dir*.

    Walks the seed/ tree inside *owlbear_dir*, copies static files, and
    replaces ``{{placeholder}}`` tokens in ``.json`` / ``.yml`` templates.
    ``settings.json`` and ``mcp.json`` are deep-merged with existing files.
    Existing refreshable consumer configs are preserved unless
    ``refresh_configs`` is true.
    A successful run records its copied and merged surfaces in
    ``.owlbear/install-manifest.json`` for conservative uninstall.
    Also receipt-activates an empty target authority store for fresh workspaces.
    Existing legacy stores remain untouched.

    Args:
        target_dir: Destination project directory.
        owlbear_dir: Root of the owlbear installation (contains ``seed/``).
        replace_hooks: Overwrite differing existing hook runtime files.
        refresh_configs: Replace existing refreshable consumer configs from seed/.
        interactive: Whether hook conflicts may prompt. Defaults to TTY detect.
        remote: Git remote used for Delivery publication.
        target_branch: Unqualified branch targeted by Delivery pull requests.
        github_repository: Exact GitHub ``owner/name`` identity for publication.
    """
    seed_dir = owlbear_dir / "seed"
    replacements = _build_replacements(owlbear_dir, target_dir)
    interactive_mode = _is_interactive_session() if interactive is None else interactive
    manifest_path = target_dir / _INSTALL_MANIFEST_PATH
    manifest, _ = _load_install_manifest(manifest_path)
    if manifest is None:
        manifest = _new_install_manifest()

    for src in sorted(seed_dir.rglob("*")):
        if src.is_dir():
            continue

        rel = src.relative_to(seed_dir)
        rel_posix = rel.as_posix()

        if src.name in _SKIP_NAMES:
            continue

        dest = target_dir / rel
        _ensure_parent_dirs(dest.parent, target_dir, manifest)

        # --- per-file dispatch ---

        if rel_posix == ".vscode/settings.json":
            _write_settings(src, dest, replacements, manifest=manifest)
            continue

        if rel_posix == ".vscode/mcp.json":
            _write_mcp(src, dest, replacements, manifest=manifest)
            continue

        if rel_posix == ".gitignore":
            before = dest.read_text(encoding="utf-8") if dest.exists() else ""
            created = not dest.exists()
            _write_gitignore(src, dest)
            _record_seed_install(
                manifest,
                rel_posix,
                dest,
                created=created,
                kind="gitignore",
                added_lines=_gitignore_added_lines(before, dest.read_text(encoding="utf-8")),
                marker_added=_OWLBEAR_GITIGNORE_MARKER not in before
                and _OWLBEAR_GITIGNORE_MARKER in dest.read_text(encoding="utf-8"),
            )
            continue

        if rel_posix == ".owlbear/.gitignore":
            before = dest.read_text(encoding="utf-8") if dest.exists() else ""
            created = not dest.exists()
            _write_gitignore(src, dest, retired_lines=frozenset())
            _record_seed_install(
                manifest,
                rel_posix,
                dest,
                created=created,
                kind="gitignore",
                added_lines=_gitignore_added_lines(before, dest.read_text(encoding="utf-8")),
                marker_added=_OWLBEAR_GITIGNORE_MARKER not in before
                and _OWLBEAR_GITIGNORE_MARKER in dest.read_text(encoding="utf-8"),
            )
            continue

        if (
            rel_posix in _SKIP_IF_EXISTS_REL
            and dest.exists()
            and not (refresh_configs and rel_posix in _REFRESHABLE_CONFIG_REL)
        ):
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

        created = not dest.exists()
        _write_seed_file(src, dest, replacements)
        _record_seed_install(manifest, rel_posix, dest, created=created)

    _write_delivery_config(
        target_dir,
        remote,
        target_branch,
        github_repository,
        interactive=interactive_mode,
    )
    _configure_copilot_profile(target_dir, interactive=interactive_mode)
    _write_install_manifest(manifest_path, manifest)


def _has_owlbear_surface(target_dir: Path) -> bool:
    """Return whether a target has a receipt or recognizable OwlBear surface."""
    if (target_dir / _INSTALL_MANIFEST_PATH).is_file():
        return True
    return any(
        (target_dir / relative).exists()
        for relative in (
            ".owlbear/delivery/config.json",
            ".owlbear/hooks/deny-writes.py",
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
        _remove_install_manifest(manifest_path, manifest_bytes, options)
    except RuntimeError as exc:
        raise UninstallError(str(exc), tuple(options.actions)) from exc
    return UninstallResult(completed=True, actions=tuple(options.actions))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":  # pragma: no cover
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
        "--remote",
        default="origin",
        metavar="NAME",
        help="Use this Git remote for Delivery publication (default: origin).",
    )
    parser.add_argument(
        "--target-branch",
        metavar="BRANCH",
        help="Use this target branch for Delivery pull requests (default: main).",
    )
    parser.add_argument(
        "--github-repository",
        metavar="OWNER/NAME",
        help="Use this GitHub repository identity, or infer it from the configured remote.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Confirm an uninstall without prompting.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show uninstall changes without modifying files.",
    )
    args = parser.parse_args()

    _target = Path.cwd()
    _owlbear = Path(__file__).resolve().parent.parent
    if args.yes and not args.uninstall:
        parser.error("--yes requires --uninstall")
    if args.dry_run and not args.uninstall:
        parser.error("--dry-run requires --uninstall")
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
        init(
            _target,
            _owlbear,
            replace_hooks=args.replace_hooks,
            refresh_configs=args.refresh_configs,
            remote=args.remote,
            target_branch=args.target_branch,
            github_repository=args.github_repository,
        )
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc
    print(f"OwlBear workspace initialised in '{_target.name}'.")
