"""Failing tests for #1851: Pydantic models for structured decision requests.

AC1 - RequestOption validates option_id regex, label <=120 chars, confidence in [0,1],
       rationale <=500 chars; invalid inputs raise ValidationError.
AC2 - DecisionRequest requires 2-10 options; ActionRequest rejects non-empty options;
       all four models use extra='forbid'.
AC3 - At-most-one recommended=True; two or more raise ValidationError.
AC4 - Resolution has three optional str|None fields, all default to None;
       extra='forbid' rejects unknown fields.
AC5 - DecisionRequest and ActionRequest share required fields (task_id, request_id,
       title <=120 chars, summary, agent, created_at ISO 8601, optional resolution);
       invalid request_id / long title / malformed created_at raise ValidationError.
AC6 - Request discriminated union routes kind='decision'->DecisionRequest,
       kind='action'→ActionRequest; invalid kind raises ValidationError.

All tests FAIL in RED phase: owlbear_kanban.request_models does not exist yet.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from owlbear_kanban.request_models import (
    ActionRequest,
    DecisionRequest,
    Request,
    RequestOption,
    Resolution,
)

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

_VALID_UUID4 = "f47ac10b-58cc-4372-a567-0e02b2c3d479"
_VALID_ISO8601 = "2026-05-24T12:00:00+02:00"

_OPTION_VALID: dict = {
    "option_id": "option-a",
    "label": "Option A",
    "confidence": 0.7,
    "recommended": False,
    "rationale": "A good rationale.",
}
_OPTION_B_VALID: dict = {
    "option_id": "option-b",
    "label": "Option B",
    "confidence": 0.5,
    "recommended": False,
    "rationale": "Another rationale.",
}

_DECISION_BASE: dict = {
    "kind": "decision",
    "task_id": 1,
    "request_id": _VALID_UUID4,
    "title": "Choose something",
    "summary": "We need to decide.",
    "agent": "copilot",
    "created_at": _VALID_ISO8601,
    "options": [_OPTION_VALID, _OPTION_B_VALID],
}

_ACTION_BASE: dict = {
    "kind": "action",
    "task_id": 1,
    "request_id": _VALID_UUID4,
    "title": "Do something",
    "summary": "We need to act.",
    "agent": "copilot",
    "created_at": _VALID_ISO8601,
}


# ---------------------------------------------------------------------------
# AC1 — RequestOption field constraints
# ---------------------------------------------------------------------------


class TestFromAC_RequestOption:
    def test_valid_option_all_fields(self) -> None:
        opt = RequestOption(**_OPTION_VALID)
        assert opt.option_id == "option-a"
        assert opt.label == "Option A"
        assert opt.confidence == 0.7
        assert opt.recommended is False
        assert opt.rationale == "A good rationale."

    def test_option_id_minimum_length_two(self) -> None:
        opt = RequestOption(**{**_OPTION_VALID, "option_id": "ab"})
        assert opt.option_id == "ab"

    def test_option_id_maximum_length_63(self) -> None:
        long_id = "a" + "b" * 61 + "c"  # 1 + 61 + 1 = 63 chars
        opt = RequestOption(**{**_OPTION_VALID, "option_id": long_id})
        assert opt.option_id == long_id

    def test_option_id_single_char_raises(self) -> None:
        with pytest.raises(ValidationError):
            RequestOption(**{**_OPTION_VALID, "option_id": "a"})

    def test_option_id_length_64_raises(self) -> None:
        too_long = "a" + "b" * 62 + "c"  # 64 chars
        with pytest.raises(ValidationError):
            RequestOption(**{**_OPTION_VALID, "option_id": too_long})

    def test_option_id_starts_with_dash_raises(self) -> None:
        with pytest.raises(ValidationError):
            RequestOption(**{**_OPTION_VALID, "option_id": "-invalid"})

    def test_option_id_ends_with_dash_raises(self) -> None:
        with pytest.raises(ValidationError):
            RequestOption(**{**_OPTION_VALID, "option_id": "invalid-"})

    def test_option_id_uppercase_raises(self) -> None:
        with pytest.raises(ValidationError):
            RequestOption(**{**_OPTION_VALID, "option_id": "Option-A"})

    def test_option_id_spaces_raises(self) -> None:
        with pytest.raises(ValidationError):
            RequestOption(**{**_OPTION_VALID, "option_id": "option a"})

    def test_label_exactly_120_chars_valid(self) -> None:
        label_120 = "x" * 120
        opt = RequestOption(**{**_OPTION_VALID, "label": label_120})
        assert len(opt.label) == 120

    def test_label_121_chars_raises(self) -> None:
        with pytest.raises(ValidationError):
            RequestOption(**{**_OPTION_VALID, "label": "x" * 121})

    def test_confidence_zero_valid(self) -> None:
        opt = RequestOption(**{**_OPTION_VALID, "confidence": 0.0})
        assert opt.confidence == 0.0

    def test_confidence_one_valid(self) -> None:
        opt = RequestOption(**{**_OPTION_VALID, "confidence": 1.0})
        assert opt.confidence == 1.0

    def test_confidence_below_zero_raises(self) -> None:
        with pytest.raises(ValidationError):
            RequestOption(**{**_OPTION_VALID, "confidence": -0.01})

    def test_confidence_above_one_raises(self) -> None:
        with pytest.raises(ValidationError):
            RequestOption(**{**_OPTION_VALID, "confidence": 1.01})

    def test_rationale_exactly_500_chars_valid(self) -> None:
        opt = RequestOption(**{**_OPTION_VALID, "rationale": "r" * 500})
        assert len(opt.rationale) == 500

    def test_rationale_501_chars_raises(self) -> None:
        with pytest.raises(ValidationError):
            RequestOption(**{**_OPTION_VALID, "rationale": "r" * 501})

    def test_extra_field_raises(self) -> None:
        with pytest.raises(ValidationError):
            RequestOption(**{**_OPTION_VALID, "unknown_field": "oops"})


# ---------------------------------------------------------------------------
# AC2 — DecisionRequest / ActionRequest options count + extra='forbid'
# ---------------------------------------------------------------------------


class TestFromAC_OptionsCountAndForbid:
    def test_decision_request_with_two_options_valid(self) -> None:
        req = DecisionRequest(**_DECISION_BASE)
        assert len(req.options) == 2

    def test_decision_request_with_ten_options_valid(self) -> None:
        options = [
            {**_OPTION_VALID, "option_id": f"opt-{i:02d}", "recommended": False}
            for i in range(10)
        ]
        req = DecisionRequest(**{**_DECISION_BASE, "options": options})
        assert len(req.options) == 10

    def test_decision_request_one_option_raises(self) -> None:
        with pytest.raises(ValidationError):
            DecisionRequest(**{**_DECISION_BASE, "options": [_OPTION_VALID]})

    def test_decision_request_eleven_options_raises(self) -> None:
        options = [
            {**_OPTION_VALID, "option_id": f"opt-{i:02d}", "recommended": False}
            for i in range(11)
        ]
        with pytest.raises(ValidationError):
            DecisionRequest(**{**_DECISION_BASE, "options": options})

    def test_decision_request_zero_options_raises(self) -> None:
        with pytest.raises(ValidationError):
            DecisionRequest(**{**_DECISION_BASE, "options": []})

    def test_action_request_no_options_valid(self) -> None:
        req = ActionRequest(**_ACTION_BASE)
        assert req.options == [] or not req.options

    def test_action_request_empty_list_valid(self) -> None:
        req = ActionRequest(**{**_ACTION_BASE, "options": []})
        assert req.options == [] or not req.options

    def test_action_request_with_options_raises(self) -> None:
        with pytest.raises(ValidationError):
            ActionRequest(**{**_ACTION_BASE, "options": [_OPTION_VALID]})

    def test_decision_request_extra_field_raises(self) -> None:
        with pytest.raises(ValidationError):
            DecisionRequest(**{**_DECISION_BASE, "unknown_field": "oops"})

    def test_action_request_extra_field_raises(self) -> None:
        with pytest.raises(ValidationError):
            ActionRequest(**{**_ACTION_BASE, "unknown_field": "oops"})


# ---------------------------------------------------------------------------
# AC3 — At-most-one recommended=True
# ---------------------------------------------------------------------------


class TestFromAC_RecommendedConstraint:
    def test_zero_recommended_valid(self) -> None:
        opts = [
            {**_OPTION_VALID, "recommended": False},
            {**_OPTION_B_VALID, "recommended": False},
        ]
        req = DecisionRequest(**{**_DECISION_BASE, "options": opts})
        assert all(not o.recommended for o in req.options)

    def test_exactly_one_recommended_valid(self) -> None:
        opts = [
            {**_OPTION_VALID, "recommended": True},
            {**_OPTION_B_VALID, "recommended": False},
        ]
        req = DecisionRequest(**{**_DECISION_BASE, "options": opts})
        assert sum(o.recommended for o in req.options) == 1

    def test_two_recommended_raises(self) -> None:
        opts = [
            {**_OPTION_VALID, "recommended": True},
            {**_OPTION_B_VALID, "recommended": True},
        ]
        with pytest.raises(ValidationError):
            DecisionRequest(**{**_DECISION_BASE, "options": opts})

    def test_three_recommended_raises(self) -> None:
        opts = [
            {**_OPTION_VALID, "option_id": "opt-a", "recommended": True},
            {**_OPTION_VALID, "option_id": "opt-b", "recommended": True},
            {**_OPTION_VALID, "option_id": "opt-c", "recommended": True},
        ]
        with pytest.raises(ValidationError):
            DecisionRequest(**{**_DECISION_BASE, "options": opts})


# ---------------------------------------------------------------------------
# AC4 — Resolution model
# ---------------------------------------------------------------------------


class TestFromAC_Resolution:
    def test_resolution_all_fields_default_to_none(self) -> None:
        res = Resolution()
        assert res.selected_option_id is None
        assert res.free_text is None
        assert res.resolved_at is None

    def test_resolution_selected_option_id_set(self) -> None:
        res = Resolution(selected_option_id="option-a")
        assert res.selected_option_id == "option-a"
        assert res.free_text is None
        assert res.resolved_at is None

    def test_resolution_free_text_set(self) -> None:
        res = Resolution(free_text="Custom answer")
        assert res.free_text == "Custom answer"

    def test_resolution_all_fields_set(self) -> None:
        res = Resolution(
            selected_option_id="option-a",
            free_text="Picked option A",
            resolved_at="2026-05-24T14:00:00+02:00",
        )
        assert res.selected_option_id == "option-a"
        assert res.free_text == "Picked option A"
        assert res.resolved_at == "2026-05-24T14:00:00+02:00"

    def test_resolution_null_values_explicit(self) -> None:
        res = Resolution(selected_option_id=None, free_text=None, resolved_at=None)
        assert res.selected_option_id is None
        assert res.free_text is None
        assert res.resolved_at is None

    def test_resolution_extra_field_raises(self) -> None:
        with pytest.raises(ValidationError):
            Resolution(unknown_field="oops")


# ---------------------------------------------------------------------------
# AC5 — Shared required fields + validation errors
# ---------------------------------------------------------------------------


class TestFromAC_SharedRequiredFields:
    def test_decision_request_all_required_fields(self) -> None:
        req = DecisionRequest(**_DECISION_BASE)
        assert req.task_id == 1
        assert req.request_id == _VALID_UUID4
        assert req.title == "Choose something"
        assert req.summary == "We need to decide."
        assert req.agent == "copilot"
        assert req.created_at == _VALID_ISO8601
        assert req.kind == "decision"

    def test_action_request_all_required_fields(self) -> None:
        req = ActionRequest(**_ACTION_BASE)
        assert req.task_id == 1
        assert req.request_id == _VALID_UUID4
        assert req.title == "Do something"
        assert req.summary == "We need to act."
        assert req.agent == "copilot"
        assert req.created_at == _VALID_ISO8601
        assert req.kind == "action"

    def test_non_uuid4_request_id_raises(self) -> None:
        with pytest.raises(ValidationError):
            DecisionRequest(**{**_DECISION_BASE, "request_id": "not-a-uuid"})

    def test_non_uuid4_sequential_uuid_raises(self) -> None:
        # UUID1 (not UUID4) should be rejected
        uuid1 = "6ba7b810-9dad-11d1-80b4-00c04fd430c8"
        with pytest.raises(ValidationError):
            DecisionRequest(**{**_DECISION_BASE, "request_id": uuid1})

    def test_title_exactly_120_chars_valid(self) -> None:
        title_120 = "t" * 120
        req = DecisionRequest(**{**_DECISION_BASE, "title": title_120})
        assert len(req.title) == 120

    def test_title_121_chars_raises(self) -> None:
        with pytest.raises(ValidationError):
            DecisionRequest(**{**_DECISION_BASE, "title": "t" * 121})

    def test_action_request_title_121_chars_raises(self) -> None:
        with pytest.raises(ValidationError):
            ActionRequest(**{**_ACTION_BASE, "title": "t" * 121})

    def test_malformed_created_at_raises(self) -> None:
        with pytest.raises(ValidationError):
            DecisionRequest(**{**_DECISION_BASE, "created_at": "not-a-date"})

    def test_malformed_created_at_on_action_raises(self) -> None:
        with pytest.raises(ValidationError):
            ActionRequest(**{**_ACTION_BASE, "created_at": "24/05/2026"})

    def test_timezone_less_created_at_on_decision_raises(self) -> None:
        # Valid ISO 8601 format but no timezone — must be rejected (AC5 refinement)
        with pytest.raises(ValidationError):
            DecisionRequest(**{**_DECISION_BASE, "created_at": "2026-05-23T12:00:00"})

    def test_timezone_less_created_at_on_action_raises(self) -> None:
        # Valid ISO 8601 format but no timezone — must be rejected (AC5 refinement)
        with pytest.raises(ValidationError):
            ActionRequest(**{**_ACTION_BASE, "created_at": "2026-05-23T12:00:00"})

    def test_resolution_defaults_to_all_none_when_absent(self) -> None:
        req = DecisionRequest(**_DECISION_BASE)
        assert req.resolution is not None
        assert req.resolution.selected_option_id is None
        assert req.resolution.free_text is None
        assert req.resolution.resolved_at is None

    def test_resolution_can_be_set_explicitly(self) -> None:
        res = {"selected_option_id": "option-a", "free_text": None, "resolved_at": None}
        req = DecisionRequest(**{**_DECISION_BASE, "resolution": res})
        assert req.resolution.selected_option_id == "option-a"

    def test_task_id_must_be_int(self) -> None:
        with pytest.raises(ValidationError):
            DecisionRequest(**{**_DECISION_BASE, "task_id": "not-an-int"})

    def test_missing_required_field_raises(self) -> None:
        incomplete = {k: v for k, v in _DECISION_BASE.items() if k != "summary"}
        with pytest.raises(ValidationError):
            DecisionRequest(**incomplete)


# ---------------------------------------------------------------------------
# AC6 — Discriminated union Request
# ---------------------------------------------------------------------------


class TestFromAC_DiscriminatedUnion:
    def test_kind_decision_resolves_to_decision_request(self) -> None:
        req = Request.model_validate(_DECISION_BASE)
        assert isinstance(req, DecisionRequest)
        assert req.kind == "decision"

    def test_kind_action_resolves_to_action_request(self) -> None:
        req = Request.model_validate(_ACTION_BASE)
        assert isinstance(req, ActionRequest)
        assert req.kind == "action"

    def test_invalid_kind_raises(self) -> None:
        with pytest.raises(ValidationError):
            Request.model_validate({**_DECISION_BASE, "kind": "unknown"})

    def test_missing_kind_raises(self) -> None:
        payload = {k: v for k, v in _DECISION_BASE.items() if k != "kind"}
        with pytest.raises(ValidationError):
            Request.model_validate(payload)

    def test_union_decision_preserves_options(self) -> None:
        req = Request.model_validate(_DECISION_BASE)
        assert isinstance(req, DecisionRequest)
        assert len(req.options) == 2

    def test_union_action_has_no_options(self) -> None:
        req = Request.model_validate(_ACTION_BASE)
        assert isinstance(req, ActionRequest)
        assert not req.options
