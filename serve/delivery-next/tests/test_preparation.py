"""TD-96, TD-107: declared test preparation, the owner's permissions, the frozen snapshot and the preparer's patch."""

import json
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from owlbear_delivery_next.change_contracts import preparation, tools
from owlbear_delivery_next.change_contracts.models import Change, Environment, Exit, Step, StepKind, Waiting
from owlbear_delivery_next.change_contracts.preparation import DataPermissions, Preparation, Preparing
from owlbear_delivery_next.change_flow import loop, worktree
from owlbear_delivery_next.settings.config import CONFIG_FORMAT, Layer, resolve
from owlbear_delivery_next.state_store.store import Store
from owlbear_delivery_next.workflow_steps import check, prepare

TOOL = """import os, pathlib, sys
act, snap, db = sys.argv[1], os.environ.get("OWLBEAR_SNAPSHOT", ""), os.environ.get("TEST_DB", "")
with open(os.environ.get("TEST_LOG") or os.environ["PREP_LOG"], "a") as f:
    f.write(f"{act} {db}\\n")
    if os.environ.get("LIVE_SECRET"):
        f.write(f"secret-{act}\\n")
if act == "export":
    pathlib.Path(snap, "db.txt").write_text("alice@example.com")
if act in {"export-symlink", "export-hardlink"}:  # the live file itself, reached from the snapshot
    live = pathlib.Path(os.environ["PREP_LOG"]).with_name("live.txt")
    (os.symlink if act == "export-symlink" else os.link)(live, pathlib.Path(snap, "db.txt"))
if act == "mask":
    p = pathlib.Path(snap, "db.txt")
    p.write_text(p.read_text().replace("alice@example.com", "user-1"))
if act == "restore":
    pathlib.Path(db).write_text(pathlib.Path(snap, "db.txt").read_text())
if act == "seed":
    pathlib.Path(db).write_text(pathlib.Path(db).read_text() + "+seeded" if pathlib.Path(db).exists() else "seeded")
if act == "fail":
    sys.exit("restore refused")
if act == "fail-long":
    sys.exit("restore refused: " + "x" * 300)
"""
SETUP = """import os, pathlib, sys
act, log = sys.argv[1], pathlib.Path(os.environ["TEST_LOG"])
with log.open("a") as f:
    f.write(f"{act}-from-patch\\n")
if act == "seed":
    pathlib.Path(os.environ["TEST_DB"]).write_text("seeded by the patch")
if act == "cleanup" and log.with_name("cleanup-fails").exists():
    sys.exit("cleanup refused")
"""
LIVE = {"TEST_DB": "postgres://live/app"}
UNCOVERED = "its isolation does not point the live TEST_DB elsewhere"


def git(root: Path, *args: str) -> str:
    return worktree.git(root, *args)


@pytest.fixture
def env(tmp_path, monkeypatch):
    """A Change worktree with a fixture and source file, a store, a command tool and its log; no live system."""
    repo = tmp_path / "repo"
    (repo / "fixtures").mkdir(parents=True)
    (repo / "src").mkdir()
    (repo / "fixtures" / "users.json").write_text("[]\n")
    (repo / "src" / "app.py").write_text("print('app')\n")
    git(repo, "init", "-q")
    git(repo, "add", ".")
    git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "base")
    (tmp_path / "tool.py").write_text(TOOL)
    log = tmp_path / "prep.log"
    monkeypatch.setenv("PREP_LOG", str(log))
    monkeypatch.setenv("TEST_DB", LIVE["TEST_DB"])
    store = Store(tmp_path / "store")
    store.root.mkdir()
    return repo, store, log, tmp_path


def run(tmp_path: Path, act: str) -> str:
    return f"{sys.executable} {tmp_path / 'tool.py'} {act}"


def option(tmp_path: Path, kind: str = "live-copy-plus-data", **fields) -> Preparation:
    live = kind != "data-only"
    base = {
        "id": "copy", "kind": kind, "cleanup": run(tmp_path, "cleanup"),
        "isolation": {"TEST_DB": str(tmp_path / "test.db"), "TEST_LOG": str(tmp_path / "prep.log")},
        "setup_globs": ["fixtures/**"],
        **({"export": run(tmp_path, "export"), "masking": run(tmp_path, "mask"), "restore": run(tmp_path, "restore"),
            "data_classes": ["customers"], "live": LIVE} if live else {}),
        **({"seed": run(tmp_path, "seed")} if kind != "live-copy" else {}),
    }  # fmt: skip
    return Preparation.model_validate(base | fields)


def settings(*options: Preparation, **rules):
    data = DataPermissions(**({"data_classes": ["customers"], "isolation": ["TEST_DB"]} | rules))
    return resolve(None, Layer(preparations=list(options), data=data))


def change(repo: Path, check: str = "visual") -> Change:
    c = Change(slug="c1", step=Step(kind=StepKind.CHECK, task=check))
    c.env = Environment(check=check, command="serve", directory=".", ready_url="http://127.0.0.1:1/")
    c.names.worktree = str(repo)
    return c


