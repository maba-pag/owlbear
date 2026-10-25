"""Full archived authority is distinct from reasons, literal headings and subsequent action explanations."""

import json
import subprocess
from datetime import UTC, datetime

import pytest

from owlbear_decisions import Decision, Link, LinkType, Origin, Scope, State, check_write, new_id, write
from owlbear_decisions.models import STATEMENT_LIMIT
from owlbear_decisions.storage import parse, serialize
from owlbear_delivery_next.change_contracts import decision_wording, pick_tools, tools
from owlbear_delivery_next.change_contracts.decision_records import DecisionBaseline
from owlbear_delivery_next.change_contracts.models import Brief, BriefDecision, Change, ErrorKind
from owlbear_delivery_next.state_store import decision_actions, decision_archive, decision_origin, decision_store
from owlbear_delivery_next.state_store.store import Lock
from owlbear_delivery_next.workflow_steps import brief_round, decision_publication, decisions_gate, lookup, pick

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


def test_an_ordinary_short_archive_keeps_a_literal_whole_heading_in_its_reason():
    rule = archived("Keep notes in the local store.", reason="Whole wording: quoted from the old note")
    assert rule.statement == "Keep notes in the local store."
    assert decision_wording.explanation(rule) == rule.rationale


@pytest.mark.parametrize("damage", ["unknown-version", "broken-json", "stub-mismatch"])
def test_unusable_inherited_binding_never_becomes_a_new_rule_and_its_note_survives_only_when_provable(damage):
    rule = archived(reason="Kept for the audit trail")
    head, _, note = rule.rationale.partition("\n\n")
    if damage == "unknown-version":
        line = head.replace("wording v1:", "wording v2:")
    elif damage == "broken-json":
        line = decision_wording.FRAME + "{"
    else:
        line = head.replace('"statement": "', '"statement": "different ')
    bad = rule.model_copy(update={"rationale": f"{line}\n\n{note}"})
    with pytest.raises(decision_wording.WordingError):
        decision_wording.framed(bad)  # promotion, withdrawal and origin correction keep strict validation
    kept = decision_wording.explanation(bad)
    assert decision_wording.FRAME not in kept
    assert "wording v" not in kept
    assert TEXT not in kept
    assert kept == ("" if damage == "unknown-version" else note)


def test_unreadable_wording_stops_the_brief_challenge_before_a_worktree_or_challenger(picking, monkeypatch):
    bad = picking.put(legacy_ambiguous())
    monkeypatch.setattr(brief_round.worktree, "ensure", lambda *_: pytest.fail("an unreadable rule starts no worktree"))
    monkeypatch.setattr(
        brief_round.sessions, "review_run", lambda *_a, **_k: pytest.fail("no challenger on bad wording")
    )
    brief_round.run(picking.store, Lock("notes"), Change(slug="notes"), picking.shared.root)
    stored = picking.store.read("notes")
    assert stored.stop.kind is ErrorKind.STATE
    assert bad.id in stored.stop.reason


def test_an_approval_refuses_an_unreadable_selected_rule_before_its_baseline_reads_it(picking):
    bad = picking.put(legacy_ambiguous())
    message = decisions_gate.unworded(decisions_gate.loaded(picking.store), Change(slug="notes"))
    assert bad.id in message
    assert "unresolved" in message


def test_the_pinned_wording_saved_with_an_approval_is_the_whole_answer():
    rule = archived()
    pin = DecisionBaseline(commit="c", at=AT, revisions={rule.id: rule.rule_revision}, said={}, picked=False)
    assert decision_publication._pinned(pin, [rule]).said[rule.id].statement == TEXT  # noqa: SLF001


def head(root) -> str:
    out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True)  # noqa: S607
    return out.stdout.strip()


def publish(root) -> str:
    subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True)  # noqa: S607
    subprocess.run(["git", "commit", "-qm", "seed"], cwd=root, check=True, capture_output=True)  # noqa: S607
    return head(root)


@pytest.mark.parametrize(
    ("action", "body"),
    [
        ("promote", {"reason": "Every project."}),
        ("withdraw", {"reason": "No longer true.", "redecide": True}),
        ("correct-origin", {"origin": "approved", "reason": "r", "confirmed": True}),
    ],
)
def test_an_owner_action_on_an_unreadable_rule_is_a_409_naming_it_and_writes_nothing(picking, action, body):
    rule = legacy_ambiguous().model_copy(update={"origin": Origin.DECIDED, "read_back": AT.date().isoformat()})
    picking.put(rule)
    before = publish(picking.shared.root)
    path = picking.shared.root / PROJECT / "decisions" / f"{rule.id}.md"
    text = path.read_text()

    got = picking.http.post(f"/api/next/decisions/{rule.id}/{action}", json={"revision": rule.revision, **body})

    assert got.status_code == 409, got.text
    assert rule.id in got.json()["detail"]
    assert "nothing was saved" in got.json()["detail"]
    assert path.read_text() == text
    assert head(picking.shared.root) == before


