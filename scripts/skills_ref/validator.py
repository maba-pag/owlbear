"""skills_ref.validator — validate skill metadata against the Agent Skills Spec."""

from __future__ import annotations

from pathlib import Path


def validate_metadata(metadata: dict, skill_dir: Path) -> list[str]:
    """Validate skill metadata against the Agent Skills Spec.

    Args:
        metadata: Parsed YAML frontmatter dict (vendor fields already filtered).
        skill_dir: Path to the skill directory (used to check name match).

    Returns:
        List of validation error messages.  Empty list means valid.
    """
    errors: list[str] = []

    if "description" not in metadata:
        errors.append("Missing required field: 'description'")

    if "name" in metadata:
        name = str(metadata["name"])
        dir_name = Path(skill_dir).name
        if name != dir_name:
            errors.append(
                f"name field '{name}' does not match directory name '{dir_name}'"
            )

    return errors