def recipe(name: str = "copy", reason: str = "orders need live data") -> tools.CheckRecipe:
    return tools.CheckRecipe(
        command="npm run preview", directory=".", ready_url="http://127.0.0.1:4173/", summary="from the scripts",
        preparation=name, reason=reason,
    )  # fmt: skip


def lines(log: Path) -> list[str]:
    return [line.split()[0] for line in log.read_text().splitlines()] if log.exists() else []


@pytest.mark.parametrize(
    ("change_", "rules", "errors"),
    [
        ({"id": "copy"}, {}, []),
        ({}, {"data_classes": []}, ["data classes customers are not permitted"]),
        ({"isolation": {}}, {"isolation": []}, ["it declares no isolation", UNCOVERED]),
        ({"isolation": {"OTHER_DB": "x"}}, {}, ["its isolation lacks TEST_DB", UNCOVERED]),
        (
            {"isolation": {"TEST_DB": LIVE["TEST_DB"]}}, {},
            ["its isolation TEST_DB equals the live value", "its isolation TEST_DB points at the live TEST_DB"],
        ),
        ({"isolation": {"TEST_DB": "x", "OTHER_DB": "postgres://u:p@LIVE:5432/app/"}}, {"isolation": []},
         ["its isolation OTHER_DB points at the live TEST_DB"]),
        ({"copies_keys": True}, {}, ["it copies keys or secrets, which are not permitted"]),
        ({"masking": ""}, {}, ["it copies customers without masking"]),
    ],
)  # fmt: skip
def test_the_owner_permissions_refuse_an_unsafe_option(tmp_path, change_, rules, errors):
    rules = {"data_classes": ["customers"], "isolation": ["TEST_DB"]} | rules
    assert preparation.refusals(option(tmp_path, **change_), DataPermissions(**rules), LIVE) == errors


@pytest.mark.parametrize(
    ("kind", "fields", "errors"),
    [
        ("data-only", {}, []),
        ("data-only", {"data_classes": ["customers"]}, ["it declares no isolation"]),
        ("live-copy-plus-data", {}, ["it declares no isolation", UNCOVERED]),
    ],
)
def test_only_a_data_only_option_copying_no_data_may_declare_no_isolation(env, kind, fields, errors):
    repo, store, _log, tmp = env
    bare = option(tmp, kind, isolation={}, **fields)
    assert preparation.refusals(bare, DataPermissions(data_classes=["customers"]), LIVE) == errors
    if not errors:  # its explicit environment is the process essentials alone
        assert prepare.isolated(prepare.Prepared(check="visual", option=bare)).keys() <= set(preparation.BASE)
        assert prepare.reusable(store, change(repo), settings(bare, isolation=[]), LIVE) is False  # nothing recorded
        prepare._write(store, "c1", prepare.Prepared(check="visual", option=bare))  # noqa: SLF001 - as accepted
        assert prepare.reusable(store, change(repo), settings(bare, isolation=[]), LIVE) is True


@pytest.mark.parametrize(
    ("test", "live", "same"),
    [
        ("postgres://ro:x@db.live:5432/app", "postgres://admin:y@DB.live/app/", True),  # credentials never differ it
        ("postgres://db.live:5433/app", "postgres://db.live:5432/app", False),
        ("postgres://db.live/app_test", "postgres://db.live/app", False),
        ("postgres://db.test/app", "postgres://db.live/app", False),
        ("mysql://db.live/app", "postgres://db.live/app", False),
        (" s3-live-bucket ", "s3-live-bucket", True),
        ("s3-test-bucket", "s3-live-bucket", False),
    ],
)
def test_a_test_value_names_live_by_url_identity_or_exact_text(test, live, same):
    assert preparation.same(test, live) is same


def test_a_live_copy_must_point_every_declared_live_resource_elsewhere(env):
    repo, store, log, tmp = env
    rules = DataPermissions(data_classes=["customers"])
    two = {"TEST_DB": LIVE["TEST_DB"], "BUCKET": "s3://live-bucket"}
    assert preparation.refusals(option(tmp, live=two), rules, {}) == [
        "its isolation does not point the live BUCKET elsewhere"
    ]
    copy = option(tmp, live=two, isolation={"TEST_DB": "postgres://LIVE/app", "BUCKET": "s3://test-bucket"})
    assert preparation.refusals(copy, rules, {}) == ["its isolation TEST_DB points at the live TEST_DB"]
    prepare._write(store, "c1", prepare.Prepared(check="visual", option=copy))  # noqa: SLF001 - as accepted
    result = prepare.launch(store, change(repo), settings(copy, isolation=[]), lambda _e: None)
    assert (result.exit, lines(log)) == (Exit.ASK, [])  # nothing exported


