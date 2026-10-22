from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pytest

from owlbear_decisions.migrate import main, preview, write_preview
from owlbear_decisions.models import Origin
from owlbear_decisions.record import parse_record
from owlbear_decisions.report import orphans
from owlbear_decisions.storage import load_folder

RECORD = Path(__file__).resolve().parents[3] / ".owlbear/research/delivery-liveness-first-rebuild.md"

SYNTHETIC = """# Decisions

Intro prose is not a topic.

## C-01 Asking

**Rows:** decided TD-1, TD-2,
TD-4, TD-5, TD-10; autonomous TD-3.

- Ask with three options [TD-1].
- Mixed line that wraps
  onto a second line [TD-1, TD-3].
- Cut quote rule [TD-2]; see [the design](design.md).
- Cross reference [TD-9].
- Long one [TD-1] {long}.

**Owner's words:**

- TD-1, 2026-10-11: "three options"
- TD-2, 2026-10-12: "keep … the rest"
- TD-5, 2026-10-13: "old \\"quoted\\" words"

**Replaced:** TD-5 by TD-1.

**Open:**

- Later work [TD-10].

## Standalone decisions

- Stays on Copilot [TD-7, decided, partly; TD-1].
- No words here [TD-8, decided].

**Owner's words:**

- TD-7, 2026-10-09: "bound to copilot"

**Spent:** TD-6.
"""


def _synthetic() -> str:
    return SYNTHETIC.format(long="word " * 60)


def _by_line(result):
    return {clause.bullet.line: clause for clause in result.clauses}


def test_parse_topics_rows_and_words():
    topics = parse_record(_synthetic())
    assert [t.heading for t in topics] == ["C-01 Asking", "Standalone"]
    assert topics[0].rows == {
        "TD-1": "decided",
        "TD-2": "decided",
        "TD-4": "decided",
        "TD-5": "decided",
        "TD-10": "decided",
        "TD-3": "autonomous",
    }
    assert topics[0].replaced == ["TD-5"]
    assert topics[0].open == ["TD-10"]
    assert topics[1].spent == ["TD-6"]
    assert topics[1].rows == {"TD-7": "decided", "TD-8": "decided"}
    assert topics[0].words[2].text == 'old "quoted" words'
    assert [t.unparsed for t in topics] == [[], []]


def test_one_entry_per_bullet_with_statement_and_aliases_inherited_without_words():
    result = preview(_synthetic())
    clauses = result.clauses
    assert len(clauses) == 7
    first = clauses[0].decision
    assert first.statement == "Ask with three options."
    assert first.aliases == ("TD-1",)
    assert first.origin is Origin.DECIDED
    assert all(c.decision.inherited and c.decision.read_back == "none" for c in clauses)  # TD-454
    assert "owner_words" not in first.content()
    quotes = ("keep … the rest", 'old "quoted" words', "bound to copilot")  # the record's quotes, not statements
    assert not [q for c in clauses for q in quotes if q in str(c.decision.content())]  # TD-449
    assert first.topic == "C-01 Asking"
    assert (first.scope, first.project, first.state) == ("project", "owlbear", "in_force")
    assert clauses[0].unclear == []
    assert clauses[1].decision.statement == "Mixed line that wraps onto a second line."
    assert clauses[2].decision.statement == "Cut quote rule; see [the design](design.md)."
    assert clauses[5].decision.topic == "Standalone"
    assert clauses[5].decision.aliases == ("TD-7", "TD-1")


def test_unclear_clauses():
    clauses = preview(_synthetic()).clauses
    assert clauses[1].unclear == []  # TD-465: mixed origins carry decided and are settled
    assert clauses[1].decision.origin is Origin.DECIDED
    assert clauses[2].unclear == []
    assert clauses[3].unclear == ["TD-9 is in no Rows line"]
    assert clauses[3].decision.origin is Origin.AUTONOMOUS
    assert any("over 240" in reason for reason in clauses[4].unclear)
    assert clauses[5].unclear == ["origin qualified as 'partly' in the record"]  # TD-1 is C-01's row: not unclear
    assert clauses[6].unclear == []  # no quote is ever needed (TD-449)