def test_a_replacement_of_a_damaged_frame_needs_a_reason_and_then_saves_a_usable_successor(picking):
    rule = archived(reason="Kept for the audit trail")
    damaged = rule.model_copy(update={"rationale": f"{decision_wording.FRAME}{{\n\nKept for the audit trail"})
    picking.put(damaged)
    before = publish(picking.shared.root)
    body = {"revision": damaged.revision, "statement": "Keep notes in Postgres.", "confirmed": True}

    blank = picking.http.post(f"/api/next/decisions/{rule.id}/replace", json=body | {"reason": ""})
    assert blank.status_code == 422, blank.text
    assert "say why" in blank.json()["detail"]
    assert head(picking.shared.root) == before

    got = picking.http.post(f"/api/next/decisions/{rule.id}/replace", json=body | {"reason": "Postgres scales."})

    assert got.status_code == 200, got.text
    successor = decision_store.load(picking.shared, PROJECT).snapshot.get(got.json()["receipts"][0]["id"]).decision
    assert decision_wording.problem(successor) == ""
    assert successor.statement == "Keep notes in Postgres."
    assert successor.links == (Link(type=LinkType.REPLACES, target=rule.id),)
    assert decision_wording.FRAME not in successor.rationale
    assert TEXT not in successor.rationale


def test_an_approval_refuses_a_saved_pick_of_an_unreadable_rule_before_its_baseline_is_pinned(picking):
    rule = picking.put(archived())
    picking.save()
    assert picking.ask(1).status_code == 200
    picking.picks.append(pick_tools.PickResult(picked=[{"id": rule.id, "note": "it governs the page"}]))
    picking.verdicts.append(tools.ReviewResult(verdict="pass"))
    picking.step()
    # The same rule now carries a pre-upgrade legacy rationale; its statement and origin are unchanged.
    legacy = legacy_ambiguous().model_copy(update={"id": rule.id})
    write(legacy, picking.shared.root / PROJECT, rule.revision)
    c = picking.change()
    view = decisions_gate.loaded(picking.store)
    fixed = pick.digest(pick.listed(view.snapshot, c), pick.moved(view.snapshot, c))
    c.brief.picked = c.brief.picked.model_copy(update={"listed": fixed})
    picking.store.write(Lock(picking.slug), c)

    got = picking.approve(1)

    assert got.status_code == 409, got.text
    assert rule.id in got.json()["detail"]
    assert "unresolved" in got.json()["detail"]
    assert picking.approved().decisions_baseline is None


def test_an_approval_saves_the_whole_wording_of_a_long_project_rule_in_its_baseline(picking):
    picking.save(
        decisions=[{"question": "Where are notes stored?", "answer": TEXT, "origin": "decided", "scope": "project"}]
    )
    rule_id = picking.change().brief.decisions[0].id
    assert picking.ask(1).status_code == 200
    picking.verdicts.append(tools.ReviewResult(verdict="pass"))
    picking.step()

    assert picking.approve(1).status_code == 200

    saved = picking.approved()
    assert saved.decisions_baseline.said[rule_id].statement == TEXT
    assert decision_archive.whole(decision_store.load(picking.shared, PROJECT).snapshot.get(rule_id).decision) == TEXT


CANON = "Keep the literal ellipsis\u2026"


def forged(statement: str, reason: str = "A reason of my own.") -> str:
    payload = json.dumps({"statement": statement, "whole": TEXT}, ensure_ascii=False)
    return f"{decision_wording.FRAME}{payload}\n\n{reason}"


def stored(picking, decision_id: str) -> Decision:
    return decision_store.load(picking.shared, PROJECT).snapshot.get(decision_id).decision


@pytest.mark.parametrize("statement", [decision_wording.short(TEXT), CANON])
def test_a_frame_supplied_in_a_proposal_reason_stays_a_note_through_the_real_promotion(picking, statement):
    got = picking.http.post(
        "/api/next/decisions/propose",
        json={"title": "Notes", "statement": statement, "confirmed": True, "rationale": forged(statement)},
    )
    assert got.status_code == 200, got.text
    rule = stored(picking, got.json()["receipts"][0]["id"])

    promoted = picking.http.post(
        f"/api/next/decisions/{rule.id}/promote", json={"revision": rule.revision, "reason": "Every project."}
    )

    assert promoted.status_code == 200, promoted.text
    successor = stored(picking, promoted.json()["receipts"][0]["id"])
    assert decision_wording.whole(successor) == statement
    assert decision_wording.problem(successor) == ""
    assert "A reason of my own." in decision_wording.explanation(successor)


