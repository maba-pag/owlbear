"""OwlBear workspace initialiser — setup/init.py.

Usage (CLI):
    python ../owlbear/setup/init.py [--replace-hooks] [--refresh-configs | --check-configs]

Run from the target project directory.  owlbear_dir is auto-detected from
the location of this script.
"""

from __future__ import annotations

import difflib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import warnings
from contextlib import suppress
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


def _write_settings(src: Path, dest: Path, replacements: dict[str, str]) -> None:
    """Write .vscode/settings.json, merging with existing file if present (AC12)."""
    template = src.read_text(encoding="utf-8")
    json_replacements = {key: json.dumps(value)[1:-1] for key, value in replacements.items()}
    template = _replace_placeholders(template, json_replacements)
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

        if rel_posix == ".owlbear/.gitignore":
            _write_gitignore(src, dest, retired_lines=frozenset())
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

        _write_seed_file(src, dest, replacements)

    _write_delivery_config(
        target_dir,
        remote,
        target_branch,
        github_repository,
        interactive=interactive_mode,
    )
    _configure_copilot_profile(target_dir, interactive=interactive_mode)


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
    args = parser.parse_args()

    _target = Path.cwd()
    _owlbear = Path(__file__).resolve().parent.parent
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
