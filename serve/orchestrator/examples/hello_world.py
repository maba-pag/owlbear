"""ACP hello-world: spawn Copilot CLI as ACP agent, send one prompt, print response."""

from __future__ import annotations

import asyncio
import contextlib
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Any

from acp import (
    PROTOCOL_VERSION,
    Client,
    RequestError,
    RequestPermissionResponse,
    connect_to_agent,
    text_block,
)
from acp.schema import AgentMessageChunk, DeniedOutcome

if TYPE_CHECKING:
    from acp.client.connection import ClientSideConnection


class HelloWorldClient(Client):
    """Minimal ACP client: streamed text to stdout, all fs/terminal ops stubbed."""

    def on_connect(self, _conn: Any) -> None:  # noqa: ANN401
        pass

    async def session_update(
        self, _session_id: str, update: Any, **_kwargs: object
    ) -> None:  # noqa: ANN401
        if isinstance(update, AgentMessageChunk) and update.content.type == "text":
            print(update.content.text, end="", flush=True)

    async def request_permission(
        self,
        _options: object,
        _session_id: str,
        _tool_call: object,
        **_kwargs: object,
    ) -> RequestPermissionResponse:
        return RequestPermissionResponse(outcome=DeniedOutcome(outcome="cancelled"))

    async def write_text_file(self, **_kwargs: object) -> None:
        raise RequestError.method_not_found("write_text_file")

    async def read_text_file(self, **_kwargs: object) -> None:
        raise RequestError.method_not_found("read_text_file")

    async def create_terminal(self, **_kwargs: object) -> None:
        raise RequestError.method_not_found("create_terminal")

    async def terminal_output(self, **_kwargs: object) -> None:
        raise RequestError.method_not_found("terminal_output")

    async def release_terminal(self, **_kwargs: object) -> None:
        raise RequestError.method_not_found("release_terminal")

    async def wait_for_terminal_exit(self, **_kwargs: object) -> None:
        raise RequestError.method_not_found("wait_for_terminal_exit")

    async def kill_terminal(self, **_kwargs: object) -> None:
        raise RequestError.method_not_found("kill_terminal")

    async def ext_method(self, method: str, _params: dict[str, Any]) -> dict[str, Any]:
        raise RequestError.method_not_found(method)

    async def ext_notification(self, _method: str, _params: dict[str, Any]) -> None:
        pass


async def _shutdown(
    proc: asyncio.subprocess.Process, conn: ClientSideConnection
) -> None:
    """Close the ACP connection and terminate the subprocess gracefully."""
    with contextlib.suppress(Exception):
        await conn.close()
    with contextlib.suppress(ProcessLookupError):
        proc.terminate()
    try:
        await asyncio.wait_for(proc.wait(), timeout=5.0)
    except TimeoutError:
        with contextlib.suppress(ProcessLookupError):
            proc.kill()


async def main() -> None:
    """Spawn Copilot CLI, send one prompt, print the streamed response."""
    binary = shutil.which("copilot")
    if binary is None:
        msg = "Copilot CLI not found on PATH. Install with: gh extension install github/gh-copilot"
        raise FileNotFoundError(msg)

    proc = await asyncio.create_subprocess_exec(
        binary,
        "--acp",
        "--stdio",
        "--allow-all-tools",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
    )
    client = HelloWorldClient()
    conn = connect_to_agent(client, proc.stdin, proc.stdout)
    try:
        await conn.initialize(protocol_version=PROTOCOL_VERSION)
        session = await conn.new_session(cwd=str(Path.cwd()), mcp_servers=[])
        await conn.prompt(
            session_id=session.session_id,
            prompt=[text_block("Say 'Hello from Copilot ACP!' and nothing else.")],
        )
        print()
    finally:
        await _shutdown(proc, conn)


if __name__ == "__main__":
    asyncio.run(main())
