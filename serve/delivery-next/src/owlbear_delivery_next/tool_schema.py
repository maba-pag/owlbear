"""A worker tool's JSON schema and its argument parsing, whose errors name the field with an example (T5)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

if TYPE_CHECKING:
    from collections.abc import Sequence

    from owlbear_delivery_next.tools import Args, Spec


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


def parse[T: Args](model: type[T], arguments: object) -> tuple[T | None, list[str]]:
    """Validate tool arguments; return the instance, or one error per field with an example."""
    try:
        data = json.loads(arguments) if isinstance(arguments, str) else arguments
        return model.model_validate(data), []
    except ValidationError as exc:
        errors = []
        for err in exc.errors():
            field = model.model_fields.get(str(err["loc"][0])) if err["loc"] else None
            example = f" - e.g. {json.dumps(field.examples[0])}" if field and field.examples else ""
            errors.append(f"{_loc(err['loc'])}: {err['msg']}{example}")
        return None, errors
    except ValueError:
        return None, ["arguments: not a JSON object - send the fields as one object"]