def test_restore_seed_cleanup_and_the_launch_never_inherit_delivery_s_environment(env, monkeypatch):
    repo, store, log, tmp = env
    monkeypatch.setenv("LIVE_SECRET", "s3cret")
    c, s = change(repo), settings(option(tmp))
    prepare._write(store, "c1", prepare.Prepared(check="visual", option=option(tmp)))  # noqa: SLF001 - as accepted
    assert prepare.launch(store, c, s, lambda _e: None).exit == Exit.PENDING
    launch = prepare.environ(store, c)
    assert set(launch) - set(preparation.BASE) == {"TEST_DB", "TEST_LOG", "OWLBEAR_SNAPSHOT"}
    assert launch["PATH"] == prepare.os.environ["PATH"]
    c.env = None
    prepare.end(store, c, repo, s, lambda _e: None)
    assert lines(log) == ["export", "secret-export", "mask", "secret-mask", "restore", "seed", "cleanup"]


def test_export_and_masking_never_run_a_script_the_preparer_edited(env):
    repo, store, log, tmp = env
    edited = option(tmp, export=f"{sys.executable} fixtures/export.py", masking=f"{sys.executable} --x=fixtures/")
    head = git(repo, "rev-parse", "HEAD").strip()
    ctx = Preparing((edited,), settings(edited).data, head, live=LIVE)
    dirty = tools.Worktree(head, head, ("fixtures/export.py", "fixtures/a.json"))
    assert preparation.check(recipe(), dirty, repo, ctx) == [
        (
            "changes: fixtures/a.json, fixtures/export.py is run by the export or masking, which read live and run "
            "only the project's committed scripts - revert it"
        )
    ]
    rec = prepare.Prepared(check="visual", option=edited, paths=["fixtures/export.py"])
    prepare._write(store, "c1", rec)  # noqa: SLF001 - as accepted
    result = prepare.launch(store, change(repo), settings(edited), lambda _e: None)
    assert (result.exit, lines(log)) == (Exit.RETRY, [])
    assert result.reason == (
        "test preparation failed: the export or masking runs fixtures/export.py, which the preparer edited; they "
        "read live"
    )


def test_keys_and_unmasked_classes_are_allowed_only_by_the_permissions(tmp_path):
    rules = DataPermissions(data_classes=["customers"], unmasked=["customers"], keys=True)
    assert preparation.refusals(option(tmp_path, masking="", copies_keys=True), rules, LIVE) == []


@pytest.mark.parametrize(
    ("fields", "error"),
    [
        ({"kind": "live-copy", "seed": ""}, ""),
        ({"export": ""}, "a live-copy-plus-data option needs export"),
        ({"kind": "live-copy", "seed": "x"}, "a live-copy option adds no data"),
        ({"data_classes": []}, "a live copy names the data classes it copies"),
        ({"live": {}}, "a live copy names its live resources in live"),
        ({"live": {"TEST_DB": " "}}, "live names each resource's live value; TEST_DB is empty"),
        ({"kind": "data-only", "export": "x"}, "a data-only option exports, masks and copies nothing"),
        ({"isolation": {"OWLBEAR_SNAPSHOT": "x"}}, "isolation names environment variables"),
        ({"setup_globs": ["../outside/*"]}, "setup_globs must be repository-relative"),
    ],
)
def test_a_declared_option_names_exactly_the_commands_its_kind_runs(tmp_path, fields, error):
    if not error:
        option(tmp_path, **fields)
        return
    with pytest.raises(ValidationError, match=error):
        option(tmp_path, **fields)


def test_a_recipe_names_a_declared_permitted_option_and_edits_only_its_setup_files(env):
    repo, _store, _log, tmp = env
    head = git(repo, "rev-parse", "HEAD").strip()
    ctx = Preparing((option(tmp),), settings(option(tmp)).data, head, live=LIVE)

    def errors(r: tools.CheckRecipe, dirty=(), at: str = head) -> list[str]:
        return preparation.check(r, tools.Worktree(at, head, tuple(dirty)), repo, ctx)

    assert errors(recipe(), ["fixtures/users.json", "fixtures/extra/new.json"]) == []
    assert errors(recipe("nope"))[0] == "preparation: nope is not a declared option - use one of copy"
    assert errors(recipe(""))[0].startswith("preparation: empty - pick one of copy; a check never runs on live")
    assert errors(recipe(reason=""))[0].startswith("reason: empty")
    assert errors(recipe(), ["src/app.py"]) == [
        "changes: src/app.py edited; you may edit only the setup files fixtures/** and no Change code - revert them"
    ]
    assert errors(recipe(), at="f" * 40)[0].startswith("changes: HEAD moved")
    denied = Preparing(ctx.options, DataPermissions(isolation=["TEST_DB"]), head, live=LIVE)
    refused = preparation.check(recipe(), tools.Worktree(head, head), repo, denied)
    assert refused[0].startswith("preparation: copy is not permitted (data classes customers are not permitted)")
    none = preparation.check(recipe(), tools.Worktree(head, head, ("fixtures/users.json",)), repo, Preparing())
    assert none == [
        "preparation: this project declares no preparation options, so no check launches - ask",
        (
            "changes: fixtures/users.json edited; you may edit nothing without a preparation option and no Change "
            "code - revert them"
        ),
    ]


