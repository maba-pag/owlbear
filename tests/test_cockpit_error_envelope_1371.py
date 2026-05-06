"""Tests for Cockpit error envelope legacy test migration (task #1371).

tests/test_cockpit_error_envelope_1370.py covers AC1-AC4(a)(b)(c) in full.
This file covers the remaining uncovered acceptance criterion:

  AC7 (td:1): Legacy durable-suite tests that assert `detail` format for domain
              errors must be updated to assert the stable {code, message} envelope.

All three tests fail until the builder updates the legacy assertion lines to use
the envelope format instead of the old FastAPI {detail} field.
"""
from __future__ import annotations

from pathlib import Path


class TestFromAC_LegacyTestMigration:
    """AC7 (td:1): Legacy durable tests migrated from detail-assertions to envelope.

    Affected files:
      - tests/test_cockpit_mutation_api_1134.py  (stale-conflict edit error)
      - tests/test_cockpit_mutation_api_1135.py  (not-found move, concurrency move)
      - tests/test_cockpit_read_api.py           (not-found task detail)

    Each test checks for the absence of the OLD domain-error assertion pattern.
    Fails now because the pattern still exists; passes after the builder removes
    the `detail`-format assertions and replaces them with envelope assertions.
    """

    _tests_dir = Path(__file__).parent

    def test_mutation_1134_stale_error_no_detail_get(self) -> None:
        """test_cockpit_mutation_api_1134 must not call .get('detail') for stale error.

        Line ~204: `detail = response.json().get("detail", "")` must be replaced
        with an envelope assertion (`code` / `message` fields).
        """
        source = (self._tests_dir / "test_cockpit_mutation_api_1134.py").read_text(
            encoding="utf-8"
        )
        assert 'response.json().get("detail"' not in source  # FAILS: pattern still present

    def test_mutation_1135_domain_errors_no_detail_subscript(self) -> None:
        """test_cockpit_mutation_api_1135 must not subscript json()['detail'] for domain errors.

        Lines ~165 and ~313: `response.json()["detail"]` must be replaced with
        assertions on the `code` or `message` fields of the error envelope.
        """
        source = (self._tests_dir / "test_cockpit_mutation_api_1135.py").read_text(
            encoding="utf-8"
        )
        assert 'response.json()["detail"]' not in source  # FAILS: pattern still present

    def test_read_api_not_found_no_detail_get(self) -> None:
        """test_cockpit_read_api must not call .get('detail') for 404 domain error.

        Line ~461: `detail = response.json().get("detail", "")` inside
        test_task_detail_nonexistent_id_returns_404_with_id_in_detail must be
        replaced with an envelope assertion on the `code` or `message` field.
        """
        source = (self._tests_dir / "test_cockpit_read_api.py").read_text(
            encoding="utf-8"
        )
        assert 'response.json().get("detail"' not in source  # FAILS: pattern still present
