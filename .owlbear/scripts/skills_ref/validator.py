"""skills_ref.validator — validate skill metadata against the Agent Skills Spec."""

from __future__ import annotations

import re
from pathlib import Path

# Matches names that consist only of lowercase letters, digits, and hyphens.
_NAME_CHARS_RE = re.compile(r"^[a-z0-9-]+$")

_MAX_NAME_LENGTH = 64
_MAX_DESCRIPTION_LENGTH = 1024


def _validate_naming_convention(value: str, label: str) -> list[str]:
    """Return naming-convention errors for *value*, labelling them with *label*.

    Checks (in order, stopping at first violation for a cleaner message):
    - only lowercase letters, digits, and hyphens
    - no leading or trailing hyphen
    - no consecutive hyphens
    """
    if not _NAME_CHARS_RE.match(value):
        return [f"{label} '{value}' must contain only lowercase letters, digits, and hyphens"]
    if value.startswith("-") or value.endswith("-"):
        return [f"{label} '{value}' must not start or end with a hyphen"]
    if "--" in value:
        return [f"{label} '{value}' must not contain consecutive hyphens"]
    return []


def validate_metadata(metadata: dict, skill_dir: Path) -> list[str]:
    """Validate skill metadata against the Agent Skills Spec.

    Args:
        metadata: Parsed YAML frontmatter dict (vendor fields already filtered).
        skill_dir: Path to the skill directory (used to check name match).

    Returns:
        List of validation error messages.  Empty list means valid.
    """
    errors: list[str] = []
    dir_name = Path(skill_dir).name

    # --- Directory name: naming convention (unconditional) ---
    errors.extend(_validate_naming_convention(dir_name, "Skill directory name"))

    # --- Directory name: max length ---
    if len(dir_name) > _MAX_NAME_LENGTH:
        errors.append(
            f"Skill directory name '{dir_name}' exceeds maximum length of "
            f"{_MAX_NAME_LENGTH} characters (got {len(dir_name)})"
        )

    # --- Required field: description ---
    if "description" not in metadata:
        errors.append("Missing required field: 'description'")
    else:
        description = str(metadata["description"])

        # Defense-in-depth: reject angle brackets (deer-flow pattern, guards
        # against accidental HTML injection in agent skill menus).
        # Allow '->' text arrows by exempting '>' immediately preceded by '-'.
        if re.search(r"<|(?<!-)>", description):
            errors.append(f"Description contains angle brackets ('<' or '>'): {description!r}")

        # Agent Skills Spec: descriptions must not exceed 1024 characters.
        if len(description) > _MAX_DESCRIPTION_LENGTH:
            errors.append(
                f"Description exceeds maximum length of {_MAX_DESCRIPTION_LENGTH} characters (got {len(description)})"
            )

    # --- Optional field: name ---
    if "name" in metadata:
        name = str(metadata["name"])
        if name != dir_name:
            errors.append(f"name field '{name}' does not match directory name '{dir_name}'")
        # The name field value must also satisfy the naming convention.
        errors.extend(_validate_naming_convention(name, "name field"))

    return errors
