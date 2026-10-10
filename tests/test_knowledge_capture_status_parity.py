"""Keep Knowledge capture status literals aligned with Browser acquisition outcomes."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import get_args

from owlbear_browser import contract as browser_contract
from owlbear_knowledge_mcp._helpers import _redact_capture_url
from owlbear_knowledge_mcp._types import CaptureFailureStatus


def test_knowledge_capture_failure_statuses_match_browser_contract() -> None:
    acquisition_status = browser_contract.AcquisitionStatus
    expected = {status.value for status in acquisition_status if status is not acquisition_status.SUCCESS} | {
        "tool_error"
    }
    assert set(get_args(CaptureFailureStatus)) == expected


def test_knowledge_capture_redaction_matches_browser_contract() -> None:
    sensitive_query_keys = browser_contract._SENSITIVE_QUERY_KEYS  # noqa: SLF001
    correlation_query_keys = browser_contract._CORRELATION_QUERY_KEYS  # noqa: SLF001
    query_names = sensitive_query_keys | correlation_query_keys | {"client_assertion", "x_api_token"}
    for name in sorted(query_names):
        sentinel = f"sentinel-{name}"
        variants = {
            name,
            name.upper(),
            "_".join(name),
            f"%{ord(name[0]):02X}{name[1:]}",
        }
        for query_name in sorted(variants):
            redacted = _redact_capture_url(
                f"https://fixture.example/p?{query_name}={sentinel}&view=full",
            )
            assert sentinel not in redacted, f"{query_name!r} retained a sensitive value"
            assert "view=full" in redacted, f"{query_name!r} redaction removed an ordinary parameter"


def test_knowledge_mcp_source_does_not_import_browser() -> None:
    source_root = Path(__file__).resolve().parents[1] / "serve" / "knowledge-mcp" / "src"
    assert source_root.is_dir()
    for source_path in source_root.rglob("*.py"):
        syntax_tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
        imported_modules = []
        for node in ast.walk(syntax_tree):
            if isinstance(node, ast.Import):
                imported_modules.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                imported_modules.append(node.module)
        browser_imports = [
            module
            for module in imported_modules
            if module == "owlbear_browser" or module.startswith("owlbear_browser.")
        ]
        assert not browser_imports, f"{source_path}: imports Browser modules {browser_imports}"
