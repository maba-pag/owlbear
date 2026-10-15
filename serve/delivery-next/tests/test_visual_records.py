"""Visual review slice 3: the round records on the Change, the design-failure setting, and the calibration store."""

import json
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from owlbear_delivery_next import calibration, config_routes, sessions, visual_settled
from owlbear_delivery_next.config import GlobalLayer, Layer, resolve
from owlbear_delivery_next.models import Change, VisualResult
from owlbear_delivery_next.store import Lock, Store
from owlbear_delivery_next.visual_records import (
    DetectorFinding,
    DetectorScan,
    JudgeFinding,
    JudgeVerdict,
    OwnerCriterion,
    OwnerDecision,
    VisualRound,
)

NOW = datetime(2026, 10, 14, 12, tzinfo=UTC)


def git(cwd: Path, *args: str) -> str:
    who = ["-c", "user.name=t", "-c", "user.email=t@example.com"]
    done = subprocess.run(["git", *who, *args], cwd=cwd, check=True, capture_output=True, text=True)  # noqa: S603, S607
    return done.stdout.strip()


@pytest.fixture
def shared_repo(tmp_path: Path, monkeypatch) -> tuple[Path, Path]:
    remote, root = tmp_path / "remote.git", tmp_path / "owlbear-data"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(remote))
    git(tmp_path, "clone", "-q", str(remote), str(root))
    for key, value in (("user.name", "t"), ("user.email", "t@example.com")):
        git(root, "config", key, value)
    git(root, "commit", "-q", "--allow-empty", "-m", "start")
    git(root, "push", "-q", "origin", "HEAD")
    home = tmp_path / "home"
    home.mkdir()
    (home / "common.json").write_text(json.dumps({"repository": str(root)}))
    monkeypatch.setenv("OWLBEAR_HOME", str(home))
    repo = tmp_path / "shop"
    git(tmp_path, "init", "-q", "-b", "main", str(repo))
    git(repo, "commit", "--allow-empty", "-qm", "start")
    git(repo, "remote", "add", "origin", "git@github.com:acme/shop-site.git")
    return root, repo


def decided(number: int, at: datetime) -> VisualRound:
    finding = JudgeFinding(
        id="design-1", state="home", width=1280, text="cramped", rule="cramped-padding", severity="P2"
    )
    return VisualRound(
        number=number,
        head="a" * 40,
        tree="b" * 40,
        states={"home": 1},
        widths=[1280],
        pack="impeccable-4.5.2.1+x",
        verdicts=[
            JudgeVerdict(lens="correctness", verdict="pass", usage_verified=True),
            JudgeVerdict(lens="design", verdict="fail", findings=[finding], unanchored="fail", usage_verified=True),
        ],
        detector=[
            DetectorScan(
                state="home",
                width=1280,
                kind="page",
                scanned=True,
                findings=[
                    DetectorFinding(
                        rule="cramped-padding", category="quality", advisory=False, where=".card", freshness="new"
                    )
                ],
            ),
        ],
        decision=OwnerDecision(outcome="fail", findings=["design-1"], comment="too tight", at=at),
        outcome="back",
        at=at,
    )


def test_a_change_keeps_its_rounds_and_the_owners_criteria() -> None:
    change = Change(
        slug="c1",
        visual_rounds=[decided(1, NOW)],
        owner_criteria=[OwnerCriterion(id="owner-1", text="too tight", round=1, brief_version=2, at=NOW)],
    )
    again = Change.model_validate_json(change.model_dump_json())
    assert again == change
    assert Change.model_validate({"slug": "old"}).visual_rounds == []  # Changes stored before keep loading
    with pytest.raises(ValidationError):
        JudgeVerdict.model_validate({"lens": "taste"})


def test_a_round_is_decided_only_on_one_verified_verdict_from_each_judge() -> None:
    good = decided(1, NOW).model_dump()
    unverified = [good["verdicts"][0], {**good["verdicts"][1], "usage_verified": False}]
    for verdicts in (good["verdicts"][:1], unverified, [*good["verdicts"], good["verdicts"][1]]):
        with pytest.raises(ValidationError, match="one verified verdict from each judge"):
            VisualRound.model_validate({**good, "verdicts": verdicts})
    assert VisualRound.model_validate({**good, "verdicts": unverified, "decision": None}).decision is None


def test_design_failures_resolve_project_then_global_then_ask() -> None:
    assert resolve(None, Layer()).design_failures == "ask"
    assert resolve(None, Layer()).sources["design_failures"] == "default"
    assert resolve(GlobalLayer(design_failures="back"), Layer()).design_failures == "back"
    chosen = resolve(GlobalLayer(design_failures="back"), Layer(design_failures="ask"))
    assert (chosen.design_failures, chosen.sources["design_failures"]) == ("ask", "project")
    with pytest.raises(ValidationError):
        Layer.model_validate({"design_failures": "reject"})


