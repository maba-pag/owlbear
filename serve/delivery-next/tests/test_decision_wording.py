"""Full archived authority is distinct from reasons, literal headings and subsequent action explanations."""

from datetime import UTC, datetime

import pytest

from owlbear_decisions import Decision, Origin, Scope, State, check_write, new_id, write
from owlbear_decisions.models import STATEMENT_LIMIT
from owlbear_decisions.storage import parse, serialize
from owlbear_delivery_next.change_contracts import decision_wording
from owlbear_delivery_next.change_contracts.models import Brief, BriefDecision, Change
from owlbear_delivery_next.state_store import decision_actions, decision_archive, decision_origin, decision_store
from owlbear_delivery_next.workflow_steps import lookup, pick

AT = datetime(2026, 10, 22, 9, tzinfo=UTC)
PROJECT = "shop-site"
TEXT = "A note is stored only in the project's own table. " * 6 + "Never keep payment-card numbers."


def archived(text=TEXT, reason=""):
    choice = BriefDecision(
        id=new_id(AT),
        question="Where are notes stored?",
        answer=text,
        reason=reason,
        origin="autonomous",
        scope="project",
    )
    brief = Brief(version=1, title="Notes", approved_at=AT, decisions=[choice])
    c = Change(slug="notes", brief=brief.model_copy(update={"approved": [brief.model_copy(deep=True)]}))
    return decision_archive.lasting(PROJECT, c, "notes")[0]


@pytest.mark.parametrize(
    "reason",
    ["Whole wording: unrelated explanation", f"Whole wording: {TEXT}", f"Why it changed: {TEXT}"],
)
def test_actual_archive_and_roundtrip_separate_reason_from_binding(reason):
    rule = archived(reason=reason)
    assert len(rule.statement) <= STATEMENT_LIMIT
    assert decision_archive.whole(rule) == TEXT
    assert decision_archive.whole(parse(serialize(rule))) == TEXT


@pytest.mark.parametrize("text", ["Use the local data store\u2026", "x" * 239 + "\u2026"])
def test_new_short_archives_with_a_literal_terminal_ellipsis_never_expand_the_reason(text):
    explanation = text[:-1] + " but permit cloud backups."
    rule = archived(text, f"Whole wording: {explanation}")
    assert rule.statement == text
    assert decision_archive.whole(parse(serialize(rule))) == text
    assert decision_wording.problem(rule) == ""


@pytest.mark.parametrize("legacy", [False, True])
def test_actual_origin_correction_preserves_proven_binding_or_refuses_ambiguity_before_writing(monkeypatch, legacy):
    rule = archived().model_copy(update={"origin": Origin.APPROVED})
    if legacy:
        rule = rule.model_copy(update={"rationale": f"From Change notes (approved).\n\nWhole wording: {TEXT}"})
    saved = []
    monkeypatch.setattr(decision_store, "load", lambda *_args: object())
    monkeypatch.setattr(decision_origin, "_entry", lambda *_args: type("Entry", (), {"decision": rule})())
    monkeypatch.setattr(decision_origin, "_stale", lambda *_args: None)
    monkeypatch.setattr(decision_origin, "rivals", lambda *_args: [])

    def retire(_shared, successor, _old, _message):
        saved.append(successor)
        return []

    monkeypatch.setattr(decision_origin, "_retire", retire)

    def correcting():
        return decision_origin.correct_origin(
            None,
            PROJECT,
            rule.id,
            rule.revision,
            origin=Origin.AUTONOMOUS,
            reason="This was an agent choice",
            confirmed=True,
            by="owner",
        )

    if legacy:
        with pytest.raises(decision_wording.WordingError, match="ambiguous legacy"):
            correcting()
        assert saved == []
        return
    correcting()
    assert len(saved) == 1
    assert saved[0].statement == rule.statement
    assert saved[0].origin is Origin.AUTONOMOUS
    assert decision_archive.whole(parse(serialize(saved[0]))) == TEXT
    assert decision_wording.problem(saved[0]) == ""


def test_literal_metadata_headings_inside_binding_survive_real_promotion(monkeypatch):
    text = TEXT + "\n\nWhy it changed: this paragraph IS binding.\n\nWhole wording: this one is binding too."
    rule = archived(text, reason=f"Whole wording: quoted explanation {text}")
    saved = []
    view = object()
    monkeypatch.setattr(decision_store, "load", lambda *_args: view)
    monkeypatch.setattr(decision_actions, "_entry", lambda *_args: type("Entry", (), {"decision": rule})())
    monkeypatch.setattr(decision_actions, "_stale", lambda *_args: None)

    def retire(_shared, wider, _source, _message):
        saved.append(wider)
        return []

    monkeypatch.setattr(decision_actions, "_retire", retire)
    decision_actions.promote(None, PROJECT, rule.id, rule.revision, reason="Apply this to all projects")
    assert len(saved) == 1
    assert saved[0].scope is Scope.GLOBAL
    assert saved[0].statement == rule.statement
    assert decision_archive.whole(parse(serialize(saved[0]))) == text
    assert "Apply this to all projects" in saved[0].rationale


