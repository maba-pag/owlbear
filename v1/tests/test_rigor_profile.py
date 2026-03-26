"""Tests for RigorProfile config model and resolution — RED phase for #618/#710."""

from __future__ import annotations

import dataclasses
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from owlbear.config import (
    RIGOR_LEAN,
    RIGOR_STANDARD,
    RIGOR_THOROUGH,
    OwlBearSettings,
    RigorProfile,
    resolve_rigor_profile,
)
from owlbear.core.deps import OwlBearDeps


@pytest.fixture(autouse=True)
def _mock_copilot_client():
    """Prevent real Copilot client creation in bootstrap tests."""
    with patch(
        "owlbear.bootstrap.create_copilot_client",
        new_callable=AsyncMock,
        return_value=AsyncMock(),
    ):
        yield


# ---------------------------------------------------------------------------
# AC: Test RigorProfile dataclass creation with all fields
# ---------------------------------------------------------------------------


class TestFromACRigorProfileDataclass:
    """RigorProfile frozen dataclass creation and field access."""

    def test_create_with_all_fields(self) -> None:
        """RigorProfile can be instantiated with review_enabled, tdd_depth, turn_budget."""
        profile = RigorProfile(review_enabled=True, tdd_depth="full", turn_budget=30)
        assert profile.review_enabled is True
        assert profile.tdd_depth == "full"
        assert profile.turn_budget == 30

    def test_is_frozen(self) -> None:
        """RigorProfile is a frozen dataclass — mutation must raise."""
        profile = RigorProfile(review_enabled=False, tdd_depth="none", turn_budget=10)
        with pytest.raises(dataclasses.FrozenInstanceError):
            profile.review_enabled = True  # type: ignore[misc]

    def test_is_dataclass(self) -> None:
        """RigorProfile is a dataclass (not pydantic model)."""
        assert dataclasses.is_dataclass(RigorProfile)


# ---------------------------------------------------------------------------
# AC: Test 3 preset constants (LEAN, STANDARD, THOROUGH) have expected field values
# ---------------------------------------------------------------------------


class TestFromACRigorPresets:
    """Module-level preset constants match exact values from #618 AC."""

    def test_lean_review_disabled(self) -> None:
        assert RIGOR_LEAN.review_enabled is False

    def test_lean_tdd_depth_smoke(self) -> None:
        assert RIGOR_LEAN.tdd_depth == "smoke"

    def test_lean_turn_budget_15(self) -> None:
        assert RIGOR_LEAN.turn_budget == 15

    def test_standard_review_enabled(self) -> None:
        assert RIGOR_STANDARD.review_enabled is True

    def test_standard_tdd_depth_full(self) -> None:
        assert RIGOR_STANDARD.tdd_depth == "full"

    def test_standard_turn_budget_30(self) -> None:
        assert RIGOR_STANDARD.turn_budget == 30

    def test_thorough_review_enabled(self) -> None:
        assert RIGOR_THOROUGH.review_enabled is True

    def test_thorough_tdd_depth_full(self) -> None:
        assert RIGOR_THOROUGH.tdd_depth == "full"

    def test_thorough_turn_budget_50(self) -> None:
        assert RIGOR_THOROUGH.turn_budget == 50


# ---------------------------------------------------------------------------
# AC: Test OwlBearSettings includes rigor_profiles dict with 3 presets by default
# AC: Test OwlBearSettings.default_rigor defaults to 'standard'
# ---------------------------------------------------------------------------


