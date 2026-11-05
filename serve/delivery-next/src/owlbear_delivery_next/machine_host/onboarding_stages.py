"""Add project's stages (item 15), each checking the real state before it acts, so Retry never repeats an effect."""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.commands import setup, setup_profile
from owlbear_delivery_next.github import branch_rules, repo_target
from owlbear_delivery_next.github.provider import MergeMethod
from owlbear_delivery_next.local_system import local_home, onboarding_git
from owlbear_delivery_next.machine_host import onboarding_end
from owlbear_delivery_next.machine_host import onboarding_probe as probe
from owlbear_delivery_next.machine_host.onboarding_job import Waiting
from owlbear_delivery_next.runtimes import readiness
from owlbear_delivery_next.settings.config import Layer, Prefs
from owlbear_delivery_next.state_store import github_writer, profile_repair
from owlbear_delivery_next.state_store.store import Store

if TYPE_CHECKING:
    from owlbear_delivery_next.github.gh_client import GhClient
    from owlbear_delivery_next.machine_host.onboarding_job import Job, Stage

CI_WAIT = 600.0  # seconds a generated CI gets to report on the pushed commit
CI_POLL = 10.0


class StageError(RuntimeError):
    """A stage that cannot go on; its text says what was found and what to do."""


def _folder(job: Job) -> Path:
    return Path(job.plan["folder"])


def _client(job: Job) -> GhClient:
    if "client" not in job.context:
        repository = job.plan["repository"]
        cwd = onboarding_git.nearest_existing(_folder(job))
        job.context["client"] = probe.client(repository, probe.account(repository), cwd)
    return job.context["client"]


def _access(job: Job) -> Any:  # noqa: ANN401 - git.access.Access
    return _client(job).writer.access()  # type: ignore[union-attr]


def _remote(job: Job) -> repo_target.RepoState | None:
    return repo_target.view(_client(job), job.plan["repository"])


def folder(job: Job) -> dict[str, Any]:
    """Create the folder, or clone the repository into it (E1)."""
    path = _folder(job)
    if job.plan["entry"] != "E1":
        path.mkdir(parents=True, exist_ok=True)
        return {}
    if (path / ".git").exists():
        if onboarding_git.folder_state(path).git == "commits":
            if job.record("folder").get("intent"):  # this run's clone, stopped before its checkout ended
                onboarding_git.finish_checkout(path)
            return {"cloned": bool(job.record("folder").get("intent"))}
        remote = _remote(job)  # an interrupted clone: fetch what it lacks
        onboarding_git.pull_default(path, remote.default_branch if remote else "main", _access(job))
        return {"cloned": True}
    job.intend("folder", f"clone {job.plan['repository']} into {path}")
    onboarding_git.clone(path.parent, probe.url(job.plan["repository"]), path.name, _access(job))
    return {"cloned": True}


def git(job: Job) -> dict[str, Any]:
    """``git init`` where there is no Git, ``origin`` to the target before any commit, and a chosen author."""
    path, plan = _folder(job), job.plan
    if not (path / ".git").exists():
        onboarding_git.init(path)
    if plan.get("github") and onboarding_git.folder_state(path).origin is None:
        onboarding_git.set_origin(path, probe.url(plan["repository"]))
    if chosen := probe.author(plan):
        onboarding_git.write_author(path, *chosen)
    return {}


def commit(job: Job) -> dict[str, Any]:
    """The first commit: the folder's files as they are, or the starter files; the CI file only where ticked."""
    path, plan = _folder(job), job.plan
    state = onboarding_git.folder_state(path)
    had_files = plan.get("had_files", state.has_files)  # what the probe found, not the starter files written since
    ci = bool(plan.get("ci") and plan.get("github")) and not plan.get("had_workflows", state.has_workflows)
    if state.git == "commits":  # a commit this run made before its result was recorded, else none of ours
        mine = bool(job.record("commit").get("intent"))
        return {"sha": onboarding_git.head(path) if mine else "", "ci": ci and mine}
    if had_files and not plan.get("files_warned"):
        msg = "the folder's files are committed only after the secrets warning was shown and confirmed"
        raise StageError(msg)
    job.intend("commit", "write the starter files and make the first commit")
    onboarding_git.starter_files(path, plan["name"], ci, readme=not had_files)
    return {"sha": onboarding_git.first_commit(path, "First commit"), "ci": ci}


def repository(job: Job) -> dict[str, Any]:
    """Create the GitHub repository with the visibility sent explicitly; a lost answer adopts only a match."""
    plan = job.plan
    owner, name = probe.split(plan["repository"])
    if (found := _remote(job)) is not None:
        if found.empty and found.visibility == plan["visibility"] and owner.casefold() == found.repository.split(
                "/")[0].casefold() and job.record("repository").get("intent"):  # fmt: skip
            return {"id": found.id, "visibility": found.visibility, "adopted": True}
        msg = (f"{plan['repository']} already exists ({'empty' if found.empty else 'with commits'}, "
               f"{found.visibility}); OwlBear never adopts a repository it did not create")  # fmt: skip
        raise StageError(msg)
    job.intend("repository", f"create {plan['repository']} ({plan['visibility']})")
    made = repo_target.create(_client(job), owner, name, plan["visibility"])
    if made.visibility != plan["visibility"]:
        msg = f"{plan['repository']} was created {made.visibility}, not {plan['visibility']}: change it on GitHub"
        raise StageError(msg)
    return {"id": made.id, "visibility": made.visibility}


