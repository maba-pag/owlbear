"""Add project's probe and preflight (item 15): what exists, which stages are left, and what must hold before any.

The probe only reads. The preflight runs after Choices on the name, owner and route chosen, and before anything is
created: Git's identity and signing are read with the target remote, because this machine picks the identity by
remote URL; GitHub's prerequisites are GitHub reads; a local-only route reads nothing on GitHub.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.commands import setup
from owlbear_delivery_next.git.command_failure import failure
from owlbear_delivery_next.github import branch_rules, repo_target
from owlbear_delivery_next.github.account import REPOSITORY_OWNER, AccountMissing, Origin, Writer
from owlbear_delivery_next.github.gh_client import GhClient
from owlbear_delivery_next.github.provider import ProviderError
from owlbear_delivery_next.local_system import data_repo, local_home, onboarding_git
from owlbear_delivery_next.runtimes import readiness
from owlbear_delivery_next.state_store import registry
from owlbear_delivery_next.state_store.layers import layered
from owlbear_delivery_next.state_store.store import MACHINE_SETTINGS, StoreError

if TYPE_CHECKING:
    from owlbear_delivery_next.github.repo_target import RepoState
    from owlbear_delivery_next.settings.config import Settings

HOST = "github.com"
ACCOUNT = "GitHub account"  # the setting's row on the Settings page
ORDER = (
    "folder",
    "git",
    "commit",
    "repository",
    "push",
    "ci",
    "protection",
    "labels",
    "shared",
    "merge_method",
    "readiness",
    "detect",
    "profile",
    "files",
    "register",
    "end",
)
SETUP = ("shared", "merge_method", "readiness", "detect", "profile", "files", "register", "end")
_REPO = re.compile(  # owner/name, or a github.com URL of it; another host is no GitHub repository
    r"(?:https?://(?:www\.)?github\.com/|git@github\.com:|ssh://git@github\.com/)?"
    r"([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/?$",
    re.IGNORECASE,
)


def projects() -> Path:
    """Where new folders go by default."""
    return Path.home() / "Projects"


def slug(name: str) -> str:
    """A repository and folder name from the owner's words."""
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", name.strip()).strip(".-") or "project"


def split(repository: str) -> tuple[str, str]:
    """``owner/name`` from a name or a URL; raises ``ValueError`` on anything else."""
    if not (m := _REPO.fullmatch(repository.strip())):
        msg = f"{repository!r} is not a repository on github.com: give owner/name or its github.com URL"
        raise ValueError(msg)
    return m.group(1), m.group(2)


def url(repository: str) -> str:
    """The HTTPS URL a new clone's ``origin`` gets."""
    return f"https://{HOST}/{repository}.git"


def resolved(repository: str) -> Settings:
    """*repository*'s settings: Global, this machine and its claimed folder's layer, if any; no store opens."""
    shared = data_repo.locate()
    claimed = shared.claimed(f"{HOST}/{repository}") if shared and repository else None
    config = shared.project_path(claimed) if shared and claimed else None
    glob = shared.global_path if shared else None
    return layered(glob, config, local_home.root() / MACHINE_SETTINGS)


def account(repository: str) -> str | None:
    """The GitHub account setting for *repository*."""
    return resolved(repository).github_account


def client(repository: str, setting: str | None, cwd: Path) -> GhClient:
    """A ``gh`` client acting as the account *setting* names on *repository* (TD-402's rule while it is unset)."""
    owner, name = split(repository)
    return GhClient(cwd, writer=Writer(setting or REPOSITORY_OWNER, Origin(HOST, owner, name)), host=HOST)


def registered_id(folder: Path) -> str:
    """The id of the project registered at *folder*, else nothing."""
    entry = next((p for p in registry.load().projects if Path(p.path) == folder), None)
    return entry.id if entry else ""


def _github(found: dict[str, Any], repository: str, folder: Path) -> RepoState | None:
    """Read the target repository and its default branch's rules into *found*; a failed read is the refusal."""
    try:
        state = repo_target.view(client(repository, found["account"], onboarding_git.nearest_existing(folder)),
                                 repository)  # fmt: skip
    except (ProviderError, AccountMissing) as exc:
        found["refusal"] = f"GitHub could not be read for {repository}: {failure(exc)}"
        return None
    if state is None:
        return None
    methods = {m.value for m in state.methods}
    found["github"] = {"empty": state.empty, "methods": sorted(methods)}
    branch = state.default_branch or "main"
    try:
        rules = branch_rules.read(client(repository, found["account"], onboarding_git.nearest_existing(folder)),
                                  repository, branch)  # fmt: skip
    except (ProviderError, AccountMissing) as exc:
        found["refusal"] = f"the branch rules of {repository} could not be read: {failure(exc)}"
        return state
    found["rules"] = rules_view(repository, rules, methods)
    return state


