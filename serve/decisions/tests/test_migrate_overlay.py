from __future__ import annotations

import json
from pathlib import Path

import pytest

from owlbear_decisions.migrate import main, write_preview
from owlbear_decisions.models import Scope
from owlbear_decisions.storage import load_folder

ROOT = Path(__file__).resolve().parents[3]
RECORD = ROOT / ".owlbear/research/delivery-liveness-first-rebuild.md"
OVERLAY = ROOT / ".owlbear/migration/decisions-overlay.json"

TEXT = """## C-01 Asking

**Rows:** decided TD-1, TD-2.

- Ask with three options [TD-1].
- The same applies here [TD-2].
- Long one [TD-1].
"""

CLEAR = "A read-back offers three close variants of the decision."


def _overlay(tmp_path: Path, **extra: object) -> Path:
    data = {
        "source": "the synthetic record, reworded",
        "notes": ["Global by the scope rule."],
        "global": [{"topic": "C-01 Asking", "original": "Ask with three options."}],
        "reworded": [
            {"topic": "C-01 Asking", "original": "The same applies here.", "statement": CLEAR, "note": "ok"},
            {"topic": "C-01 Asking", "original": "Long one.", "statement": "word " * 60, "note": "uncertain: long"},
        ],
    }
    path = tmp_path / "overlay.json"
    path.write_text(json.dumps(data | extra), encoding="utf-8")
    return path


def _run(tmp_path: Path, overlay: Path) -> tuple[object, str, list[str]]:
    record = tmp_path / "record.md"
    record.write_text(TEXT, encoding="utf-8")
    out = tmp_path / "out"
    result = write_preview(record, out, overlay=overlay)
    files = [p.read_text(encoding="utf-8") for p in out.rglob("D-*.md")]
    return result, (out / "REPORT.md").read_text(encoding="utf-8"), files


def test_rewording_replaces_the_statement_and_the_report_shows_both(tmp_path):
    result, report, files = _run(tmp_path, _overlay(tmp_path))
    by_original = {c.bullet.statement: c for c in result.clauses}
    reworded = by_original["The same applies here."].decision
    assert (reworded.statement, reworded.title) == (CLEAR, "A read-back offers three close variants of the …")
    row = next(line for line in report.splitlines() if CLEAR in line and "|" in line)
    assert "| The same applies here. | " + CLEAR + " | ok | |" in row
    section = report.split("## Reworded for your review (TD-462)")[1]
    assert section.index("uncertain: long") < section.index("| ok |")  # uncertain ones first
    assert not [f for f in files if "The same applies here" in f or "Long one" in f]
    assert any("over 240" in reason for reason in by_original["Long one."].unclear)


def test_a_global_entry_lands_in_the_global_layer(tmp_path):
    result, report, _ = _run(tmp_path, _overlay(tmp_path))
    shared = load_folder(tmp_path / "out").decisions.values()
    assert [(d.statement, d.scope, d.project) for d in shared] == [("Ask with three options.", Scope.GLOBAL, "")]
    assert len(load_folder(tmp_path / "out" / "owlbear").decisions) == 2
    assert "- Global by the scope rule." in report.split("## Global by TD-442")[1]
    assert {f.rule for f in result.findings} == {"statement-length"}


def test_a_stale_entry_is_listed(tmp_path, capsys):
    stale = {"topic": "C-01 Asking", "original": "A line since removed."}
    overlay = _overlay(tmp_path, **{"global": [stale]})
    record = tmp_path / "record.md"
    record.write_text(TEXT, encoding="utf-8")
    assert main([str(record), str(tmp_path / "out"), "--overlay", str(overlay)]) == 0
    assert ", 2 reworded, 0 Global, 1 stale overlay entries;" in capsys.readouterr().out
    report = (tmp_path / "out" / "REPORT.md").read_text(encoding="utf-8")
    assert "- global, C-01 Asking: A line since removed." in report.split("## Overlay entries that match no line")[1]


def test_an_overlay_listing_one_original_twice_is_refused(tmp_path):
    twice = [{"topic": "C-01 Asking", "original": "Long one."}] * 2
    with pytest.raises(ValueError, match="lists one original twice"):
        _run(tmp_path, _overlay(tmp_path, **{"global": twice}))
    assert not (tmp_path / "out").exists()


def test_real_record_with_the_real_overlay_validates_clean(tmp_path):
    overlay = json.loads(OVERLAY.read_text(encoding="utf-8"))
    result = write_preview(RECORD, tmp_path, overlay=OVERLAY)
    assert result.stale == []
    assert result.findings == []
    assert sum(1 for c in result.clauses if c.rewording) == len(overlay["reworded"])
    assert sum(1 for c in result.clauses if c.decision.scope is Scope.GLOBAL) == len(overlay["global"])
    files = "\n".join(p.read_text(encoding="utf-8") for p in tmp_path.rglob("D-*.md"))
    assert not [e["original"] for e in overlay["reworded"] if e["original"] in files]