def push(job: Job) -> dict[str, Any]:
    """The first push of the local commits, or an unborn clone's pull of the repository's (E4b)."""
    path = _folder(job)
    remote, local = _remote(job), onboarding_git.folder_state(path).git == "commits"
    if remote is None:
        msg = f"{job.plan['repository']} is not on GitHub"
        raise StageError(msg)
    if not remote.empty and local:
        return {"pushed": False}
    if not remote.empty:
        onboarding_git.pull_default(path, remote.default_branch, _access(job))
        return {"pulled": remote.default_branch}
    job.intend("push", "push the first commit")
    onboarding_git.push_first(path, _access(job))
    return {"pushed": True}


def ci(job: Job) -> dict[str, Any]:
    """A bounded wait for the generated ``CI`` on the pushed commit; it is required only when it reported."""
    made = job.result("commit")
    if not made.get("ci"):
        return {"generated": False}
    deadline, status = time.monotonic() + CI_WAIT, "missing"
    while time.monotonic() < deadline:
        status = repo_target.ci_status(_client(job), job.plan["repository"], made["sha"])
        if status not in {"missing", "queued", "in_progress", "pending"}:
            break
        time.sleep(CI_POLL)
    return {"generated": True, "status": status}


def protection(job: Job) -> dict[str, Any]:
    """OwlBear's ruleset where the branch has no rules, or the ticked changes where one ruleset governs it."""
    plan = job.plan
    remote = _remote(job) if plan.get("protect") else None
    if not plan.get("protect"):
        return {"applied": False, "why": "not ticked"}
    if remote is None or MergeMethod.MERGE not in remote.methods:
        return {"applied": False, "why": "this repository doesn't allow merge commits; OwlBear's protection needs them"}
    branch, client = remote.default_branch or "main", _client(job)
    rules = branch_rules.read(client, plan["repository"], branch)
    if rules.plan_limit:
        return {"applied": False, "why": rules.plan_limit}
    if (landed := _landed(job, client, rules)) is not None:
        return landed
    if not (rules.rules or rules.classic):
        ran = job.result("ci")
        body = branch_rules.new_ruleset(
            branch, require_ci=bool(ran.get("generated") and ran.get("status") != "missing")
        )
        _sending(job, None, body, f"create the ruleset {body['name']}")
        answer = branch_rules.create(client, plan["repository"], body)
        return _checked(body, answer, {"ruleset": answer.get("id"), "created": True})
    return _change(job, client, remote, rules)


def _sending(job: Job, ident: int | None, body: dict[str, Any], what: str) -> None:
    """Keep what a ruleset write sends before it goes, so a write whose answer was lost is read back on Resume."""
    job.record("protection")["sent"] = {"id": ident, "body": body}
    job.intend("protection", what)


def _landed(job: Job, client: GhClient, rules: branch_rules.Rules) -> dict[str, Any] | None:
    """An earlier write whose answer was lost, read back: done when GitHub holds what was sent, else nothing."""
    if (sent := job.record("protection").get("sent")) is None:
        return None
    repository, body = job.plan["repository"], sent["body"]
    ids = [sent["id"]] if sent["id"] is not None else sorted({r.get("ruleset_id") for r in rules.rules} - {None})
    for ident in ids:
        held = branch_rules.read_ruleset(client, repository, ident)
        if held.get("name") == body["name"] and not branch_rules.differences(body, held):
            return {"ruleset": ident, "created": sent["id"] is None, "read_back": True}
    return None


def _change(job: Job, client: GhClient, remote: repo_target.RepoState, rules: branch_rules.Rules) -> dict[str, Any]:
    """The needed changes and chosen advice, applied only where one repository ruleset governs the branch."""
    plan = job.plan
    if (ident := branch_rules.one_ruleset(rules)) is None:
        return {"applied": False, "listed": True}
    seen = probe.rules_view(plan["repository"], rules, {m.value for m in remote.methods})
    if seen["items"] != plan.get("rules_items"):
        msg = f"the branch's rules changed since Choices.\nShown then: {plan.get('rules_items')}\nNow: {seen['items']}"
        raise StageError(msg)
    whole = branch_rules.read_ruleset(client, plan["repository"], ident)
    body = branch_rules.changed(whole, plan.get("needs", []), plan.get("advice", []))
    if not (fields := branch_rules.differences(whole, body)):
        return {"applied": False, "why": branch_rules.NOTHING}
    _sending(job, ident, body, f"change ruleset {ident}: {'; '.join(fields)}")
    answer = branch_rules.replace(client, plan["repository"], ident, body)
    return _checked(body, answer, {"ruleset": ident, "changed": fields})


