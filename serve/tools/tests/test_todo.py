"""Behavioral tests for the advisory TODO scanner."""

from __future__ import annotations

from pathlib import Path

import pytest

from owlbear_tools.todo import run_todo


def test_todo_ignores_instructional_templates_and_keeps_concrete_markers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "prompt.md").write_text("> **TODO:** {category} — {description} [#{id}]\n", encoding="utf-8")
    (tmp_path / "legacy.md").write_text("> **TODO:** {category} — {description} [#{task_id}]\n", encoding="utf-8")
    (tmp_path / "real.md").write_text("> **TODO:** stale — update the command table [#1234]\n", encoding="utf-8")

    run_todo()

    output = capsys.readouterr().out
    assert "1 TODO marker(s)" in output
    assert "real.md:1" in output
    assert "{category}" not in output


def test_todo_does_not_descend_into_nested_git_checkouts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    nested = tmp_path / "nested-worktree"
    nested.mkdir()
    (nested / ".git").write_text("gitdir: /tmp/other\n", encoding="utf-8")
    (nested / "real.md").write_text("> **TODO:** stale — duplicate checkout [#5678]\n", encoding="utf-8")

    run_todo()

    assert "No TODO markers found" in capsys.readouterr().out


def test_todo_ignores_binary_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "binary.dat").write_bytes(b"> **TODO:** stale - binary\n\0")

    run_todo()

    assert "No TODO markers found" in capsys.readouterr().out


def test_todo_skips_archived_and_egg_info_directories(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    legacy = tmp_path / ".owlbear/legacy"
    legacy.mkdir(parents=True)
    (legacy / "brief.md").write_text("> **TODO:** stale - archived [#1]\n", encoding="utf-8")
    egg_info = tmp_path / "package.egg-info"
    egg_info.mkdir()
    (egg_info / "metadata.txt").write_text("> **TODO:** stale - generated [#2]\n", encoding="utf-8")

    run_todo()

    assert "No TODO markers found" in capsys.readouterr().out


def test_todo_skips_symlinks_outside_the_scan_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    outside = tmp_path.parent / "outside-todo"
    outside.mkdir()
    (outside / "real.md").write_text("> **TODO:** stale - outside [#3]\n", encoding="utf-8")
    (tmp_path / "outside.md").symlink_to(outside / "real.md")

    run_todo()

    assert "No TODO markers found" in capsys.readouterr().out