def test_calibration_keeps_decided_rounds_in_the_shared_repository_with_local_screenshots(
    shared_repo, tmp_path
) -> None:
    root, repo = shared_repo
    store = Store.open(repo)
    before, after = tmp_path / "b.png", tmp_path / "a.png"
    before.write_bytes(b"before")
    after.write_bytes(b"after")
    shots = {"before-home-1280.png": before, "after-home-1280.png": after}
    assert calibration.keep(store.shared, store.name, "c1", decided(1, NOW), shots) == ""
    kept = root / "shop-site" / "visual" / "c1-1"
    assert git(root, "log", "--format=%s", "-1") == "visual: c1 round 1 decided"
    assert git(root, "ls-files", "shop-site/visual") == "shop-site/visual/c1-1/round.json"
    assert [(kept / n).read_bytes() for n in shots] == [b"before", b"after"]
    assert store.shared.pending() == ""  # the screenshots are excluded, not unsaved
    assert git(repo, "status", "--porcelain") == ""
    [(again, images)] = calibration.cases(store.shared, store.name)
    assert (again, images) == (decided(1, NOW), [kept / "after-home-1280.png", kept / "before-home-1280.png"])
    with pytest.raises(ValueError, match="only a round the owner decided"):
        calibration.keep(store.shared, store.name, "c1", decided(2, NOW).model_copy(update={"decision": None}), {})
    for slug, image in (("../x", "a.png"), ("/abs", "a.png"), ("c1", "round.json"), ("c1", "../a.png")):
        with pytest.raises(ValueError, match="plain"):
            calibration.keep(store.shared, store.name, slug, decided(2, NOW), {image: after})
    assert sorted(p.name for p in kept.parent.iterdir()) == ["c1-1"]  # nothing was written for them


def test_only_the_newest_decided_rounds_keep_their_screenshots(shared_repo, tmp_path, monkeypatch) -> None:
    _root, repo = shared_repo
    store = Store.open(repo)
    monkeypatch.setattr(calibration, "ROUNDS", 2)
    shot = tmp_path / "s.png"
    shot.write_bytes(b"png")
    for n, minutes in ((1, 3), (2, 1), (3, 2)):  # round 1 was decided last
        calibration.keep(store.shared, store.name, "c1", decided(n, NOW + timedelta(minutes=minutes)), {"s.png": shot})
    kept = {r.number: bool(images) for r, images in calibration.cases(store.shared, store.name)}
    assert kept == {1: True, 3: True, 2: False}  # the earliest decision keeps its verdicts only


def test_a_round_the_owner_decided_is_kept_with_its_before_and_after_screenshots(shared_repo, tmp_path) -> None:
    root, repo = shared_repo
    store = Store.open(repo)
    change = Change(slug="c1", visual_rounds=[decided(1, NOW)])
    change.visual = VisualResult(head="a" * 40, tree="t", files=["home-1280.png"], at=NOW)
    change.before = VisualResult(head="b" * 40, tree="t", files=["home-1280.png"], at=NOW)
    out, old = tmp_path / "after", store.before_dir("c1", "b" * 40)
    for folder, data in ((out, b"after"), (old, b"before")):
        folder.mkdir(parents=True)
        (folder / "home-1280.png").write_bytes(data)
    visual_settled.calibrated(store, change, out)
    kept = root / "shop-site" / "visual" / "c1-1"
    assert [(kept / n).read_bytes() for n in ("after-home-1280.png", "before-home-1280.png")] == [b"after", b"before"]


def test_a_change_stored_before_round_decisions_loads_without_its_old_answer(tmp_path) -> None:
    store = Store(tmp_path / "store")
    store.write(Lock("c1"), Change(slug="c1", visual=VisualResult(head="h", tree="t", at=NOW)))
    path = store.root / "changes" / "c1" / "change.json"
    data = json.loads(path.read_text())
    data["format"] = 2
    data["visual"] |= {"decision": "accept", "note": "fine"}
    path.write_text(json.dumps(data))
    assert store.read("c1").visual.head == "h"


def test_each_judge_s_agreement_with_the_owner_is_counted_per_lens_and_model(shared_repo) -> None:
    def judged(n, owner, correct, design, unanchored):
        r = decided(n, NOW + timedelta(minutes=n))
        verdicts = [
            r.verdicts[0].model_copy(update={"verdict": correct, "model": "gpt-6.1-sol"}),
            r.verdicts[1].model_copy(update={"verdict": design, "unanchored": unanchored, "model": "claude-opus-5.5"}),
        ]
        return r.model_copy(update={"verdicts": verdicts, "decision": r.decision.model_copy(update={"outcome": owner})})

    rounds = [judged(1, "fail", "pass", "fail", "pass"), judged(2, "pass", "pass", "unsure", "unsure")]
    assert calibration.agreement(rounds) == [
        {"judge": "correctness", "model": "gpt-6.1-sol", "decided": 2, "agreed": 1, "disagreed": 1, "unsure": 0},
        {"judge": "design", "model": "claude-opus-5.5", "decided": 2, "agreed": 1, "disagreed": 0, "unsure": 1},
        {"judge": "design before the detector", "model": "claude-opus-5.5", "decided": 2, "agreed": 0,
         "disagreed": 1, "unsure": 1},
    ]  # fmt: skip
    _root, repo = shared_repo
    store = Store.open(repo)
    assert config_routes._state(store)["agreement"] == []  # noqa: SLF001
    calibration.keep(store.shared, store.name, "c1", rounds[0], {})
    assert [a["agreed"] for a in config_routes._state(store)["agreement"]] == [0, 1, 0]  # noqa: SLF001


def test_without_a_shared_repository_nothing_is_kept_anywhere(tmp_path) -> None:
    repo = tmp_path / "shop"
    git(tmp_path, "init", "-q", "-b", "main", str(repo))
    git(repo, "commit", "--allow-empty", "-qm", "start")
    assert Store.open(repo).shared is None
    assert sessions.memory(Store.open(repo)) is None
