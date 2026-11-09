"""#1066: a stuck step's repair at its three boundaries: weakened checks, unfinished edits, public issues."""

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from owlbear_delivery_next.change_contracts import check_hint
from owlbear_delivery_next.change_contracts.models import Brief, Change, Plan, Step, StepKind, Task
from owlbear_delivery_next.change_contracts.profile_record import Profile, ProfileEntry
from owlbear_delivery_next.change_contracts.repair_records import Witness
from owlbear_delivery_next.change_contracts.repair_tools import Defect
from owlbear_delivery_next.change_flow import stuck, worktree
from owlbear_delivery_next.github.account import Origin
from owlbear_delivery_next.workflow_steps import defect_issue, repair_copy, step_repair

NOW = datetime(2026, 11, 7, 12, tzinfo=UTC)


@pytest.fixture
def repo(tmp_path, monkeypatch) -> Path:
    (tmp_path / "gitconfig").write_text("")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(tmp_path / "gitconfig"))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    for who in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{who}_NAME", "t")
        monkeypatch.setenv(f"GIT_{who}_EMAIL", "t@t")
    work = tmp_path / "work"
    (work / "tests").mkdir(parents=True)
    for name, text in {"a.txt": "a\n", "b.txt": "b\n", "tests/test_a.py": "def test_a():\n    assert 1\n"}.items():
        (work / name).write_text(text)
    worktree.git(work, "init", "-q", "-b", "c1")
    worktree.git(work, "add", ".")
    worktree.git(work, "commit", "-q", "-m", "base")
    return work


def stuck_change() -> Change:
    c = Change(
        slug="c1", brief=Brief(version=1, approved_version=1, challenged=1, scope=["."]),
        plan=Plan(tasks=[Task(id="t1", title="t1", scope=["."])]), step=Step(kind=StepKind.BUILD, task="t1"),
    )  # fmt: skip
    stuck.start(c, "project-env:build:check-pytest", "the check pytest cannot finish", NOW)
    return c


def test_a_fix_that_weakens_a_test_is_never_applied(repo, tmp_path) -> None:
    c, at = stuck_change(), tmp_path / "copy"
    r = c.repairs.current
    r.base, r.fix = repair_copy.copy(repo, at), "patch"
    (at / "tests/test_a.py").write_text("import pytest\n\n\n@pytest.mark.skip\ndef test_a():\n    assert 1\n")
    head = worktree.git(repo, "rev-parse", "HEAD")
    store = SimpleNamespace(log=lambda *_: None, write=lambda *_: None)
    step_repair._proven(store, None, c, (repo, at), ("true",), 60.0, Profile())  # noqa: SLF001
    assert "weakens a check" in c.stop.reason
    assert "tests/test_a.py (adds a suppression or skip)" in c.stop.reason
    assert (worktree.git(repo, "rev-parse", "HEAD"), c.repairs.done[-1].commit) == (head, "")  # nothing applied


