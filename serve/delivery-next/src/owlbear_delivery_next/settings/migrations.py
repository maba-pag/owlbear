"""Forward migrations of stored records, keyed by the format they upgrade from."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import TypeAdapter

from owlbear_delivery_next.change_contracts.models import Role
from owlbear_delivery_next.change_contracts.profile_record import RoleModel
from owlbear_delivery_next.settings import carried
from owlbear_delivery_next.settings.config import Agent, Layer
from owlbear_delivery_next.settings.improvement import CATEGORIES

if TYPE_CHECKING:
    from collections.abc import Callable

type Migrations = dict[int, Callable[[dict[str, Any]], dict[str, Any]]]
ROLES: TypeAdapter[dict[Role, RoleModel]] = TypeAdapter(dict[Role, RoleModel])


def roles_moved(data: dict[str, Any]) -> dict[str, Any]:
    """Profile format 1 to 2: the role overrides moved to the project settings; each is checked, then dropped."""
    ROLES.validate_python(data.pop("roles", {}))
    return data


def prefs_import_added(data: dict[str, Any]) -> dict[str, Any]:
    """Profile format 2 to 3: the legacy preference import marker (R15); older runtimes refuse format 3."""
    return data


def prefs_basis_added(data: dict[str, Any]) -> dict[str, Any]:
    """Profile format 3 to 4: the claim's config basis (R15); a pending claim without one never fills on its own."""
    return data


def with_roles(layer: Layer, found: dict[Role, RoleModel]) -> Layer:
    """The layer with old role overrides filling only the model and effort fields it leaves empty."""
    agents = dict(layer.agents)
    for role, old in found.items():
        own = agents.get(role, Agent())
        agents[role] = own.model_copy(update={"model": own.model or old.model, "effort": own.effort or old.effort})
    return layer.model_copy(update={"agents": agents})


def _challenged(brief: object) -> None:
    if isinstance(brief, dict):
        if "reviewed" in brief:
            brief["challenged"] = brief.pop("reviewed")
        for snapshot in brief.get("approved") or []:
            _challenged(snapshot)


def brief_challenged(data: dict[str, Any]) -> dict[str, Any]:
    """Change format 1 to 2: the brief review is a challenge (TD-73); the field is renamed in every brief snapshot.

    A format-1 consent may still carry ``queued_at`` from the removed merge queue (340cb6d59); it is dropped.
    """
    _challenged(data.get("brief"))
    if isinstance(consent := data.get("consent"), dict):
        consent.pop("queued_at", None)
    return data


def visual_decided(data: dict[str, Any]) -> dict[str, Any]:
    """Change format 2 to 3: the owner decides a visual round (TD-79); a capture keeps no accept or repair answer."""
    for capture in (data.get("visual"), data.get("before")):
        if isinstance(capture, dict):
            capture.pop("decision", None)
            capture.pop("note", None)
    return data


def seed_dropped(data: dict[str, Any]) -> dict[str, Any]:
    """Settings format 1 to 2: declared preparation options replace the seed command (TD-96); it is dropped.

    A seed command names no isolation or cleanup, so it cannot become an option; the owner declares one instead.
    """
    data.pop("seed", None)
    return data


def rounds_kept(data: dict[str, Any]) -> dict[str, Any]:
    """Change format 3 to 4: TD-208's loops replace TD-189's round fields on tasks and disputes; they are dropped."""
    for task in (data.get("plan") or {}).get("tasks") or []:
        if isinstance(task, dict):
            task.pop("found_in", None)
            for d in task.get("disputes") or []:
                if isinstance(d, dict):
                    d.pop("direct", None)
                    d.pop("repeat_of", None)
    return data


def judge_renamed(data: dict[str, Any]) -> dict[str, Any]:
    """Settings format 2 to 3: the designer role is the design judge (TD-169); its settings keep their values."""
    agents = data.get("agents")
    if isinstance(agents, dict) and "designer" in agents:
        agents["design-judge"] = agents.pop("designer")
    return data


def minutes_added(data: dict[str, Any]) -> dict[str, Any]:
    """Settings format 3 to 4: an agent may set its session time limit (TD-286); older runtimes refuse format 4."""
    return data


def labels_added(data: dict[str, Any]) -> dict[str, Any]:
    """Settings format 4 to 5: pull request labels and the marker switch (TD-308); older runtimes refuse format 5."""
    return data


