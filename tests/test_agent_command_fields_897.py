from __future__ import annotations

import pathlib
import re

import pytest
import yaml

AGENTS_DIR = pathlib.Path(__file__).parent.parent / "share" / "agents"
EXPECTED_CMD_PREFIX = "uv run python .owlbear/hooks/"


def _parse_frontmatter(path: pathlib.Path) -> dict:
    content = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    assert match, f"No YAML frontmatter found in {path.name}"
    return yaml.safe_load(match.group(1))


def _hook_commands(fm: dict, hook_type: str) -> list[str]:
    hooks = fm.get("hooks", {}) or {}
    return [h["command"] for h in hooks.get(hook_type, [])]


class TestFromAC_AgentCommandFields:
    """AC: update agent.md command: fields from powershell to uv run python."""

    # ── AC6: grep -r "powershell" share/agents/ returns no results ──────────

    def test_no_powershell_in_any_agent_file(self) -> None:
        violations = [
            p.name
            for p in AGENTS_DIR.glob("*.agent.md")
            if "powershell" in p.read_text(encoding="utf-8").lower()
        ]
        assert violations == [], f"Files still containing 'powershell': {violations}"

    # ── AC7: grep -r ".ps1" share/agents/ returns no results ─────────────────

    def test_no_ps1_in_any_agent_file(self) -> None:
        violations = [
            p.name
            for p in AGENTS_DIR.glob("*.agent.md")
            if ".ps1" in p.read_text(encoding="utf-8")
        ]
        assert violations == [], f"Files still containing '.ps1': {violations}"

    # ── AC2: every command: field uses uv run python ─────────────────────────

    def test_all_hook_commands_use_uv_run_python(self) -> None:
        violations: list[str] = []
        for path in sorted(AGENTS_DIR.glob("*.agent.md")):
            fm = _parse_frontmatter(path)
            for hook_type, hook_list in (fm.get("hooks") or {}).items():
                for hook in hook_list:
                    cmd = hook.get("command", "")
                    if not cmd.startswith(EXPECTED_CMD_PREFIX):
                        violations.append(f"{path.name} [{hook_type}]: {cmd!r}")
        assert violations == [], f"Non-compliant commands:\n" + "\n".join(violations)

    # ── AC3 + AC4 + AC5: hook type and script preserved per agent ────────────

    def test_architect_hook_uses_deny_code_writes_py(self) -> None:
        fm = _parse_frontmatter(AGENTS_DIR / "architect.agent.md")
        cmds = _hook_commands(fm, "PreToolUse")
        assert "uv run python .owlbear/hooks/deny-code-writes.py" in cmds

    def test_auditor_hook_uses_deny_writes_py(self) -> None:
        fm = _parse_frontmatter(AGENTS_DIR / "auditor.agent.md")
        cmds = _hook_commands(fm, "PreToolUse")
        assert "uv run python .owlbear/hooks/deny-writes.py" in cmds

    def test_builder_hook_mappings(self) -> None:
        fm = _parse_frontmatter(AGENTS_DIR / "builder.agent.md")
        assert "uv run python .owlbear/hooks/session-context.py" in _hook_commands(fm, "SessionStart")
        assert "uv run python .owlbear/hooks/lint-changed.py" in _hook_commands(fm, "PostToolUse")

    def test_challenger_hook_uses_deny_writes_py(self) -> None:
        fm = _parse_frontmatter(AGENTS_DIR / "challenger.agent.md")
        cmds = _hook_commands(fm, "PreToolUse")
        assert "uv run python .owlbear/hooks/deny-writes.py" in cmds

    def test_code_reader_hook_uses_deny_writes_py(self) -> None:
        fm = _parse_frontmatter(AGENTS_DIR / "code-reader.agent.md")
        cmds = _hook_commands(fm, "PreToolUse")
        assert "uv run python .owlbear/hooks/deny-writes.py" in cmds

    def test_doc_writer_hook_mappings(self) -> None:
        fm = _parse_frontmatter(AGENTS_DIR / "doc-writer.agent.md")
        assert "uv run python .owlbear/hooks/session-context.py" in _hook_commands(fm, "SessionStart")
        assert "uv run python .owlbear/hooks/deny-code-writes.py" in _hook_commands(fm, "PreToolUse")

    def test_fix_attempt_hook_uses_lint_changed_py(self) -> None:
        fm = _parse_frontmatter(AGENTS_DIR / "fix-attempt.agent.md")
        cmds = _hook_commands(fm, "PostToolUse")
        assert "uv run python .owlbear/hooks/lint-changed.py" in cmds

    def test_ideation_architect_hook_uses_allow_stances_only_py(self) -> None:
        fm = _parse_frontmatter(AGENTS_DIR / "ideation-architect.agent.md")
        cmds = _hook_commands(fm, "PreToolUse")
        assert "uv run python .owlbear/hooks/allow-stances-only.py" in cmds

    def test_ideation_critic_hook_uses_deny_writes_py(self) -> None:
        fm = _parse_frontmatter(AGENTS_DIR / "ideation-critic.agent.md")
        cmds = _hook_commands(fm, "PreToolUse")
        assert "uv run python .owlbear/hooks/deny-writes.py" in cmds

    def test_ideation_data_hook_uses_allow_stances_only_py(self) -> None:
        fm = _parse_frontmatter(AGENTS_DIR / "ideation-data.agent.md")
        cmds = _hook_commands(fm, "PreToolUse")
        assert "uv run python .owlbear/hooks/allow-stances-only.py" in cmds

    def test_ideation_enduser_hook_uses_allow_stances_only_py(self) -> None:
        fm = _parse_frontmatter(AGENTS_DIR / "ideation-enduser.agent.md")
        cmds = _hook_commands(fm, "PreToolUse")
        assert "uv run python .owlbear/hooks/allow-stances-only.py" in cmds

    def test_ideation_security_hook_uses_allow_stances_only_py(self) -> None:
        fm = _parse_frontmatter(AGENTS_DIR / "ideation-security.agent.md")
        cmds = _hook_commands(fm, "PreToolUse")
        assert "uv run python .owlbear/hooks/allow-stances-only.py" in cmds

    def test_quality_runner_hook_uses_deny_writes_py(self) -> None:
        fm = _parse_frontmatter(AGENTS_DIR / "quality-runner.agent.md")
        cmds = _hook_commands(fm, "PreToolUse")
        assert "uv run python .owlbear/hooks/deny-writes.py" in cmds

    def test_researcher_hook_uses_deny_code_writes_py(self) -> None:
        fm = _parse_frontmatter(AGENTS_DIR / "researcher.agent.md")
        cmds = _hook_commands(fm, "PreToolUse")
        assert "uv run python .owlbear/hooks/deny-code-writes.py" in cmds

    def test_reviewer_hook_uses_deny_writes_py(self) -> None:
        fm = _parse_frontmatter(AGENTS_DIR / "reviewer.agent.md")
        cmds = _hook_commands(fm, "PreToolUse")
        assert "uv run python .owlbear/hooks/deny-writes.py" in cmds

    def test_test_writer_hook_mappings(self) -> None:
        fm = _parse_frontmatter(AGENTS_DIR / "test-writer.agent.md")
        assert "uv run python .owlbear/hooks/session-context.py" in _hook_commands(fm, "SessionStart")
        assert "uv run python .owlbear/hooks/deny-src-writes.py" in _hook_commands(fm, "PreToolUse")