def rules_view(repository: str, rules: branch_rules.Rules, methods: set[str]) -> dict[str, Any]:
    """What Choices shows of the branch's rules: the allowed methods, the sources, and the comparison."""
    allowed = sorted(branch_rules.allowed_methods(methods, rules))
    comparison = branch_rules.compare(rules)
    links = {str(s): branch_rules.settings_url(repository, s) for s in branch_rules.sources(rules)}
    items = [
        {"key": i.key, "source": str(i.source), "sentence": i.sentence, "holds": i.holds, "applicable": i.applicable}
        for i in (*comparison.needs, *comparison.advice)
    ]
    return {
        "allowed": allowed,
        "plan_limit": rules.plan_limit,
        "one_ruleset": branch_rules.one_ruleset(rules),
        "links": links,
        "items": items,
        "needs": [i.key for i in comparison.needs],
        "summary": comparison.summary,
        "any": bool(rules.rules or rules.classic),
    }


def _target(start: dict[str, Any]) -> tuple[str, bool, str, Path, str]:
    """The start's kind, whether it goes on GitHub, the repository named, the folder and the name."""
    kind, github, repository = start.get("kind", "folder"), bool(start.get("github", True)), ""
    if kind == "github":
        owner, name = split(start.get("repository", ""))
        repository, github = f"{owner}/{name}", True
        folder = Path(start.get("folder") or projects() / name)
    elif kind == "new":
        name = slug(start.get("name", ""))
        folder = Path(start.get("folder") or projects() / name)
    else:
        if not str(start.get("folder") or "").strip():
            msg = "name the folder on this Mac"
            raise ValueError(msg)
        folder = Path(start["folder"])
        name = folder.name
    return kind, github, repository, folder.expanduser().resolve(), name


def probe(start: dict[str, Any]) -> dict[str, Any]:
    """What exists for the owner's start, the first missing stage onwards, or why it is refused."""
    kind, github, asked, folder, name = _target(start)
    state, repository = onboarding_git.folder_state(folder), asked
    if state.origin:
        try:
            owner, name = split(state.origin)
            repository = f"{owner}/{name}"
        except ValueError:
            repository = ""
    found: dict[str, Any] = {"folder": str(folder), "name": name, "github": None, "rules": None,
                             "repository": repository, "origin": state.origin or "", "refusal": "",
                             "state": {"exists": state.exists, "empty": state.empty, "files": state.has_files,
                                       "git": state.git, "workflows": state.has_workflows},
                             "registered": registered_id(folder), "account": None, "on_github": github}  # fmt: skip
    if state.enclosing:
        found["enclosing"] = str(state.enclosing)
        found["refusal"] = (f"{folder} lies inside the repository {state.enclosing}: add that repository instead, "
                            "or choose it explicitly as the folder")  # fmt: skip
    elif state.origin and not repository:
        found["refusal"] = f"origin {state.origin} is not a GitHub repository OwlBear can publish to"
    elif asked and repository.casefold() != asked.casefold():
        found["refusal"] = (f"{folder} is a clone of {repository}, not of {asked}: choose another folder for "
                            f"{asked}, or start from that folder")  # fmt: skip
    elif github and repository:
        _remote(found, kind, repository, folder, has_origin=bool(state.origin))
    if found["refusal"]:
        return found
    found["author_missing"] = _author_missing(folder, state.origin or (url(repository) if repository else ""))
    found["old_task"] = setup.has_task(folder / ".vscode" / "tasks.json")
    found["stages"], found["entry"] = stages(found)
    found["refusal"] = _conflict(found) or ""
    return found


def _remote(found: dict[str, Any], kind: str, repository: str, folder: Path, *, has_origin: bool) -> None:
    """The account setting, the repository and its rules, and where a push would go; a problem is the refusal."""
    try:
        found["account"] = account(repository)
    except (StoreError, data_repo.DataRepoError) as exc:
        found["refusal"] = f"the {ACCOUNT} setting could not be read: {failure(exc)}"
        return
    remote = _github(found, repository, folder)
    if found["refusal"]:
        return
    if remote is None and kind == "github":
        found["refusal"] = f"{repository} does not exist on GitHub, or this account can't see it"
    elif has_origin and (other := onboarding_git.push_urls_name(folder, "origin", url(repository))):
        found["refusal"] = f"a push from {folder} would go to {', '.join(other)}, not {repository}"


