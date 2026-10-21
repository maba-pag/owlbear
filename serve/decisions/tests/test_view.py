from __future__ import annotations

import hashlib
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

from owlbear_decisions import Link, LinkType, Origin, Scope, State, new_id, snapshot, write
from owlbear_decisions.view import hash_problem, main, render

AT = datetime(2026, 10, 20, tzinfo=UTC)
ROOT = Path(__file__).parents[3]
COMMIT = "0123456789abcdef0123456789abcdef01234567"


def put(root, make, seed, scope=Scope.PROJECT, **changes):
    project = "" if scope is Scope.GLOBAL else changes.pop("project", "owlbear")
    change = changes.pop("change", "")
    decision = make(id=new_id(AT, seed=seed), scope=scope, project=project, change=change, **changes)
    write(decision, root / project / "changes" / change if change else root / project)
    return decision


def data(root, make):
    """Global and owlbear decisions in force and retired, a draft, a conflict, a finding and another project's."""
    autonomous = {"origin": Origin.AUTONOMOUS, "applies_to": {}}
    found = {
        "rule": put(root, make, "rule", Scope.GLOBAL, aliases=("TD-1",), topic="Global rules", **autonomous),
        "old": put(root, make, "old", aliases=("TD-2",), title="Old lint", state=State.REPLACED),
        "gone": put(root, make, "gone", aliases=(), topic="", title="Gone", state=State.WITHDRAWN, **autonomous),
        "spent": put(root, make, "spent", Scope.CHANGE, change="20261020-0900-notes", state=State.SPENT),
        "draft": put(root, make, "draft", state=State.DRAFT, title="Maybe"),
        "flag": put(root, make, "flag", aliases=("TD-9",), conflict=True, title="Flagged"),
        "other": put(root, make, "other", project="shop", title="Shop only"),
    }
    found["new"] = put(
        root, make, "new", aliases=("TD-3",), links=(Link(type=LinkType.REPLACES, target=found["old"].id),)
    )
    missing = new_id(AT, seed="missing")
    found["bad"] = put(root, make, "bad", title="Broken link", links=(Link(type=LinkType.DEPENDS_ON, target=missing),))
    return found


def git(root: Path, *args: str) -> str:
    done = subprocess.run(  # noqa: S603 - fixed git argument vector
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],  # noqa: S607
        cwd=root, capture_output=True, text=True, check=True,
    )  # fmt: skip
    return done.stdout.strip()


def test_the_view_lists_global_then_the_projects_rules_by_topic_and_retired_ones_in_history(tmp_path, make):
    found = data(tmp_path / "data", make)

    text = render(snapshot(tmp_path / "data", "owlbear"), COMMIT)

    rules, history = text.split("## History")
    assert rules.index("### Global") < rules.index(found["rule"].id) < rules.index("### `owlbear`")
    assert rules.index("### `owlbear`") < rules.index("#### C-28 Code and tool rules") < rules.index(found["new"].id)
    assert f"- **`{found['new'].id}` (TD-3)** Lint once" in rules
    assert "  - Statement: The builder's code is linted once, at submission." in rules
    assert "  - Origin: decided by owner, chat 2026-10-20, 2026-10-20; scope: project `owlbear`" in rules
    assert "  - Applies to: paths `serve/**/*.py`; roles `builder`" in rules
    assert "  - Read back: confirmed 2026-10-20" in rules
    assert "words" not in rules
    assert f"  - Links: replaces `{found['old'].id}` (TD-2)" in rules
    assert "Applies to" not in rules[rules.index(found["rule"].id) : rules.index("### `owlbear`")]
    assert "Drafts (proposed, not in force) are not listed: 1." in rules
    for name in ("old", "gone", "spent", "draft", "other"):
        assert f"- **`{found[name].id}`" not in rules, name
    assert (
        f"- `{found['old'].id}` (TD-2) replaced by `{found['new'].id}` (TD-3): Old lint (project `owlbear`)" in history
    )
    assert f"- `{found['gone'].id}` withdrawn: Gone (project `owlbear`)" in history
    assert f"- `{found['spent'].id}` (TD-417) spent: Lint once (Change `owlbear/20261020-0900-notes`)" in history
    assert "Shop only" not in text
    assert found["other"].id not in text
    assert f"Data commit: `{COMMIT}`" in text
    assert "`.owlbear/research/delivery-liveness-first-rebuild.md` stays authoritative" in text


