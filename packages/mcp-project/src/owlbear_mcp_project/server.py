"""OwlBear MCP project server — exposes project metadata as MCP tools and resources."""

from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from mcp.server.fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations
from pydantic import ValidationError

from owlbear_mcp_project.models import OwlbearProjectFile
from owlbear_mcp_project.tree import build_tree

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

__all__ = [
    "AppContext",
    "app_lifespan",
    "mcp",
    "project_info",
    "project_list",
    "project_readme",
    "project_structure",
]

_STRUCTURE_EXCLUDES: frozenset[str] = frozenset({
    ".git",
    "__pycache__",
    "node_modules",
    ".venv",
    ".mypy_cache",
})


@dataclass(slots=True)
class AppContext:
    """Runtime context passed through MCP lifespan to all tools."""

    project_file: OwlbearProjectFile | None
    project_root: Path
    owlbear_root: Path


@asynccontextmanager
async def app_lifespan(_server: FastMCP) -> AsyncGenerator[AppContext, None]:
    """Resolve project and owlbear roots, read project file, yield AppContext."""
    project_root = Path.cwd()

    owlbear_env = os.environ.get("OWLBEAR_ROOT")
    owlbear_root = Path(owlbear_env) if owlbear_env else Path("..")

    project_file: OwlbearProjectFile | None = None
    config_path = project_root / "owlbear-project.json"
    if config_path.exists():
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
            project_file = OwlbearProjectFile.model_validate(data)
        except (json.JSONDecodeError, ValidationError, OSError):
            project_file = None

    yield AppContext(
        project_file=project_file,
        project_root=project_root,
        owlbear_root=owlbear_root,
    )


mcp = FastMCP("owlbear-project", lifespan=app_lifespan)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True))
async def project_info(ctx: Context) -> dict[str, Any] | str:
    """Return project metadata dict, or a descriptive error string if config is absent."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    if app_ctx.project_file is None:
        return "No owlbear-project.json found in project root."
    pf = app_ctx.project_file
    return {
        "name": pf.name,
        "type": pf.type,
        "project_path": str(app_ctx.project_root),
        "owlbear_path": pf.owlbear_path,
        "created_at": str(pf.created_at),
    }


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True))
async def project_list(ctx: Context) -> list[dict[str, str]]:
    """List registered projects from {owlbear_root}/data/projects/."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    projects_dir = app_ctx.owlbear_root / "data" / "projects"
    if not projects_dir.is_dir():
        return []
    results: list[dict[str, str]] = []
    for path in sorted(projects_dir.iterdir()):
        if path.suffix != ".json":
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        results.append({"name": path.stem, "path": data.get("path", "")})
    return results


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True))
async def project_readme(ctx: Context) -> str:
    """Return README.md content from project root, or a fallback string if absent."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    readme = app_ctx.project_root / "README.md"
    if not readme.exists():
        return "No README.md found in project root."
    return readme.read_text(encoding="utf-8")


@mcp.resource("project://readme")
async def project_readme_resource() -> str:
    """MCP resource: project://readme — returns README.md content or fallback."""
    readme = Path.cwd() / "README.md"
    if not readme.exists():
        return "No README.md found in project root."
    return readme.read_text(encoding="utf-8")


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True))
async def project_structure(ctx: Context) -> str:
    """Return an indented directory tree (max depth 3) of the project root."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    return build_tree(app_ctx.project_root, exclude=set(_STRUCTURE_EXCLUDES))


@mcp.resource("project://structure")
async def project_structure_resource() -> str:
    """MCP resource: project://structure — indented tree of project root."""
    return build_tree(Path.cwd(), exclude=set(_STRUCTURE_EXCLUDES))
