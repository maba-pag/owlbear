"""Code-shape rules (TD-33): agents aim for 400 lines per module, the test fails at 500 raw lines."""

from __future__ import annotations

import asyncio
import warnings
from pathlib import Path
from typing import Any

from owlbear_delivery_next.change_contracts import tools
from owlbear_delivery_next.change_contracts.models import ErrorKind, Exit, StepKind
from owlbear_delivery_next.commands import mcp_server

SRC = Path(__file__).resolve().parents[1] / "src" / "owlbear_delivery_next"
WEB = SRC / "web"
VENDORED = (WEB / "vendor", WEB / "pds")  # third-party releases, not the package's own code
LIMIT = 500
FIELDS = 6  # T5: about six fields per object
WIDER = {"save_brief": 9}  # decisions and non_goals (reuse study v2, Sol finding 6); specified (TD-179 rule 1)
WIDER |= {"record_decision": 8}  # scope, the replacement it makes (TD-450), origin (D-01M5WAFJ99912ER7V0YEPJP2G5)
OWNED = [  # C-28: pages, scripts and styles count like modules
    p
    for p in WEB.rglob("*")
    if p.suffix in {".html", ".mjs", ".js", ".css"} and not any(p.is_relative_to(v) for v in VENDORED)
]


def test_every_module_is_within_the_limit() -> None:
    files = [*SRC.rglob("*.py"), *OWNED]
    counts = {str(p.relative_to(SRC)): len(p.read_text(encoding="utf-8").splitlines()) for p in files}
    over = sorted(f"{name} has {count} lines; split it by use case" for name, count in counts.items() if count > LIMIT)
    assert any(p.suffix == ".py" for p in files)  # the source tree was found: an empty one would pass vacuously
    assert over == []


def test_vocabularies_stay_small() -> None:
    if len(StepKind) > 11:  # TD-417: a guide, not a gate; a new kind's reason is recorded beside it in StepKind
        warnings.warn(f"{len(StepKind)} step kinds, more than the design's eleven", stacklevel=1)
    assert len(ErrorKind) <= 15
    assert {e for e in Exit if e is not Exit.PENDING} == {Exit.DONE, Exit.RETRY, Exit.ASK, Exit.BACK, Exit.STOP}
    assert len(Exit) == 6


def _resolve(node: dict[str, Any], defs: dict[str, Any]) -> dict[str, Any]:
    while "$ref" in node:
        node = defs[node["$ref"].rsplit("/", 1)[-1]]
    return node


def _objects(node: dict[str, Any], defs: dict[str, Any]) -> list[dict[str, Any]]:
    """The object schemas a field holds: itself, its array items, or its union members."""
    node = _resolve(node, defs)
    if "properties" in node or node.get("type") == "object":
        return [node]
    subs = [node["items"]] if "items" in node else []
    return [o for s in [*subs, *node.get("anyOf", []), *node.get("oneOf", [])] for o in _objects(s, defs)]


def _shape(name: str, obj: dict[str, Any], defs: dict[str, Any], depth: int = 0) -> list[str]:
    """T4/T5 problems of one object: an undescribed or opaque field, more than about six fields, deep nesting."""
    fields = obj.get("properties", {})
    problems = [f"{name}: {len(fields)} fields"] if len(fields) > WIDER.get(name, FIELDS) else []
    problems += [f"{name}: nested {depth} levels"] if depth > 1 else []
    problems += [f"{name}: an object without declared fields"] if not fields else []
    for field, node in fields.items():
        if not (node.get("description") or _resolve(node, defs).get("description")):
            problems.append(f"{name}.{field}: no description")
        problems += [p for o in _objects(node, defs) for p in _shape(f"{name}.{field}", o, defs, depth + 1)]
    return problems


def test_every_agent_tool_is_described_small_and_flat() -> None:
    """TD-63: no count of tools; each agent-facing tool has described fields, about six, one nesting level."""
    specs = [v for v in vars(tools).values() if isinstance(v, tools.Spec)]
    schemas = [(f"{s.name}:{s.model.__name__}", s.model.model_json_schema()) for s in specs]
    schemas += [(t.name, t.input_schema) for t in asyncio.run(mcp_server.mcp.list_tools())]
    assert {s.name for s in specs} >= {"submit_result", "ask_question", "report_wrong_premise", "report_missing_tool"}
    problems = [p for name, schema in schemas for p in _shape(name, schema, schema.get("$defs", {}))]
    assert problems == []