def test_an_inherited_decision_shows_it_was_never_read_back(tmp_path, make):
    root = tmp_path / "data"
    inherited = put(root, make, "inherited", title="Inherited", inherited=True, read_back="none")
    unread = put(root, make, "unread", title="Unread", read_back="none")

    rules = render(snapshot(root, "owlbear"), COMMIT).split("## History")[0]

    blocks = {d.id: rules[rules.index(d.id) :].split("\n- ")[0] for d in (inherited, unread)}
    assert "  - Read back: inherited, never read back" in blocks[inherited.id]
    assert "confirmed" not in rules
    assert "Read back" not in blocks[unread.id]


def test_conflicts_and_findings_are_marked_and_listed_never_hidden(tmp_path, make):
    found = data(tmp_path, make)

    text = render(snapshot(tmp_path, "owlbear"), COMMIT)

    flagged = text[text.index(f"**`{found['flag'].id}`") :]
    assert flagged.index("  - **Conflict:** not active until the owner resolves it") < flagged.index("\n#")
    broken = text[text.index(f"**`{found['bad'].id}`") :]
    assert broken.index("  - **Findings:** link-target (see Findings); not active") < broken.index("\n#")
    findings = text[text.index("## Findings") :]
    assert f"- `owlbear/decisions/{found['bad'].id}.md`: link-target: depends_on target" in findings
    assert str(tmp_path) not in text  # paths are relative to the data root, so the view does not depend on it


def test_the_view_is_deterministic_and_its_last_line_hashes_everything_above(tmp_path, make):
    data(tmp_path / "a", make)
    shutil.copytree(tmp_path / "a", tmp_path / "b")

    text = render(snapshot(tmp_path / "a", "owlbear"), COMMIT)

    assert text == render(snapshot(tmp_path / "b", "owlbear"), COMMIT)
    assert text.splitlines()[-1].startswith("<!-- decisions-view sha256:")
    assert hash_problem(text) == ""
    assert "edited by hand" in hash_problem(text.replace("Lint once", "Lint twice", 1))
    assert "last line" in hash_problem(text.rsplit("<!--", 1)[0])


def test_an_empty_data_repository_is_an_empty_view_and_none_needs_one(tmp_path, make):
    (tmp_path / "owlbear" / "research").mkdir(parents=True)

    text = render(snapshot(tmp_path, "owlbear"), "none")

    assert "Data commit: none (no decisions migrated yet)" in text
    assert text.count("None.") == 3
    put(tmp_path, make, "one")
    with pytest.raises(ValueError, match="names the data commit"):
        render(snapshot(tmp_path, "owlbear"), "none")
    with pytest.raises(ValueError, match="not a commit hash"):
        render(snapshot(tmp_path, "owlbear"), "main")


def test_the_committed_view_is_the_view_of_a_data_repository_without_decisions(tmp_path, capsys):
    """The scheduled check passes today: owlbear-data has no decisions until the owner reviews the migration."""
    git(tmp_path, "init", "-q")
    (tmp_path / "owlbear").mkdir()
    (tmp_path / "owlbear" / "notes.md").write_text("x\n", encoding="utf-8")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-q", "-m", "data")

    assert main([str(tmp_path), "--out", str(ROOT / ".owlbear/decisions.md"), "--check"]) == 0
    assert "matches owlbear-data" in capsys.readouterr().out