class TestFromACRigorSettings:
    """OwlBearSettings rigor-related fields and validation."""

    def test_rigor_profiles_has_three_keys(self, default_settings: OwlBearSettings) -> None:
        """rigor_profiles dict defaults to 3 preset entries."""
        assert set(default_settings.rigor_profiles.keys()) == {
            "lean",
            "standard",
            "thorough",
        }

    def test_rigor_profiles_lean_matches_preset(self, default_settings: OwlBearSettings) -> None:
        assert default_settings.rigor_profiles["lean"] == RIGOR_LEAN

    def test_rigor_profiles_standard_matches_preset(
        self, default_settings: OwlBearSettings
    ) -> None:
        assert default_settings.rigor_profiles["standard"] == RIGOR_STANDARD

    def test_rigor_profiles_thorough_matches_preset(
        self, default_settings: OwlBearSettings
    ) -> None:
        assert default_settings.rigor_profiles["thorough"] == RIGOR_THOROUGH

    def test_default_rigor_is_standard(self, default_settings: OwlBearSettings) -> None:
        """default_rigor defaults to 'standard'."""
        assert default_settings.default_rigor == "standard"

    def test_custom_profile_accepted(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A custom profile added to rigor_profiles dict is valid if default_rigor matches."""
        custom = RigorProfile(review_enabled=False, tdd_depth="none", turn_budget=5)
        profiles = {
            "lean": RIGOR_LEAN,
            "standard": RIGOR_STANDARD,
            "thorough": RIGOR_THOROUGH,
            "quick": custom,
        }
        # Clear env to avoid interference
        for var in [k for k in os.environ if k.startswith("OWLBEAR_")]:
            monkeypatch.delenv(var, raising=False)
        settings = OwlBearSettings(rigor_profiles=profiles)
        assert settings.rigor_profiles["quick"] == custom

    def test_unknown_default_rigor_rejected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """field_validator rejects default_rigor when the key is not in rigor_profiles."""
        for var in [k for k in os.environ if k.startswith("OWLBEAR_")]:
            monkeypatch.delenv(var, raising=False)
        with pytest.raises(ValidationError):
            OwlBearSettings(default_rigor="nonexistent")


# ---------------------------------------------------------------------------
# AC: Test resolve_rigor_profile
# ---------------------------------------------------------------------------


class TestFromACResolveRigorProfile:
    """resolve_rigor_profile extracts rigor:* tag and returns matching profile."""

    def test_returns_lean_for_rigor_lean_tag(self, default_settings: OwlBearSettings) -> None:
        """rigor:lean tag -> RIGOR_LEAN profile."""
        result = resolve_rigor_profile(default_settings, ["rigor:lean"])
        assert result == RIGOR_LEAN

    def test_returns_thorough_for_rigor_thorough_tag(
        self, default_settings: OwlBearSettings
    ) -> None:
        """rigor:thorough tag -> RIGOR_THOROUGH profile."""
        result = resolve_rigor_profile(default_settings, ["rigor:thorough"])
        assert result == RIGOR_THOROUGH

    def test_returns_default_when_no_rigor_tag(self, default_settings: OwlBearSettings) -> None:
        """No rigor:* tag -> default profile (standard)."""
        result = resolve_rigor_profile(default_settings, ["scope:core", "type:test"])
        assert result == RIGOR_STANDARD

    def test_ignores_non_rigor_tags(self, default_settings: OwlBearSettings) -> None:
        """Non-rigor tags are ignored; only rigor:* tags matter."""
        result = resolve_rigor_profile(default_settings, ["phase-1", "config", "scope:core"])
        assert result == RIGOR_STANDARD

    def test_empty_tags_returns_default(self, default_settings: OwlBearSettings) -> None:
        """Empty tag list -> default profile."""
        result = resolve_rigor_profile(default_settings, [])
        assert result == RIGOR_STANDARD

    def test_rigor_tag_among_many(self, default_settings: OwlBearSettings) -> None:
        """rigor:lean tag mixed with other tags still resolves to lean."""
        result = resolve_rigor_profile(
            default_settings,
            ["scope:core", "phase-3", "rigor:lean", "type:build"],
        )
        assert result == RIGOR_LEAN


# ---------------------------------------------------------------------------
# AC: Test OwlBearDeps accepts rigor_profile field (default None, optional)
# ---------------------------------------------------------------------------


class TestFromACOwlBearDepsRigor:
    """OwlBearDeps.rigor_profile field."""

    def test_rigor_profile_default_none(self) -> None:
        """OwlBearDeps with no rigor_profile argument defaults to None."""
        deps = OwlBearDeps(hooks=MagicMock())
        assert deps.rigor_profile is None

    def test_rigor_profile_accepts_value(self) -> None:
        """OwlBearDeps accepts a RigorProfile instance."""
        profile = RigorProfile(review_enabled=True, tdd_depth="full", turn_budget=30)
        deps = OwlBearDeps(hooks=MagicMock(), rigor_profile=profile)
        assert deps.rigor_profile == profile


# ---------------------------------------------------------------------------
# AC: Bootstrap wires settings.rigor_profiles[settings.default_rigor] into deps
# ---------------------------------------------------------------------------


class TestFromACBootstrapRigorWiring:
    """Bootstrap wires the default rigor profile into OwlBearDeps."""

    @pytest.mark.asyncio
    async def test_bootstrap_deps_has_default_rigor_profile(
        self, tmp_path: os.PathLike[str]
    ) -> None:
        """After bootstrap, agent deps should have the default rigor profile set."""
        from pathlib import Path
        from unittest.mock import AsyncMock, patch

        from owlbear.bootstrap import bootstrap

        mock_model = MagicMock()
        mock_model.model_name = "test-model"
        settings = OwlBearSettings()
        with (
            patch(
                "owlbear.bootstrap.create_copilot_model",
                new_callable=AsyncMock,
                return_value=mock_model,
            ),
            patch("owlbear.core.agent.Agent"),
        ):
            result = await bootstrap(settings, workspace_root=Path(tmp_path))

        expected = settings.rigor_profiles[settings.default_rigor]
        assert result.agent._deps.rigor_profile == expected
