"""TD-171: each layer imports only itself and the layers before it.

The modules are still flat; the folders follow this allocation (`layers-4`, agreed with Sol) when the code moves. Until
then this test keeps today's imports movable: a module in no layer, or an import of a later layer, fails it. PENDING
lists planned upward edges still open; a fixed one must leave it (the `setup` split closed the last six).
"""

import ast
from importlib.resources import files
from pathlib import Path

ROOT = Path(str(files("owlbear_delivery_next")))
NAME = "owlbear_delivery_next"
LAYERS: dict[str, tuple[str, ...]] = {
    "local_system": (
        "storage_io", "mask", "codebase", "shell_parse", "processes", "process_probe", "lint", "preload", "data_repo",
        "local_home", "git", "git.*", "github", "github.*", "git_files", "text_files",
    ),
    "change_contracts": (
        "models", "failures", "evidence", "spend", "visual_records", "inbox", "profile_record", "tools", "tool_schema",
        "preparation", "permissions", "amendment_records", "dispute_tools", "round_records",
    ),
    "change_flow": ("loop", "moves", "budgets", "status", "progress", "brief_tools", "steps.worktree", "repairs",
                    "disputes", "round_flow", "rebuilds", "round_marks", "plan_rounds", "brief_rounds"),
    "design_packs": ("design_pack", "detector", "pack_update", "calibration", "pack_git", "design_tools"),
    "settings": ("config", "roles", "migrations", "profile", "rounds"),
    "state_store": (
        "store", "profile_share", "briefs", "change_record", "backlog", "backlog_issues", "backlog_migrate",
    ),
    "runtimes": (
        "ahp", "catalogue", "sdk_usage", "session_result", "missing", "results", "sdk_adapter", "sdk_teardown",
        "prompts", "step_inbox", "window_files", "vscode_adapter", "vscode_contract", "vscode_step", "leftovers",
        "model_choices", "subagents", "amendments", "copilot_cli", "readiness",
    ),
    "workflow_steps": ("steps", "steps.*", "held", "overlap", "sessions", "session_choice"),
    "pack_runs": ("pack_candidate", "pack_job", "pack_replay", "visual_settled", "pack_updater", "pack_rounds",
                  "pack_run"),
    "project_host": ("host", "api", "answers", "config_routes", "memory_routes", "backlog_routes", "pack_routes",
                     "pages", "launches", "brief_routes"),
    "commands": ("__init__", "__main__", "cli", "mcp_server", "step_mcp", "runner", "setup"),
}  # fmt: skip
ORDER = list(LAYERS)
PENDING: set[tuple[str, str]] = set()


def _name(path: Path) -> str:
    parts = [p for p in path.relative_to(ROOT).with_suffix("").parts if p != "__init__"]
    return ".".join(parts) or "__init__"


MODULES = {_name(p): p for p in ROOT.rglob("*.py") if "__pycache__" not in p.parts}


def _layer(module: str) -> str | None:
    found = (
        n for n, ms in LAYERS.items() for m in ms if module == m or (m.endswith(".*") and module.startswith(m[:-1]))
    )
    return next(found, None)


def _imports(path: Path) -> set[str]:
    """The package modules a file imports, type-only imports included: they are dependencies too."""
    out = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith(NAME):
            rest = node.module[len(NAME) :].lstrip(".")
            for alias in node.names:
                sub = f"{rest}.{alias.name}" if rest else alias.name
                out.add(sub if sub in MODULES else rest or sub)
        elif isinstance(node, ast.Import):
            out |= {a.name[len(NAME) + 1 :] for a in node.names if a.name.startswith(f"{NAME}.")}
    return {m for m in out if m in MODULES}


def _upward() -> set[tuple[str, str]]:
    return {
        (m, d)
        for m, path in MODULES.items()
        for d in _imports(path)
        if d != m and ORDER.index(_layer(d) or ORDER[0]) > ORDER.index(_layer(m) or ORDER[-1])
    }


def test_every_module_has_a_layer() -> None:
    assert sorted(m for m in MODULES if _layer(m) is None) == []


def test_each_layer_imports_only_itself_and_the_layers_before_it() -> None:
    assert sorted(_upward() - PENDING) == []


def test_a_pending_upward_import_leaves_the_list_once_it_is_gone() -> None:
    assert sorted(PENDING - _upward()) == []
