"""Tests for #1522: proof_bundle migration script.

AC lines tested:
  - AC1: callable in owlbear_kanban.migrate extracts Proof bundle: value from body
         and writes it to frontmatter proof_bundle field
  - AC2: only the first matched Proof bundle: line is removed from body;
         later occurrences in pipeline-note sections are preserved
  - AC3: when frontmatter already contains a non-None proof_bundle value,
         callable returns without modifying the file
"""

from __future__ import annotations

from pathlib import Path

from owlbear_kanban.migrate import _migrate_proof_bundle_field


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_task_file(
    tmp_path: Path,
    frontmatter: str,
    body: str,
    *,
    filename: str = "1000.md",
) -> Path:
    path = tmp_path / filename
    content = f"---\n{frontmatter.strip()}\n---\n{body}"
    path.write_text(content, encoding="utf-8")
    return path


def _body_section(content: str) -> str:
    """Return the body text after the closing --- delimiter."""
    fm_end = content.index("\n---\n", 4)
    return content[fm_end + len("\n---\n"):]


def _fm_section(content: str) -> str:
    """Return the frontmatter text between the two --- delimiters."""
    fm_end = content.index("\n---\n", 4)
    return content[4:fm_end]


# ---------------------------------------------------------------------------
# AC1 — extract proof_bundle value from body line, write to frontmatter
# ---------------------------------------------------------------------------


