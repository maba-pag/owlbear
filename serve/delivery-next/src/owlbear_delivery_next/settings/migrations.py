"""Forward migrations of stored records, keyed by the format they upgrade from."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import TypeAdapter

from owlbear_delivery_next.change_contracts.models import Role
from owlbear_delivery_next.change_contracts.profile_record import RoleModel
from owlbear_delivery_next.settings.config import Agent, Layer

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
PROFILE: Migrations = {1: roles_moved, 2: prefs_import_added, 3: prefs_basis_added}
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
}