def test_a_selector_fix_is_held_even_when_its_own_empty_check_passes(repo, tmp_path, monkeypatch) -> None:
    package = repo / "serve/tools"
    source = package / "src/owlbear_tools"
    source.mkdir(parents=True)
    (package / "pyproject.toml").write_text('[project.scripts]\ntest = "owlbear_tools.testing:test_main"\n')
    for name, text in {
        "testing.py": "from owlbear_tools import task_scope, missing_selector\n",
        "task_scope.py": "from . import task_testing\n",
        "task_testing.py": "from .test_impact import select\n\ndef commands():\n    return ['tests/test_a.py']\n",
        "test_impact.py": "from owlbear_tools import test_dependencies\n",
        "test_dependencies.py": "FORMAT = 1\n",
    }.items():
        (source / name).write_text(text)
    worktree.git(repo, "add", "serve/tools")
    worktree.git(repo, "commit", "-q", "-m", "root selector")
    c, at = stuck_change(), tmp_path / "copy"
    c.brief.scope = ["serve/tools"]
    r = c.repairs.current
    r.base, r.fix = repair_copy.copy(repo, at), "patch"
    path = "serve/tools/src/owlbear_tools/task_testing.py"
    (at / path).write_text("def commands():\n    return []\n")
    witness = (check_hint.task_command(check_hint.qualified(".", "uv run test --changed"), r.base, r.base),)
    head = worktree.git(repo, "rev-parse", "HEAD")
    monkeypatch.setattr(
        step_repair,
        "_ran",
        lambda _at, commands, *_: Witness(
            commands=list(commands), exit=0, seconds=0.0, output="No test scope matched."
        ),
    )
    store = SimpleNamespace(log=lambda *_: None, write=lambda *_: None)
    flagged = tuple(command.replace("uv run ", "uv run --locked ", 1) for command in witness)
    step_repair._proven(store, None, c, (repo, at), flagged, 60.0, Profile())  # noqa: SLF001
    assert worktree.git(repo, "rev-parse", "HEAD") == head
    assert r.held == [f"changes {path}, which the step's check runs, so it proves nothing alone"]
    assert all(
        step_repair._named(f"serve/tools/src/owlbear_tools/{name}.py", witness, repo)  # noqa: SLF001
        for name in ("testing", "task_scope", "task_testing", "test_impact", "test_dependencies")
    )
    missing = "serve/tools/src/owlbear_tools/missing_selector.py"
    assert not (repo / missing).exists()
    assert step_repair._named(missing, witness, repo)  # noqa: SLF001
    assert step_repair._named(path, ("uv run --locked test --changed",), repo)  # noqa: SLF001
    assert step_repair._named(path, ("python -m owlbear_tools.testing --changed",), repo)  # noqa: SLF001
    (source / "task_scope.py").write_text("def broken(\n")
    reason = step_repair._check_hold(path, witness, repo)  # noqa: SLF001
    assert "cannot inspect the unchanged check" in reason
    assert "task_scope.py" in reason
    assert "proves nothing alone" in reason
    (source / "task_scope.py").write_text("from . import task_testing\n")
    malformed = repo / "serve/aaa/pyproject.toml"
    malformed.parent.mkdir()
    malformed.write_text("[project\n")
    worktree.git(repo, "add", "serve/aaa/pyproject.toml")
    reason = step_repair._check_hold(path, witness, repo)  # noqa: SLF001
    assert "TOMLDecodeError" in reason
    assert str(malformed) in reason
    assert "proves nothing alone" in reason
    (package / "pyproject.toml").write_text("[project\n")
    monkeypatch.setattr(worktree, "tracking", lambda *_: "c1")
    prof = Profile(
        entries={
            "check:.": ProfileEntry(state="known", value="uv run test --changed", evidence="owner confirmed"),
        }
    )
    bound = step_repair._witness(c, prof, repo)  # noqa: SLF001
    assert len(bound) == 1
    assert f"--task-base {r.base}" in bound[0]
    assert "--target " in bound[0]
    assert "TOMLDecodeError" in r.evidence
    assert "serve/tools/pyproject.toml" in r.evidence


def test_a_fix_reaches_the_branch_without_touching_the_steps_unfinished_edits(repo, tmp_path) -> None:
    (repo / "a.txt").write_text("a, unstaged\n")
    (repo / "b.txt").write_text("b, staged\n")
    worktree.git(repo, "add", "b.txt")
    (repo / "u.txt").write_text("untracked\n")
    at = tmp_path / "copy"
    base = repair_copy.copy(repo, at)
    (at / "c.txt").write_text("the fix\n")
    repair_copy.changed(at, base)
    fix = repair_copy.commit(at, "fix")
    new = repair_copy.apply(repo, "c1", base, fix, "fix: c")
    assert worktree.git(repo, "show", "--name-only", "--format=", new).split() == ["c.txt"]  # the fix alone
    assert ((repo / "a.txt").read_text(), (repo / "u.txt").read_text()) == ("a, unstaged\n", "untracked\n")
    assert worktree.git(repo, "diff", "--cached", "--name-only").split() == ["b.txt"]  # still staged, unchanged
    (at / "a.txt").write_text("a, by the repair\n")  # the same file as the unfinished edit
    repair_copy.changed(at, base)
    again = repair_copy.commit(at, "fix a")
    with pytest.raises(repair_copy.RepairError, match=r"a\.txt, which hold the step's unfinished edits"):
        repair_copy.apply(repo, "c1", base, again, "fix: a")
    assert ((repo / "a.txt").read_text(), worktree.git(repo, "rev-parse", "HEAD").strip()) == ("a, unstaged\n", new)


def test_a_private_projects_defect_text_naming_it_is_held_not_filed(repo, monkeypatch) -> None:
    made: list[str] = []
    issues = SimpleNamespace(find=lambda _m: None, create=lambda title, _body: made.append(title))
    monkeypatch.setattr(defect_issue, "OwlbearIssues", lambda *_: issues)
    monkeypatch.setattr(defect_issue.Origin, "of", classmethod(lambda *_: Origin("github.com", "acme", "secret-shop")))
    monkeypatch.setattr(defect_issue.repo_target, "view", lambda *_: SimpleNamespace(visibility="private"))
    store = SimpleNamespace(name="secret-shop", root=repo / "store")
    path = "serve/tools/src/owlbear_tools/testing.py:216"
    named = Defect(
        title="--changed runs the full suite", text="secret-shop's a.txt routes to the full suite", paths=[path]
    )
    said = defect_issue.file(store, repo, named)
    held = "it names this private project, or that could not be checked (a.txt, secret-shop)"
    assert said.startswith(f"held for you, not filed: {held}")
    assert made == []
