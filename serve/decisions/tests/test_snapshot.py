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


@pytest.mark.parametrize("view", ["local", "foreign-replacement", "foreign-promotion", "nonfolder"])
def test_snapshot_visibility_and_local_completeness(tmp_path, make, view):
    rule = put(tmp_path, make, Scope.GLOBAL)
    if view == "foreign-replacement":
        replaces = (Link(type=LinkType.REPLACES, target=rule.id),)
        first = put(tmp_path, make, project="a", links=replaces)
        second = put(tmp_path, make, project="b", links=replaces)
        put(tmp_path, make, project="c")
        seen = snapshot(tmp_path, "c")
        assert {(f.rule, f.involves) for f in seen.findings} == {
            (code, (d.id, rule.id)) for code in ("replace-scope", "two-successors") for d in (first, second)
        }
        assert not seen.active(rule.id)
        return
    if view == "foreign-promotion":
        source = put(tmp_path, make, project="shop")
        promoted = put(tmp_path, make, Scope.GLOBAL, links=(Link(type=LinkType.PROMOTED_FROM, target=source.id),))
        seen = snapshot(tmp_path, "owlbear")
        assert seen.findings == ()
        assert seen.active(promoted.id)
        return
    if view == "nonfolder":
        (tmp_path / "owlbear").mkdir()
        (tmp_path / "owlbear" / "decisions").write_text("", encoding="utf-8")
        seen = snapshot(tmp_path, "owlbear")
        assert [f.message for f in seen.findings] == ["not a folder: decisions must be a real folder"]
        assert not seen.complete
        assert [layer.scope for layer in snapshot(tmp_path, "absent").layers] == [Scope.GLOBAL]
        return
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


@pytest.mark.parametrize("flagged", [False, True], ids=["competing-successors", "conflict-without-findings"])
def test_snapshot_activity_requires_force_and_clear_graph(tmp_path, make, flagged):
    if flagged:
        decision = put(tmp_path, make, conflict=True)
        seen = snapshot(tmp_path, "owlbear")
        assert seen.findings == ()
        assert not seen.active(decision.id)
        return
    old = put(tmp_path, make)
    first = put(tmp_path, make, links=(Link(type=LinkType.REPLACES, target=old.id),))
    second = put(tmp_path, make, links=(Link(type=LinkType.REPLACES, target=old.id),))

    seen = snapshot(tmp_path, "owlbear")

    assert {f.rule for f in seen.findings} == {"two-successors"}
    assert {f.involves for f in seen.findings} == {(first.id, old.id), (second.id, old.id)}
    assert len(seen.findings_for(old.id)) == 2
    assert not seen.active(first.id)
    assert not seen.active(second.id)


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


@pytest.mark.parametrize("locked", ["shop", "shop/changes", "shop/decisions"])
def test_another_projects_unreadable_folder_is_a_finding_outside_the_view_not_a_stop(tmp_path, make, locked):
    rule = put(tmp_path, make, Scope.GLOBAL)
    own = put(tmp_path, make)
    put(tmp_path, make, project="shop")
    put(tmp_path, make, Scope.CHANGE, project="shop", change="20261020-090000-notes")
    (tmp_path / locked).chmod(0)
    try:
        seen = snapshot(tmp_path, "owlbear")
        with pytest.raises(PermissionError):
            snapshot(tmp_path, "shop")  # its own project's folder still stops it
    finally:
        (tmp_path / locked).chmod(0o755)

    assert {e.decision.id for e in seen.entries} == {rule.id, own.id}
    assert (seen.complete, seen.findings) == (True, ())
    [(layer, finding)] = seen.outside
    where = tmp_path / ("shop/changes" if locked == "shop/changes" else "shop")  # each layer is read on its own
    assert (layer.project, layer.scope, finding.rule, finding.path) == ("shop", Scope.PROJECT, "unreadable", str(where))
    assert seen.active(rule.id)


def test_readable_foreign_layer_still_counts_beside_an_unreadable_layer(tmp_path, make):
    rule = put(tmp_path, make, Scope.GLOBAL)
    put(tmp_path, make, project="shop", links=(Link(type=LinkType.REPLACES, target=rule.id),))
    put(tmp_path, make, Scope.CHANGE, project="shop", change="20261020-090000-notes")
    (tmp_path / "shop" / "changes").chmod(0)
    try:
        seen = snapshot(tmp_path, "owlbear")
    finally:
        (tmp_path / "shop" / "changes").chmod(0o755)

    assert not seen.active(rule.id)  # shop's readable replacement of a Global rule is still a finding here
    assert "replace-scope" in {f.rule for f in seen.findings}
    assert not seen.unreadable
    assert [(layer.project, finding.rule) for layer, finding in seen.outside] == [("shop", "unreadable")]


def test_another_projects_unreadable_folder_keeps_its_whole_error(tmp_path, make, monkeypatch):
    """#971: the finding says the error's type and every line of its message, never only its start."""
    import importlib  # noqa: PLC0415 - the module, not the function the package exports under its name

    module = importlib.import_module("owlbear_decisions.snapshot")
    put(tmp_path, make, project="shop")
    said = (
        "BEGIN the folder could not be listed\n" + "\n".join(f"line {i:03d} of the reason" for i in range(60)) + "\nEND"
    )

    def unlistable(_folder):
        raise OSError(said)

    monkeypatch.setattr(module, "change_folders", unlistable)
    [(_layer, finding)] = snapshot(tmp_path, "owlbear").outside
    assert (finding.path, finding.message) == (str(tmp_path / "shop" / "changes"), f"cannot be read: OSError: {said}")