def labelled_added(data: dict[str, Any]) -> dict[str, Any]:
    """Change format 4 to 5: the PR its labels went on (TD-308); older runtimes refuse format 5."""
    return data


def subagents_added(data: dict[str, Any]) -> dict[str, Any]:
    """Settings format 5 to 6: each role's subagent switch (TD-376) replaces the planner-only experiment's."""
    data.pop("explore", None)
    return data


def sessions_added(data: dict[str, Any]) -> dict[str, Any]:
    """Settings format 6 to 7: agent sessions at once per project (TD-336); older runtimes refuse format 7."""
    return data


def test_roles_added(data: dict[str, Any]) -> dict[str, Any]:
    """Settings format 7 to 8: the test reviewer and curator roles (TD-339); older runtimes refuse format 8."""
    return data


def watcher_added(data: dict[str, Any]) -> dict[str, Any]:
    """Settings format 8 to 9: the watcher's role and its switch (2026-10-23); older runtimes refuse format 9."""
    return data


def defaults_removed(data: dict[str, Any]) -> dict[str, Any]:
    """Settings format 9 to 10: code ships no defaults (2026-10-23); ``settings_carry.carry`` fills Global once."""
    return data


def machine_added(data: dict[str, Any]) -> dict[str, Any]:
    """Settings format 10 to 11: Global's machine settings (2026-10-23); the first machine's move fills them."""
    return data


def spotter_renamed(data: dict[str, Any]) -> dict[str, Any]:
    """Settings format 11 to 12: the watcher became the Spotter (2026-10-25); older runtimes refuse format 12.

    The switch's ``true`` becomes the learning mode and ``false`` the mode off; unset stays unset, and the role's
    agent settings move to the new name. Nothing else is invented: the Spotter's other settings start unset.
    """
    switch = data.pop("watcher", None)
    if switch is not None:
        data["spotter"] = {"mode": "learning" if switch else "off"}
    agents = data.get("agents")
    if isinstance(agents, dict) and "watcher" in agents:
        agents["spotter"] = agents.pop("watcher")
    return data


def prefs_added(data: dict[str, Any]) -> dict[str, Any]:
    """Settings format 12 to 13: the five preferences, unset until a layer sets them (R15); older runtimes refuse 13."""
    return data


def spotter_switched(data: dict[str, Any]) -> dict[str, Any]:
    """Settings format 13 to 14: an on/off switch and four categories' actions replace the Spotter's mode (2026-10-26).

    Off stays off. Learning recorded what the Spotter would do, so it becomes on with every category's action
    ``record``. Live becomes on with the actions left unset in that layer: a wider layer's apply, else the owner
    chooses them (D-01M5WB09Z3ZKJVN02WGWVHGWBH). The Spotter's other settings keep their values; older runtimes
    refuse format 14.

    An unknown mode is refused: the layer cannot be migrated, and nothing guesses its switch.

    Raises:
        ValueError: The mode is none of off, learning and live.
    """
    spotter = data.get("spotter")
    if isinstance(spotter, dict) and "mode" in spotter:
        mode = spotter.pop("mode")
        if mode is not None and (not isinstance(mode, str) or mode not in {"off", "learning", "live"}):
            msg = f"the Spotter's mode {mode!r} is none of off, learning and live"
            raise ValueError(msg)
        if mode is not None:
            spotter["switch"] = "off" if mode == "off" else "on"
        if mode == "learning":
            spotter |= dict.fromkeys(CATEGORIES.values(), "record")
    return data


def _retired(data: dict[str, Any], key: str, allowed: Callable[[object], bool]) -> None:
    """Drop a retired setting; a value the format never allowed is refused, not dropped."""
    if key in data:
        value = data.pop(key)
        if not allowed(value):
            msg = f"the retired setting {key} is {value!r}, which the format never allowed"
            raise ValueError(msg)


def _on_off(value: object) -> bool:
    if not isinstance(value, dict) or not set(value) <= {"sdk", "window"}:
        return False
    return all(type(on) is bool for on in value.values())


def _flag(value: object) -> bool:
    return value is None or type(value) is bool


def _browser_only(value: object) -> bool:
    return value is None or (isinstance(value, list) and all(category == "browser" for category in value))


