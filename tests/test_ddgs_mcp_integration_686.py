"""Failing tests for task #686 — Add ddgs MCP server to VS Code config and agent tool allowlists.

AC contract under test:
  AC1: ddgs[mcp] added as a dependency in pyproject.toml dev group
  AC2: seed/.vscode/mcp.json configured with a ddgs MCP server entry (ddgs mcp command)
  AC3: researcher.agent.md tools list updated with 'ddgs/search_text' and 'ddgs/extract_content'
  AC4: ideator.agent.md tools list updated with 'ddgs/search_text'
  AC5: Smoke — ddgs[mcp] package is installed and minimum version is satisfied

All tests fail (RED phase) against current codebase because:
  - pyproject.toml dev group has no ddgs entry
  - seed/.vscode/mcp.json has no ddgs server entry
  - researcher.agent.md and ideator.agent.md tools lists have no ddgs/* entries
  - ddgs package is not installed in the project venv
"""

from __future__ import annotations

import importlib.metadata
import importlib.util
import json
import re
import subprocess
import tomllib
from pathlib import Path

ROOT = Path(__file__).parent.parent
SEED_MCP_JSON = ROOT / "seed" / ".vscode" / "mcp.json"
RESEARCHER_AGENT = ROOT / "share" / "agents" / "researcher.agent.md"
IDEATOR_AGENT = ROOT / "share" / "agents" / "ideator.agent.md"
PYPROJECT = ROOT / "pyproject.toml"


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _get_frontmatter(path: Path) -> str:
    """Return the YAML frontmatter block between the first pair of --- delimiters."""
    content = path.read_text(encoding="utf-8")
    match = re.search(r"\A---\n(.*?)\n---", content, re.DOTALL)
    if match is None:
        raise ValueError(f"No frontmatter found in {path}")
    return match.group(1)


def _parse_tools_list(frontmatter: str) -> list[str]:
    """Parse the tools inline list from agent frontmatter.

    Handles both same-line syntax (tools: [a, b]) and indented-next-line:
        tools:
          [a, b]
    """
    pattern = r"^tools:\s*(?:\n\s*)?\[(.+?)\]"
    match = re.search(pattern, frontmatter, re.MULTILINE | re.DOTALL)
    if match is None:
        return []
    raw = match.group(1)
    entries = [entry.strip().strip("'\"") for entry in raw.split(",")]
    return [e for e in entries if e]


# ---------------------------------------------------------------------------
# AC1 — ddgs[mcp] dependency in pyproject.toml dev group
# ---------------------------------------------------------------------------


class TestFromAC_DdgsDependency:
    """AC1: ddgs[mcp] must be present in [dependency-groups].dev in pyproject.toml."""

    def test_pyproject_dev_deps_contain_ddgs(self) -> None:
        """pyproject.toml [dependency-groups].dev must include a ddgs entry."""
        assert PYPROJECT.exists(), f"pyproject.toml not found at {PYPROJECT}"
        with PYPROJECT.open("rb") as fh:
            data = tomllib.load(fh)
        dev_deps: list[str] = data.get("dependency-groups", {}).get("dev", [])
        assert any("ddgs" in dep for dep in dev_deps), (
            f"'ddgs' not found in [dependency-groups].dev: {dev_deps}\n"
            "AC1 requires: add 'ddgs[mcp]>=9.13,<10' (or similar) to the dev dependency group."
        )

    def test_pyproject_ddgs_dep_has_mcp_extra(self) -> None:
        """The ddgs entry must declare the [mcp] extra for MCP server support."""
        with PYPROJECT.open("rb") as fh:
            data = tomllib.load(fh)
        dev_deps: list[str] = data.get("dependency-groups", {}).get("dev", [])
        ddgs_entries = [dep for dep in dev_deps if "ddgs" in dep]
        assert ddgs_entries, "No ddgs entry found in [dependency-groups].dev."
        assert any("[mcp]" in dep for dep in ddgs_entries), (
            f"ddgs entry(s) in dev deps missing [mcp] extra: {ddgs_entries}\n"
            "AC1 requires: 'ddgs[mcp]' — the mcp extra installs the MCP server support."
        )

    def test_pyproject_ddgs_dep_has_version_constraint(self) -> None:
        """The ddgs[mcp] dependency must have a version pin (not a bare package name)."""
        with PYPROJECT.open("rb") as fh:
            data = tomllib.load(fh)
        dev_deps: list[str] = data.get("dependency-groups", {}).get("dev", [])
        ddgs_entries = [dep for dep in dev_deps if "ddgs" in dep]
        assert ddgs_entries, "No ddgs entry found in [dependency-groups].dev."
        assert any(re.search(r"(>=|<=|==|~=|!=|>|<)", dep) for dep in ddgs_entries), (
            f"ddgs dep(s) carry no version constraint: {ddgs_entries}\n"
            "A version pin (e.g. >=9.13,<10) is required to prevent silent breakage on upgrades."
        )


