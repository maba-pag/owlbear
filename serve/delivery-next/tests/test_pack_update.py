"""Design pack update tooling (design skill research §3.5): notice, rule diff, golden pages, calibration replay."""

import dataclasses
import hashlib
import json
import subprocess
from datetime import UTC, datetime, timedelta
from http.client import IncompleteRead
from importlib.resources import files
from pathlib import Path

import pytest

from owlbear_delivery_next import (
    calibration,
    cli,
    config_routes,
    design_pack,
    design_tools,
    detector,
    pack_candidate,
    pack_replay,
    pack_update,
    preload,
    readiness,
)
from owlbear_delivery_next.processes import Termination
from owlbear_delivery_next.session_result import Run
from owlbear_delivery_next.store import Store
from owlbear_delivery_next.visual_records import DesignInput, JudgeVerdict, OwnerDecision, VisualRound

NOW = datetime(2026, 10, 14, 12, tzinfo=UTC)


def git(cwd: Path, *args: str) -> str:
    who = ["-c", "user.name=t", "-c", "user.email=t@example.com"]
    done = subprocess.run(["git", *who, *args], cwd=cwd, check=True, capture_output=True, text=True)  # noqa: S603, S607
    return done.stdout.strip()


@pytest.fixture
def repo(tmp_path: Path, monkeypatch) -> Path:
    """A project clone with a shared settings repository."""
    remote, root = tmp_path / "remote.git", tmp_path / "owlbear-data"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(remote))
    git(tmp_path, "clone", "-q", str(remote), str(root))
    git(root, "commit", "-q", "--allow-empty", "-m", "start")
    git(root, "push", "-q", "origin", "HEAD")
    for key, value in (("user.name", "t"), ("user.email", "t@example.com")):
        git(root, "config", key, value)
    home = tmp_path / "home"
    home.mkdir()
    (home / "data.json").write_text(json.dumps({"repository": str(root)}))
    monkeypatch.setenv("OWLBEAR_HOME", str(home))
    project = tmp_path / "shop"
    git(tmp_path, "init", "-q", "-b", "main", str(project))
    git(project, "commit", "--allow-empty", "-qm", "start")
    git(project, "remote", "add", "origin", "git@github.com:acme/shop-site.git")
    return project


def releases(*tags: str, prerelease: tuple[str, ...] = ()):
    return lambda _url: json.dumps([{"tag_name": t, "prerelease": t in prerelease} for t in tags]).encode()


def test_the_notice_counts_newer_skill_releases_and_offline_is_unknown() -> None:
    assert design_pack.manifest()["upstream"]["tag"] == "skill-v4.5.2"
    tags = ("skill-v4.5.1", "skill-v4.5.2", "skill-v4.5.10", "skill-v5.0.0", "skill-v5.1.0-rc1", "engine-v9.0.0")
    assert pack_update.behind(releases(*tags, prerelease=("skill-v5.1.0-rc1",))) == 2  # by version, not by text
    assert pack_update.behind() is None  # offline: tests never go online
    assert pack_update.behind(lambda _url: b'{"message": "rate limited"}') is None
    assert pack_update.behind(lambda _url: b"not json") is None
    assert pack_update.behind(lambda _url: b'[{"tag_name": null}, 3, {"tag_name": "skill-v4.6.0"}]') == 1

    def truncated(_url: str) -> bytes:
        partial = b"["
        raise IncompleteRead(partial)

    assert pack_update.behind(truncated) is None
    with pytest.raises(design_pack.PackError, match="cannot download"):
        design_pack.install()  # the default download is offline in tests too