def legacy_ambiguous():
    rule = archived()
    rationale = f"From Change notes (approved).\n\nWhole wording: {TEXT}\n\nWhy it changed: Apply globally"
    return rule.model_copy(update={"rationale": rationale})


def test_replaying_the_original_approved_answer_can_frame_a_legacy_rule_without_rewriting_its_identity():
    fresh = archived()
    old = fresh.model_copy(update={"rationale": f"From Change notes (approved).\n\nWhole wording: {TEXT}"})
    with pytest.raises(decision_wording.WordingError, match="ambiguous legacy"):
        decision_archive.whole(old)
    check_write(old, fresh, old.revision)
    assert fresh.id == old.id
    assert fresh.statement == old.statement
    assert decision_wording.framed(fresh) == fresh.rationale
    assert decision_archive.whole(fresh) == TEXT


def test_a_single_legacy_marker_cannot_distinguish_a_full_answer_from_a_quoted_reason():
    expanded = TEXT
    canonical = decision_wording.short(expanded)
    rule = archived(expanded)
    historical = rule.model_copy(update={"rationale": f"From Change notes (approved).\n\nWhole wording: {expanded}"})
    quoted = archived(canonical, f"Whole wording: {expanded}")
    quoted = quoted.model_copy(update={"rationale": historical.rationale})
    assert (historical.statement, historical.rationale, historical.source) == (
        quoted.statement,
        quoted.rationale,
        quoted.source,
    )
    for candidate in (historical, quoted):
        with pytest.raises(decision_wording.WordingError, match="ambiguous legacy"):
            decision_archive.whole(candidate)


@pytest.mark.parametrize("text", ["ordinary\nformatting", TEXT, "Keep the literal ellipsis\u2026"])
def test_genuine_canonical_wording_is_not_rewritten_or_expanded_from_an_unrelated_reason(text):
    rule = archived().model_copy(
        update={
            "statement": text,
            "source": "the owner's confirmed intent",
            "rationale": f"Whole wording: {TEXT}\n\nWhole wording: quoted reason",
        }
    )
    assert decision_archive.whole(rule) == text


@pytest.mark.parametrize("damage", ["unknown-version", "broken-json", "stub-mismatch"])
def test_damaged_framed_authority_is_a_visible_fault(damage):
    rule = archived()
    reason = (
        rule.rationale.replace("wording v1:", "wording v2:")
        if damage == "unknown-version"
        else (
            decision_wording.FRAME + "{"
            if damage == "broken-json"
            else rule.rationale.replace('"statement": "', '"statement": "different ')
        )
    )
    bad = rule.model_copy(update={"rationale": reason})
    with pytest.raises(decision_wording.WordingError):
        decision_archive.whole(bad)
    assert decision_wording.problem(bad)


@pytest.mark.parametrize("boundary", ["worker", "chat"])
def test_ambiguous_legacy_authority_refuses_the_whole_lookup_before_a_picker(picking, monkeypatch, boundary):
    good = Decision(
        id=new_id(),
        title="Other rule",
        statement="Keep every note local.",
        scope=Scope.PROJECT,
        project=PROJECT,
        state=State.IN_FORCE,
        origin=Origin.APPROVED,
        actor="shaper",
        created_at=AT,
    )
    picking.put(good)
    bad = picking.put(legacy_ambiguous())
    calls = []
    monkeypatch.setattr(lookup, "_ran", lambda *_args: calls.append("must not run"))
    if boundary == "worker":
        from owlbear_delivery_next.state_store.store import Lock  # noqa: PLC0415 - only the worker boundary

        result, done = lookup.worker(picking.store, Lock("notes"), Change(slug="notes"), "Which rules?")
    else:
        result, done = lookup.chat(picking.shared, PROJECT, "Which rules?", picking.store.settings)
    assert result["failed"]
    assert "decisions" not in result
    assert {row["id"] for row in result["unresolved"]} == {bad.id}
    assert all(row["reason"] for row in result["unresolved"])
    assert done is None
    assert calls == []


def test_ambiguous_wording_refuses_shaping_pick_without_starting_an_sdk_session(picking, monkeypatch):
    from owlbear_delivery_next.state_store.store import Lock  # noqa: PLC0415 - the actual pick's write boundary

    bad = picking.put(legacy_ambiguous())
    monkeypatch.setattr(pick, "_session", lambda *_args: pytest.fail("ambiguous authority cannot reach a picker"))
    after = pick.run(picking.store, Lock("notes"), Change(slug="notes"))
    assert after.brief.picked.status == "failed"
    assert bad.id in after.brief.picked.reason


def test_a_foreign_project_legacy_ambiguity_does_not_poison_this_projects_lookup(picking):
    other = picking.shared.root / "elsewhere"
    other.mkdir()
    write(legacy_ambiguous().model_copy(update={"project": "elsewhere"}), other)
    result, done = lookup.chat(picking.shared, PROJECT, "Which rules?", picking.store.settings)
    assert result == {"decisions": [], "note": lookup.NONE}
    assert done is None