# ---------------------------------------------------------------------------
# AC2 — seed/.vscode/mcp.json ddgs server entry
# ---------------------------------------------------------------------------


class TestFromAC_SeedMcpConfig:
    """AC2: seed/.vscode/mcp.json must have a ddgs stdio server entry invoking 'ddgs mcp'."""

    def test_seed_mcp_json_has_ddgs_server_key(self) -> None:
        """seed/.vscode/mcp.json servers must include a key containing 'ddgs'."""
        assert SEED_MCP_JSON.exists(), (
            f"seed/.vscode/mcp.json not found at {SEED_MCP_JSON}\n"
            "AC2 requires: add the ddgs server entry to the seed mcp.json template."
        )
        data = json.loads(SEED_MCP_JSON.read_text(encoding="utf-8"))
        servers: dict = data.get("servers", {})
        ddgs_keys = [k for k in servers if "ddgs" in k.lower()]
        assert ddgs_keys, (
            f"No 'ddgs' server key in seed/.vscode/mcp.json servers: {list(servers.keys())}\n"
            "AC2 requires: add a 'ddgs' stdio server entry to the seed mcp.json template."
        )

    def test_ddgs_mcp_server_is_stdio_type(self) -> None:
        """The ddgs server entry must be type: stdio (ddgs mcp is a stdio subprocess)."""
        assert SEED_MCP_JSON.exists(), f"seed/.vscode/mcp.json not found at {SEED_MCP_JSON}"
        data = json.loads(SEED_MCP_JSON.read_text(encoding="utf-8"))
        servers: dict = data.get("servers", {})
        ddgs_server = next((v for k, v in servers.items() if "ddgs" in k.lower()), None)
        assert ddgs_server is not None, "No ddgs server found in seed mcp.json."
        assert ddgs_server.get("type") == "stdio", (
            f"ddgs MCP server must be type 'stdio', got: {ddgs_server.get('type')!r}\n"
            "The ddgs mcp subcommand runs as a stdio subprocess, not an HTTP server."
        )

    def test_ddgs_mcp_server_args_contain_ddgs(self) -> None:
        """The ddgs server args must include 'ddgs' to invoke the ddgs CLI."""
        assert SEED_MCP_JSON.exists(), f"seed/.vscode/mcp.json not found at {SEED_MCP_JSON}"
        data = json.loads(SEED_MCP_JSON.read_text(encoding="utf-8"))
        servers: dict = data.get("servers", {})
        ddgs_server = next((v for k, v in servers.items() if "ddgs" in k.lower()), None)
        assert ddgs_server is not None, "No ddgs server found in seed mcp.json."
        args: list[str] = ddgs_server.get("args", [])
        assert "ddgs" in args, (
            f"ddgs server args must include 'ddgs': {args}\n"
            "Expected args pattern: ['run', ..., 'ddgs', 'mcp']"
        )

    def test_ddgs_mcp_server_args_ddgs_immediately_precedes_mcp(self) -> None:
        """In the args list, 'ddgs' must appear immediately before 'mcp' (correct CLI syntax)."""
        assert SEED_MCP_JSON.exists(), f"seed/.vscode/mcp.json not found at {SEED_MCP_JSON}"
        data = json.loads(SEED_MCP_JSON.read_text(encoding="utf-8"))
        servers: dict = data.get("servers", {})
        ddgs_server = next((v for k, v in servers.items() if "ddgs" in k.lower()), None)
        assert ddgs_server is not None, "No ddgs server found in seed mcp.json."
        args: list[str] = ddgs_server.get("args", [])
        assert "ddgs" in args, f"'ddgs' not found in args: {args}"
        ddgs_idx = args.index("ddgs")
        assert ddgs_idx + 1 < len(args), (
            f"'ddgs' is the last element in args with nothing after it — got: {args}\n"
            "The correct invocation requires 'mcp' to follow 'ddgs'."
        )
        assert args[ddgs_idx + 1] == "mcp", (
            f"'mcp' must immediately follow 'ddgs' in args — got: {args}\n"
            "The correct invocation is: `ddgs mcp` (CLI subcommand syntax)."
        )


# ---------------------------------------------------------------------------
# AC3 — researcher.agent.md tools list
# ---------------------------------------------------------------------------