def test_check_passes_on_equal_fails_on_a_changed_decision_and_ignores_unrelated_data_commits(tmp_path, make, capsys):
    root, out = tmp_path / "data", tmp_path / "decisions.md"
    root.mkdir()
    git(root, "init", "-q")
    data(root, make)
    git(root, "add", ".")
    git(root, "commit", "-q", "-m", "decisions")
    pinned = git(root, "rev-parse", "HEAD")
    assert main([str(root), "--out", str(out)]) == 0
    assert f"Data commit: `{pinned}`" in out.read_text(encoding="utf-8")
    assert main([str(root), "--out", str(out), "--check"]) == 0

    (root / "owlbear" / "research.md").write_text("unrelated\n", encoding="utf-8")
    git(root, "add", ".")
    git(root, "commit", "-q", "-m", "unrelated")
    assert main([str(root), "--out", str(out), "--check"]) == 0  # a new data commit alone is not staleness

    put(root, make, "later", title="A later rule")
    git(root, "add", ".")
    git(root, "commit", "-q", "-m", "a new decision")
    capsys.readouterr()
    assert main([str(root), "--out", str(out), "--check"]) == 1
    err = capsys.readouterr().err
    assert "is stale" in err
    assert "+- **`" in err
    assert "A later rule" in err
    assert "the lead chat regenerates the view" in err
    assert out.read_text(encoding="utf-8").count(pinned) == 1  # --check never writes


def test_a_rules_rationale_and_consequences_are_listed_so_check_compares_them(tmp_path, make):
    root, out = tmp_path / "data", tmp_path / "decisions.md"
    rule = put(root, make, "rule", consequences="Reviews\n wait  for lint.")
    assert main([str(root), "--out", str(out), "--commit", COMMIT]) == 0
    text = out.read_text(encoding="utf-8")
    assert "  - Rationale: Why: **speed**. Second paragraph.\n  - Consequences: Reviews wait for lint.\n" in text

    for changed in ({"rationale": "Why: cost."}, {"consequences": "Reviews never wait."}):
        held = rule
        rule = rule.model_copy(update=changed)
        write(rule, root / "owlbear", held.revision)
        assert main([str(root), "--out", str(out), "--commit", COMMIT, "--check"]) == 1, changed
        assert main([str(root), "--out", str(out), "--commit", COMMIT]) == 0


def test_check_fails_on_a_missing_or_hand_edited_view(tmp_path, capsys):
    out = tmp_path / "decisions.md"
    (tmp_path / "data").mkdir()

    assert main([str(tmp_path / "data"), "--commit", "none", "--out", str(out), "--check"]) == 1
    assert "is missing" in capsys.readouterr().err
    assert main([str(tmp_path / "data"), "--commit", "none", "--out", str(out)]) == 0
    out.write_text(out.read_text(encoding="utf-8").replace("None.", "Nothing.", 1), encoding="utf-8")
    assert main([str(tmp_path / "data"), "--commit", "none", "--out", str(out), "--check"]) == 1
    assert "edited by hand" in capsys.readouterr().err


def test_a_rehashed_line_that_only_looks_like_the_commit_line_is_still_compared(tmp_path, capsys):
    out = tmp_path / "decisions.md"
    (tmp_path / "data").mkdir()
    assert main([str(tmp_path / "data"), "--commit", "none", "--out", str(out)]) == 0
    body = out.read_text(encoding="utf-8").rsplit("<!--", 1)[0].replace("None.", "None.\nData commit: Use tabs.", 1)
    out.write_text(f"{body}<!-- decisions-view sha256:{hashlib.sha256(body.encode()).hexdigest()} -->\n")

    assert hash_problem(out.read_text(encoding="utf-8")) == ""  # the pull-request check cannot tell
    assert main([str(tmp_path / "data"), "--commit", "none", "--out", str(out), "--check"]) == 1  # main's can
    assert "is stale" in capsys.readouterr().err


def test_a_promoted_decision_shows_its_global_successor_in_history(tmp_path, make):
    source = put(tmp_path, make, "source", title="Local rule", state=State.REPLACED)
    wide = put(tmp_path, make, "wide", Scope.GLOBAL, title="Wide rule",
               links=(Link(type=LinkType.PROMOTED_FROM, target=source.id),))  # fmt: skip

    history = render(snapshot(tmp_path, "owlbear"), COMMIT).split("## History")[1]

    assert f"- `{source.id}` (TD-417) replaced by `{wide.id}` (TD-417): Local rule" in history