def _conflict(found: dict[str, Any]) -> str:
    git, remote = found["state"]["git"], found["github"]
    if remote and not remote["empty"] and git != "commits" and found["state"]["files"]:
        return (f"{found['folder']} has files but no commits, and {found['repository']} has commits: "
                "pull them or move the files away first")  # fmt: skip
    return ""


def stages(found: dict[str, Any]) -> tuple[list[str], str]:
    """The stages left for what the probe found, and the entry's name for the dialog."""
    st, remote, github = found["state"], found["github"], found["on_github"]
    remote_commits, local_commits = bool(remote) and not remote["empty"], st["git"] == "commits"
    clone = remote_commits and (not st["exists"] or (st["empty"] and st["git"] == "none"))
    left: set[str] = {"folder"} if clone or not st["exists"] else set()
    if found["author_missing"] or (not clone and (st["git"] == "none" or (github and not found["origin"]))):
        left.add("git")  # Git, origin before any commit, and a chosen author, after a clone too
    if not (clone or local_commits or remote_commits):
        left |= {"commit", "ci"} if github else {"commit"}
    if github and not remote:
        left.add("repository")
    if github and not clone and not (local_commits and remote_commits):
        left.add("push")  # the first push, or an unborn clone's pull of the repository's commits
    left |= {"protection", "labels", *SETUP} if github else {"files", "end"}
    if found["registered"]:
        left.discard("register")
    return [s for s in ORDER if s in left], _entry(st, remote, github=github, clone=clone)


def _entry(st: dict[str, Any], remote: dict[str, Any] | None, *, github: bool, clone: bool) -> str:
    if clone:
        return "E1"
    if not github:
        return "E3" if st["files"] else "E5"
    if remote is None:
        return "E3b" if st["git"] == "commits" else ("E3" if st["files"] else "E5")
    if remote["empty"]:
        return "E4c" if st["git"] == "commits" else ("E3" if st["files"] else "E4a")
    return "E2" if st["git"] == "commits" else "E4b"


def _author_missing(folder: Path, target: str) -> bool:
    return not readiness.identity(onboarding_git.target_probe(onboarding_git.nearest_existing(folder), target)).ok


def author(plan: dict[str, Any]) -> tuple[str, str] | None:
    """The Git author Choices named, both fields; ``None`` when it named none or only half of one."""
    given = plan.get("author") or {}
    name, email = str(given.get("name") or "").strip(), str(given.get("email") or "").strip()
    return (name, email) if name and email else None


def preflight(plan: dict[str, Any]) -> list[str]:
    """What must hold before anything is created, each failure whole; empty when the run may start."""
    folder, repository = Path(plan["folder"]), plan.get("repository", "")
    # the remote the first commit will see: the folder's own origin, else the one the Git stage sets
    own = onboarding_git.folder_state(folder).origin if folder.exists() else None
    target = own or (url(repository) if plan.get("github") and repository else "")
    where = onboarding_git.nearest_existing(folder)
    probe_git = onboarding_git.target_probe(where, target)
    out = []
    if not (signing := readiness.signing(probe_git)).ok:
        out.append(f"commit signing: {signing.detail}. {signing.fix}")
    given = plan.get("author") or {}
    if any(str(given.get(k) or "").strip() for k in ("name", "email")) and not author(plan):
        out.append("git author: name both the author's name and email, or neither")
    if not author(plan) and not (who := readiness.identity(probe_git)).ok:
        out.append(f"git identity: {who.detail}; name the Git author in Choices")
    if not plan.get("github"):
        return out
    if not (setting := account(repository)):
        return [*out, f"the {ACCOUNT} setting is unset; set it on the Settings page, then try again"]
    gh = client(repository, setting, where)
    try:
        gh.writer.access()  # type: ignore[union-attr]
        if "repository" in plan["stages"] and not repo_target.name_free(gh, *split(repository)):
            out.append(f"{repository} already exists on GitHub; choose another name")
    except (ProviderError, AccountMissing) as exc:
        out.append(f"GitHub: {failure(exc)}")
    if why := readiness.reach(HOST):
        out.append(f"network: https://{HOST}: {why}")
    return out
