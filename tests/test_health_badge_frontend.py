"""HealthBadge frontend structural regression tests.

Promoted from the task-scoped suite for task #1158.

These tests verify that:
  1. The component file exists at the expected path.
  2. The Vitest test file exists at the expected path.
"""

from __future__ import annotations

import pathlib

# Provenance: promoted from task-scoped suite for task #1158.


ROOT = pathlib.Path(__file__).parent.parent
COMPONENT_PATH = ROOT / "serve/cockpit/web/src/components/HealthBadge.tsx"
TEST_PATH = ROOT / "serve/cockpit/web/src/__tests__/HealthBadge.test.tsx"


class TestFromAC_HealthBadgeStructure:
    """Structural guards — AC: component and test file paths."""

    # AC: Component exported as default from serve/cockpit/web/src/components/HealthBadge.tsx
    def test_component_file_exists_at_contract_path(self) -> None:
        assert COMPONENT_PATH.exists(), (
            f"HealthBadge component not found at {COMPONENT_PATH}. "
            "Builder must create serve/cockpit/web/src/components/HealthBadge.tsx."
        )

    def test_component_file_is_non_empty(self) -> None:
        assert COMPONENT_PATH.exists(), (
            "Component file missing — run test_component_file_exists_at_contract_path first."
        )
        content = COMPONENT_PATH.read_text()
        assert len(content.strip()) > 0, "HealthBadge.tsx must not be empty."

    # AC: unit tests in serve/cockpit/web/src/__tests__/HealthBadge.test.tsx
    def test_vitest_test_file_exists_at_contract_path(self) -> None:
        assert TEST_PATH.exists(), (
            f"Vitest test file not found at {TEST_PATH}. "
            "Builder must move .owlbear/scratch/HealthBadge_1158.test.tsx to "
            "serve/cockpit/web/src/__tests__/HealthBadge.test.tsx."
        )

    def test_vitest_test_file_contains_testfromac_class(self) -> None:
        assert TEST_PATH.exists(), "Test file missing — run test_vitest_test_file_exists_at_contract_path first."
        content = TEST_PATH.read_text()
        assert "TestFromAC_HealthBadge" in content, (
            "Vitest test file must contain the TestFromAC_HealthBadge describe block."
        )

    def test_component_file_contains_default_export(self) -> None:
        assert COMPONENT_PATH.exists(), "Component file missing."
        content = COMPONENT_PATH.read_text()
        assert "export default" in content, "HealthBadge.tsx must use 'export default' for its component."

    def test_component_file_contains_health_badge_props_or_interface(self) -> None:
        assert COMPONENT_PATH.exists(), "Component file missing."
        content = COMPONENT_PATH.read_text()
        assert "ScanItem" in content or "HealthBadgeProps" in content, (
            "HealthBadge.tsx must define ScanItem and/or HealthBadgeProps interface."
        )

    def test_component_file_uses_data_health_attribute(self) -> None:
        assert COMPONENT_PATH.exists(), "Component file missing."
        content = COMPONENT_PATH.read_text()
        assert "data-health" in content, "HealthBadge.tsx must use the data-health attribute for green/red state."

    def test_component_file_uses_data_testid_health_badge(self) -> None:
        assert COMPONENT_PATH.exists(), "Component file missing."
        content = COMPONENT_PATH.read_text()
        variants = (
            'data-testid="health-badge"',
            "data-testid={'health-badge'}",
            'data-testid={"health-badge"}',
        )
        assert any(v in content for v in variants), (
            'HealthBadge.tsx must include data-testid="health-badge" on the root badge element.'
        )

    # AC 7 (refined cycle 2): Component must NOT wrap itself in PorscheDesignSystemProvider.
    # App.tsx provides the provider at root — nested providers are a defect.
    def test_component_file_does_not_import_pds_provider(self) -> None:
        assert COMPONENT_PATH.exists(), "Component file missing."
        content = COMPONENT_PATH.read_text(encoding="utf-8")
        assert "PorscheDesignSystemProvider" not in content, (
            "HealthBadge.tsx must NOT import or instantiate PorscheDesignSystemProvider. "
            "App.tsx provides it at root — HealthBadge must rely on the app-level provider, "
            "not nest its own. Remove the import and wrapper from HealthBadge.tsx."
        )
