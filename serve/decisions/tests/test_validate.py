from __future__ import annotations

import pytest

from owlbear_decisions.models import Link, LinkType, Scope, State, new_id
from owlbear_decisions.storage import serialize, write
from owlbear_decisions.validate import Entry, Layer, check, main, validate, validate_repo


def entry(root, make, scope=Scope.PROJECT, project="p", change="", **changes):
    project = "" if scope is Scope.GLOBAL else project
    change = change or ("c1" if scope is Scope.CHANGE else "")
    decision = make(**{"id": new_id(), "aliases": (), "scope": scope, "project": project, "change": change, **changes})
    folder = root / project / "changes" / change if change else root / project
    return Entry(folder / "decisions" / f"{decision.id}.md", Layer(folder, scope, project, change), decision)


@pytest.mark.parametrize("failure", ["schema", "link-type"])
def test_validator_classifies_file_schema_failures(tmp_path, make, failure):
    good = entry(tmp_path, make, Scope.GLOBAL)
    write(good.decision, good.layer.folder)
    if failure == "schema":
        (good.path.parent / "broken.md").write_text("nothing\n", encoding="utf-8")
    else:
        linked = good.decision.model_copy(update={"links": (Link(type=LinkType.RELATED_TO, target=new_id()),)})
        good.path.write_text(serialize(linked).replace("type: related_to", "type: contradicts"), encoding="utf-8")
    assert [f.rule for f in validate_repo(tmp_path)] == [failure]


@pytest.mark.parametrize("duplicate", [False, True], ids=["shared-alias", "shared-id"])
def test_identity_uniqueness_is_not_alias_uniqueness(tmp_path, make, duplicate):
    first = entry(tmp_path, make, Scope.GLOBAL, aliases=("TD-1",))
    second = entry(tmp_path, make, aliases=("TD-1",), **({"id": first.decision.id} if duplicate else {}))
    findings = check([first, second])
    assert [f.rule for f in findings] == (["duplicate-id"] * 2 if duplicate else [])
    if duplicate:
        assert {f.path for f in findings} == {str(first.path), str(second.path)}


@pytest.mark.parametrize(
    "case",
    [
        (LinkType.REPLACES, {"scope": Scope.GLOBAL}, {"scope": Scope.GLOBAL}, []),
        (LinkType.REPLACES, {}, {}, []),
        (LinkType.REPLACES, {"scope": Scope.CHANGE}, {}, []),
        (LinkType.REPLACES, {"scope": Scope.CHANGE}, {"scope": Scope.CHANGE}, []),
        (LinkType.REPLACES, {"scope": Scope.GLOBAL}, {}, ["replace-scope"]),
        (LinkType.REPLACES, {"scope": Scope.GLOBAL}, {"scope": Scope.CHANGE}, ["replace-scope"]),
        (LinkType.REPLACES, {}, {"scope": Scope.CHANGE}, ["replace-scope"]),
        (LinkType.REPLACES, {"scope": Scope.CHANGE, "change": "c2"}, {"scope": Scope.CHANGE}, ["replace-scope"]),
        (LinkType.PROMOTED_FROM, {}, {"scope": Scope.GLOBAL}, []),
        (LinkType.PROMOTED_FROM, {"scope": Scope.CHANGE}, {"scope": Scope.GLOBAL}, []),
        (LinkType.PROMOTED_FROM, {"scope": Scope.CHANGE}, {}, []),
        (LinkType.PROMOTED_FROM, {"scope": Scope.GLOBAL}, {"scope": Scope.GLOBAL}, ["no-successor", "promote-scope"]),
        (LinkType.PROMOTED_FROM, {}, {}, ["no-successor", "promote-scope"]),
        (LinkType.PROMOTED_FROM, {"scope": Scope.CHANGE, "project": "q"}, {}, ["no-successor", "promote-scope"]),
        (LinkType.PROMOTED_FROM, {}, {"scope": Scope.CHANGE}, ["no-successor", "promote-scope"]),
        (LinkType.DEPENDS_ON, {"scope": Scope.GLOBAL}, {}, []),
        (LinkType.RELATED_TO, {}, {"project": "q"}, ["link-target"]),
        (LinkType.RELATED_TO, {}, {"scope": Scope.GLOBAL}, ["link-target"]),
        (LinkType.EXCEPTION_TO, {}, {}, ["exception-target"]),
        (LinkType.DEPENDS_ON, None, {}, ["link-target"]),
    ],
)
def test_links_respect_visibility_replacement_and_promotion_scope(tmp_path, make, case):
    link, target, source, expected = case
    old = entry(tmp_path, make, **(target or {}), state=State.REPLACED if link in {
        LinkType.REPLACES, LinkType.PROMOTED_FROM
    } else State.IN_FORCE)
    successor = entry(tmp_path, make, **source, links=(Link(type=link, target=old.decision.id),))
    findings = check([old, successor] if target is not None else [successor])
    assert sorted(f.rule for f in findings) == expected
    for finding in findings:
        assert successor.decision.id in finding.involves or finding.involves == (old.decision.id,)


