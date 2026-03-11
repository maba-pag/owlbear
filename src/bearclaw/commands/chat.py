"""Chat command — interactive CLI REPL with OwlBear."""

from __future__ import annotations

import asyncio
import contextlib
import inspect
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer

from owlbear.bootstrap import bootstrap
from owlbear.config import OwlBearSettings
from owlbear.core.errors import error_to_user_message
from owlbear.memory.session import SessionStore
from owlbear.tools.github_api import parse_git_remote

if TYPE_CHECKING:
    from owlbear.channels.cli import CLIChannel
    from owlbear.core.agent import OwlBearAgent

app = typer.Typer()

_EXIT_KEYWORDS = frozenset({"exit", "quit"})


@app.command()
def chat(
    model: Annotated[str | None, typer.Option("--model", help="LLM model name.")] = None,
    session: Annotated[
        str | None,
        typer.Option("--session", help="Session name (default: auto-generated)."),
    ] = None,
    workspace: Annotated[
        str,
        typer.Option("--workspace", help="Workspace root directory."),
    ] = ".",
    project: Annotated[
        str | None,
        typer.Option("--project", help="Project name for scoped sessions."),
    ] = None,
) -> None:
    """Start an interactive chat REPL with OwlBear."""
    from pathlib import Path as _Path  # noqa: PLC0415

    ws = _Path(workspace).resolve()
    asyncio.run(
        _chat_async(model=model, session=session, workspace_root=ws, project=project),
    )


async def _read_multiline(channel: CLIChannel) -> str | None:
    """Accumulate lines until ``!end`` or EOF, return joined text."""
    lines: list[str] = []
    await channel.send("(multi-line mode — type !end to submit)")
    while True:
        ml = await channel.receive(prompt="... ")
        if ml is None or ml.strip() == "!end":
            break
        lines.append(ml)
    return "\n".join(lines) if lines else None


def _detect_github_remote(workspace_root: Path) -> tuple[str, str] | None:
    """Auto-detect GitHub owner/repo from ``git remote get-url origin``.

    Returns:
        Tuple of ``(owner, repo)`` on success, or ``None`` if detection fails.
    """
    result = subprocess.run(
        ["git", "remote", "get-url", "origin"],  # noqa: S607
        capture_output=True,
        text=True,
        cwd=workspace_root,
        check=False,
    )
    if result.returncode != 0:
        return None
    try:
        return parse_git_remote(result.stdout.strip())
    except ValueError:
        return None


def _build_chat_session(
    settings: OwlBearSettings,
    session: str | None,
    *,
    project_id: str | None = None,
) -> tuple[str, SessionStore]:
    """Resolve session name and create a :class:`SessionStore`.

    When *project_id* is provided the session file is placed under
    ``config_dir/projects/{project_id}/sessions/``.  Otherwise the
    legacy ``config_dir/sessions/`` directory is used (backward compat).
    """
    from datetime import UTC, datetime  # noqa: PLC0415
    from pathlib import Path  # noqa: PLC0415

    name = session or f"chat-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}"
    base = Path(settings.config_dir)
    if project_id:
        base = base / "projects" / project_id
    path = base / "sessions" / f"{name}.jsonl"
    return name, SessionStore(path)


async def _chat_async(
    *,
    model: str | None,
    session: str | None,
    workspace_root: Path,
    project: str | None = None,
) -> None:
    """Run the interactive chat REPL loop."""
    settings = OwlBearSettings()
    model_name = model or settings.chat_model

    # Resolve project name → id for session scoping.
    project_id: str | None = None
    if project:
        from owlbear.projects.store import ProjectStore  # noqa: PLC0415

        store_dir = Path(settings.config_dir) / "projects"
        proj = ProjectStore(store_dir).get_by_name(project)
        project_id = proj.id

    session_name, store = _build_chat_session(settings, session, project_id=project_id)

    # Load existing history (resume previous session).
    store.load()

    # Delegate all hook/toolset/channel assembly to bootstrap().
    result = await bootstrap(settings, channel_name="cli", workspace_root=workspace_root)

    # Override session with user-specified store (chat-specific naming).
    result.agent.session = store

    # Override model if --model provided.
    if model:
        result.agent.update_model(model)

    # Banner.
    await result.channel.send(
        f"OwlBear Chat — model: {model_name}, session: {session_name}",
    )
    await result.channel.send(
        "Type !multi for multi-line input (!end to submit). Type exit or quit to leave.",
    )

    try:
        await _chat_loop(result.agent, result.channel)
    finally:
        for cb in result.cleanup:
            with contextlib.suppress(Exception):
                rv = cb()
                if inspect.isawaitable(rv):
                    await rv


async def _chat_loop(agent: OwlBearAgent, channel: CLIChannel) -> None:
    """Core receive → turn → send loop."""
    try:
        while True:
            line = await channel.receive(prompt="> ")
            if line is None:
                break

            text = line.strip()
            if text.lower() in _EXIT_KEYWORDS:
                break
            if not text:
                continue

            if text == "!multi":
                text = await _read_multiline(channel)  # type: ignore[assignment]
                if text is None:
                    continue

            try:
                response = await agent.turn(text)
                await channel.send(response)
            except Exception as exc:  # noqa: BLE001
                await channel.send(f"Error: {error_to_user_message(exc)}")
    except KeyboardInterrupt:
        pass

    await channel.send("Goodbye!")
