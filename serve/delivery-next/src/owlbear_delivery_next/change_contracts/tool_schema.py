"""A worker tool's JSON schema and its argument parsing, whose errors name the field with an example (T5).

A value over a field's limit is refused with its length, the limit and what to cut (C-28); nothing is truncated.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, get_args

from pydantic import BaseModel, ValidationError

if TYPE_CHECKING:
    from collections.abc import Sequence

    from pydantic.fields import FieldInfo
    from pydantic_core import ErrorDetails

    from owlbear_delivery_next.change_contracts.tools import Args, Spec

TEXT, ITEMS = "shorten it", "combine related items; leave out none the result needs"
# What to cut from a field over its limit, by the model that declares it: the evidence the field carries stays.
SHORTEN = {
    ("PlanTask", "goal"): "name each criterion by its id and how the Builder knows it is met; leave out how to "
    "build it, or split the task",
    ("PlanTask", "scope"): "name the directories that hold the files instead of each file",
    ("PlanTask", "checks"): "list each check once",
    ("PlanResult", "tasks"): "merge small tasks into larger ones; every criterion stays covered",
    ("BuildResult", "summary"): "say what changed and why in a few sentences; the commit shows the rest",
    ("BuildResult", "checks"): "report each task check once, as it last ran",
    ("ReviewResult", "findings"): "merge findings with the same fix; leave out none that must be fixed",
    ("ReviewResult", "covered_paths"): "name the directories you read instead of each file",
    ("VisualReviewResult", "covered_paths"): "list each required screenshot once, by its exact file name",
}


def _inline(node: object, defs: dict[str, Any]) -> object:
    if isinstance(node, dict):
        if "$ref" in node:
            return _inline(defs[node["$ref"].rsplit("/", 1)[-1]], defs)
        return {k: _inline(v, defs) for k, v in node.items() if k != "$defs"}
    return [_inline(v, defs) for v in node] if isinstance(node, list) else node


def schema(spec: Spec) -> dict[str, Any]:
    """Return the tool's JSON schema with every reference inlined."""
    raw = spec.model.model_json_schema()
    inlined = _inline(raw, raw.get("$defs", {}))
    return inlined if isinstance(inlined, dict) else raw


def _loc(loc: Sequence[int | str]) -> str:
    out = ""
    for part in loc:
        out += f"[{part}]" if isinstance(part, int) else (f".{part}" if out else str(part))
    return out or "arguments"


def _model(annotation: object) -> type[BaseModel] | None:
    """The model a field holds: itself, its list's items or a member of its union."""
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return annotation
    return next((m for a in get_args(annotation) if (m := _model(a)) is not None), None)


def _field(model: type[BaseModel], loc: Sequence[int | str]) -> tuple[tuple[str, str], FieldInfo | None, int]:
    """The field an error's path ends in: (the model declaring it, its name), its info and the list indices after it."""
    key, info, depth, here = ("", ""), None, 0, model
    for part in loc:
        found = here.model_fields.get(part) if isinstance(part, str) and here is not None else None
        if found is not None and here is not None:
            key, info, depth, here = (_declaring(here, str(part)), str(part)), found, 0, _model(found.annotation)
        depth += isinstance(part, int)
    return key, info, depth


def _declaring(model: type[BaseModel], name: str) -> str:
    """The class whose advice *name* takes: the model's own, else the declaring class's, which subclasses share."""
    if (model.__name__, name) in SHORTEN:
        return model.__name__
    return next(c.__name__ for c in reversed(model.__mro__) if name in getattr(c, "__annotations__", {}))


def _example(info: FieldInfo | None, depth: int) -> str:
    example = info.examples[0] if info and info.examples else None
    for _ in range(depth):
        example = example[0] if isinstance(example, list) and example else example
    return f" - e.g. {json.dumps(example)}" if example is not None else ""


def _error(model: type[BaseModel], err: ErrorDetails) -> str:
    """One field's error: over a limit its length, the limit and what to cut, else the message and an example."""
    where, (key, info, depth) = _loc(err["loc"]), _field(model, err["loc"])
    limit, given, advice = (err.get("ctx") or {}).get("max_length"), err.get("input"), SHORTEN.get(key, "")
    if err["type"] == "string_too_long" and isinstance(given, str):
        return f"{where}: {len(given)} characters, at most {limit} - {advice or TEXT}"
    if err["type"] == "too_long" and isinstance(given, list):
        return f"{where}: {len(given)} items, at most {limit} - {advice or ITEMS}"
    return f"{where}: {err['msg']}{_example(info, depth)}"


def parse[T: Args](model: type[T], arguments: object) -> tuple[T | None, list[str]]:
    """Validate tool arguments; return the instance, or one error per field with an example or, over a limit, a cut."""
    try:
        data = json.loads(arguments) if isinstance(arguments, str) else arguments
        return model.model_validate(data), []
    except ValidationError as exc:
        return None, [_error(model, err) for err in exc.errors()]
    except ValueError:
        return None, ["arguments: not a JSON object - send the fields as one object"]