def test_the_notice_is_read_offline_refreshed_at_most_daily_and_shown_by_setup_and_settings(repo, monkeypatch) -> None:
    calls = []

    def fetch(url: str) -> bytes:
        calls.append(url)
        return releases("skill-v4.6.0")(url)

    assert pack_update.notice(refresh=False, fetch=fetch) == {
        "pack": "impeccable-4.5.2.1",
        "behind": None,
        "checked_at": None,
    }
    assert pack_update.notice(refresh=True) == {"pack": "impeccable-4.5.2.1", "behind": None, "checked_at": None}
    assert (pack_update.notice(refresh=True, fetch=fetch)["behind"], len(calls)) == (1, 1)  # offline was not kept
    assert (pack_update.notice(refresh=True, fetch=fetch)["behind"], len(calls)) == (1, 1)  # checked today
    shown = "design pack impeccable-4.5.2.1: 1 release behind"
    assert pack_update.said(pack_update.notice(refresh=False)) == shown
    assert config_routes._state(Store.open(repo))["design_pack"] == shown  # noqa: SLF001
    monkeypatch.setattr(readiness, "readiness", lambda *_a: [])  # the other facts probe the machine and the network
    assert readiness.check(repo, None) == [readiness.Check("design pack updates", ok=True, detail=shown)]  # host start
    path = design_pack.folder().parent / pack_update.NOTICE
    path.write_text(json.dumps(json.loads(path.read_text()) | {"tag": "skill-v4.0.0"}))
    assert pack_update.notice(refresh=False)["behind"] is None  # another pinned pack's count
    assert (pack_update.notice(refresh=True, fetch=fetch)["behind"], len(calls)) == (1, 2)
    old = (datetime.now(UTC) - timedelta(days=2)).isoformat()
    path.write_text(json.dumps(json.loads(path.read_text()) | {"checked_at": old}))
    assert (
        pack_update.said(pack_update.notice(refresh=True))
        == "design pack impeccable-4.5.2.1: releases upstream unknown"
    )
    assert pack_update.notice(refresh=False)["behind"] is None  # the settings page no longer shows the old count


def registry(*rules: tuple[str, ...]) -> str:
    entries = "".join(
        f'    Antipattern {{\n        id: "{i}",\n        category: "slop",\n        scopes: None,\n'
        f'        severity: {severity},\n        name: "{n}",\n        description: "{d}",\n'
        f"        skill_section: None,\n        skill_guideline: None,\n    }},\n"
        for i, n, d, severity in (r if len(r) == 4 else (*r, "None") for r in rules)
    )
    fixture = '    Antipattern {\n        id: "fixture-only",\n        category: "quality",\n        name: "x",\n'
    fixture += '        description: "a test fixture",\n        skill_section: None,\n    },\n'
    return f"pub static ANTIPATTERNS: &[Antipattern] = &[\n{entries}];\n\n#[cfg(test)]\nmod tests {{\n{fixture}}}\n"


def test_the_diff_reports_rules_added_removed_and_changed_and_skill_files_changed(tmp_path) -> None:
    clone = tmp_path / "impeccable"
    git(tmp_path, "init", "-q", "-b", "main", str(clone))
    (clone / "crates/foundation/src").mkdir(parents=True)
    (clone / "skill").mkdir()
    versions = (
        (
            "skill-v4.5.2",
            [("side-tab", "Side tab", "old"), ("gradient-text", "Gradient text", "g"), ("flat", "Flat", "f")],
        ),
        (
            "skill-v4.6.0",
            [
                ("side-tab", "Side tab", 'new \\"text\\"'),
                ("glow", "Glow", "x"),
                ("flat", "Flat", "f", "Some(Severity::Warning)"),
            ],
        ),
    )
    for tag, rules in versions:
        (clone / pack_update.REGISTRY).write_text(registry(*rules))
        (clone / "skill/SKILL.md").write_text(tag)
        if tag != "skill-v4.5.2":
            (clone / "skill/new.md").write_text("new")
        git(clone, "add", "-A")
        git(clone, "commit", "-qm", tag)
        git(clone, "tag", tag)
    assert set(pack_update.rules(clone, "skill-v4.5.2")) == {"side-tab", "gradient-text", "flat"}  # not the fixture
    report = pack_update.diff(clone, "skill-v4.6.0")
    assert "## Rules added\n- glow: Glow\n" in report
    assert "## Rules removed\n- gradient-text: Gradient text\n" in report
    assert (
        "## Rules changed\n- flat: Flat\n  - severity: None -> Some(Severity::Warning)\n- side-tab: Side tab\n"
        in report
    )
    assert '  - description: "old" -> "new \\"text\\""\n' in report  # every field, not only the ones once read
    assert "## Skill files changed\n- M\tskill/SKILL.md\n- A\tskill/new.md\n" in report
    assert report.endswith(f"Skill text: git -C {clone} diff skill-v4.5.2 skill-v4.6.0 -- skill")
    (clone / pack_update.REGISTRY).write_text(registry(("side-tab", "x", "y")).replace('        name: "x",\n', ""))
    git(clone, "commit", "-qam", "unnamed")
    git(clone, "tag", "skill-v4.7.0")
    with pytest.raises(ValueError, match="read 1 of 1 rules whole"):
        pack_update.rules(clone, "skill-v4.7.0")
    (clone / pack_update.REGISTRY).write_text("// moved\n")
    git(clone, "commit", "-qam", "moved")
    git(clone, "tag", "skill-v5.0.0")
    with pytest.raises(ValueError, match="no pub static ANTIPATTERNS table"):
        pack_update.rules(clone, "skill-v5.0.0")