@pytest.mark.parametrize("kind", ["repeated", "two-live", "draft", "promotion-draft", "two-promotions", "mixed"])
def test_successor_count_includes_only_eligible_live_successors(tmp_path, make, kind):
    old = entry(tmp_path, make, state=State.REPLACED)
    link = Link(type=LinkType.PROMOTED_FROM if "promotion" in kind else LinkType.REPLACES, target=old.decision.id)
    first = entry(tmp_path, make, scope=Scope.GLOBAL if "promotion" in kind else Scope.PROJECT,
                  state=State.DRAFT if kind == "draft" else State.IN_FORCE,
                  links=(link, link) if kind == "repeated" else (link,))
    entries = [old, first]
    expected = []
    if kind in {"two-live", "two-promotions", "mixed"}:
        second = entry(tmp_path, make, Scope.GLOBAL if kind in {"two-promotions", "mixed"} else Scope.PROJECT,
                       links=(Link(type=LinkType.PROMOTED_FROM if kind != "two-live" else LinkType.REPLACES,
                                   target=old.decision.id),))
        entries += [second, entry(tmp_path, make, Scope.GLOBAL if kind == "two-promotions" else Scope.PROJECT,
                                  state=State.WITHDRAWN, links=(link,))]
        expected = ["two-successors"] * 2
    elif kind == "draft":
        expected = ["no-successor"]
    elif kind == "promotion-draft":
        proposed = entry(tmp_path, make, state=State.REPLACED)
        entries += [proposed, entry(tmp_path, make, Scope.GLOBAL, state=State.DRAFT,
                                   links=(Link(type=LinkType.PROMOTED_FROM, target=proposed.decision.id),))]
        expected = ["no-successor"]
    findings = check(entries)
    assert sorted(f.rule for f in findings) == expected
    if kind in {"two-live", "two-promotions", "mixed"}:
        assert {f.involves for f in findings} == {
            (first.decision.id, old.decision.id), (second.decision.id, old.decision.id)
        }
    elif kind in {"draft", "promotion-draft"}:
        assert findings[0].involves == ((old if kind == "draft" else proposed).decision.id,)


@pytest.mark.parametrize("kind", ["240", "241", "outside-change", "wrong-project"])
def test_placement_and_statement_limit_are_independent_findings(tmp_path, make, kind):
    found = entry(tmp_path, make, statement="x" * int(kind)) if kind.isdigit() else entry(
        tmp_path, make, Scope.CHANGE if kind == "outside-change" else Scope.PROJECT, project="q"
    )
    if not kind.isdigit():
        found = Entry(found.path, Layer(tmp_path / "p", Scope.PROJECT, "p"), found.decision)
    findings = check([found])
    assert [f.rule for f in findings] == ([] if kind == "240" else [
        "statement-length" if kind == "241" else "placement"
    ])
    if kind == "outside-change":
        assert "outside a change folder" in findings[0].message


def test_validator_cli_and_explicit_layer_selection(tmp_path, make, capsys):
    rule = entry(tmp_path, make, Scope.GLOBAL)
    local = entry(tmp_path, make, links=(Link(type=LinkType.EXCEPTION_TO, target=rule.decision.id),))
    change = entry(tmp_path, make, Scope.CHANGE, links=(Link(type=LinkType.REFINES, target=rule.decision.id),))
    for found in (rule, local, change):
        write(found.decision, found.layer.folder)
    assert validate_repo(tmp_path) == []
    assert main([str(tmp_path)]) == 0
    assert capsys.readouterr().out.endswith("0 finding(s)\n")
    long = entry(tmp_path, make, statement="x" * 241)
    write(long.decision, long.layer.folder)
    assert [f.rule for f in validate(None, [tmp_path / "p"])] == ["link-target", "link-target", "statement-length"]
    assert validate(tmp_path, []) == []
    assert main([str(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert "statement-length: statement has 241 characters" in out
    assert out.endswith("1 finding(s)\n")
