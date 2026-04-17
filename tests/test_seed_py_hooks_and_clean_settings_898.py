"""Tests for task #898: Update seed/ with .py hooks and clean settings.

Contract-level filesystem assertions verifying that:
1. seed/.owlbear/hooks/ contains exactly 7 .py hook files (replacing .ps1)
2. No .ps1 files remain in seed/.owlbear/hooks/
3. seed/.vscode/settings.json contains no Windows-only terminal profile blocks
4. No .ps1 references remain anywhere in seed/
5. No "powershell" string remains in any file under seed/

AC coverage:
  AC1: All .ps1 files in seed/.owlbear/hooks/ replaced with .py equivalents
  AC2: 7 .py hooks present in seed/.owlbear/hooks/ — deny-scratch-only-writes drift fixed
  AC3: Windows-only terminal profiles removed from seed/.vscode/settings.json
  AC4/AC5: grep -r ".ps1" seed/ returns no results
  AC6: grep -r "powershell" seed/ returns no results
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parent.parent
SEED_HOOKS = ROOT / "seed" / ".owlbear" / "hooks"
SEED_SETTINGS = ROOT / "seed" / ".vscode" / "settings.json"
SEED_DIR = ROOT / "seed"

EXPECTED_HOOKS = {
    "allow-stances-only.py",
    "deny-code-writes.py",
    "deny-scratch-only-writes.py",
    "deny-src-writes.py",
    "deny-writes.py",
    "lint-changed.py",
    "session-context.py",
}


# ---------------------------------------------------------------------------
# AC2: Exactly 7 .py hooks present in seed/.owlbear/hooks/
# ---------------------------------------------------------------------------


class TestFromAC_SeedPyHooksPresent:
    """AC1 + AC2: seed/.owlbear/hooks/ must contain exactly 7 .py hook files."""

    def test_exactly_seven_py_hooks_exist(self) -> None:
        """seed/.owlbear/hooks/ must have exactly 7 .py files after builder copies them."""
        py_files = list(SEED_HOOKS.glob("*.py"))
        assert len(py_files) == 7, (
            f"Expected 7 .py hook files in seed/.owlbear/hooks/, found {len(py_files)}: "
            f"{[f.name for f in py_files]}"
        )

    def test_all_expected_hook_names_present(self) -> None:
        """All 7 named .py hooks must be present in seed/.owlbear/hooks/."""
        actual = {f.name for f in SEED_HOOKS.glob("*.py")}
        missing = EXPECTED_HOOKS - actual
        assert not missing, f"Missing .py hook files: {sorted(missing)}"

    def test_deny_scratch_only_writes_py_exists(self) -> None:
        """deny-scratch-only-writes.py must be present — this was the seed drift (AC2)."""
        hook = SEED_HOOKS / "deny-scratch-only-writes.py"
        assert hook.exists(), (
            "deny-scratch-only-writes.py missing from seed/.owlbear/hooks/ — this was the drift item"
        )

    def test_each_py_hook_is_nonempty(self) -> None:
        """Each .py hook copied to seed/ must exist and have non-zero content."""
        for name in EXPECTED_HOOKS:
            hook = SEED_HOOKS / name
            assert hook.exists(), f"{name} missing from seed/.owlbear/hooks/"
            assert hook.stat().st_size > 0, f"{name} exists but is empty"


# ---------------------------------------------------------------------------
# AC1: No .ps1 files remain in seed/.owlbear/hooks/
# ---------------------------------------------------------------------------


class TestFromAC_SeedPs1FilesRemoved:
    """AC1: All .ps1 files must be absent from seed/.owlbear/hooks/ after replacement."""

    def test_no_ps1_files_in_seed_hooks_dir(self) -> None:
        """seed/.owlbear/hooks/ must contain zero .ps1 files after builder deletes them."""
        ps1_files = list(SEED_HOOKS.glob("*.ps1"))
        assert ps1_files == [], (
            f"Found .ps1 files still present in seed/.owlbear/hooks/: {[f.name for f in ps1_files]}"
        )

    def test_allow_stances_only_ps1_absent(self) -> None:
        """allow-stances-only.ps1 must be deleted from seed/."""
        assert not (SEED_HOOKS / "allow-stances-only.ps1").exists()

    def test_deny_code_writes_ps1_absent(self) -> None:
        """deny-code-writes.ps1 must be deleted from seed/."""
        assert not (SEED_HOOKS / "deny-code-writes.ps1").exists()

    def test_deny_src_writes_ps1_absent(self) -> None:
        """deny-src-writes.ps1 must be deleted from seed/."""
        assert not (SEED_HOOKS / "deny-src-writes.ps1").exists()

    def test_deny_writes_ps1_absent(self) -> None:
        """deny-writes.ps1 must be deleted from seed/."""
        assert not (SEED_HOOKS / "deny-writes.ps1").exists()

    def test_lint_changed_ps1_absent(self) -> None:
        """lint-changed.ps1 must be deleted from seed/."""
        assert not (SEED_HOOKS / "lint-changed.ps1").exists()

    def test_session_context_ps1_absent(self) -> None:
        """session-context.ps1 must be deleted from seed/."""
        assert not (SEED_HOOKS / "session-context.ps1").exists()


# ---------------------------------------------------------------------------
# AC4/AC5: No .ps1 references anywhere in seed/
# ---------------------------------------------------------------------------


class TestFromAC_SeedNoPs1References:
    """AC4 + AC5: grep -r '.ps1' seed/ must return no results."""

    def test_no_ps1_files_anywhere_in_seed(self) -> None:
        """No .ps1 files must exist anywhere under seed/ after builder completes."""
        ps1_files = list(SEED_DIR.rglob("*.ps1"))
        assert ps1_files == [], (
            f"Found .ps1 files under seed/: {[str(p.relative_to(ROOT)) for p in ps1_files]}"
        )

    def test_no_ps1_string_in_seed_files(self) -> None:
        """No file under seed/ may contain the string '.ps1' (AC5: grep -r '.ps1' seed/)."""
        matches: list[str] = []
        for path in SEED_DIR.rglob("*"):
            if not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if ".ps1" in text:
                matches.append(str(path.relative_to(ROOT)))
        assert matches == [], f"Files under seed/ still reference .ps1: {matches}"


# ---------------------------------------------------------------------------
# AC6: No "powershell" string anywhere in seed/
# ---------------------------------------------------------------------------


class TestFromAC_SeedNoPowershellReferences:
    """AC6: grep -r 'powershell' seed/ must return no results (case-insensitive)."""

    def test_no_powershell_string_in_seed_files(self) -> None:
        """No file under seed/ may contain 'powershell' (case-insensitive) after cleanup."""
        matches: list[str] = []
        for path in SEED_DIR.rglob("*"):
            if not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if "powershell" in text.lower():
                matches.append(str(path.relative_to(ROOT)))
        assert matches == [], f"Files under seed/ still contain 'powershell': {matches}"


# ---------------------------------------------------------------------------
# AC3: Windows-only terminal profile blocks removed from seed/.vscode/settings.json
# ---------------------------------------------------------------------------


class TestFromAC_SeedSettingsWindowsProfilesRemoved:
    """AC3: seed/.vscode/settings.json must not contain Windows-only terminal settings."""

    def test_no_default_profile_windows_key(self) -> None:
        """terminal.integrated.defaultProfile.windows must be absent from settings.json."""
        text = SEED_SETTINGS.read_text(encoding="utf-8")
        assert "defaultProfile.windows" not in text, (
            "settings.json still has terminal.integrated.defaultProfile.windows (Windows-only)"
        )

    def test_no_pwsh_terminal_profile(self) -> None:
        """The 'pwsh' terminal profile block must be absent from settings.json."""
        text = SEED_SETTINGS.read_text(encoding="utf-8")
        assert '"pwsh"' not in text, (
            "settings.json still contains 'pwsh' terminal profile (Windows-only)"
        )

    def test_no_pwsh_exe_path(self) -> None:
        """pwsh.exe path must be absent from settings.json."""
        text = SEED_SETTINGS.read_text(encoding="utf-8")
        assert "pwsh.exe" not in text, (
            "settings.json still contains pwsh.exe path (Windows-only)"
        )

    def test_no_profiles_windows_key(self) -> None:
        """terminal.integrated.profiles.windows block must be absent from settings.json."""
        text = SEED_SETTINGS.read_text(encoding="utf-8")
        assert "profiles.windows" not in text, (
            "settings.json still contains profiles.windows block (Windows-only)"
        )