def test_golden_pages_report_what_an_engine_missed_or_found_unexpectedly(monkeypatch) -> None:
    def scan(_pack, paths, cwd):
        bad, good = (next(p for p in paths if p.name == name) for name in ("bad.html", "good.html"))
        assert cwd.is_dir()
        golden = files("owlbear_delivery_next").joinpath("golden", "bad.html")
        assert (bad.read_bytes(), good.parent) == (golden.read_bytes(), cwd)
        found = {"rule": "side-tab", "category": "slop", "advisory": False, "name": "n", "detail": ""}
        return [
            detector.Finding(**found, where=f"{bad}:3"),
            detector.Finding(**found | {"rule": "glow"}, where="good.html"),
        ]

    monkeypatch.setattr(detector, "scan_source", scan)
    wrong = pack_update.golden(object(), pages=False)
    assert wrong["good.html (source)"] == {"unexpected": ["glow"], "missing": []}
    assert wrong["bad.html (source)"]["unexpected"] == []
    assert "gradient-text" in wrong["bad.html (source)"]["missing"]
    assert "side-tab" not in wrong["bad.html (source)"]["missing"]


@pytest.mark.browser
def test_the_installed_engine_and_bundle_find_exactly_the_golden_rules(monkeypatch) -> None:
    monkeypatch.setenv("OWLBEAR_HOME", str(Path.home() / ".owlbear"))  # this machine's pack, read only
    pack = design_pack.installed()
    if pack is None:
        pytest.skip("the design pack is not installed (owlbear-next design-pack --install)")
    assert pack_update.golden(pack) == {}  # by source and in the rendered pages
    blind = dataclasses.replace(pack, bundle="window.impeccableDetectAsync = async () => []")  # a bundle finding none
    assert pack_update.golden(blind)["bad.html (page)"] == {
        "unexpected": [],
        "missing": ["gradient-text", "gray-on-color", "low-contrast", "side-tab"],
    }


def test_the_manifest_activates_a_pack_in_one_switch_and_a_rollback_needs_no_download(monkeypatch) -> None:
    def pins(name: str, engine: bytes, bundle: bytes) -> dict:
        made = design_pack.manifest()
        made["pack"] = name
        made["engine"][design_pack.platform_name()] = hashlib.sha256(engine).hexdigest()
        made["bundle"]["sha256"] = hashlib.sha256(bundle).hexdigest()
        return made

    old, new = pins("impeccable-1", b"e1", b"b1"), pins("impeccable-2", b"e2", b"b2")
    active = {"pins": old}
    monkeypatch.setattr(design_pack, "manifest", lambda: json.loads(json.dumps(active["pins"])))
    design_pack.install(lambda url: b"e1" if "releases" in url else b"b1")
    active["pins"] = new  # the reviewed commit that switches the manifest, skills with it
    assert design_pack.installed() is None  # never the old pack under the new name
    assert design_pack.install(lambda url: b"e2" if "releases" in url else b"b2").bundle == "b2"
    active["pins"] = old  # reverting that commit

    def offline(url: str) -> bytes:
        msg = f"a rollback downloads nothing: {url}"
        raise AssertionError(msg)

    assert design_pack.install(offline).bundle == "b1"
    assert sorted(p.name for p in design_pack.folder().parent.iterdir()) == ["impeccable-1", "impeccable-2"]


