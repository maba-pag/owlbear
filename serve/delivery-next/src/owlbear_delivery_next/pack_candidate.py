"""A design pack update's candidate and its challenge (TD-101): detector pins and skills together, judged whole.

The skills were extracted once; an update keeps their text, moves their provenance to the new tag, and the
challenger judges whether they still hold against upstream's new skill text and rules. It only reads: a ``fix`` stops
the update, and the owner revises the skills before the next run.
"""

from __future__ import annotations

import hashlib
import io
import json
import re
import subprocess
import tarfile
import tempfile
import uuid
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next import (
    design_pack,
    pack_update,
    preload,
    prompts,
    roles,
    sdk_adapter,
    sessions,
    setup,
    tools,
)
from owlbear_delivery_next.models import StepKind
from owlbear_delivery_next.permissions import Policy

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_delivery_next.calibration import Replay
    from owlbear_delivery_next.session_result import Run
    from owlbear_delivery_next.store import Store

CLONE = "https://github.com/{repository}.git"
ENGINE_VERSION = "ENGINE_VERSION"  # upstream's pin of the released engine, at the repository root
LICENCE = {"IMPECCABLE-LICENSE": "LICENSE"}  # the pack's licence file and upstream's
MANIFEST, NOTICE = "design_pack.json", f"{preload.ROOT}/NOTICE.md"  # the package files an update rewrites
DIGEST = re.compile(r"\b[0-9a-f]{64}\b")
LABEL = "pack-challenge"


@dataclass(frozen=True)
class Candidate:
    """The pack an update would activate: its pins, its provenance notice, and its files installed on this machine."""

    tag: str
    pins: dict[str, Any]
    manifest: str  # the new design_pack.json, in the old one's layout
    notice: str  # the new NOTICE.md
    installed: design_pack.Installed


def sync(clone: Path, repository: str) -> None:
    """Clone upstream into *clone*, or fetch its tags when it is there; nothing in it is ever run."""
    if (clone / ".git").is_dir():
        _run(["git", "-C", str(clone), "fetch", "--quiet", "--tags", "--force", "origin"])
    else:
        clone.parent.mkdir(parents=True, exist_ok=True)
        _run(["git", "clone", "--quiet", "--no-checkout", CLONE.format(repository=repository), str(clone)])


def _run(command: list[str]) -> bytes:
    return subprocess.run(command, capture_output=True, check=True, timeout=600).stdout  # noqa: S603


def _show(clone: Path, tag: str, path: str) -> bytes:
    return _run(["git", "-C", str(clone), "show", f"{tag}:{path}"])


def prepare(clone: Path, package: Path, tag: str, download: Callable[[str], bytes]) -> Candidate:
    """The candidate at *tag*: upstream's commit, engine version and digests, bundle digest, the same skills.

    Raises:
        design_pack.PackError: A pin cannot be read, upstream's licence changed, or a file does not verify.
    """
    old = json.loads((package / MANIFEST).read_text(encoding="utf-8"))
    pins = json.loads(json.dumps(old))
    try:
        commit = _run(["git", "-C", str(clone), "rev-list", "-n1", tag]).decode().strip()
        engine = _show(clone, tag, ENGINE_VERSION).decode().strip()
        bundle = _show(clone, tag, old["bundle"]["path"])
        licences = {name: _show(clone, tag, path) for name, path in LICENCE.items()}
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, UnicodeDecodeError) as exc:
        msg = f"upstream at {tag} lacks a file the pack pins: {exc}"
        raise design_pack.PackError(msg) from exc
    if not re.fullmatch(r"\d+(\.\d+){1,3}", engine):
        msg = f"upstream's {ENGINE_VERSION} at {tag} is not a version: {engine[:40]!r}"
        raise design_pack.PackError(msg)
    if changed := [n for n, data in licences.items() if hashlib.sha256(data).hexdigest() != old["licence"].get(n)]:
        msg = f"upstream's licence changed at {tag} ({', '.join(changed)}); review it by hand before an update"
        raise design_pack.PackError(msg)
    pins["pack"] = f"impeccable-{tag.removeprefix('skill-v')}.1"
    pins["upstream"] |= {"tag": tag, "commit": commit, "engine": engine}
    pins["bundle"]["sha256"] = hashlib.sha256(bundle).hexdigest()
    for platform in pins["engine"]:
        pins["engine"][platform] = _published(download, pins, platform)
    raw = design_pack.RAW.format(repository=pins["upstream"]["repository"], commit=commit, path=old["bundle"]["path"])
    installed = design_pack.install(lambda url: bundle if url == raw else download(url), pins)
    up = old["upstream"]
    notice = (package / NOTICE).read_text(encoding="utf-8")
    if up["tag"] not in notice or up["commit"] not in notice:
        msg = f"{NOTICE} does not name the pinned tag and commit, so its provenance cannot move"
        raise design_pack.PackError(msg)
    return Candidate(tag, pins, _relaid(package, old, pins), _moved(notice, up, pins["upstream"]), installed)


