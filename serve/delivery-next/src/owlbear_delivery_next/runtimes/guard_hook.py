"""The shell guard's warnings in a step: a pre-tool hook that tells the agent what the guard found and lets it run.

D-01M6DX04FRP680Z4GGHK5B9VRC: below ``strict`` some findings only warn. The hook judges each shell call before it
runs, at the level its worker was built with; on a warning it journals ``warned`` and hands the agent the finding as
added context, never a permission decision, so the permission callback stays the only place that refuses.
"""

from __future__ import annotations

import traceback
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.change_contracts.permissions import Request, judge
from owlbear_delivery_next.local_system.mask import redact

if TYPE_CHECKING:
    from owlbear_delivery_next.runtimes.sdk_adapter import _Step

SHELL = "bash"  # the runtime's shell tool; its arguments hold the whole command
WARNING = (  # D-01M6DX667JAWPWV2RY3BB4G879
    "OwlBear's shell guard lets this command run but warns: {reason}. Check whether it breaks a rule; if it does, fix "
    "the cause or ask."
)


def pre_tool(step: _Step, data: dict[str, Any], offered: frozenset[str]) -> dict[str, str] | None:
    """The added context for a shell call the guard only warns about, else None; a failure stops the step."""
    if data.get("toolName") != SHELL:
        return None
    text = str((data.get("toolArgs") or {}).get("command") or "")
    try:
        cfg = step.cfg
        req = Request("shell", (text,), text=text)
        verdict = judge(cfg.policy, req, offered, memory=cfg.user.memory, level=cfg.user.guard)
    except Exception:  # noqa: BLE001 - the SDK would swallow it; the step records it and stops instead
        error = redact(traceback.format_exc())
        step.log(event="hook-failed", hook="preToolUse", error=error)
        step.finish("error", detail=f"the shell guard's warning hook failed: {error}")
        return None
    if verdict is None or verdict.refuse:
        return None
    reason = redact(verdict.reason)
    step.log(event="warned", kind="shell", request=[redact(text)], reason=reason)
    return {"additionalContext": WARNING.format(reason=reason)}
