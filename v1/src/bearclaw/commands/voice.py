"""Voice subcommands — STT, TTS, and brainstorm sessions."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from bearclaw.commands import _cli_error

app = typer.Typer(
    name="voice",
    help="Voice I/O commands (requires: uv sync --extra voice).",
    no_args_is_help=True,
)


def _make_voice_channel(duration: float = 5.0) -> object:
    """Create a VoiceChannel with the given recording duration.

    Raises:
        ImportError: If the ``[voice]`` extras are not installed.
    """
    from owlbear.voice.channel import VoiceChannel  # noqa: PLC0415

    return VoiceChannel(record_duration=duration)


@app.command("listen")
def voice_listen(
    duration: Annotated[
        float,
        typer.Option("--duration", "-d", help="Recording duration in seconds."),
    ] = 5.0,
) -> None:
    """Record audio and print transcription."""
    try:
        ch = _make_voice_channel(duration)
    except ImportError as exc:
        _cli_error(str(exc))

    text = asyncio.run(ch.receive())  # type: ignore[union-attr]

    if text is None:
        typer.echo("No speech detected.")
    else:
        typer.echo(text)


@app.command("speak")
def voice_speak(
    text: Annotated[str, typer.Argument(help="Text to speak aloud.")],
) -> None:
    """Speak the given text via TTS."""
    try:
        ch = _make_voice_channel()
    except ImportError as exc:
        _cli_error(str(exc))

    asyncio.run(ch.send(text))  # type: ignore[union-attr]


@app.command("brainstorm")
def voice_brainstorm(
    duration: Annotated[
        float,
        typer.Option("--duration", "-d", help="Max session duration in seconds."),
    ] = 120.0,
    idle_timeout: Annotated[
        float,
        typer.Option(
            "--idle-timeout",
            "-i",
            help="End session after this many seconds of silence.",
        ),
    ] = 10.0,
) -> None:
    """Open-ended brainstorm session with live transcription."""
    try:
        ch = _make_voice_channel()
    except ImportError as exc:
        _cli_error(str(exc))

    def _on_update(text: str) -> None:
        typer.echo(f"\r{text}", nl=False)

    transcript = asyncio.run(
        ch.brainstorm(  # type: ignore[union-attr]
            duration=duration,
            idle_timeout=idle_timeout,
            on_update=_on_update,
        ),
    )
    typer.echo()  # newline after live updates
    typer.echo(transcript)