def _published(download: Callable[[str], bytes], pins: dict[str, Any], platform: str) -> str:
    """The engine's digest as its release publishes it, in the ``.sha256`` file beside each asset."""
    up = pins["upstream"]
    url = design_pack.RELEASE.format(repository=up["repository"], engine=up["engine"], platform=platform) + ".sha256"
    try:
        found = DIGEST.search(download(url).decode("ascii", "replace"))
    except OSError as exc:
        msg = f"cannot download {url}: {exc}"
        raise design_pack.PackError(msg) from exc
    if found is None:
        msg = f"{url} holds no sha256 digest"
        raise design_pack.PackError(msg)
    return found.group()


def _moved(text: str, old: dict[str, str], new: dict[str, str]) -> str:
    return text.replace(old["commit"], new["commit"]).replace(f"`{old['tag']}`", f"`{new['tag']}`")


def _relaid(package: Path, old: dict[str, Any], new: dict[str, Any]) -> str:
    """The new manifest in the old one's layout: each changed value replaced where it stands.

    Raises:
        design_pack.PackError: A value is not unique in the file, so replacing it could change another.
    """
    text = (package / MANIFEST).read_text(encoding="utf-8")
    pairs = [(old["pack"], new["pack"]), *((old["upstream"][k], v) for k, v in new["upstream"].items())]
    pairs += [(old["engine"][k], v) for k, v in new["engine"].items()]
    pairs += [(old["bundle"]["sha256"], new["bundle"]["sha256"])]
    for was, now in pairs:
        if was != now:
            if text.count(f'"{was}"') != 1:
                msg = f"{MANIFEST} holds {was!r} more than once"
                raise design_pack.PackError(msg)
            text = text.replace(f'"{was}"', f'"{now}"')
    if json.loads(text) != new:
        msg = f"{MANIFEST} could not be rewritten in place"
        raise design_pack.PackError(msg)
    return text


def message(c: Candidate, diff: str, golden: str, replayed: str, package: Path) -> str:
    """The challenger's first message: the whole candidate pack and the update's evidence."""
    skills = [
        f"### {name}\n\n{(package / preload.ROOT / name / 'SKILL.md').read_text('utf-8')}" for name in c.pins["skills"]
    ]
    return "\n".join(
        [
            f"You challenge a design pack update to `{c.pins['pack']}` (upstream `{c.tag}`) before it is activated.",
            "The worktree holds upstream's skill text at the new tag under `upstream/skill/`. You only read.",
            prompts.READ_ONLY,
            "",
            "## Judge",
            (
                "Pass only when the whole pack holds: the pinned detector and the extracted skills below agree with "
                "upstream's new rules and skill text, the golden pages and the calibration replay support it, and no "
                "skill rule contradicts a detector rule. Each place is a skill and its section, or a rule id. A fix "
                "names the skill text to change; Delivery does not change it, the owner does."
            ),
            "",
            "## Rule and skill diff",
            diff,
            "",
            f"## Golden pages\n{golden}",
            f"## Calibration replay\n{replayed}",
            "",
            "## Candidate skills (unchanged text, provenance moved to the new tag)",
            *skills,
            "",
            "## Finish",
            prompts.REVIEW_FINISH,
        ]
    )


def challenge(
    store: Store, c: Candidate, clone: Path, text: str, run: Callable[[Store, sdk_adapter.Session], Run]
) -> tuple[bool, str]:
    """One fresh read-only challenger session over the candidate: whether it passed, and why not."""
    role = roles.chosen(store.settings(), LABEL)
    with tempfile.TemporaryDirectory(prefix="owlbear-pack-") as tmp:
        at = Path(tmp)
        code, said = setup.probe_in(at)(["git", "init", "-q"])  # the window places its files only in a repository
        if code:
            return False, f"the challenger's worktree could not be a git repository: {said[:200] or code}"
        archive = _run(["git", "-C", str(clone), "archive", c.tag, pack_update.SKILL])
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            tar.extractall(at / "upstream", filter="data")
        cfg = sdk_adapter.Session(
            kind=StepKind.REVIEW, worktree=at, session_id=f"{LABEL}-{uuid.uuid4().hex[:8]}", message=text,
            resume=False, policy=Policy(at, write=False), observe=lambda: tools.Worktree("", ""), checks=(),
            submit=tools.REVIEW, model=role.model, effort=role.effort, context=role.context, role="challenger",
            judging=True, memory=sessions.memory(store),
        )  # fmt: skip
        done = run(store, replace(cfg, fresh=cfg.message))
    return verdict(done)


def verdict(done: Run) -> tuple[bool, str]:
    """A pass, or the findings, wrong premise or ending that stops the update."""
    if not (done.termination and done.termination.confirmed):
        return False, f"the challenger {done.session_id} may still be running; stop it before updating again"
    if done.ending != "result" or not isinstance(done.payload, tools.ReviewResult):
        return False, f"the challenger ended with {done.ending}: {done.detail or 'no verdict'}"[:600]
    if done.payload.verdict == "pass":
        return True, "passed"
    found = "; ".join(f"{f.place}: {f.problem} (fix: {f.fix})" for f in done.payload.findings)
    return False, f"the challenger asks for fixes: {found or 'none named'}"[:2000]


def said_replay(r: Replay) -> str:
    """The replay in words, as the CLI says it."""
    verdict_ = "advisory: too few rounds" if r.advisory else "within the margin" if r.ok else "below the margin"
    return (
        f"{r.rounds} decided rounds, {r.left_out} left out; the design judge agreed with the owner "
        f"{r.before:.0%} as recorded, {r.after:.0%} with this pack ({verdict_})"
    )