def test_with_no_safe_option_delivery_asks_and_starts_no_preparer(tmp_path):
    unsafe = settings(option(tmp_path), data_classes=[])
    asked = prepare.unsafe(unsafe, LIVE)
    assert (asked.exit, asked.cause, [o.next for o in asked.question.options]) == (
        Exit.ASK, "project-env:check:preparation-unsafe", [StepKind.CHECK, "pause"]
    )  # fmt: skip
    assert "copy: data classes customers are not permitted" in asked.reason
    assert prepare.unsafe(settings(option(tmp_path)), LIVE) is None


def test_without_a_declared_option_no_check_launches_and_the_owner_is_asked_to_declare_one(env):
    repo, store, _log, tmp = env
    asked = prepare.unsafe(settings(), LIVE)
    assert (asked.exit, asked.cause, [o.next for o in asked.question.options]) == (
        Exit.ASK, "project-env:check:preparation-missing", [StepKind.CHECK, "pause"]
    )  # fmt: skip
    assert "Declare at least one under `preparations` in the project's settings (`<project folder>/config.json`" in (
        asked.reason
    )
    assert "data-only option whose seed and cleanup are `true`" in asked.reason
    c = change(repo)
    assert not prepare.reusable(store, c, settings(), LIVE)  # a last recipe without a preparation never relaunches
    with pytest.raises(prepare.PrepareError, match="the check has no test preparation"):
        prepare.merge_base(store, c, settings(), lambda _e: None)(tmp)  # nor does the "before" capture
    assert prepare.environ(store, c) is None
    none = option(tmp, "data-only", id="none", seed="true", cleanup="true", isolation={"APP_ENV": "test"})
    assert prepare.unsafe(resolve(None, Layer(preparations=[none])), LIVE) is None  # a project without data


def test_one_frozen_snapshot_is_restored_separately_before_each_capture_and_ended(env):
    repo, store, log, tmp = env
    c, s, events = change(repo), settings(option(tmp)), []
    prepare._write(store, "c1", prepare.Prepared(check="visual", option=option(tmp)))  # noqa: SLF001 - as accepted
    before_root = tmp / "merge-base"
    before_root.mkdir()

    launched = prepare.merge_base(store, c, s, events.append)(before_root)
    assert launched["TEST_DB"] == str(tmp / "test.db")  # the "before" launch runs isolated
    assert (tmp / "test.db").read_text() == "user-1+seeded"  # masked before it was frozen, then seeded
    (tmp / "test.db").write_text("changed by the before capture")
    assert prepare.due(store, c)
    result = prepare.launch(store, c, s, events.append)
    assert (result.exit, result.waiting) == (Exit.PENDING, Waiting.CHECK_START)
    assert (tmp / "test.db").read_text() == "user-1+seeded"  # the same snapshot, restored again
    assert lines(log) == ["export", "mask", "restore", "seed", "restore", "seed"]
    assert all(line.endswith(str(tmp / "test.db")) for line in log.read_text().splitlines()[2:])
    rec = prepare.read(store, "c1", "visual")
    snapshot = Path(rec.snapshot)
    assert (snapshot.is_dir(), snapshot.is_relative_to(repo), prepare.due(store, c)) == (True, False, False)
    assert prepare.environ(store, c)["OWLBEAR_SNAPSHOT"] == rec.snapshot

    assert prepare.left(store, c) == []  # the check's environment still runs
    c.env = None
    assert prepare.end(store, c, repo, s, events.append) is None
    assert (lines(log)[-1], snapshot.exists()) == ("cleanup", False)  # retention: deleted after the check
    assert prepare.left(store, c) == []


def test_cleanup_runs_after_a_failed_restore_and_the_snapshot_may_be_kept(env):
    repo, store, log, tmp = env
    failing = option(tmp, restore=run(tmp, "fail"))
    c, s = change(repo, "pc1"), settings(failing, retention="keep")
    prepare._write(store, "c1", prepare.Prepared(check="pc1", option=failing))  # noqa: SLF001 - as accepted
    result = prepare.launch(store, c, s, lambda _e: None)
    assert (result.exit, "restore refused" in result.reason) == (Exit.RETRY, True)
    c.env = None  # a failed preparation forgets the environment, as the runner does
    assert [r.check for r in prepare.left(store, c)] == ["pc1"]
    prepare.end(store, c, repo, s, lambda _e: None)
    assert lines(log) == ["export", "mask", "fail", "cleanup"]
    assert Path(prepare.read(store, "c1", "pc1").snapshot).is_dir()  # the owner keeps it until the next export


LONG = "restore refused: " + "x" * 300