class TestFromAC_ResearcherAgentTools:
    """AC3: researcher.agent.md tools list must include 'ddgs/search_text' and 'ddgs/extract_content'."""

    def test_researcher_tools_contain_ddgs_search_text(self) -> None:
        """AC3: researcher.agent.md tools list must include 'ddgs/search_text'."""
        assert RESEARCHER_AGENT.exists(), f"researcher.agent.md not found at {RESEARCHER_AGENT}"
        frontmatter = _get_frontmatter(RESEARCHER_AGENT)
        tools = _parse_tools_list(frontmatter)
        assert "ddgs/search_text" in tools, (
            f"'ddgs/search_text' not found in researcher.agent.md tools: {tools}\n"
            "AC3 requires: add 'ddgs/search_text' to the researcher agent tools list."
        )

    def test_researcher_tools_contain_ddgs_extract_content(self) -> None:
        """AC3: researcher.agent.md tools list must include 'ddgs/extract_content'."""
        assert RESEARCHER_AGENT.exists(), f"researcher.agent.md not found at {RESEARCHER_AGENT}"
        frontmatter = _get_frontmatter(RESEARCHER_AGENT)
        tools = _parse_tools_list(frontmatter)
        assert "ddgs/extract_content" in tools, (
            f"'ddgs/extract_content' not found in researcher.agent.md tools: {tools}\n"
            "AC3 requires: add 'ddgs/extract_content' to the researcher agent tools list."
        )

    def test_researcher_has_both_ddgs_tools_simultaneously(self) -> None:
        """AC3 boundary: both ddgs tools must be present at the same time — not just one."""
        assert RESEARCHER_AGENT.exists(), f"researcher.agent.md not found at {RESEARCHER_AGENT}"
        frontmatter = _get_frontmatter(RESEARCHER_AGENT)
        tools = _parse_tools_list(frontmatter)
        missing = {"ddgs/search_text", "ddgs/extract_content"} - set(tools)
        assert not missing, (
            f"Researcher agent is missing ddgs tool(s): {missing}\n"
            "AC3 requires both ddgs/search_text AND ddgs/extract_content for full web-research capability."
        )


# ---------------------------------------------------------------------------
# AC4 — ideator.agent.md tools list
# ---------------------------------------------------------------------------


class TestFromAC_IdeatorAgentTools:
    """AC4: ideator.agent.md tools list must include 'ddgs/search_text' only (not extract_content)."""

    def test_ideator_tools_contain_ddgs_search_text(self) -> None:
        """AC4: ideator.agent.md tools list must include 'ddgs/search_text'."""
        assert IDEATOR_AGENT.exists(), f"ideator.agent.md not found at {IDEATOR_AGENT}"
        frontmatter = _get_frontmatter(IDEATOR_AGENT)
        tools = _parse_tools_list(frontmatter)
        assert "ddgs/search_text" in tools, (
            f"'ddgs/search_text' not found in ideator.agent.md tools: {tools}\n"
            "AC4 requires: add 'ddgs/search_text' to the ideator agent tools list."
        )

    def test_ideator_tools_do_not_contain_ddgs_extract_content(self) -> None:
        """AC4 boundary: ideator must not receive ddgs/extract_content AND must have search_text."""
        assert IDEATOR_AGENT.exists(), f"ideator.agent.md not found at {IDEATOR_AGENT}"
        frontmatter = _get_frontmatter(IDEATOR_AGENT)
        tools = _parse_tools_list(frontmatter)
        # Failing condition: ddgs/search_text must be present first (not yet added).
        # This ensures the test is change-detecting: the whole tools block is unset.
        assert "ddgs/search_text" in tools, (
            "'ddgs/search_text' is absent from ideator.agent.md — "
            "AC4 must add search_text (and only search_text) to the ideator tools list."
        )
        assert "ddgs/extract_content" not in tools, (
            "'ddgs/extract_content' must NOT be in ideator.agent.md tools.\n"
            "Per AC4, ideator receives ddgs/search_text only; ddgs/extract_content is researcher-only."
        )


# ---------------------------------------------------------------------------
# AC5 — ddgs[mcp] smoke: package installed and minimum version met
# ---------------------------------------------------------------------------


