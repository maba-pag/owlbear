"""Finding-verdict admission and backward-compatible publication receipt boundaries."""

import json

import pytest

from owlbear_delivery_next.audit_runs import job, record, sessions
from owlbear_delivery_next.change_contracts import project_audit_tools, tools
from owlbear_delivery_next.local_system.processes import Termination
from owlbear_delivery_next.runtimes.results import Gate
from owlbear_delivery_next.runtimes.session_result import Run
from owlbear_delivery_next.state_store.store import Store

from .test_audit_runs import _report


def _verdict(number, verdict="accepted"):
    return {
        "finding": number,
        "verdict": verdict,
        "reason": "The stored receipt is lost on this path.",
        "decisions": [],
        "duplicate_of": "",
    }


def test_verifier_gate_requires_exact_coverage_and_receipt_rechecks_it(tmp_path):
    root = tmp_path / "workspace"
    (root / "context").mkdir(parents=True)
    run_file = root / "context" / "run.json"
    findings = [_report()["findings"][0], _report()["findings"][0]]
    run_file.write_text(json.dumps({"note": "Check the receipt path.", "findings": findings}))
    cfg = sessions.verifier(Store(tmp_path / "store"), root, "Check the receipt path.")
    assert cfg.worktree == cfg.policy.root == root
    assert not cfg.policy.write
    assert not cfg.helpers
    assert (cfg.role, cfg.job, cfg.submit) == ("audit-verifier", "audit-verify", project_audit_tools.VERDICT)
    done = Run(cfg.session_id, termination=Termination(confirmed=True), model_check="verified")
    gate = Gate(cfg, done, lambda **_kw: None, lambda: None)
    assert tools.ASK not in gate.specs
    refused, ok = gate.call(cfg.submit, {"verdicts": [_verdict(1), _verdict(1)]})
    assert not ok
    assert "verdicts.finding" in refused
    assert not gate.done
    refused, ok = gate.call(cfg.submit, {"verdicts": [_verdict(1), _verdict(3)]})
    assert not ok
    assert "verdicts.finding" in refused
    assert not gate.done
    _, ok = gate.call(cfg.submit, {"verdicts": [_verdict(2, "unsure"), _verdict(1)]})
    assert ok
    assert sessions.verified(done, root) is done.payload
    with pytest.raises(RuntimeError, match="audit ended"):
        sessions.accepted(done, root)
    run_file.write_text(json.dumps({"note": "", "findings": findings[:1]}))
    with pytest.raises(ValueError, match=r"verdicts\.finding"):
        sessions.verified(done, root)
    run_file.write_text(json.dumps({"note": "", "findings": findings}))
    done.termination = None
    with pytest.raises(RuntimeError, match="not confirmed gone"):
        sessions.verified(done, root)
    done.termination, done.model_check = Termination(confirmed=True), "unknown"
    with pytest.raises(RuntimeError, match="model is unknown"):
        sessions.verified(done, root)


def test_record_preserves_legacy_receipts_and_verified_summary_only_work(tmp_path):
    store = Store(tmp_path / "store", name="owlbear")
    legacy = _report()
    record.save(store, "doc", legacy)
    loaded = record.load(store)["doc"]
    assert loaded == {**legacy, "session": ""}
    assert record.unpublished(loaded) == 1
    checked = {
        **legacy,
        "verified": True,
        "verdicts": [_verdict(1, "rejected")],
        "verifier_session": "verifier-one",
        "summary_issue": {"number": None, "url": "", "pending": None, "complete": False},
        "parts": [{"part": "defects", "ran": True, "note": "Read the receipt path."}],
    }
    record.save(store, "code", checked)
    assert record.load(store)["code"]["parts"] == checked["parts"]
    assert record.unpublished(checked) == 1
    checked["summary_issue"].update(number=7, url="https://github.com/acme/tools/issues/7", complete=True)
    assert record.unpublished(checked) == 0
    checked["verdicts"] = [_verdict(1)]
    assert record.unpublished(checked) == 1
    checked["findings"][0]["number"] = 8
    assert record.unpublished(checked) == 0
    checked["findings"], checked["verdicts"] = [], []
    checked["summary_issue"]["complete"] = False
    assert record.unpublished(checked) == 1
    assert job.Audits(store).offered() == ("doc", "agent", "code")
    assert job.Audits(Store(tmp_path / "consumer", name="consumer")).offered() == ("doc", "code")