def test_orphans_exclude_cited_replaced_and_spent():
    assert orphans(preview(_synthetic())) == ["TD-4"]


def test_equal_statements_get_distinct_ids_and_other_brackets_stay():
    text = "## C-02 Twins\n\n**Rows:** decided TD-1, TD-2.\n\n- Keep X [TD-1].\n- Keep X [TD-2].\n"
    text += "- Use [TD-1 must stay literal] as the label [TD-2].\n\n**Constraints:**\n\n- Hidden rule [TD-1].\n"
    result = preview(text)
    assert len({c.decision.id for c in result.clauses}) == 3
    assert result.clauses[2].decision.statement == "Use [TD-1 must stay literal] as the label."
    assert [item.text for item in result.topics[0].unparsed] == ["(unknown section) Hidden rule [TD-1]."]


def test_ids_are_reproducible():
    assert [c.decision.id for c in preview(_synthetic()).clauses] == [
        c.decision.id for c in preview(_synthetic()).clauses
    ]


def test_write_preview_files_and_report(tmp_path):
    record = tmp_path / "record.md"
    record.write_text(_synthetic(), encoding="utf-8")
    before = hashlib.sha256(record.read_bytes()).hexdigest()
    out = tmp_path / "out"
    result = write_preview(record, out)
    assert hashlib.sha256(record.read_bytes()).hexdigest() == before
    loaded = load_folder(out / "owlbear")
    assert loaded.errors == []
    assert sorted(d.id for d in loaded.decisions.values()) == sorted(c.decision.id for c in result.clauses)
    assert all(d.inherited for d in loaded.decisions.values())
    files = [p.read_text(encoding="utf-8") for p in (out / "owlbear" / "decisions").iterdir()]
    assert not [f for f in files if "owner_words" in f or "bound to copilot" in f]
    report = (out / "REPORT.md").read_text(encoding="utf-8")
    headings = ("Counts", "Unclear clauses", "Orphan rows", "Global by TD-442", "Reworded (TD-462)")
    for heading in (*headings, "Overlay entries that match no line", "Validator findings", "Concordance"):
        assert f"## {heading}" in report
    assert "- TD-4 (decided, C-01 Asking)" in report
    assert "No overlay applied: every entry is proposed for `owlbear`." in report
    assert {f.rule for f in result.findings} == {"statement-length"}
    with pytest.raises(FileExistsError):
        write_preview(record, out)


def test_cli(tmp_path, capsys):
    record = tmp_path / "record.md"
    record.write_text(_synthetic(), encoding="utf-8")
    assert main([str(record), str(tmp_path / "out")]) == 0
    assert capsys.readouterr().out.startswith("7 entries, 3 unclear clauses, 1 orphan rows")


def _in_force_bullets(text: str) -> int:
    count, active = 0, False
    for line in text.splitlines():
        if line.startswith("## "):
            active = bool(re.match(r"## (C-\d+ |Standalone decisions)", line))
        elif line.startswith("**") and not line.startswith("**Rows:**"):
            active = False
        elif active and line.startswith("- "):
            count += 1
    return count


def test_real_record_migrates_every_in_force_bullet(tmp_path):
    text = RECORD.read_text(encoding="utf-8")
    result = write_preview(RECORD, tmp_path)
    assert len(result.clauses) == _in_force_bullets(text)
    assert len({c.bullet.line for c in result.clauses}) == len(result.clauses)
    assert len({c.decision.id for c in result.clauses}) == len(result.clauses)
    assert [item for topic in result.topics for item in topic.unparsed] == []
    assert len(load_folder(tmp_path / "owlbear").decisions) == len(result.clauses)
    assert {f.rule for f in result.findings} <= {"statement-length"}
    unclear = {c.decision.id for c in result.clauses if c.unclear}
    flagged = {Path(f.path).stem for f in result.findings}
    assert flagged <= unclear
    assert RECORD.read_text(encoding="utf-8") == text
