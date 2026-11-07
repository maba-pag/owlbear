"""Explicit shaping-role messages shared by initial launch and later queued hand-offs."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from owlbear_delivery_next.runtimes.ahp import Json
    from owlbear_delivery_next.runtimes.vscode_contract import StepSpec


def build(spec: StepSpec, schema: Json | None, agent: Json | None) -> Json:
    """Name model, effort, context and listed agent without changing the owner's picker."""
    config: Json = {} if schema is not None and "thinkingLevel" not in schema else {"thinkingLevel": spec.effort}
    sizes = ((schema or {}).get("contextSize") or {}).get("enum") or []
    if sizes:
        labels = (schema or {})["contextSize"].get("enumDescriptions") or []
        default = next((s for s, d in zip(sizes, labels, strict=False) if d == "Default"), min(sizes))
        config["contextSize"] = max(sizes) if spec.context == "long" else default
    message: Json = {"text": spec.prompt, "origin": {"kind": "user"}, "model": {"id": spec.model, "config": config}}
    if agent:
        message["agent"] = agent
    return message


def rejection(ev: Json | None, client: str, seq: int) -> str | None:
    """The host's complete rejection for this client's exact action."""
    if not ev or ev.get("method") != "action":
        return None
    params = ev.get("params") or {}
    origin = params.get("origin") or {}
    if "rejectionReason" not in params or (origin.get("clientId"), origin.get("clientSeq")) != (client, seq):
        return None
    return str(params["rejectionReason"]) or "no reason given"
