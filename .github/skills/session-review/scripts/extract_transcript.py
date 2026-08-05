"""Extract bounded review evidence from a persisted Copilot JSONL transcript."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import deque
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

_SESSION_ID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F-]{27,}$")
_SENSITIVE_KEY = re.compile(
    r"(?:authorization|cookie|credential|password|passwd|secret|token|api[_-]?key|private[_-]?key)",
    re.IGNORECASE,
)
_TEXT_SECRETS = (
    re.compile(r"(?i)(authorization\s*[:=]\s*bearer\s+)[^\s,;]+"),
    re.compile(r"(?i)((?:api[_-]?key|password|passwd|secret|token)\s*[:=]\s*)[^\s,;]+"),
)
_REDACTED = "<redacted>"


@dataclass
class ToolEvent:
    """One transcript-visible tool invocation."""

    name: str
    tool_call_id: str
    timestamp: str
    success: bool | None = None
    arguments: object | None = None


@dataclass
class Turn:
    """One user-led conversation turn reconstructed from sequential events."""

    index: int
    timestamp: str
    user: str
    assistant: list[str] = field(default_factory=list)
    tools: list[ToolEvent] = field(default_factory=list)


@dataclass(frozen=True)
class ExtractConfig:
    """Content and disclosure controls for transcript extraction."""

    max_content_chars: int
    include_tools: bool
    include_tool_arguments: bool


@dataclass(frozen=True)
class TurnSelection:
    """Stable selectors applied to reconstructed one-based turns."""

    from_turn: int | None = None
    to_turn: int | None = None
    last_turns: int | None = None
    around: str | None = None
    context_turns: int = 1


def _redact_text(value: str) -> str:
    redacted = value
    for pattern in _TEXT_SECRETS:
        redacted = pattern.sub(rf"\1{_REDACTED}", redacted)
    return redacted


def _redact(value: object) -> object:
    if isinstance(value, Mapping):
        return {
            str(key): _REDACTED if _SENSITIVE_KEY.search(str(key)) else _redact(item) for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith(("{", "[")):
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                pass
            else:
                return _redact(parsed)
        return _redact_text(value)
    return value


def _bounded_text(value: object, limit: int) -> str:
    if not isinstance(value, str):
        value = json.dumps(value, ensure_ascii=True, sort_keys=True)
    redacted = _redact_text(value)
    if len(redacted) <= limit:
        return redacted
    omitted = len(redacted) - limit
    return f"{redacted[:limit]}\n<... {omitted} chars omitted>"


def _decode_arguments(value: object, limit: int) -> object:
    if not isinstance(value, str):
        redacted = _redact(value)
    else:
        try:
            redacted = _redact(json.loads(value))
        except json.JSONDecodeError:
            redacted = _redact_text(value)
    rendered = json.dumps(redacted, ensure_ascii=True, sort_keys=True)
    return redacted if len(rendered) <= limit else _bounded_text(rendered, limit)


def _event_lines(path: Path) -> Iterator[dict[str, Any]]:
    with path.open(encoding="utf-8") as transcript:
        for line_number, line in enumerate(transcript, start=1):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                message = f"invalid JSON at {path}:{line_number}: {exc.msg}"
                raise ValueError(message) from exc
            if isinstance(event, dict):
                yield event


def extract_turns(
    path: Path,
    config: ExtractConfig,
    *,
    retain_last: int | None = None,
) -> tuple[dict[str, object], list[Turn]]:
    """Stream *path* and return session metadata plus bounded user-led turns."""
    metadata: dict[str, object] = {"transcript": str(path)}
    retained: list[Turn] | deque[Turn] = deque(maxlen=retain_last) if retain_last is not None else []
    current: Turn | None = None
    tools: dict[str, ToolEvent] = {}
    turn_count = 0

    for event in _event_lines(path):
        event_type = event.get("type")
        timestamp = str(event.get("timestamp", ""))
        data = event.get("data")
        if not isinstance(data, dict):
            data = {}

        if event_type == "session.start":
            _update_metadata(metadata, data)
            continue

        if event_type == "user.message":
            turn_count += 1
            current = _new_turn(turn_count, timestamp, data, config)
            retained.append(current)
            tools = {}
            continue

        if current is None:
            continue
        _apply_turn_event(event, timestamp, current, tools, config)

    metadata["turn_count"] = turn_count
    return metadata, list(retained)


def _update_metadata(metadata: dict[str, object], data: Mapping[str, object]) -> None:
    for key in ("sessionId", "startTime", "producer", "version", "vscodeVersion", "copilotVersion"):
        if key in data:
            metadata[key] = data[key]


def _new_turn(index: int, timestamp: str, data: Mapping[str, object], config: ExtractConfig) -> Turn:
    return Turn(
        index=index,
        timestamp=timestamp,
        user=_bounded_text(data.get("content", ""), config.max_content_chars),
    )


def _apply_turn_event(
    event: Mapping[str, object],
    timestamp: str,
    turn: Turn,
    tools: dict[str, ToolEvent],
    config: ExtractConfig,
) -> None:
    event_type = event.get("type")
    data = event.get("data")
    if not isinstance(data, dict):
        return
    if event_type == "assistant.message":
        _append_assistant_message(turn, tools, data, timestamp, config)
    elif event_type == "tool.execution_start" and config.include_tools:
        _append_tool(turn, tools, data, timestamp, config)
    elif event_type == "tool.execution_complete" and config.include_tools:
        _complete_tool(tools, data)


def _append_assistant_message(
    turn: Turn,
    tools: dict[str, ToolEvent],
    data: Mapping[str, object],
    timestamp: str,
    config: ExtractConfig,
) -> None:
    content = data.get("content")
    if isinstance(content, str) and content:
        turn.assistant.append(_bounded_text(content, config.max_content_chars))
    if not config.include_tools:
        return
    requests = data.get("toolRequests")
    if isinstance(requests, list):
        for request in requests:
            if isinstance(request, dict):
                _append_tool(turn, tools, request, timestamp, config)


def _complete_tool(tools: Mapping[str, ToolEvent], data: Mapping[str, object]) -> None:
    tool_call_id = str(data.get("toolCallId", ""))
    tool = tools.get(tool_call_id)
    if tool is None:
        return
    success = data.get("success")
    tool.success = success if isinstance(success, bool) else None


def _append_tool(
    turn: Turn,
    tools: dict[str, ToolEvent],
    data: Mapping[str, object],
    timestamp: str,
    config: ExtractConfig,
) -> None:
    tool_call_id = str(data.get("toolCallId", ""))
    if not tool_call_id or tool_call_id in tools:
        return
    name = str(data.get("toolName") or data.get("name") or "unknown")
    arguments = (
        _decode_arguments(data.get("arguments"), config.max_content_chars) if config.include_tool_arguments else None
    )
    tool = ToolEvent(name=name, tool_call_id=tool_call_id, timestamp=timestamp, arguments=arguments)
    tools[tool_call_id] = tool
    turn.tools.append(tool)


def select_turns(turns: Sequence[Turn], selection: TurnSelection) -> list[Turn]:
    """Select a stable bounded subset from reconstructed turns."""
    selected = list(turns)
    if selection.from_turn is not None:
        selected = [turn for turn in selected if turn.index >= selection.from_turn]
    if selection.to_turn is not None:
        selected = [turn for turn in selected if turn.index <= selection.to_turn]
    if selection.around:
        needle = selection.around.casefold()
        matching = {turn.index for turn in selected if needle in _searchable_turn(turn).casefold()}
        included = {
            index
            for match in matching
            for index in range(
                max(1, match - selection.context_turns),
                match + selection.context_turns + 1,
            )
        }
        selected = [turn for turn in selected if turn.index in included]
    if selection.last_turns is not None:
        selected = selected[-selection.last_turns :]
    return selected


def _searchable_turn(turn: Turn) -> str:
    tool_content = " ".join(
        f"{tool.name} {json.dumps(tool.arguments, ensure_ascii=True) if tool.arguments is not None else ''}"
        for tool in turn.tools
    )
    return " ".join((turn.user, *turn.assistant, tool_content))


def render_json(metadata: Mapping[str, object], turns: Iterable[Turn]) -> str:
    """Render extracted evidence as structured JSON."""
    payload = {
        "session": dict(metadata),
        "evidence_limit": "Tool completion records expose success but not result bodies.",
        "turns": [asdict(turn) for turn in turns],
    }
    return json.dumps(payload, ensure_ascii=True, indent=2)


def render_markdown(metadata: Mapping[str, object], turns: Iterable[Turn]) -> str:
    """Render extracted evidence as compact review Markdown."""
    lines = [
        "# Transcript Evidence",
        "",
        f"- Session: {metadata.get('sessionId', 'unknown')}",
        f"- Transcript: {metadata['transcript']}",
        f"- Total turns: {metadata['turn_count']}",
        "- Evidence limit: Tool completion records expose success but not result bodies.",
    ]
    for turn in turns:
        lines.extend(("", f"## Turn {turn.index}", "", f"**User ({turn.timestamp})**", "", turn.user))
        for message in turn.assistant:
            lines.extend(("", "**Assistant**", "", message))
        if turn.tools:
            lines.extend(("", "**Tools**", ""))
            for tool in turn.tools:
                status = "success" if tool.success is True else "failed" if tool.success is False else "unknown"
                lines.append(f"- `{tool.name}` ({status}) at {tool.timestamp}")
                if tool.arguments is not None:
                    rendered = json.dumps(tool.arguments, ensure_ascii=True, sort_keys=True)
                    lines.append(f"  Arguments: `{rendered}`")
    return "\n".join(lines)


def transcript_roots() -> tuple[Path, ...]:
    """Return existing VS Code workspace-storage roots for this platform."""
    candidates: list[Path] = []
    override = os.environ.get("VSCODE_COPILOT_TRANSCRIPTS_ROOT")
    if override:
        candidates.append(Path(override).expanduser())
    home = Path.home()
    candidates.extend(
        (
            home / "Library/Application Support/Code/User/workspaceStorage",
            home / ".config/Code/User/workspaceStorage",
        )
    )
    appdata = os.environ.get("APPDATA")
    if appdata:
        candidates.append(Path(appdata) / "Code/User/workspaceStorage")
    return tuple(dict.fromkeys(path for path in candidates if path.is_dir()))


def locate_transcript(session_id: str, roots: Sequence[Path] | None = None) -> Path:
    """Locate one exact transcript without recursively scanning unrelated files."""
    if not _SESSION_ID.fullmatch(session_id):
        message = "session ID must be a UUID-like identifier"
        raise ValueError(message)
    matches = [
        candidate
        for root in roots or transcript_roots()
        for candidate in root.glob(f"*/GitHub.copilot-chat/transcripts/{session_id}.jsonl")
    ]
    if not matches:
        message = f"transcript not found for session {session_id}"
        raise FileNotFoundError(message)
    if len(matches) > 1:
        rendered = ", ".join(str(path) for path in matches)
        message = f"multiple transcripts found for session {session_id}: {rendered}"
        raise ValueError(message)
    return matches[0]


def _positive(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        message = "must be at least 1"
        raise argparse.ArgumentTypeError(message)
    return parsed


def _nonnegative(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        message = "must be nonnegative"
        raise argparse.ArgumentTypeError(message)
    return parsed


def parser() -> argparse.ArgumentParser:
    """Build the transcript-extractor command parser."""
    command = argparse.ArgumentParser(description=__doc__)
    source = command.add_mutually_exclusive_group(required=True)
    source.add_argument("--session-id", help="Exact Copilot session ID to locate")
    source.add_argument("--transcript", type=Path, help="Explicit transcript JSONL path")
    command.add_argument("--last-turns", type=_positive, help="Keep only the last N selected turns")
    command.add_argument("--from-turn", type=_positive, help="First one-based turn to include")
    command.add_argument("--to-turn", type=_positive, help="Last one-based turn to include")
    command.add_argument("--around", help="Select turns containing this case-insensitive text")
    command.add_argument("--context-turns", type=_nonnegative, default=1, help="Turns around each text match")
    command.add_argument("--include-tools", action="store_true", help="Include tool names and completion status")
    command.add_argument(
        "--include-tool-arguments",
        action="store_true",
        help="Include redacted tool arguments; implies --include-tools",
    )
    command.add_argument("--max-content-chars", type=_positive, default=4000, help="Per-message content limit")
    command.add_argument("--format", choices=("json", "markdown"), default="json")
    return command


def main(argv: Sequence[str] | None = None) -> int:
    """Run the bounded transcript extraction command."""
    args = parser().parse_args(argv)
    if args.from_turn is not None and args.to_turn is not None and args.from_turn > args.to_turn:
        parser().error("--from-turn cannot exceed --to-turn")
    try:
        path = args.transcript or locate_transcript(args.session_id)
        _require_file(path)
        config = ExtractConfig(
            max_content_chars=args.max_content_chars,
            include_tools=args.include_tools or args.include_tool_arguments,
            include_tool_arguments=args.include_tool_arguments,
        )
        retain_last = (
            args.last_turns
            if args.last_turns is not None and args.from_turn is None and args.to_turn is None and args.around is None
            else None
        )
        metadata, turns = extract_turns(path, config, retain_last=retain_last)
        selection = TurnSelection(
            from_turn=args.from_turn,
            to_turn=args.to_turn,
            last_turns=args.last_turns,
            around=args.around,
            context_turns=args.context_turns,
        )
        selected = select_turns(turns, selection)
    except (FileNotFoundError, OSError, ValueError) as exc:
        sys.stderr.write(f"extract-transcript: {exc}\n")
        return 1
    output = render_markdown(metadata, selected) if args.format == "markdown" else render_json(metadata, selected)
    sys.stdout.write(f"{output}\n")
    return 0


def _require_file(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(path)


if __name__ == "__main__":
    raise SystemExit(main())
