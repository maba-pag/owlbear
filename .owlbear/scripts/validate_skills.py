"""Validate OwlBear skill directories against the Agent Skills Spec.

Filters out VS Code vendor fields (user-invocable, argument-hint,
disable-model-invocation) before validation so OwlBear-specific extensions
do not produce false positives.

Usage:
    python scripts/validate_skills.py <skill_dir> [<skill_dir> ...]
"""

from __future__ import annotations

import sys
from pathlib import Path

from skills_ref.errors import ParseError
from skills_ref.parser import find_skill_md, parse_frontmatter
from skills_ref.validator import validate_metadata

# OwlBear-specific VS Code vendor fields — not part of the Agent Skills Spec.
_VENDOR_FIELDS = frozenset({"user-invocable", "argument-hint", "disable-model-invocation"})


def validate_skill(skill_dir: Path) -> list[str]:
    """Validate a skill directory, filtering OwlBear vendor fields.

    Args:
        skill_dir: Path to the skill directory containing SKILL.md.

    Returns:
        List of validation error messages.  Empty list means valid.
    """
    skill_dir = Path(skill_dir)

    if not skill_dir.exists():
        return [f"Path does not exist: {skill_dir}"]

    if not skill_dir.is_dir():
        return [f"Not a directory: {skill_dir}"]

    skill_md = find_skill_md(skill_dir)
    if skill_md is None:
        return ["Missing required file: SKILL.md"]

    try:
        content = skill_md.read_text(encoding="utf-8")
        metadata, _ = parse_frontmatter(content)
    except ParseError as e:
        return [str(e)]

    # Strip vendor fields so they don't trigger "unexpected fields" errors.
    filtered_metadata = {k: v for k, v in metadata.items() if k not in _VENDOR_FIELDS}

    return validate_metadata(filtered_metadata, skill_dir)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point.  Accepts skill directory paths as positional arguments.

    When called with no arguments, auto-discovers all skill directories under
    ``share/skills/``.
    """
    args = argv if argv is not None else sys.argv[1:]

    if not args:
        # Auto-discover skill directories (cross-platform, no shell glob needed).
        skills_root = Path("share/skills")
        if skills_root.is_dir():
            args = [str(p) for p in sorted(skills_root.iterdir()) if p.is_dir()]
        if not args:
            sys.stderr.write("Usage: validate_skills.py [<skill_dir> ...]\n")
            return 1

    has_errors = False
    for raw_path in args:
        skill_dir = Path(raw_path)
        errors = validate_skill(skill_dir)
        if errors:
            has_errors = True
            for error in errors:
                sys.stderr.write(f"[{skill_dir.name}] {error}\n")

    return 1 if has_errors else 0


if __name__ == "__main__":
    sys.exit(main())