def test_a_replaced_ordinary_ellipsis_wording_promotes_with_its_canonical_statement(picking):
    got = picking.http.post(
        "/api/next/decisions/propose",
        json={"title": "Notes", "statement": CANON, "confirmed": True, "reason": "Plain."},
    )
    rule = stored(picking, got.json()["receipts"][0]["id"])
    longer = decision_wording.short(TEXT)
    replaced = picking.http.post(
        f"/api/next/decisions/{rule.id}/replace",
        json={"revision": rule.revision, "statement": longer, "confirmed": True, "redecide": True, "reason": "Longer."},
    )
    assert replaced.status_code == 200, replaced.text
    successor = stored(picking, replaced.json()["receipts"][0]["id"])

    promoted = picking.http.post(
        f"/api/next/decisions/{successor.id}/promote",
        json={"revision": successor.revision, "reason": "Every project."},
    )

    assert promoted.status_code == 200, promoted.text
    widened = stored(picking, promoted.json()["receipts"][0]["id"])
    assert decision_wording.whole(widened) == longer
    assert decision_wording.problem(widened) == ""


def test_an_archived_replacement_with_a_literal_ellipsis_is_usable_and_promotes_canonically(picking):
    rule = legacy_ambiguous()
    picking.put(rule)
    replaced = picking.http.post(
        f"/api/next/decisions/{rule.id}/replace",
        json={"revision": rule.revision, "statement": CANON, "confirmed": True, "reason": "Whole wording: kept it."},
    )
    assert replaced.status_code == 200, replaced.text
    successor = stored(picking, replaced.json()["receipts"][0]["id"])
    assert decision_wording.whole(successor) == CANON
    assert decision_wording.problem(successor) == ""

    promoted = picking.http.post(
        f"/api/next/decisions/{successor.id}/promote",
        json={"revision": successor.revision, "reason": "Every project."},
    )

    assert promoted.status_code == 200, promoted.text
    widened = stored(picking, promoted.json()["receipts"][0]["id"])
    assert decision_wording.whole(widened) == CANON
    assert decision_wording.problem(widened) == ""
    assert "Whole wording: kept it." in decision_wording.explanation(widened)


LEGACY_NOTE = "From Change notes (approved).\n\nWhy it changed: Apply globally"


def legacy_short_ellipsis():
    """An archive from before framing: a literal terminal ellipsis, canonical wording, and no Whole wording note."""
    return archived(CANON).model_copy(
        update={"rationale": LEGACY_NOTE, "origin": Origin.DECIDED, "read_back": AT.date().isoformat()}
    )


def test_a_legacy_managed_ellipsis_is_framed_before_any_note_even_when_its_whole_wording_is_canonical():
    rule = legacy_short_ellipsis()
    assert decision_wording.framed(rule).startswith(decision_wording.FRAME)
    survivor = rule.model_copy(update={"rationale": decision_wording.framed(rule)})
    assert decision_wording.whole(parse(serialize(survivor))) == CANON
    assert decision_wording.explanation(survivor) == LEGACY_NOTE


def test_an_ordinary_answer_ending_in_an_ellipsis_keeps_its_raw_rationale_until_promotion():
    ordinary = legacy_short_ellipsis().model_copy(update={"source": "chat", "rationale": "A plain reason."})
    assert decision_wording.framed(ordinary) == "A plain reason."


@pytest.mark.parametrize("route", ["promote", "correct-origin"])
def test_a_legacy_short_ellipsis_archive_stays_canonical_after_a_real_reason_write(picking, route):
    rule = legacy_short_ellipsis()
    picking.put(rule)
    body = {"revision": rule.revision, "reason": "Whole wording: kept it."}
    if route == "correct-origin":
        body |= {"origin": "autonomous", "confirmed": True}

    got = picking.http.post(f"/api/next/decisions/{rule.id}/{route}", json=body)

    assert got.status_code == 200, got.text
    successor = parse(serialize(stored(picking, got.json()["receipts"][0]["id"])))
    assert decision_wording.whole(successor) == CANON
    assert decision_wording.problem(successor) == ""
    assert "Whole wording: kept it." in decision_wording.explanation(successor)
    assert "Apply globally" in decision_wording.explanation(successor)
