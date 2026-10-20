"""Validate prompt entry points against active agent and skill roots.

Usage:
    python .owlbear/scripts/validate_prompts.py [<prompt_file> ...]
    # No args = discover prompts in share/prompts/ and .owlbear/prompts/
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PROMPT_ROOTS = (_REPO_ROOT / "share" / "prompts", _REPO_ROOT / ".owlbear" / "prompts")
_AGENT_ROOTS = (_REPO_ROOT / "share" / "agents", _REPO_ROOT / ".owlbear" / "agents")
_SKILL_ROOTS = (_REPO_ROOT / "share" / "skills", _REPO_ROOT / ".owlbear" / "skills")
_BUILTIN_AGENTS = frozenset({"agent", "Explore", "General Purpose"})
_BARE_SKILL_REFERENCE = re.compile(r"`([hwr]-[a-z0-9-]+)`")
_RELATIVE_SKILL_REFERENCE = re.compile(r"((?:\.\./)+skills/[a-z0-9-]+/SKILL\.md)")


def _frontmatter(content: str, prompt_file: Path) -> tuple[dict[str, object], list[str], str]:
    """Parse prompt frontmatter and return metadata, errors, and the body."""
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, [f"{prompt_file}: missing YAML frontmatter"], content
    try:
        closing = next(index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---")
    except StopIteration:
        return {}, [f"{prompt_file}: unterminated YAML frontmatter"], content

    try:
        parsed = yaml.safe_load("\n".join(lines[1:closing]))
    except yaml.YAMLError as exc:
        return {}, [f"{prompt_file}: invalid YAML frontmatter: {exc}"], "\n".join(lines[closing + 1 :])
    if not isinstance(parsed, dict):
        return {}, [f"{prompt_file}: YAML frontmatter must be a mapping"], "\n".join(lines[closing + 1 :])
    return parsed, [], "\n".join(lines[closing + 1 :])


def _root_candidates(prompt_file: Path, roots: tuple[Path, ...], directory: str) -> tuple[Path, ...]:
    """Return the prompt-local root followed by the configured active roots."""
    prompt_local_root = prompt_file.parent.parent / directory
    return tuple(dict.fromkeys((prompt_local_root, *roots)))


def _agent_names(prompt_file: Path) -> set[str]:
    """Collect agent names available to a prompt."""
    names: set[str] = set(_BUILTIN_AGENTS)
    for root in _root_candidates(prompt_file, _AGENT_ROOTS, "agents"):
        names.update(path.name.removesuffix(".agent.md") for path in root.glob("*.agent.md"))
    return names


def _skill_names(prompt_file: Path) -> set[str]:
    """Collect skill names available to a prompt."""
    names: set[str] = set()
    for root in _root_candidates(prompt_file, _SKILL_ROOTS, "skills"):
        if root.is_dir():
            names.update([path.name for path in root.iterdir() if path.is_dir()])
    return names


def _check_skill_references(prompt_file: Path, body: str) -> list[str]:
    """Verify explicit relative and named skill references in a prompt body."""
    errors: list[str] = []
    errors.extend(
        [
            f"{prompt_file}: referenced skill file does not exist: {relative_path}"
            for relative_path in _RELATIVE_SKILL_REFERENCE.findall(body)
            if not (prompt_file.parent / relative_path).is_file()
        ]
    )

    available_skills = _skill_names(prompt_file)
    errors.extend(
        [
            f"{prompt_file}: referenced skill does not exist in active roots: {skill_name}"
            for skill_name in _BARE_SKILL_REFERENCE.findall(body)
            if skill_name not in available_skills
        ]
    )
    return errors


def validate_prompt(prompt_file: Path) -> list[str]:
    """Validate one prompt's metadata, routing target, and skill references."""
    prompt_file = Path(prompt_file)
    if not prompt_file.is_file():
        return [f"Prompt file does not exist: {prompt_file}"]

    metadata, errors, body = _frontmatter(prompt_file.read_text(encoding="utf-8"), prompt_file)
    description = metadata.get("description")
    if not isinstance(description, str) or not description.strip():
        errors.append(f"{prompt_file}: description must be a non-empty string")

    agent = metadata.get("agent")
    if agent is not None:
        if not isinstance(agent, str) or not agent.strip():
            errors.append(f"{prompt_file}: agent must be a non-empty string when declared")
        elif agent not in _agent_names(prompt_file):
            errors.append(f"{prompt_file}: prompt agent does not resolve: {agent}")

    tools = metadata.get("tools")
    if tools is not None and (
        not isinstance(tools, list) or any(not isinstance(tool, str) or not tool.strip() for tool in tools)
    ):
        errors.append(f"{prompt_file}: tools must be a list of non-empty strings when declared")

    errors.extend(_check_skill_references(prompt_file, body))
    return errors


def _discover_prompt_files() -> list[Path]:
    """Discover prompts from every active project customization root."""
    return sorted({prompt_file for root in _PROMPT_ROOTS if root.is_dir() for prompt_file in root.glob("*.prompt.md")})


def main(argv: list[str] | None = None) -> int:
    """Validate explicit prompt files or every prompt in active roots."""
    args = argv if argv is not None else sys.argv[1:]
    prompt_files = [Path(path) for path in args] if args else _discover_prompt_files()
    if not prompt_files:
        roots = ", ".join(str(root) for root in _PROMPT_ROOTS)
        sys.stderr.write(f"No prompt files found in active roots: {roots}\n")
        return 1

    has_errors = False
    for prompt_file in prompt_files:
        errors = validate_prompt(prompt_file)
        if errors:
            has_errors = True
            for error in errors:
                sys.stderr.write(f"{error}\n")

    if not has_errors and not args:
        print(f"PASS - all {len(prompt_files)} prompt files conform to routing conventions")
    return 1 if has_errors else 0


if __name__ == "__main__":
    sys.exit(main())