def window_runtime_dropped(data: dict[str, Any]) -> dict[str, Any]:
    """Settings format 14 to 15: the window runtime's switches and per-agent settings go (2026-10-26).

    Only a VS Code window read the runtimes, the visibility and the tool categories; no step did, so none applied.
    A value the format never allowed is refused, not dropped.
    """
    _retired(data, "runtimes", _on_off)
    _retired(data, "visible", _flag)
    agents = data.get("agents")
    if isinstance(agents, dict):
        for agent in agents.values():
            if isinstance(agent, dict):
                _retired(agent, "runtime", lambda v: v is None or v in ("sdk", "window"))
                _retired(agent, "visible", _flag)
                _retired(agent, "categories", _browser_only)
    return data


def _whole(value: object) -> bool:
    return value is None or (type(value) is int and value >= 0)


DAILY = (
    "spotter_budget",
    "retro_budget",
    "retro_verbose_cap",
)  # the daily credit budgets, each in Global's machine part


def daily_budgets_dropped(data: dict[str, Any]) -> dict[str, Any]:
    """Settings format 15 to 16: no daily credit budgets (D-01M5XCD49YHHR1NQKKY8TQD0C3); each leaves Global's machine.

    Each look, Retro run and paid replay run stops at its own credit limit instead. A budget the format never allowed
    (a whole number, at least 0) is refused, not dropped. Only Global has a machine part; other layers pass unchanged.
    """
    machine = data.get("machine")
    if isinstance(machine, dict):
        for key in DAILY:
            _retired(machine, key, _whole)
    return data


def credit_limits_written(data: dict[str, Any]) -> dict[str, Any]:
    """Global's format 15 to 16: the credit limits are written into Global once (D-01M5XCD49YHHR1NQKKY8TQD0C3).

    The per-look limit goes into the Spotter's settings, the Retro and paid replay run limits into the machine part,
    each at five times its expected cost (``settings.carried``). A section Global leaves out, or sets to null, is made
    with the limit alone; every other value stays. ``state_store.settings_carry.limits`` saves and publishes the result.
    """
    data = daily_budgets_dropped(data)
    spotter = data.get("spotter") or {}
    machine = data.get("machine") or {}
    if isinstance(spotter, dict) and isinstance(machine, dict):  # anything else is left for validation to refuse
        spotter.setdefault("look_credit_limit", carried.LOOK_CREDIT_LIMIT)
        machine.setdefault("retro_run_credit_limit", carried.RETRO_RUN_CREDIT_LIMIT)
        machine.setdefault("replay_run_credit_limit", carried.REPLAY_RUN_CREDIT_LIMIT)
        data["spotter"], data["machine"] = spotter, machine
    return data


def runtime_switch_dropped(data: dict[str, Any]) -> dict[str, Any]:
    """Profile format 4 to 5: the per-project runtime switch goes; steps run only through the SDK (2026-10-26).

    A switch that names neither managed nor vscode was never valid, so it is refused, not dropped.
    """
    _retired(data, "runtime", lambda v: v in ("managed", "vscode"))
    return data


def tests_added(data: dict[str, Any]) -> dict[str, Any]:
    """Change format 5 to 6: a test review's record and step (TD-373); older runtimes refuse format 6."""
    return data


def waivers_added(data: dict[str, Any]) -> dict[str, Any]:
    """Change format 6 to 7: the criteria the owner accepted unmet (TD-341); older runtimes refuse format 7."""
    return data


def held_records_added(data: dict[str, Any]) -> dict[str, Any]:
    """Change format 7 to 8: held results kept with the Change and their receipts (RUN-04); older runtimes refuse 8."""
    return data


CHANGE: Migrations = {
    1: brief_challenged,
    2: visual_decided,
    3: rounds_kept,
    4: labelled_added,
    5: tests_added,
    6: waivers_added,
    7: held_records_added,
}
PROFILE: Migrations = {1: roles_moved, 2: prefs_import_added, 3: prefs_basis_added, 4: runtime_switch_dropped}
CONFIG: Migrations = {
    1: seed_dropped,
    2: judge_renamed,
    3: minutes_added,
    4: labels_added,
    5: subagents_added,
    6: sessions_added,
    7: test_roles_added,
    8: watcher_added,
    9: defaults_removed,
    10: machine_added,
    11: spotter_renamed,
    12: prefs_added,
    13: spotter_switched,
    14: window_runtime_dropped,
    15: daily_budgets_dropped,
}
GLOBAL: Migrations = CONFIG | {15: credit_limits_written}  # the Global layer's: only it is written the limits