class TestFromAC_ProofBundleMigration:
    """Tests derived from AC1, AC2, AC3 for _migrate_proof_bundle_field."""

    def test_returns_migrated_status_on_success(self, tmp_path: Path) -> None:
        """AC1 happy: callable returns ('migrated', None) when extraction succeeds."""
        fm = "id: 1000\ntitle: Test\nstatus: todo\n"
        body = "Some notes.\nProof bundle: smoke\nMore text.\n"
        path = _make_task_file(tmp_path, fm, body)
        result, reason = _migrate_proof_bundle_field(path)
        assert result == "migrated"
        assert reason is None

    def test_extracts_smoke_value_to_frontmatter(self, tmp_path: Path) -> None:
        """AC1 happy: 'smoke' extracted from body line, written to proof_bundle."""
        fm = "id: 1001\ntitle: Test\nstatus: todo\n"
        body = "Proof bundle: smoke\n"
        path = _make_task_file(tmp_path, fm, body, filename="1001.md")
        _migrate_proof_bundle_field(path)
        content = path.read_text(encoding="utf-8")
        assert "proof_bundle: smoke" in _fm_section(content)

    def test_extracts_behavioral_value_to_frontmatter(self, tmp_path: Path) -> None:
        """AC1 happy: 'behavioral' extracted correctly."""
        fm = "id: 1002\ntitle: Test\nstatus: todo\n"
        body = "Proof bundle: behavioral\n"
        path = _make_task_file(tmp_path, fm, body, filename="1002.md")
        _migrate_proof_bundle_field(path)
        content = path.read_text(encoding="utf-8")
        assert "proof_bundle: behavioral" in _fm_section(content)

    def test_extracts_critical_value_to_frontmatter(self, tmp_path: Path) -> None:
        """AC1 happy: 'critical' extracted correctly."""
        fm = "id: 1003\ntitle: Test\nstatus: todo\n"
        body = "Proof bundle: critical\n"
        path = _make_task_file(tmp_path, fm, body, filename="1003.md")
        _migrate_proof_bundle_field(path)
        content = path.read_text(encoding="utf-8")
        assert "proof_bundle: critical" in _fm_section(content)

    def test_value_with_surrounding_whitespace_trimmed(self, tmp_path: Path) -> None:
        """AC1 edge: extra whitespace around value is trimmed."""
        fm = "id: 1004\ntitle: Test\nstatus: todo\n"
        body = "Proof bundle:  smoke  \n"
        path = _make_task_file(tmp_path, fm, body, filename="1004.md")
        _migrate_proof_bundle_field(path)
        content = path.read_text(encoding="utf-8")
        # Frontmatter must contain trimmed value, not padded value
        assert "proof_bundle: smoke" in _fm_section(content)
        assert "proof_bundle:  smoke  " not in content

    def test_proof_bundle_line_at_start_of_body(self, tmp_path: Path) -> None:
        """AC1 edge: Proof bundle: is the very first body line."""
        fm = "id: 1005\ntitle: Test\nstatus: todo\n"
        body = "Proof bundle: smoke\nOther content.\n"
        path = _make_task_file(tmp_path, fm, body, filename="1005.md")
        result, _ = _migrate_proof_bundle_field(path)
        assert result == "migrated"
        content = path.read_text(encoding="utf-8")
        assert "proof_bundle: smoke" in _fm_section(content)

    def test_dry_run_does_not_write_file(self, tmp_path: Path) -> None:
        """AC1 boundary: dry_run=True reports 'migrated' but writes no changes."""
        fm = "id: 1006\ntitle: Test\nstatus: todo\n"
        body = "Proof bundle: smoke\n"
        path = _make_task_file(tmp_path, fm, body, filename="1006.md")
        original = path.read_text(encoding="utf-8")
        result, _ = _migrate_proof_bundle_field(path, dry_run=True)
        assert result == "migrated"
        assert path.read_text(encoding="utf-8") == original

    # -----------------------------------------------------------------------
    # AC2 — first line removed, later occurrences preserved
    # -----------------------------------------------------------------------

    def test_first_occurrence_removed_from_body(self, tmp_path: Path) -> None:
        """AC2 happy: first Proof bundle: line is removed from body."""
        fm = "id: 1010\ntitle: Test\nstatus: todo\n"
        body = "Proof bundle: smoke\nOther text.\n"
        path = _make_task_file(tmp_path, fm, body, filename="1010.md")
        _migrate_proof_bundle_field(path)
        content = path.read_text(encoding="utf-8")
        assert "Proof bundle: smoke" not in _body_section(content)

    def test_second_occurrence_preserved_in_body(self, tmp_path: Path) -> None:
        """AC2 edge: second Proof bundle: line is NOT removed."""
        fm = "id: 1011\ntitle: Test\nstatus: todo\n"
        body = (
            "Proof bundle: smoke\n"
            "2026-05-01T10:00:00+00:00\n"
            "## Builder Notes\n"
            "Proof bundle: smoke\n"
        )
        path = _make_task_file(tmp_path, fm, body, filename="1011.md")
        _migrate_proof_bundle_field(path)
        content = path.read_text(encoding="utf-8")
        body_part = _body_section(content)
        # Second occurrence (in pipeline-note section) must remain
        assert "Proof bundle: smoke" in body_part

    def test_only_first_of_multiple_occurrences_removed(self, tmp_path: Path) -> None:
        """AC2 edge: body has three occurrences; only the first is removed."""
        fm = "id: 1012\ntitle: Test\nstatus: todo\n"
        body = (
            "Proof bundle: behavioral\n"
            "## Notes\n"
            "Proof bundle: behavioral\n"
            "## More Notes\n"
            "Proof bundle: behavioral\n"
        )
        path = _make_task_file(tmp_path, fm, body, filename="1012.md")
        _migrate_proof_bundle_field(path)
        content = path.read_text(encoding="utf-8")
        body_part = _body_section(content)
        assert body_part.count("Proof bundle: behavioral") == 2

    def test_pipeline_note_occurrence_preserved(self, tmp_path: Path) -> None:
        """AC2 edge: Proof bundle: in ## Test-Writer Notes section preserved."""
        fm = "id: 1013\ntitle: Test\nstatus: todo\n"
        body = (
            "Proof bundle: behavioral\n"
            "2026-05-01T10:00:00+00:00\n"
            "## Test-Writer Notes\n"
            "- Proof bundle: behavioral\n"
        )
        path = _make_task_file(tmp_path, fm, body, filename="1013.md")
        _migrate_proof_bundle_field(path)
        content = path.read_text(encoding="utf-8")
        body_part = _body_section(content)
        # Pipeline-note occurrence must remain
        assert "Proof bundle: behavioral" in body_part

    # -----------------------------------------------------------------------
    # AC3 — already has non-None proof_bundle → no modification
    # -----------------------------------------------------------------------

    def test_returns_already_when_proof_bundle_set(self, tmp_path: Path) -> None:
        """AC3 happy: frontmatter has proof_bundle: smoke → returns 'already'."""
        fm = "id: 1020\ntitle: Test\nstatus: todo\nproof_bundle: smoke\n"
        body = "Proof bundle: smoke\n"
        path = _make_task_file(tmp_path, fm, body, filename="1020.md")
        result, _ = _migrate_proof_bundle_field(path)
        assert result == "already"

    def test_file_not_modified_when_proof_bundle_already_set(
        self, tmp_path: Path
    ) -> None:
        """AC3 happy: file content unchanged when proof_bundle already present."""
        fm = "id: 1021\ntitle: Test\nstatus: todo\nproof_bundle: behavioral\n"
        body = "Proof bundle: behavioral\n"
        path = _make_task_file(tmp_path, fm, body, filename="1021.md")
        original = path.read_text(encoding="utf-8")
        _migrate_proof_bundle_field(path)
        assert path.read_text(encoding="utf-8") == original

    def test_proof_bundle_null_in_frontmatter_proceeds(self, tmp_path: Path) -> None:
        """AC3 boundary: proof_bundle: null (None) in frontmatter → proceed."""
        fm = "id: 1022\ntitle: Test\nstatus: todo\nproof_bundle: null\n"
        body = "Proof bundle: smoke\n"
        path = _make_task_file(tmp_path, fm, body, filename="1022.md")
        result, _ = _migrate_proof_bundle_field(path)
        assert result == "migrated"

    def test_missing_proof_bundle_key_proceeds(self, tmp_path: Path) -> None:
        """AC3 boundary: no proof_bundle key in frontmatter → proceed with migration."""
        fm = "id: 1023\ntitle: Test\nstatus: todo\n"
        body = "Proof bundle: smoke\n"
        path = _make_task_file(tmp_path, fm, body, filename="1023.md")
        result, _ = _migrate_proof_bundle_field(path)
        assert result == "migrated"

    # -----------------------------------------------------------------------
    # Error paths
    # -----------------------------------------------------------------------

    def test_missing_frontmatter_delimiter(self, tmp_path: Path) -> None:
        """Error: file has no --- delimiter → ('failed', reason)."""
        path = tmp_path / "1030.md"
        path.write_text("id: 1030\ntitle: Broken\n", encoding="utf-8")
        result, reason = _migrate_proof_bundle_field(path)
        assert result == "failed"
        assert reason is not None

    def test_yaml_parse_error(self, tmp_path: Path) -> None:
        """Error: malformed YAML in frontmatter → ('failed', reason)."""
        path = tmp_path / "1031.md"
        path.write_text("---\n: broken: [yaml\n---\nBody\n", encoding="utf-8")
        result, reason = _migrate_proof_bundle_field(path)
        assert result == "failed"
        assert reason is not None

    def test_os_error_reading_nonexistent_file(self, tmp_path: Path) -> None:
        """Error: file does not exist → ('failed', reason)."""
        path = tmp_path / "nonexistent_1522.md"
        result, reason = _migrate_proof_bundle_field(path)
        assert result == "failed"
        assert reason is not None

    # -----------------------------------------------------------------------
    # Boundary conditions
    # -----------------------------------------------------------------------

    def test_no_proof_bundle_line_in_body(self, tmp_path: Path) -> None:
        """Boundary: no Proof bundle: line in body, no proof_bundle in frontmatter.

        Callable must not write an empty or None value.
        Acceptable outcomes: 'already' (nothing to extract) or 'failed'.
        """
        fm = "id: 1040\ntitle: Test\nstatus: todo\n"
        body = "Some body text with no proof bundle line.\n"
        path = _make_task_file(tmp_path, fm, body, filename="1040.md")
        result, _ = _migrate_proof_bundle_field(path)
        assert result in {"already", "failed"}

    def test_empty_value_after_colon_not_written(self, tmp_path: Path) -> None:
        """Boundary: 'Proof bundle:' with no value → not written as blank proof_bundle."""
        fm = "id: 1041\ntitle: Test\nstatus: todo\n"
        body = "Proof bundle:\n"
        path = _make_task_file(tmp_path, fm, body, filename="1041.md")
        result, _ = _migrate_proof_bundle_field(path)
        # Empty value should not produce proof_bundle: '' in frontmatter
        # Acceptable: 'already' (treated as no-op) or 'failed'
        assert result in {"already", "failed"}

    # -----------------------------------------------------------------------
    # AC1+AC2 — differentiated multi-match: different values prove first-match
    # semantics for both frontmatter population and body removal
    # -----------------------------------------------------------------------

    def test_frontmatter_value_comes_from_first_match_not_later(
        self, tmp_path: Path
    ) -> None:
        """AC1+AC2: first body line has 'smoke', later line has 'behavioral'.

        Frontmatter proof_bundle must be 'smoke' (first match), not 'behavioral'.
        This test distinguishes first-match extraction from any-match extraction.
        """
        fm = "id: 1042\ntitle: Test\nstatus: todo\n"
        body = (
            "Proof bundle: smoke\n"
            "## Builder Notes\n"
            "Proof bundle: behavioral\n"
        )
        path = _make_task_file(tmp_path, fm, body, filename="1042.md")
        _migrate_proof_bundle_field(path)
        content = path.read_text(encoding="utf-8")
        fm_text = _fm_section(content)
        assert "proof_bundle: smoke" in fm_text
        assert "proof_bundle: behavioral" not in fm_text

    def test_first_match_line_removed_not_later_match_line(
        self, tmp_path: Path
    ) -> None:
        """AC2: first body line has 'smoke', later line has 'behavioral'.

        After migration: 'Proof bundle: smoke' is removed from body;
        'Proof bundle: behavioral' remains in body.
        This test distinguishes first-line removal from any-line removal.
        """
        fm = "id: 1043\ntitle: Test\nstatus: todo\n"
        body = (
            "Proof bundle: smoke\n"
            "## Builder Notes\n"
            "Proof bundle: behavioral\n"
        )
        path = _make_task_file(tmp_path, fm, body, filename="1043.md")
        _migrate_proof_bundle_field(path)
        content = path.read_text(encoding="utf-8")
        body_part = _body_section(content)
        assert "Proof bundle: smoke" not in body_part
        assert "Proof bundle: behavioral" in body_part