def kept_round(  # noqa: PLR0913 - one round, varied by each case
    number: int,
    owner: str,
    recorded: str,
    *,
    inputs: bool = True,
    model: str = "claude-opus-5.5",
    tier: str = "default",
) -> VisualRound:
    names = ["home-1280-A.png", "home-1280-B.png"]
    return VisualRound(
        number=number,
        head="a" * 40,
        tree="b" * 40,
        states={"home": 1},
        widths=[1280],
        pack="impeccable-4.5.2.1+x",
        blind={"home-1280-A.png": "after", "home-1280-B.png": "before"},
        design_inputs=[DesignInput(message="judge home", reveal="The detector found: none.", images=names)]
        if inputs
        else [],
        verdicts=[
            JudgeVerdict(lens="correctness", verdict="pass", usage_verified=True),
            JudgeVerdict(
                lens="design", verdict=recorded, usage_verified=True, model=model, effort="high", context=tier
            ),
        ],
        decision=OwnerDecision(outcome=owner, at=NOW + timedelta(minutes=number)),
        outcome="back" if owner == "fail" else "merge",
        at=NOW,
    )


def test_a_replay_compares_agreement_with_the_owner_and_holds_back_only_from_enough_rounds() -> None:
    few = calibration.replayed([(kept_round(1, "fail", "fail"), "pass"), (kept_round(2, "pass", "pass"), None)])
    assert (few.rounds, few.before, few.after, few.advisory, few.ok) == (2, 1.0, 0.0, True, True)
    rounds = [kept_round(n, "pass", "pass" if n <= 16 else "fail") for n in range(1, 21)]  # 16 of 20 agreed
    within = calibration.replayed([(r, "pass" if n < 14 else "fail") for n, r in enumerate(rounds)])  # 14 agree
    assert (within.agreed_before, within.agreed_after, within.advisory, within.ok) == (16, 14, False, True)
    below = calibration.replayed([(r, "pass" if n < 13 else "unsure") for n, r in enumerate(rounds)])
    assert (below.agreed_after, below.ok) == (13, False)
    undecided = kept_round(21, "pass", "pass").model_copy(update={"decision": None})
    assert calibration.replayed([(undecided, "pass")]).rounds == 0