class TestFromAC_DdgsMcpSmoke:
    """AC5: ddgs[mcp] package is installed in the project venv and meets the minimum version."""

    def test_ddgs_package_is_importable(self) -> None:
        """AC5: ddgs must be importable (confirms ddgs[mcp] was installed per AC1)."""
        spec = importlib.util.find_spec("ddgs")
        assert spec is not None, (
            "ddgs package is not importable — AC1 dependency has not been installed yet.\n"
            "Run: uv sync --group dev  (after adding ddgs[mcp] to pyproject.toml)"
        )

    def test_ddgs_installed_version_meets_minimum(self) -> None:
        """AC5: installed ddgs version must be >= 9.13 (the release that added MCP server support)."""
        spec = importlib.util.find_spec("ddgs")
        assert spec is not None, (
            "ddgs not installed; cannot check version. Install ddgs[mcp]>=9.13 first."
        )
        version_str = importlib.metadata.version("ddgs")
        parts = version_str.split(".")
        major, minor = int(parts[0]), int(parts[1])
        assert (major, minor) >= (9, 13), (
            f"ddgs {version_str} is below the required minimum 9.13.\n"
            "MCP server support was added in v9.13 — the dep pin must be >=9.13."
        )

    def test_ddgs_mcp_server_startup_responds_to_initialize(self) -> None:
        """AC5: ddgs MCP server must respond to a JSON-RPC 'initialize' request via stdio."""
        initialize_msg = (
            json.dumps({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "pytest-smoke", "version": "0.1"},
                },
            })
            + "\n"
        )
        result = subprocess.run(
            ["uv", "run", "ddgs", "mcp"],
            input=initialize_msg,
            capture_output=True,
            timeout=15,
            text=True,
        )
        assert result.stdout.strip(), (
            "ddgs MCP server produced no stdout in response to 'initialize' — "
            "AC5 requires the server to start and respond over stdio.  "
            f"exit={result.returncode}  stderr={result.stderr[:200]!r}"
        )
        first_line = result.stdout.strip().splitlines()[0]
        response = json.loads(first_line)
        assert response.get("jsonrpc") == "2.0", (
            f"Response must be JSON-RPC 2.0, got: {first_line!r}"
        )
        assert "result" in response, (
            f"'initialize' response must contain 'result', got: {first_line!r}"
        )

    def test_ddgs_mcp_server_tools_list_contains_search_text(self) -> None:
        """AC5: tools/list from the running ddgs MCP server must include 'search_text'."""
        msgs = "\n".join([
            json.dumps({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "pytest-smoke", "version": "0.1"},
                },
            }),
            json.dumps({
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
                "params": {},
            }),
            json.dumps({
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
                "params": {},
            }),
        ]) + "\n"
        result = subprocess.run(
            ["uv", "run", "ddgs", "mcp"],
            input=msgs,
            capture_output=True,
            timeout=15,
            text=True,
        )
        lines = [ln for ln in result.stdout.strip().splitlines() if ln.strip()]
        assert lines, (
            "ddgs MCP server produced no output — cannot verify tools.  "
            f"exit={result.returncode}  stderr={result.stderr[:200]!r}"
        )
        tool_names: list[str] = []
        for line in lines:
            try:
                msg = json.loads(line)
                result_data = msg.get("result", {})
                if "tools" in result_data:
                    tool_names = [t.get("name", "") for t in result_data["tools"]]
                    break
            except json.JSONDecodeError:
                continue
        assert "search_text" in tool_names, (
            f"'search_text' not found in ddgs MCP server tools: {tool_names}\n"
            "AC5 requires the live MCP server to expose the 'search_text' tool."
        )

    def test_ddgs_mcp_server_tools_list_contains_extract_content(self) -> None:
        """AC5: tools/list from the running ddgs MCP server must include 'extract_content'."""
        msgs = "\n".join([
            json.dumps({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "pytest-smoke", "version": "0.1"},
                },
            }),
            json.dumps({
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
                "params": {},
            }),
            json.dumps({
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
                "params": {},
            }),
        ]) + "\n"
        result = subprocess.run(
            ["uv", "run", "ddgs", "mcp"],
            input=msgs,
            capture_output=True,
            timeout=15,
            text=True,
        )
        lines = [ln for ln in result.stdout.strip().splitlines() if ln.strip()]
        assert lines, (
            "ddgs MCP server produced no output — cannot verify tools.  "
            f"exit={result.returncode}  stderr={result.stderr[:200]!r}"
        )
        tool_names: list[str] = []
        for line in lines:
            try:
                msg = json.loads(line)
                result_data = msg.get("result", {})
                if "tools" in result_data:
                    tool_names = [t.get("name", "") for t in result_data["tools"]]
                    break
            except json.JSONDecodeError:
                continue
        assert "extract_content" in tool_names, (
            f"'extract_content' not found in ddgs MCP server tools: {tool_names}\n"
            "AC5 requires the live MCP server to expose the 'extract_content' tool."
        )
