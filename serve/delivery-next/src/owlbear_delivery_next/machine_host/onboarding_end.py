"""Add project's ending (item 15): registered, profile confirmed and ready for Delivery, as three separate facts."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.github import branch_rules, repo_target
from owlbear_delivery_next.machine_host import onboarding_probe as probe
from owlbear_delivery_next.state_store.store import Store

if TYPE_CHECKING:
    from owlbear_delivery_next.machine_host.onboarding_job import Job

LOCAL = "Local only: not on GitHub"


def facts(job: Job) -> dict[str, Any]:
    """The three facts, what is missing with its fix, and the chat-tool files' results."""
    plan, said = job.plan, job.result("files").get("said", [])
    if not plan.get("github"):
        return {"local": True, "registered": False, "profile": False, "ready": False, "missing": [LOCAL], "files": said}
    machine, registered = job.context["machine"], job.result("register")
    p = machine.get(registered.get("id") or probe.registered_id(Path(plan["folder"])))
    p._ready()  # noqa: SLF001 - a host checks readiness in the background as it loads; the ending waits for a result
    info, missing = p.info(), []
    if info["state"] != "loaded":  # a host that failed to load serves nothing
        missing.append(f"project: {info['state']}" + (f": {info['reason']}" if info.get("reason") else ""))
    store = job.context.get("store") or Store.open(Path(plan["folder"]), repair=True)
    prof = store.read_profile()
    if info.get("blocked"):
        missing.append(f"settings: {info['blocked']}")
    missing += [f"readiness: {line}" for line in info.get("ready") or []]
    missing += _rules(job, store)
    if info.get("setup"):
        missing.append(f"chats can't reach Delivery: register its chat server; {' '.join(said)}")
    return {
        "local": False,
        "registered": True,
        "id": p.entry.id,
        "profile": bool(prof and prof.confirmed_at),
        "ready": not missing,
        "missing": missing,
        "files": said,
    }


def _rules(job: Job, store: Store) -> list[str]:
    """Why the project's merge method isn't allowed here, and each need its rules still miss, with its link."""
    method = store.settings().prefs.merge_method
    repository = job.plan["repository"]
    gh = probe.client(repository, probe.account(repository), Path(job.plan["folder"]))
    if (remote := repo_target.view(gh, repository)) is None:
        return [f"merge method: {repository} can't be read"]
    rules = branch_rules.read(gh, repository, remote.default_branch or "main")
    allowed = branch_rules.allowed_methods({m.value for m in remote.methods}, rules)
    out = []
    if not allowed:
        out.append("merge method: this repository and its rules allow none; change them on GitHub")
    elif method is None or method.value not in allowed:
        shown = method.value if method else "unset"
        out.append(f"merge method: {shown} is not allowed here ({', '.join(sorted(allowed))} are); set it on Settings")
    if job.plan.get("protect") and job.result("protection").get("listed"):  # OwlBear could only list the changes
        unmet = [i for i in branch_rules.compare(rules).needs if not i.holds]
        out += [f"rules: {i.sentence}; change it on GitHub: {branch_rules.settings_url(repository, i.source)}"
                for i in unmet]  # fmt: skip
    return out


def merge_allowed(found: dict[str, Any]) -> list[str]:
    """The merge methods the probed repository allows, for Choices; every method for a repository still to make."""
    if (rules := found.get("rules")) is not None:
        return rules["allowed"]
    if (remote := found.get("github")) is not None:
        return remote["methods"]
    return list(branch_rules.METHODS)
