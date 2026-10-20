from __future__ import annotations

import pytest

from owlbear_decisions import Link, LinkType, Scope, State, new_id, snapshot, write
from owlbear_decisions.storage import load_folder


def put(root, make, scope=Scope.PROJECT, project="owlbear", change="", **changes):
    project = "" if scope is Scope.GLOBAL else project
    decision = make(id=new_id(), aliases=(), scope=scope, project=project, change=change, **changes)
    folder = root / project / "changes" / change if change else root / project
    write(decision, folder)
    return decision


def test_a_snapshot_holds_global_and_one_projects_layers_with_their_findings(tmp_path, make):
    rule = put(tmp_path, make, Scope.GLOBAL)
    own = put(tmp_path, make, links=(Link(type=LinkType.EXCEPTION_TO, target=rule.id),))
    spent = put(tmp_path, make, Scope.CHANGE, change="20261020-090000-notes", state=State.SPENT)
    other = put(tmp_path, make, project="shop")
    (tmp_path / "shop" / "decisions" / "broken.md").write_text("nothing\n", encoding="utf-8")
    (tmp_path / "owlbear" / "decisions" / "broken.md").write_text("nothing\n", encoding="utf-8")

    seen = snapshot(tmp_path, "owlbear")

    assert {e.decision.id: e.layer.scope for e in seen.entries} == {
        rule.id: Scope.GLOBAL, own.id: Scope.PROJECT, spent.id: Scope.CHANGE
    }  # fmt: skip
    assert other.id not in {e.decision.id for e in seen.entries}
    assert [(f.rule, f.path.endswith("owlbear/decisions/broken.md")) for f in seen.findings] == [("schema", True)]
    assert seen.findings[0].involves == ()  # a file that did not load involves no decision
    assert seen.unreadable == seen.findings
    assert not seen.complete  # the rules the broken file holds are unknown
    assert snapshot(tmp_path, "").complete  # shop's broken file is not in the Global view
    assert seen.active(rule.id)
    assert seen.active(own.id)
    assert not seen.active(spent.id)


def test_two_in_force_successors_involve_both_and_what_they_replace(tmp_path, make):
    old = put(tmp_path, make)
    first = put(tmp_path, make, links=(Link(type=LinkType.REPLACES, target=old.id),))
    second = put(tmp_path, make, links=(Link(type=LinkType.REPLACES, target=old.id),))

    seen = snapshot(tmp_path, "owlbear")

    assert {f.rule for f in seen.findings} == {"two-successors"}
    assert {f.involves for f in seen.findings} == {(first.id, old.id), (second.id, old.id)}
    assert len(seen.findings_for(old.id)) == 2
    assert not seen.active(first.id)
    assert not seen.active(second.id)


def test_a_conflict_flag_keeps_a_decision_out_of_force_without_any_finding(tmp_path, make):
    flagged = put(tmp_path, make, conflict=True)

    seen = snapshot(tmp_path, "owlbear")

    assert seen.findings == ()
    assert not seen.active(flagged.id)


def test_findings_follow_the_decisions_they_involve_not_where_their_files_lie(tmp_path, make):
    rule = put(tmp_path, make, Scope.GLOBAL)
    replaces = (Link(type=LinkType.REPLACES, target=rule.id),)
    in_a, in_b = put(tmp_path, make, project="a", links=replaces), put(tmp_path, make, project="b", links=replaces)
    put(tmp_path, make, project="c")

    seen = snapshot(tmp_path, "c")

    assert {(f.rule, f.involves) for f in seen.findings} == {
        ("replace-scope", (in_a.id, rule.id)), ("replace-scope", (in_b.id, rule.id)),
        ("two-successors", (in_a.id, rule.id)), ("two-successors", (in_b.id, rule.id)),
    }  # fmt: skip
    assert not seen.active(rule.id)


def test_links_are_judged_over_the_whole_repository(tmp_path, make):
    source = put(tmp_path, make, project="shop")
    promoted = put(tmp_path, make, Scope.GLOBAL, links=(Link(type=LinkType.PROMOTED_FROM, target=source.id),))

    seen = snapshot(tmp_path, "owlbear")

    assert seen.findings == ()
    assert seen.active(promoted.id)


def test_a_decisions_path_that_is_a_file_is_a_finding_and_a_missing_project_has_no_layer(tmp_path):
    (tmp_path / "owlbear").mkdir()
    (tmp_path / "owlbear" / "decisions").write_text("", encoding="utf-8")

    seen = snapshot(tmp_path, "owlbear")
    assert [f.message for f in seen.findings] == ["not a folder: decisions must be a real folder"]
    assert not seen.complete
    assert [layer.scope for layer in snapshot(tmp_path, "absent").layers] == [Scope.GLOBAL]


@pytest.mark.parametrize(
    ("locked", "layer"),
    [
        ("owlbear", "owlbear"),
        ("owlbear/changes", "owlbear/changes/20261020-090000-notes"),
        ("owlbear/decisions", "owlbear"),
    ],
)
def test_a_folder_that_cannot_be_looked_into_raises_instead_of_loading_as_empty(tmp_path, make, locked, layer):
    put(tmp_path, make)
    put(tmp_path, make, Scope.CHANGE, change="20261020-090000-notes")
    (tmp_path / locked).chmod(0)
    try:
        with pytest.raises(PermissionError):
            snapshot(tmp_path, "owlbear")
        with pytest.raises(PermissionError):
            load_folder(tmp_path / layer)
    finally:
        (tmp_path / locked).chmod(0o755)
