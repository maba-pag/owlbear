"""What each runtime offers beyond the shared baseline (runtime research P15 to P19).

The settings page shows it; a missing-tool report is classified against it (TD-36). It does not route steps yet.
"""

from __future__ import annotations

import re
from typing import Any

CATALOGUE: dict[str, Any] = {
    "baseline": "the runtime's own tools (files, edit, shell) and Delivery's result tools",
    "runtimes": [
        {
            "runtime": "sdk",
            "adds": "nothing beyond the baseline",
            "mcp": "only servers Delivery passes",
            "live_view": "no (VS Code shows a snapshot at most)",
            "outside_writes": "Delivery's hard guard (TD-45)",
        },
        {
            "runtime": "window",
            "adds": "the VS Code window's tools: browser, tasks, problems",
            "mcp": "your VS Code mcp.json",
            "live_view": "yes",
            "outside_writes": "the watcher, once it exists (D6)",
        },
    ],
    "categories": {
        "browser": {
            "runtime": "window",
            "tools": [
                "openBrowserPage",
                "readPage",
                "screenshotPage",
                "navigatePage",
                "clickElement",
                "typeInPage",
                "hoverElement",
                "dragElement",
                "handleDialog",
                "runPlaywrightCode",
            ],
        },
        "problems": {"runtime": "window", "tools": ["get_errors"]},
        "tasks": {"runtime": "window", "tools": ["runTask", "getTaskOutput", "createAndRunTask"]},
    },
}


def _key(name: str) -> str:
    """One spelling for a tool name: ``open_browser_page`` and ``openBrowserPage`` are the same tool."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def runtime_of(names: set[str]) -> str | None:
    """The runtime whose category or tool carries one of *names*, if the catalogue lists it."""
    keys = {_key(n) for n in names}
    for category, entry in CATALOGUE["categories"].items():
        if keys & {_key(category), *(_key(t) for t in entry["tools"])}:
            return entry["runtime"]
    return None