def _checked(sent: dict[str, Any], answer: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    if differ := branch_rules.differences(sent, answer):
        msg = "GitHub's answer differs from what OwlBear sent:\n" + "\n".join(differ)
        raise StageError(msg)
    return result


def labels(job: Job) -> dict[str, Any]:
    """The Global labels, created where the repository lacks them, if ticked."""
    plan, client = job.plan, None
    if not (wanted := plan.get("labels") or []):
        return {"created": []}
    client = _client(job)
    have = repo_target.labels(client, plan["repository"])
    made = [x for x in wanted if x not in have]
    for label in made:
        repo_target.create_label(client, plan["repository"], label)
    return {"created": made}


def shared(job: Job) -> dict[str, Any]:
    """Claim the project's shared folder before any store opens; on a collision the owner names it."""
    said: list[str] = []
    name = job.answers.get("shared_folder", "")
    if not setup.project_folder(_folder(job), name, lambda _q: "", said.append):
        kind = "shared_folder"
        raise Waiting(kind, {"why": "\n".join(said)})
    return {"said": said}


def _store(job: Job) -> Store:
    if "store" not in job.context:
        job.context["store"] = Store.open(_folder(job), repair=True)
    return job.context["store"]


def merge_method(job: Job) -> dict[str, Any]:
    """The project's merge method, as the owner's save; done only once a save returned no notice."""
    method = job.plan.get("method")
    if not method:
        return {"written": False}
    store = _store(job)

    def change(layer: Layer) -> Layer:
        prefs = (layer.prefs or Prefs()).model_copy(update={"merge_method": MergeMethod(method)})
        return layer.model_copy(update={"prefs": prefs})

    what = f"{store.name or 'the project'}: merge method {method} (Add project)"
    if notice := store.save(store.config_path, Layer, change, what, owner=True):
        raise StageError(notice)
    return {"written": method, "clean": True}


def ready(job: Job) -> dict[str, Any]:
    """Readiness, as setup checks it; each failure with its fix."""
    store, path, said = _store(job), _folder(job), []
    found = setup_profile.saved(store, said.append)
    writer = github_writer.of(store, path, detecting=True)
    job.context.update(saved=found, writer=writer)
    if failed := [c for c in readiness.check(path, found[0], writer) if not c.ok]:
        raise StageError("\n".join(f"{c.name}: {c.detail} · fix: {c.fix}" for c in failed))
    return {"said": said}


def detect(job: Job) -> dict[str, Any]:
    """Detect the profile."""
    if "saved" not in job.context:
        ready(job)
    job.context["profile"] = setup_profile.detect(_folder(job), job.context["saved"][0], job.context["writer"])
    return {}


def profile(job: Job) -> dict[str, Any]:
    """Show the profile and wait for the owner's confirmation, then save it as setup does."""
    said: list[str] = []
    if receipt := profile_repair.pending(_store(job)):  # a confirmed replacement still to publish, as setup resumes it
        if not setup_profile.publish_repair(_store(job), receipt, said.append, resumed=True):
            raise StageError("\n".join(said))
        return {"version": receipt.profile.version}
    if "profile" not in job.context:
        detect(job)
    prof = job.context["profile"]
    if (values := job.answers.get("profile")) is None:
        settings = setup_profile.profile.SETTINGS
        entries = [
            {"key": k, "state": e.state, "value": e.value, "evidence": e.evidence, "settable": k not in settings}
            for k, e in sorted(prof.entries.items())
        ]
        kind = "profile"
        raise Waiting(kind, {"entries": entries, "notes": job.result("readiness").get("said", [])})
    prof = setup_profile.confirmed(prof, {k: v for k, v in values.items() if v}, by="Add project")
    if not setup_profile.keep(_store(job), prof, job.context["saved"], said.append):  # Retry saves these answers
        raise StageError("\n".join(said))
    return {"version": prof.version}


def files(job: Job) -> dict[str, Any]:
    """The chat-tool files, each with its own consent; a refusal is shown with its snippet."""
    said: list[str] = []
    python = str(local_home.stable(Path(sys.executable)))
    agreed = job.plan.get("consents") or {}
    setup.write_project_files(_folder(job), python, lambda _q: "", said.append, given=False, agreed=agreed)
    return {"said": said}


def register(job: Job) -> dict[str, Any]:
    """Register the clone on this machine."""
    machine = job.context["machine"]
    if pid := probe.registered_id(_folder(job)):
        return {"id": pid, "kept": True}
    return {"id": machine.register(_folder(job)).entry.id, "kept": False}


STAGES: dict[str, Stage] = {
    "folder": folder,
    "git": git,
    "commit": commit,
    "repository": repository,
    "push": push,
    "ci": ci,
    "protection": protection,
    "labels": labels,
    "shared": shared,
    "merge_method": merge_method,
    "readiness": ready,
    "detect": detect,
    "profile": profile,
    "files": files,
    "register": register,
    "end": onboarding_end.facts,
}
