"""The watcher's report-only policy (W1a): identified targets, unresolved shell effects and the order of the roots."""

from __future__ import annotations

from pathlib import Path

import pytest

from owlbear_delivery_next.change_contracts import watch_policy
from owlbear_delivery_next.change_contracts.watch_policy import NO_PATH, OUTSIDE, SHELL, Asked, Call, Places, judge


@pytest.fixture
def lay(tmp_path):
    """A machine: OwlBear's folder with two Changes' worktrees and state, a main checkout and a temporary folder."""
    home = tmp_path / "home"
    owlbear = home / ".owlbear"
    own, other = owlbear / "worktrees" / "shop-1a2b3c4d" / "c1", owlbear / "worktrees" / "shop-1a2b3c4d" / "c2"
    store = owlbear / "projects" / "p1"
    clone, tmp = tmp_path / "clone", tmp_path / "tmp"
    for folder in (own / "src", other, store / "changes" / "c1", store / "changes" / "c2", clone / ".git", tmp):
        folder.mkdir(parents=True)
    exempt = (tmp, home / ".cache", home / "Library" / "Caches", home / ".npm", owlbear, store)  # pytest's are in /tmp
    guarded = (owlbear / "worktrees", store / "changes", clone, clone / ".git")
    places = Places(guarded, (store / "changes" / "c1",), exempt, home, tmp).resolved()
    return {"own": own.resolve(), "other": other, "store": store, "clone": clone, "tmp": tmp, "home": home} | {
        "places": places
    }


def edit(path: str) -> Call:
    return Call("edit", {"path": path})


def shell(*asked: Asked, redirect: bool = False) -> Call:
    return Call("bash", {"command": "make"}, redirect, asked)


def outcome(lay, call: Call) -> watch_policy.Outcome:
    return judge(call, lay["own"], lay["places"])


def test_the_never_judged_roots_are_temporary_folders_and_the_users_tool_caches(tmp_path) -> None:
    env = {"TMPDIR": str(tmp_path / "T"), "UV_CACHE_DIR": str(tmp_path / "uv"), "HOME": "ignored"}
    found = watch_policy.exempt(tmp_path, env)
    temporary = (Path("/tmp"), Path("/private/var/folders"))  # noqa: S108 - the roots it names
    assert found[:5] == (*temporary, tmp_path / ".cache", tmp_path / "Library" / "Caches", tmp_path / ".npm")
    assert found[5:] == (tmp_path / "T", tmp_path / "uv")


def test_a_file_tools_write_is_judged_by_where_its_canonical_path_lies(lay) -> None:
    inside = ["src/a.py", "./src/../src/b.py", str(lay["own"] / "c.py"), "$TMPDIR/x", "${TMPDIR}/y"]
    inside += [str(lay["store"] / "changes" / "c1" / "notes.json"), str(lay["store"] / "delivery.db")]
    inside += ["~/.cache/uv/wheel", "~/Library/Caches/ms-playwright/x", "~/.npm/_cacache/x"]
    for path in inside:
        assert outcome(lay, edit(path)).inside, path
    home = lay["home"].resolve()
    assert outcome(lay, edit("~/notes.txt")) == watch_policy.Outcome((str(home / "notes.txt"),))
    assert outcome(lay, edit("../c2/x.py")).targets == (str(lay["other"].resolve() / "x.py"),)  # relative, outside
    assert outcome(lay, edit("~/notes.txt")).verdict == OUTSIDE == "outside write (not judged yet)"


def test_another_changes_worktree_or_state_and_the_main_checkout_are_reported_even_under_an_exempt_root(lay) -> None:
    under_owlbear = [lay["other"] / "app.py", lay["store"] / "changes" / "c2" / "change.json"]
    checkout = [lay["clone"] / "README.md", lay["clone"] / ".git" / "config"]  # pytest's tmp_path: a temp root
    for path in [*under_owlbear, *checkout]:
        assert outcome(lay, edit(str(path))).targets == (str(path.resolve()),), path


def test_a_checkout_under_a_temporary_root_is_still_the_checkout(tmp_path) -> None:
    tmp, home = tmp_path / "T", tmp_path / "home"
    clone, own = tmp / "clone", tmp / "worktrees" / "c1"
    for folder in (clone / ".git", own, home):
        folder.mkdir(parents=True)
    places = Places((tmp / "worktrees", clone, clone / ".git"), (), (tmp,), home, tmp).resolved()
    assert judge(edit(str(clone / "a.py")), own.resolve(), places).targets == (str((clone / "a.py").resolve()),)
    assert judge(edit("$TMPDIR/scratch.txt"), own.resolve(), places).inside
    assert judge(edit("x.py"), own.resolve(), places).inside  # its own worktree, first of all


def test_symlinks_are_resolved_for_targets_and_roots(lay) -> None:
    (lay["own"] / "out").symlink_to(lay["home"])
    (lay["home"] / "into").symlink_to(lay["own"])
    assert outcome(lay, edit("out/escaped.txt")).targets == (str(lay["home"].resolve() / "escaped.txt"),)
    assert outcome(lay, edit(str(lay["home"] / "into" / "fine.txt"))).inside


def test_read_tools_and_read_requests_yield_nothing(lay) -> None:
    assert outcome(lay, Call("view", {"path": "/etc/hosts"})).inside
    assert outcome(lay, Call("grep", {"pattern": "x", "path": "/"})).inside
    assert outcome(lay, Call("view", {"path": "/etc/hosts"}, asked=(Asked("read", ("/etc/hosts",)),))).inside


def test_every_shell_call_is_unresolved_unless_the_runtime_proves_each_command_read_only(lay) -> None:
    ro, writes = Asked("shell", read_only=True), Asked("shell", read_only=False)
    assert outcome(lay, shell()).unresolved == SHELL  # the start alone proves nothing
    assert outcome(lay, shell()).verdict == "unresolved (shell effects not classified yet)"
    assert outcome(lay, shell(ro)).inside
    assert outcome(lay, shell(writes)).unresolved == SHELL
    assert outcome(lay, shell(ro, writes)).unresolved == SHELL
    assert outcome(lay, shell(Asked("shell", read_only=True, redirect=True))).unresolved == SHELL
    assert outcome(lay, shell(ro, redirect=True)).unresolved == SHELL  # the start saw a write redirection


def test_read_only_evidence_suppresses_only_the_shell_effect_it_covers(lay) -> None:
    outside = Asked("write", (str(lay["home"] / "x.txt"),))
    mixed = outcome(lay, shell(Asked("shell"), outside))
    assert (mixed.targets, mixed.unresolved, mixed.verdict) == ((str(lay["home"].resolve() / "x.txt"),), SHELL, OUTSIDE)
    covered = outcome(lay, shell(Asked("shell", read_only=True), outside))
    assert (covered.targets, covered.unresolved) == ((str(lay["home"].resolve() / "x.txt"),), "")


def test_a_write_requests_paths_and_its_file_edits_are_identified_targets(lay) -> None:
    moved = Asked("write", (str(lay["own"] / "a.py"), str(lay["home"] / "b.py"), str(lay["other"] / "c.py")))
    assert outcome(lay, Call("apply_patch", "*** patch", asked=(moved,))).targets == (
        str(lay["home"].resolve() / "b.py"),
        str(lay["other"].resolve() / "c.py"),
    )
    assert outcome(lay, Call("apply_patch", "*** patch")).unresolved == NO_PATH  # its targets are not known yet
    assert outcome(lay, Call("mcp-tool", {"x": 1})).inside