def test_a_replay_rejudges_kept_rounds_with_their_exact_messages_and_screenshots(repo, tmp_path) -> None:
    store = Store.open(repo)
    after, before = tmp_path / "after.png", tmp_path / "before.png"
    after.write_bytes(b"after")
    before.write_bytes(b"before")
    shots = {"after-home-1280.png": after, "before-home-1280.png": before}
    calibration.keep(store.shared, store.name, "c1", kept_round(1, "fail", "pass"), shots)
    calibration.keep(store.shared, store.name, "c1", kept_round(2, "pass", "pass", inputs=False), shots)
    calibration.keep(store.shared, store.name, "c2", kept_round(3, "pass", "pass"), {})  # screenshots pruned
    partial = kept_round(4, "pass", "pass")
    partial.design_inputs[0].images.pop()  # kept inputs that no longer show every image
    calibration.keep(store.shared, store.name, "c3", partial, shots)
    calibration.keep(store.shared, store.name, "c4", kept_round(5, "pass", "pass"), shots)
    linked = calibration.folder(store.shared, store.name) / "c4-5" / "after-home-1280.png"
    linked.unlink()
    (secret := tmp_path / "private.png").write_bytes(b"private")
    linked.symlink_to(secret)  # a screenshot leading out of the calibration folder is never attached
    other = kept_round(6, "pass", "pass", model="gpt-6.1-sol")  # judged by another model: not the pack's doing
    calibration.keep(store.shared, store.name, "c6", kept_round(7, "pass", "pass", tier="long"), shots)  # or tier
    calibration.keep(store.shared, store.name, "c5", other, shots)
    seen = []

    def run(cfg):
        seen.append(cfg)
        look = design_tools.DesignLook(
            verdict="fail",
            findings=[{"image": "home-1280-A.png", "problem": "unreadable", "rule": "Contrast", "severity": "P1"}],
            preferences=[{"pair": "home-1280", "better": "equal", "why": "same"}],
            covered_paths=["home-1280-A.png", "home-1280-B.png"],
        )
        final = design_tools.DesignResult(**look.model_dump())
        return Run(cfg.session_id, ending="result", payload=final, first=look, termination=Termination(confirmed=True))

    folder = tmp_path / "candidate-skills"  # the candidate's own skills, as the updater left them
    for name in design_pack.manifest()["skills"]:
        (folder / name).mkdir(parents=True)
        (folder / name / "SKILL.md").write_text(preload.text(name) + "\nedited by the updater\n")
    result = pack_replay.replay(store, candidate(folder), run=run)
    assert (result.rounds, result.agreed_before, result.agreed_after) == (1, 0, 1)  # the after's new problem fails
    assert result.left_out == 6
    assert (
        result.pack == design_pack.identity(candidate().manifest, folder) != design_pack.identity()
    )  # the candidate's
    assert result.pack != design_pack.identity(candidate().manifest)  # its edited skills count, not the package's
    assert result.pack.startswith("impeccable-4.6.0.1+")
    [cfg] = seen
    assert cfg.skills == folder  # the judge loads the candidate's skills
    assert (cfg.role, cfg.message, cfg.reveal, cfg.model) == (
        "designer",
        "judge home",
        "The detector found: none.",
        "claude-opus-5.5",
    )
    assert (cfg.submit, cfg.first_look) == (design_tools.FINAL, design_tools.FIRST)
    assert [a["displayName"] for a in cfg.attachments] == ["home-1280-A.png", "home-1280-B.png"]
    assert cfg.observe().changed == ("home-1280-A.png", "home-1280-B.png")
    assert (cfg.policy.write, cfg.resume, cfg.session_id.startswith("replay-")) == (False, False, True)


def test_a_replay_judge_left_running_stops_the_replay_before_another_starts(repo, tmp_path) -> None:
    store = Store.open(repo)
    (shot := tmp_path / "s.png").write_bytes(b"png")
    shots = {"after-home-1280.png": shot, "before-home-1280.png": shot}
    for n in (1, 2):
        calibration.keep(store.shared, store.name, f"c{n}", kept_round(n, "pass", "pass"), shots)
    started = []

    def run(cfg):
        started.append(cfg.session_id)
        return Run(cfg.session_id, ending="result", termination=Termination(confirmed=False))

    with pytest.raises(pack_replay.ReplayError, match="may still be running"):
        pack_replay.replay(store, run=run)
    assert len(started) == 1


def candidate(folder: Path | None = None, **pins) -> pack_candidate.Candidate:
    made = design_pack.manifest() | {"pack": "impeccable-4.6.0.1"} | pins
    return pack_candidate.Candidate("skill-v4.6.0", made, json.dumps(made), "notice", None, folder)


def test_a_replay_refuses_a_candidate_whose_skills_the_judge_does_not_load(repo) -> None:
    with pytest.raises(design_pack.PackError, match="names skills the judge does not load"):
        pack_replay.replay(Store.open(repo), candidate(skills=["other"]), run=lambda _cfg: None)


def test_the_cli_runs_each_update_tool_and_reports_failures(repo, capsys) -> None:
    assert cli.main(["--repo", str(repo), "design-pack", "--check"]) == 0
    assert capsys.readouterr().out == "design pack impeccable-4.5.2.1: releases upstream unknown\n"
    assert cli.main(["--repo", str(repo), "design-pack", "--golden"]) == 1
    assert "not installed" in capsys.readouterr().out
    assert cli.main(["--repo", str(repo), "design-pack", "--replay"]) == 0
    assert capsys.readouterr().out.startswith("calibration replay: 0 decided rounds")
    assert cli.main(["--repo", str(repo), "design-pack", "--diff", str(repo), "--to", "skill-v9"]) == 1
    assert "CalledProcessError" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        cli.main(["--repo", str(repo), "design-pack", "--diff", str(repo)])
