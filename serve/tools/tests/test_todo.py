"""Behavioral tests for the advisory TODO scanner."""

from __future__ import annotations

from pathlib import Path

import pytest

from owlbear_tools.todo import run_todo


def test_todo_ignores_binary_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    for name, text in {
        "prompt.md": "> **TODO:** {category} — {description} [#{id}]\n",
        "legacy.md": "> **TODO:** {category} — {description} [#{task_id}]\n",
        "real.md": "> **TODO:** stale — update the command table [#1234]\n",
        "nested-worktree/.git": "gitdir: /tmp/other\n",
        "nested-worktree/real.md": "> **TODO:** stale - duplicate checkout [#5678]\n",
        ".owlbear/legacy/brief.md": "> **TODO:** stale - archived [#1]\n",
        ".venv-3.12.14/lib/python3.12/site-packages/third_party.py": "> **TODO:** stale - generated [#2]\n",
        "package.egg-info/metadata.txt": "> **TODO:** stale - generated [#3]\n",
    }.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    (tmp_path / "binary.dat").write_bytes(b"> **TODO:** stale - binary\n\0")
    outside = tmp_path.parent / "outside-todo"
    outside.mkdir()
    (outside / "real.md").write_text("> **TODO:** stale - outside [#3]\n", encoding="utf-8")
    (tmp_path / "outside.md").symlink_to(outside / "real.md")

    assert run_todo() == 0

    output = capsys.readouterr().out
    assert "1 TODO marker(s)" in output
    assert "real.md:1: > **TODO:** stale — update the command table [#1234]" in output
    assert "{category}" not in output

    (tmp_path / "real.md").unlink()
    assert run_todo() == 0
    assert "No TODO markers found" in capsys.readouterr().out
