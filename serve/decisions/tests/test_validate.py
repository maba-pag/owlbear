from __future__ import annotations

import pytest

from owlbear_decisions.models import Link, LinkType, Origin, Scope, State, new_id
from owlbear_decisions.storage import serialize, write
from owlbear_decisions.validate import main, validate, validate_repo


@pytest.fixture
def put(tmp_path, make):
    """Write a decision into the layer its scope names under `tmp_path`; returns it."""

    def put_(scope=Scope.PROJECT, project="p", change="", folder=None, **changes):
        project = "" if scope is Scope.GLOBAL else project
        change = change or ("c1" if scope is Scope.CHANGE else "")
        fields = {"id": new_id(), "aliases": (), "scope": scope, "project": project, "change": change}
        decision = make(**{**fields, **changes})
        if folder is None:
            folder = tmp_path / project / "changes" / change if change else tmp_path / project
        write(decision, folder)
        return decision

    return put_


def rules(root):
    return sorted(finding.rule for finding in validate_repo(root))


def test_a_clean_repository_has_no_findings(tmp_path, put):
    rule = put(Scope.GLOBAL)
    put(links=(Link(type=LinkType.EXCEPTION_TO, target=rule.id),))
    put(Scope.CHANGE, links=(Link(type=LinkType.REFINES, target=rule.id),))
    assert validate_repo(tmp_path) == []
    assert main([str(tmp_path)]) == 0


def test_schema_error(tmp_path, put):
    put()
    (tmp_path / "p" / "decisions" / "broken.md").write_text("nothing\n", encoding="utf-8")
    assert rules(tmp_path) == ["schema"]


def test_link_type_outside_the_set(tmp_path, put):
    decision = put(Scope.GLOBAL, links=(Link(type=LinkType.RELATED_TO, target=new_id()),))
    path = tmp_path / "decisions" / f"{decision.id}.md"
    path.write_text(serialize(decision).replace("type: related_to", "type: contradicts"), encoding="utf-8")
    assert rules(tmp_path) == ["link-type"]


def test_a_repeated_replaces_link_is_one_successor(tmp_path, put):
    old = put(state=State.REPLACED)
    link = Link(type=LinkType.REPLACES, target=old.id)
    put(links=(link, link))
    assert rules(tmp_path) == []


def test_duplicate_id(tmp_path, put):
    first = put(Scope.GLOBAL)
    put(id=first.id)
    assert rules(tmp_path) == ["duplicate-id", "duplicate-id"]


def test_an_alias_may_name_several_entries(tmp_path, put):
    put(aliases=("TD-1",))
    put(aliases=("TD-1",))
    assert rules(tmp_path) == []


def test_missing_link_target(tmp_path, put):
    put(links=(Link(type=LinkType.DEPENDS_ON, target=new_id()),))
    assert rules(tmp_path) == ["link-target"]


def test_global_cannot_link_into_a_project_but_a_project_may_target_global(tmp_path, put):
    rule = put(Scope.GLOBAL)
    local = put(links=(Link(type=LinkType.DEPENDS_ON, target=rule.id),))
    other = put(project="q", links=(Link(type=LinkType.RELATED_TO, target=local.id),))
    put(Scope.GLOBAL, links=(Link(type=LinkType.RELATED_TO, target=other.id),))
    put(Scope.GLOBAL, links=(Link(type=LinkType.PROMOTED_FROM, target=other.id),))
    assert rules(tmp_path) == ["link-target", "link-target"]


def test_two_in_force_successors(tmp_path, put):
    old = put(state=State.REPLACED)
    put(links=(Link(type=LinkType.REPLACES, target=old.id),))
    put(links=(Link(type=LinkType.REPLACES, target=old.id),))
    put(state=State.WITHDRAWN, links=(Link(type=LinkType.REPLACES, target=old.id),))
    assert rules(tmp_path) == ["two-successors", "two-successors"]


def test_replaced_without_successor(tmp_path, put):
    old = put(state=State.REPLACED)
    put(state=State.DRAFT, links=(Link(type=LinkType.REPLACES, target=old.id),))
    assert rules(tmp_path) == ["no-successor"]


def test_decided_without_owner_words(tmp_path, put):
    put(owner_words=())
    put(owner_words=(), origin=Origin.AUTONOMOUS)
    assert rules(tmp_path) == ["owner-words"]


def test_statement_over_240_characters(tmp_path, put):
    put(statement="x" * 240)
    put(statement="x" * 241)
    assert rules(tmp_path) == ["statement-length"]


def test_change_decision_outside_a_change_folder(tmp_path, put):
    put(Scope.CHANGE, folder=tmp_path / "p")
    findings = validate_repo(tmp_path)
    assert [f.rule for f in findings] == ["placement"]
    assert "outside a change folder" in findings[0].message


def test_project_decision_in_another_projects_folder(tmp_path, put):
    put(project="q", folder=tmp_path / "p")
    assert rules(tmp_path) == ["placement"]


def test_exception_to_a_non_global_decision(tmp_path, put):
    local = put()
    put(links=(Link(type=LinkType.EXCEPTION_TO, target=local.id),))
    assert rules(tmp_path) == ["exception-target"]


def test_validate_takes_explicit_folders(tmp_path, put):
    put(owner_words=())
    assert [f.rule for f in validate(None, [tmp_path / "p"])] == ["owner-words"]
    assert validate(tmp_path, []) == []


def test_cli_prints_findings_and_fails(tmp_path, put, capsys):
    put(owner_words=())
    assert main([str(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert "owner-words: a decided decision needs the owner's words" in out
    assert out.endswith("1 finding(s)\n")
