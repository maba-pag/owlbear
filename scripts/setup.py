"""Setup script — OwlBear v2 workspace bootstrap."""

from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path


def compute_owlbear_relpath(owlbear_dir: Path, project_dir: Path) -> str:
    """Return the relative POSIX path from project_dir to owlbear_dir."""
    return Path(os.path.relpath(owlbear_dir, project_dir)).as_posix()


def create_vscode_settings(project_dir: Path, owlbear_dir: Path) -> None:
    """Create or merge .vscode/settings.json with owlbear agent/skill/instruction locations."""
    vscode_dir = project_dir / ".vscode"
    vscode_dir.mkdir(parents=True, exist_ok=True)
    settings_file = vscode_dir / "settings.json"

    existing: dict = {}
    if settings_file.exists():
        existing = json.loads(settings_file.read_text(encoding="utf-8"))

    rel = compute_owlbear_relpath(owlbear_dir, project_dir)

    owlbear_keys: dict = {
        "chat.agentFilesLocations": {
            f"{rel}/agents": "OwlBear Agents",
            f"{rel}/.github/agents": "OwlBear GitHub Agents",
        },
        "chat.agentSkillsLocations": {
            f"{rel}/skills": "OwlBear Skills",
            f"{rel}/.github/skills": "OwlBear GitHub Skills",
        },
        "chat.instructionsFilesLocations": {
            f"{rel}/instructions": "OwlBear Instructions",
            f"{rel}/.github/instructions": "OwlBear GitHub Instructions",
        },
    }

    # Merge: owlbear keys are defaults; existing user keys take priority
    merged = {**owlbear_keys, **existing}
    settings_file.write_text(json.dumps(merged, indent=2), encoding="utf-8")


def create_mcp_config(project_dir: Path, owlbear_dir: Path) -> None:
    """Create .vscode/mcp.json with three owlbear MCP server entries. Skips if already exists."""
    vscode_dir = project_dir / ".vscode"
    vscode_dir.mkdir(parents=True, exist_ok=True)
    mcp_file = vscode_dir / "mcp.json"

    if mcp_file.exists():
        return

    rel = compute_owlbear_relpath(owlbear_dir, project_dir)
    config = {
        "servers": {
            "github": {
                "type": "http",
                "url": "https://api.githubcopilot.com/mcp/",
            },
            "owlbearKanban": {
                "type": "stdio",
                "command": "uv",
                "args": ["run", "--project", rel, "-m", "owlbear_mcp_kanban"],
            },
            "owlbearKnowledge": {
                "type": "stdio",
                "command": "uv",
                "args": ["run", "--project", rel, "-m", "owlbear_mcp_knowledge"],
            },
            "owlbearProject": {
                "type": "stdio",
                "command": "uv",
                "args": ["run", "--project", rel, "-m", "owlbear_mcp_project"],
            },
        }
    }
    mcp_file.write_text(json.dumps(config, indent=2), encoding="utf-8")


def create_kanban_dir(project_dir: Path, owlbear_dir: Path) -> None:
    """Create kanban/ with config.yml, tasks/, and setup.ps1. Skips config.yml if exists."""
    kanban_dir = project_dir / "kanban"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "tasks").mkdir(exist_ok=True)

    config_dest = kanban_dir / "config.yml"
    if not config_dest.exists():
        config_src = owlbear_dir / "kanban" / "config.yml"
        content = config_src.read_text(encoding="utf-8")
        # Reset next_id to a clean value instead of carrying over owlbear's sequence
        content = re.sub(r"next_id:\s*\d+", "next_id: 1", content)
        config_dest.write_text(content, encoding="utf-8")

    setup_ps1_src = owlbear_dir / "kanban" / "setup.ps1"
    setup_ps1_dest = kanban_dir / "setup.ps1"
    if not setup_ps1_dest.exists():
        shutil.copy2(setup_ps1_src, setup_ps1_dest)


def create_knowledge_dir(project_dir: Path) -> None:
    """Create data/knowledge/ directory."""
    (project_dir / "data" / "knowledge").mkdir(parents=True, exist_ok=True)


def create_copilot_instructions(project_dir: Path, name: str) -> None:
    """Create .github/copilot-instructions.md with project name. Skips if already exists."""
    github_dir = project_dir / ".github"
    github_dir.mkdir(parents=True, exist_ok=True)
    instructions_file = github_dir / "copilot-instructions.md"

    if instructions_file.exists():
        return

    content = f"# {name}\n\nThis is the OwlBear workspace for the **{name}** project.\n"
    instructions_file.write_text(content, encoding="utf-8")


def setup(
    project_dir: Path | None = None,
    owlbear_dir: Path | None = None,
) -> None:
    """Bootstrap an OwlBear workspace in project_dir.

    Args:
        project_dir: Target project directory. Defaults to current working directory.
        owlbear_dir: Path to the owlbear installation. Auto-detected from script location.
    """
    if project_dir is None:
        project_dir = Path.cwd()
    if owlbear_dir is None:
        owlbear_dir = Path(__file__).resolve().parent.parent

    name = project_dir.name

    create_vscode_settings(project_dir, owlbear_dir)
    create_mcp_config(project_dir, owlbear_dir)
    create_kanban_dir(project_dir, owlbear_dir)
    create_knowledge_dir(project_dir)
    create_copilot_instructions(project_dir, name=name)

    print(f"\nOwlBear workspace setup complete for '{name}'.")
    print("Next steps:")
    print("  1. Open the project in VS Code.")
    print("  2. Run `kanban/setup.ps1` to download kanban-md.")
    print("  3. Start orchestrating with the OwlBear agents.")
    print("  4. Edit .vscode/mcp.json to add project-specific MCP servers.")
    print()


if __name__ == "__main__":
    setup()