@pytest.mark.parametrize(("act", "cause"), [("fail", "restore refused"), ("fail-long", LONG)])
def test_a_failed_command_on_a_long_path_still_says_why(env, act, cause):
    repo, store, _log, tmp = env
    deep = tmp
    if (pad := 290 - len(run(tmp, act)) - 1) > 0:  # a declared command of about 290 characters, wherever tmp is
        deep = tmp.joinpath(*(["d" * 100] * (pad // 101)), "e" * (pad % 101 or 1))
        deep.mkdir(parents=True)
        (deep / "tool.py").write_text(TOOL)
    failing = option(tmp, restore=run(deep, act))
    assert len(failing.restore) >= 289
    c, s = change(repo, "pc1"), settings(failing)
    prepare._write(store, "c1", prepare.Prepared(check="pc1", option=failing))  # noqa: SLF001 - as accepted
    result = prepare.launch(store, c, s, lambda _e: None)
    assert result.reason.endswith(f"failed: {cause[: check.CAUSE]}")  # the note is whole, not cut by the cap
    assert len(result.reason) <= 300


@pytest.mark.parametrize("args", [["python", "tool.py", "fail"], ["/" + "x" * 200 + "/python", "/w/tool.py", "fail"]])
def test_a_note_quotes_a_command_within_its_bound_keeping_its_end(args):
    shown = check.shown(args)
    assert len(shown) <= check.SHOWN
    assert shown.endswith("/w/tool.py fail" if len(args[0]) > 100 else "python tool.py fail")


def test_a_snapshot_changed_after_it_was_frozen_is_never_restored(env):
    repo, store, _log, tmp = env
    c, s = change(repo), settings(option(tmp))
    prepare._write(store, "c1", prepare.Prepared(check="visual", option=option(tmp)))  # noqa: SLF001 - as accepted
    (tmp / "mb").mkdir()
    prepare.merge_base(store, c, s, lambda _e: None)(tmp / "mb")
    (Path(prepare.read(store, "c1", "visual").snapshot) / "db.txt").write_text("alice@example.com")
    result = prepare.launch(store, c, s, lambda _e: None)
    assert (result.exit, result.reason) == (
        Exit.RETRY,
        "test preparation failed: the snapshot changed after it was frozen",
    )


def test_a_revoked_permission_asks_and_a_changed_option_prepares_again(env):
    repo, store, _log, tmp = env
    c = change(repo)
    prepare._write(store, "c1", prepare.Prepared(check="visual", option=option(tmp)))  # noqa: SLF001 - as accepted
    assert prepare.launch(store, c, settings(option(tmp), data_classes=[]), lambda _e: None).exit == Exit.ASK
    changed = prepare.launch(store, c, settings(option(tmp, seed=run(tmp, "other"))), lambda _e: None)
    assert (changed.exit, changed.reason) == (Exit.RETRY, "the preparation option copy changed since it was chosen")
    assert not prepare.reusable(store, c, settings(option(tmp, seed=run(tmp, "other"))), LIVE)
    assert prepare.reusable(store, c, settings(option(tmp)), LIVE)


def test_setup_edits_become_a_patch_applied_for_the_check_and_discarded_after(env):
    repo, store, _log, tmp = env
    data = option(tmp, "data-only", id="fixtures")
    c, s = change(repo, "pc1"), settings(data)
    (repo / "src" / "left.py").write_text("found before the session\n")
    ctx = prepare.context(store, c, s, repo)
    (repo / "fixtures" / "users.json").write_text('[{"name": "Ada"}]\n')
    (repo / "fixtures" / "orders.json").write_text("[]\n")
    accepted = loop.StepResult(exit=Exit.PENDING, waiting=Waiting.PERSON_CHECK)

    assert prepare.chosen(store, c, repo, recipe("fixtures"), ctx, accepted) is accepted
    assert prepare.edits(repo) == ["src/left.py"]  # the preparer's edits are gone; what it found stays
    assert sorted(prepare.read(store, "c1", "pc1").paths) == ["fixtures/orders.json", "fixtures/users.json"]
    (repo / "src" / "left.py").unlink()

    assert prepare.launch(store, c, s, lambda _e: None).exit == Exit.PENDING
    assert (repo / "fixtures" / "users.json").read_text() == '[{"name": "Ada"}]\n'  # applied
    assert sorted(prepare.edits(repo)) == ["fixtures/orders.json", "fixtures/users.json"]
    c.env = None
    assert prepare.end(store, c, repo, s, lambda _e: None) is None
    assert (prepare.edits(repo), (repo / "fixtures" / "users.json").read_text()) == ([], "[]\n")
    assert prepare.read(store, "c1", "pc1").paths  # kept with the recipe for its next check


OLD, NEW, THIRD = "fixtures/users.json", "fixtures/néw users.json", "fixtures/third.json"


@pytest.mark.parametrize("how", ["worktree", "index", "chained"])
def test_a_preparer_s_rename_is_kept_as_its_setup_patch_and_undone(env, how):
    repo, store, _log, tmp = env
    c, s = change(repo, "pc1"), settings(option(tmp, "data-only", id="fixtures"))
    ctx = prepare.context(store, c, s, repo)
    if how == "worktree":
        (repo / OLD).rename(repo / NEW)
        git(repo, "add", "-N", NEW)  # " R new\0old": a rename in the worktree column (#744)
    else:
        git(repo, "mv", OLD, NEW)
    if how == "chained":
        (repo / NEW).rename(repo / THIRD)
        git(repo, "add", "-N", THIRD)  # "R  new\0old\0 R third\0new"
    assert git(repo, "status", "--porcelain=v1", "-z").startswith((" R " if how == "worktree" else "R  ") + NEW)
    names = sorted({OLD, NEW} | ({THIRD} if how == "chained" else set()))
    assert sorted(prepare.edits(repo)) == names  # both real ends, each once
    accepted = loop.StepResult(exit=Exit.PENDING, waiting=Waiting.PERSON_CHECK)

    assert prepare.chosen(store, c, repo, recipe("fixtures"), ctx, accepted) is accepted
    assert (prepare.edits(repo), (repo / OLD).read_text()) == ([], "[]\n")
    assert sorted(prepare.read(store, "c1", "pc1").paths) == names

    assert prepare.launch(store, c, s, lambda _e: None).exit == Exit.PENDING
    last = THIRD if how == "chained" else NEW
    assert (not (repo / OLD).exists(), (repo / last).read_text()) == (True, "[]\n")  # applied
    c.env = None
    assert prepare.end(store, c, repo, s, lambda _e: None) is None
    assert (prepare.edits(repo), (repo / OLD).read_text()) == ([], "[]\n")


def test_a_setup_file_added_then_deleted_leaves_an_empty_patch(env):
    repo, store, _log, tmp = env
    c, s = change(repo, "pc1"), settings(option(tmp, "data-only", id="fixtures"))
    (repo / "src" / "left.py").write_text("found before the session\n")
    ctx = prepare.context(store, c, s, repo)
    (repo / "fixtures" / "tmp.json").write_text("{}\n")
    git(repo, "add", "fixtures/tmp.json")
    (repo / "fixtures" / "tmp.json").unlink()  # "AD": only in the index, nothing to keep against HEAD
    accepted = loop.StepResult(exit=Exit.PENDING, waiting=Waiting.PERSON_CHECK)

    assert prepare.chosen(store, c, repo, recipe("fixtures"), ctx, accepted) is accepted
    assert prepare.read(store, "c1", "pc1").paths == []  # no pathless capture of the edit it found
    assert prepare.launch(store, c, s, lambda _e: None).exit == Exit.PENDING
    assert (prepare.edits(repo), (repo / "src" / "left.py").read_text()) == (
        ["src/left.py"],
        "found before the session\n",
    )


def test_a_session_that_ends_without_a_recipe_keeps_none_of_its_edits(env):
    repo, store, _log, tmp = env
    c, s = change(repo, "pc1"), settings(option(tmp))
    ctx = prepare.context(store, c, s, repo)
    (repo / "fixtures" / "users.json").write_text("edited\n")
    asked = loop.StepResult(exit=Exit.ASK)
    assert prepare.chosen(store, c, repo, recipe(), ctx, asked) is asked
    assert (prepare.edits(repo), prepare.read(store, "c1", "pc1")) == ([], None)


def test_a_patch_that_cannot_be_discarded_stops_the_change(env, monkeypatch):
    repo, store, _log, tmp = env
    c, s = change(repo, "pc1"), settings(option(tmp))
    rec = prepare.Prepared(check="pc1", option=option(tmp), paths=["fixtures/users.json"], applied=str(repo), open=True)
    prepare._write(store, "c1", rec)  # noqa: SLF001 - an applied patch
    c.env = None

    def broken(*_a):
        raise subprocess.CalledProcessError(128, "git", stderr=b"index.lock exists")

    monkeypatch.setattr(prepare, "discard", broken)
    stop = prepare.end(store, c, repo, s, lambda _e: None)
    assert (stop.exit, stop.stop.action) == (Exit.STOP, f"Discard those edits in {repo}")
    assert prepare.left(store, c)  # it is ended again once the owner resumes


def test_an_old_project_layer_with_a_seed_command_loads_without_it(tmp_path):
    store = Store(tmp_path)
    store.config_path.write_text(json.dumps({"format": 1, "seed": "npm run seed", "widths": [1600]}))
    layer = store.read_config()
    assert (layer.format, layer.widths, "seed" in layer.model_dump()) == (CONFIG_FORMAT, [1600], False)
    assert "seed" not in store.settings().model_dump()
    with pytest.raises(ValidationError, match="seed"):
        Layer.model_validate({"format": 3, "seed": "npm run seed"})


def test_an_old_layers_designer_settings_become_the_design_judges(tmp_path):
    store = Store(tmp_path)
    store.config_path.write_text(json.dumps({"format": 2, "agents": {"designer": {"model": "g-2", "effort": "low"}}}))

    layer = store.read_config()

    assert (layer.format, list(layer.agents)) == (CONFIG_FORMAT, ["design-judge"])  # TD-169
    assert (store.settings().agents["design-judge"].model, store.settings().sources["agents.design-judge.model"]) == (
        "g-2",
        "project",
    )


def test_the_edits_of_a_preparer_whose_runner_died_are_discarded_before_any_later_step(env):
    repo, store, _log, tmp = env
    c, events = change(repo, "pc1"), []
    (repo / "src" / "left.py").write_text("found before the session\n")
    prepare.context(store, c, settings(option(tmp)), repo)
    (repo / "fixtures" / "users.json").write_text("edited by the preparer\n")
    (repo / "fixtures" / "new.json").write_text("{}\n")
    prepare.stray(store, "c1", events.append)  # the runner died before the session's end was recorded
    assert (prepare.edits(repo), events[0]["event"]) == (["src/left.py"], "prepared-stray")
    prepare.stray(store, "c1", events.append)
    assert len(events) == 1


def test_a_live_copy_pointing_at_live_is_refused_and_never_exported(env):
    repo, store, log, tmp = env
    rules = DataPermissions(data_classes=["customers"], isolation=["TEST_DB"])
    copy = option(tmp, isolation={"TEST_DB": "postgres://live:5432/app"})
    why = ["its isolation TEST_DB points at the live TEST_DB"]
    assert preparation.refusals(copy, rules, LIVE) == why
    data = option(tmp, "data-only", id="fixtures")
    head = git(repo, "rev-parse", "HEAD").strip()
    ctx = Preparing((copy, data), rules, head, live=LIVE)
    refused = preparation.check(recipe(), tools.Worktree(head, head), repo, ctx)
    assert refused[0] == f"preparation: copy is not permitted ({why[0]}) - pick another or ask"
    assert preparation.check(recipe("fixtures"), tools.Worktree(head, head), repo, ctx) == []

    prepare._write(store, "c1", prepare.Prepared(check="visual", option=copy))  # noqa: SLF001 - as accepted
    assert prepare.launch(store, change(repo), settings(copy), lambda _e: None).exit == Exit.ASK
    alongside = prepare.launch(store, change(repo), settings(copy, data), lambda _e: None)
    assert (alongside.exit, alongside.reason) == (Exit.RETRY, "the preparation option copy is no longer permitted")
    assert lines(log) == []  # nothing exported
    prepare._write(store, "c1", prepare.Prepared(check="pc1", option=data))  # noqa: SLF001 - as accepted
    assert prepare.launch(store, change(repo, "pc1"), settings(data), lambda _e: None).exit == Exit.PENDING
    assert lines(log) == ["seed"]


@pytest.mark.parametrize("link", ["export-symlink", "export-hardlink"])
def test_an_export_that_reaches_live_through_a_link_is_never_masked_and_is_deleted(env, link):
    repo, store, log, tmp = env
    (live := tmp / "live.txt").write_text("alice@example.com")
    linked = option(tmp, export=run(tmp, link))
    c, s = change(repo), settings(linked, retention="keep")
    prepare._write(store, "c1", prepare.Prepared(check="visual", option=linked))  # noqa: SLF001 - as accepted
    kept = set(prepare.snapshots().iterdir()) if prepare.snapshots().is_dir() else set()
    result = prepare.launch(store, c, s, lambda _e: None)
    assert (result.exit, result.reason) == (
        Exit.RETRY, "test preparation failed: the snapshot holds db.txt, a link or special file"
    )  # fmt: skip
    assert (lines(log), live.read_text()) == ([link], "alice@example.com")  # masking never ran through the link
    assert prepare.read(store, "c1", "visual").snapshot == ""
    assert set(prepare.snapshots().iterdir()) == kept  # deleted


def test_a_failed_masking_is_deleted_even_when_the_owner_keeps_snapshots(env, monkeypatch):
    repo, store, _log, tmp = env
    failing = option(tmp, masking=run(tmp, "fail"))
    c, s = change(repo), settings(failing, retention="keep")
    prepare._write(store, "c1", prepare.Prepared(check="visual", option=failing))  # noqa: SLF001 - as accepted
    events = []
    with monkeypatch.context() as broken:
        broken.setattr(prepare.shutil, "rmtree", lambda *_a, **_k: None)  # the deletion fails
        result = prepare.launch(store, c, s, lambda _e: None)
        assert result.reason.startswith("test preparation failed: the unmasked snapshot ")
        assert "could not be deleted; the masking command" in result.reason
        snapshot = Path(prepare.read(store, "c1", "visual").snapshot)
        assert (snapshot / "db.txt").read_text() == "alice@example.com"
        c.env = None
        assert prepare.end(store, c, repo, s, events.append) is None
        assert (events[-1]["outstanding"], [r.check for r in prepare.left(store, c)]) == (True, ["visual"])
    assert prepare.end(store, c, repo, s, events.append) is None
    assert (snapshot.exists(), prepare.left(store, c), events[-1]["cleanup"]) == (False, [], "ok")
    assert prepare.read(store, "c1", "visual").snapshot == ""  # an unmasked snapshot is never kept


def patched(env) -> tuple[Change, object, Path]:
    """A data-only check whose seed and cleanup run a setup script only the preparer's accepted patch holds."""
    repo, store, _log, tmp = env
    script = f"{sys.executable} fixtures/setup.py"
    data = option(tmp, "data-only", id="fixtures", seed=f"{script} seed", cleanup=f"{script} cleanup")
    c, s = change(repo, "pc1"), settings(data)
    ctx = prepare.context(store, c, s, repo)
    (repo / "fixtures" / "setup.py").write_text(SETUP)
    accepted = loop.StepResult(exit=Exit.PENDING, waiting=Waiting.PERSON_CHECK)
    assert prepare.chosen(store, c, repo, recipe("fixtures"), ctx, accepted) is accepted
    assert not (repo / "fixtures" / "setup.py").exists()
    return c, s, tmp / "test.db"


def test_seed_and_cleanup_run_with_the_setup_patch_and_a_failed_cleanup_stays_outstanding_until_it_succeeds(env):
    repo, store, log, tmp = env
    c, s, db = patched(env)
    assert prepare.launch(store, c, s, lambda _e: None).exit == Exit.PENDING
    assert (lines(log), db.read_text()) == (["seed-from-patch"], "seeded by the patch")  # the data-only seed
    (fails := tmp / "cleanup-fails").write_text("")
    c.env, events = None, []
    assert prepare.end(store, c, repo, s, events.append) is None
    assert (lines(log)[-1], events[-1]["outstanding"]) == ("cleanup-from-patch", True)  # the patch's own script ran
    assert (prepare.edits(repo), [r.check for r in prepare.left(store, c)]) == ([], ["pc1"])  # discarded; still owed
    fails.unlink()
    assert prepare.end(store, c, repo, s, events.append) is None  # the next runner: the patch is applied again
    assert (lines(log)[-1], events[-1]["cleanup"], prepare.left(store, c), prepare.edits(repo)) == (
        "cleanup-from-patch", "ok", [], []
    )  # fmt: skip


def commit(repo: Path, *paths: str) -> None:
    git(repo, "add", *paths)
    git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "by the preparer")


@pytest.mark.parametrize("ending", ["chosen", "stray"])
def test_a_preparer_commit_is_undone_and_none_of_its_edits_stay(env, ending):
    repo, store, _log, tmp = env
    c, s, events = change(repo, "pc1"), settings(option(tmp)), []
    start = git(repo, "rev-parse", "HEAD").strip()
    ctx = prepare.context(store, c, s, repo)
    (repo / "fixtures" / "users.json").write_text("committed by the preparer\n")
    (repo / "src" / "app.py").write_text("print('changed')\n")
    commit(repo, "fixtures/users.json", "src/app.py")
    (repo / "fixtures" / "orders.json").write_text("[]\n")
    if ending == "chosen":
        accepted = loop.StepResult(exit=Exit.PENDING, waiting=Waiting.PERSON_CHECK)
        result = prepare.chosen(store, c, repo, recipe(), ctx, accepted)
        assert (result.exit, result.reason.startswith("the preparer committed")) == (Exit.RETRY, True)
    else:
        prepare.stray(store, "c1", events.append)
        assert events[0]["reset"] != start
    assert (git(repo, "rev-parse", "HEAD").strip(), prepare.edits(repo)) == (start, [])
    assert ((repo / "fixtures" / "users.json").read_text(), prepare.read(store, "c1", "pc1")) == ("[]\n", None)


@pytest.mark.parametrize("ending", ["chosen", "stray"])
def test_ignored_setup_files_the_preparer_created_or_changed_are_put_back(env, ending):
    repo, store, _log, tmp = env
    (repo / ".gitignore").write_text("*.local\n")
    commit(repo, ".gitignore")
    (repo / "fixtures" / "kept.local").write_text("the owner's\n")
    (repo / "src" / "other.local").write_text("outside the setup globs\n")
    c, s = change(repo, "pc1"), settings(option(tmp))
    ctx = prepare.context(store, c, s, repo)
    (repo / "fixtures" / "kept.local").write_text("changed by the preparer\n")
    (repo / "fixtures" / "deep").mkdir()
    (repo / "fixtures" / "deep" / "new.local").write_text("made by the preparer\n")
    if ending == "chosen":
        accepted = loop.StepResult(exit=Exit.PENDING, waiting=Waiting.PERSON_CHECK)
        assert prepare.chosen(store, c, repo, recipe(), ctx, accepted) is accepted
    else:
        prepare.stray(store, "c1", lambda _e: None)
    assert (repo / "fixtures" / "kept.local").read_text() == "the owner's\n"
    assert not (repo / "fixtures" / "deep" / "new.local").exists()
    assert (repo / "src" / "other.local").read_text() == "outside the setup globs\n"
