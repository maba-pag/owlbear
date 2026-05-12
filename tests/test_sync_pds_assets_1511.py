"""Smoke tests for #1511 — Cockpit: Implement PDS asset sync script.

One test per AC line (proof bundle: smoke). All must FAIL in the RED phase
because the script and updated assets do not yet exist.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
WEB_ROOT = REPO_ROOT / "serve" / "cockpit" / "web"
SCRIPT_PATH = WEB_ROOT / "scripts" / "sync-pds-assets.mjs"
COMPONENTS_DIR = WEB_ROOT / "public" / "porsche-design-system" / "components"
ICONS_DIR = WEB_ROOT / "public" / "porsche-design-system" / "icons"
PACKAGE_JSON = WEB_ROOT / "package.json"

# Known v4.1.0 core chunk filename — from research #1510 (cdn.ui.porsche.com).
_CORE_CHUNK_V41 = "porsche-design-system.v4.1.0.59dc31ee9c99f5a43eb5.js"

# Known stale v4.0.0 component chunk — present before sync, must be removed.
_STALE_V40_CHUNK = "porsche-design-system.accordion.352b95e194c521a42606.js"


class TestFromAC_SyncPdsAssetsScript:
    """Smoke tests derived from Revised AC (AC-1 through AC-8) of #1511."""

    def test_ac1_script_file_exists(self) -> None:
        """AC-1: serve/cockpit/web/scripts/sync-pds-assets.mjs exists."""
        assert SCRIPT_PATH.exists(), f"Script not found: {SCRIPT_PATH}"

    def test_ac2_script_is_valid_esm(self) -> None:
        """AC-2: Script is syntactically valid ESM (node --check exits 0)."""
        result = subprocess.run(
            ["node", "--check", str(SCRIPT_PATH)],
            capture_output=True,
            text=True,
            cwd=WEB_ROOT,
        )
        assert result.returncode == 0, f"node --check failed: {result.stderr}"

    def test_ac3_components_dir_has_v41_core_chunk(self) -> None:
        """AC-3: After sync, components/ contains the v4.1.0 core chunk."""
        core_chunk = COMPONENTS_DIR / _CORE_CHUNK_V41
        assert core_chunk.exists(), (
            f"v4.1.0 core chunk missing in {COMPONENTS_DIR}: {_CORE_CHUNK_V41}"
        )

    def test_ac4_icons_dir_has_290_svg_files(self) -> None:
        """AC-4: After sync, icons/ contains 290 .svg files."""
        svgs = list(ICONS_DIR.glob("*.svg"))
        assert len(svgs) == 290, f"Expected 290 SVGs in {ICONS_DIR}, found {len(svgs)}"

    def test_ac5_package_json_has_sync_pds_command(self) -> None:
        """AC-5: package.json scripts contains the sync:pds command."""
        pkg = json.loads(PACKAGE_JSON.read_text())
        scripts = pkg.get("scripts", {})
        assert "sync:pds" in scripts, (
            f"sync:pds not found in package.json scripts: {sorted(scripts)}"
        )

    def test_ac6_stale_v40_component_files_removed(self) -> None:
        """AC-6: After sync, stale v4.0.0 component chunk files are cleared."""
        stale = COMPONENTS_DIR / _STALE_V40_CHUNK
        assert not stale.exists(), (
            f"Stale v4.0.0 component file still present (not cleared): {stale}"
        )

    def test_ac7_correct_file_counts_after_sync(self) -> None:
        """AC-7: components/ has 59 v4.1.0 .js files; icons/ has 290 .svg files."""
        js_files = list(COMPONENTS_DIR.glob("*.js"))
        svg_files = list(ICONS_DIR.glob("*.svg"))
        core_v41_present = (COMPONENTS_DIR / _CORE_CHUNK_V41).exists()
        # Count must be 59 AND v4.1.0 core chunk present (distinguishes from v4.0.0 state).
        assert core_v41_present, (
            f"v4.1.0 core chunk missing — components/ may still have stale v4.0.0 files"
        )
        assert len(js_files) == 59, (
            f"Expected 59 .js files in components/, found {len(js_files)}"
        )
        assert len(svg_files) == 290, (
            f"Expected 290 .svg files, found {len(svg_files)}"
        )

    def test_ac8_exits_nonzero_with_descriptive_error_on_parse_failure(
        self, tmp_path: Path
    ) -> None:
        """AC-8: Script exits non-zero with descriptive error when parsing fails."""
        # Provide a syntactically valid but semantically empty index.mjs so the script
        # can read it but cannot extract the core chunk URL.
        esm_dir = (
            tmp_path
            / "node_modules"
            / "@porsche-design-system"
            / "components-js"
            / "esm"
        )
        esm_dir.mkdir(parents=True)
        (esm_dir / "index.mjs").write_text("// empty — no chunk URL\nexport {};")
        result = subprocess.run(
            ["node", str(SCRIPT_PATH)],
            capture_output=True,
            text=True,
            cwd=str(tmp_path),
            env={**os.environ},
            timeout=30,
        )
        assert result.returncode != 0, (
            "Expected non-zero exit when chunk-map parsing fails"
        )
        error_out = result.stderr + result.stdout
        # Node's own "Cannot find module" error won't contain these domain terms.
        # The script must emit its own descriptive error mentioning the failure domain.
        assert any(
            kw in error_out.lower()
            for kw in ("cdn", "chunk-map", "chunk map", "index.mjs", "parse")
        ), f"Expected descriptive error message from script, got: {error_out[:300]!r}"

    @pytest.mark.api
    @pytest.mark.slow
    @pytest.mark.timeout(180)
    def test_ac_script_execution_creates_outputs_in_isolated_workspace(
        self, tmp_path: Path
    ) -> None:
        """Proof: executing the script creates 59 component files + 290 icons from scratch.

        Runs sync-pds-assets.mjs in an isolated tmpdir with node_modules symlinked from
        the real workspace. Starts from empty output dirs so pre-committed assets cannot
        mask a broken or no-op script. Requires CDN access — marked api/slow.
        """
        nm_link = tmp_path / "node_modules"
        nm_link.symlink_to(WEB_ROOT / "node_modules")
        (tmp_path / "public" / "porsche-design-system" / "components").mkdir(parents=True)
        (tmp_path / "public" / "porsche-design-system" / "icons").mkdir(parents=True)

        result = subprocess.run(
            ["node", str(SCRIPT_PATH)],
            capture_output=True,
            text=True,
            cwd=str(tmp_path),
            timeout=120,
        )
        assert result.returncode == 0, (
            f"Script failed in isolated workspace: {result.stderr}\n{result.stdout}"
        )

        out_components = tmp_path / "public" / "porsche-design-system" / "components"
        out_icons = tmp_path / "public" / "porsche-design-system" / "icons"
        js_files = list(out_components.glob("*.js"))
        svg_files = list(out_icons.glob("*.svg"))
        assert len(js_files) == 59, (
            f"Script produced {len(js_files)} .js files in isolated workspace (expected 59)"
        )
        assert len(svg_files) == 290, (
            f"Script produced {len(svg_files)} .svg files in isolated workspace (expected 290)"
        )

    def test_ac8_cdn_download_failure_returns_descriptive_error(
        self, tmp_path: Path
    ) -> None:
        """AC-8: Script exits non-zero with descriptive error when CDN download fails (HTTP 503).

        Uses a Node.js harness that stubs globalThis.fetch to return 503 before
        importing the script. The fetch mock is in place when main() runs so the
        core-chunk download fails without any real network traffic.
        """
        esm_dir = (
            tmp_path
            / "node_modules"
            / "@porsche-design-system"
            / "components-js"
            / "esm"
        )
        esm_dir.mkdir(parents=True)
        (esm_dir / "index.mjs").write_text(
            'cdn.url+"/porsche-design-system/components/'
            'porsche-design-system.v4.1.0.59dc31ee9c99f5a43eb5.js"'
        )
        script_js = json.dumps(str(SCRIPT_PATH))
        harness = tmp_path / "harness.mjs"
        harness.write_text(
            "globalThis.fetch = async () => "
            "({ ok: false, status: 503, text: async () => 'Service Unavailable' });\n"
            f"await import({script_js});\n"
        )
        result = subprocess.run(
            ["node", str(harness)],
            capture_output=True,
            text=True,
            cwd=str(tmp_path),
            env={**os.environ},
            timeout=30,
        )
        assert result.returncode != 0, "Expected non-zero exit when CDN returns HTTP 503"
        error_out = result.stderr + result.stdout
        assert any(
            kw in error_out.lower()
            for kw in ("cdn", "download", "http")
        ), f"Expected descriptive CDN-failure error, got: {error_out[:300]!r}"

    def test_ac8_chunk_map_parse_failure_returns_descriptive_error(
        self, tmp_path: Path
    ) -> None:
        """AC-8: Script exits non-zero with descriptive error when component chunk-map parse fails.

        Uses a Node.js harness that stubs globalThis.fetch to return HTTP 200 with
        content that has no .u=e=> component-map pattern. The script can download the
        core chunk successfully but parseComponentHashes must fail with a descriptive error.
        """
        esm_dir = (
            tmp_path
            / "node_modules"
            / "@porsche-design-system"
            / "components-js"
            / "esm"
        )
        esm_dir.mkdir(parents=True)
        (esm_dir / "index.mjs").write_text(
            'cdn.url+"/porsche-design-system/components/'
            'porsche-design-system.v4.1.0.59dc31ee9c99f5a43eb5.js"'
        )
        # Core chunk fetch succeeds (HTTP 200) but content lacks the .u=e=> chunk-map pattern.
        script_js = json.dumps(str(SCRIPT_PATH))
        harness = tmp_path / "harness.mjs"
        harness.write_text(
            "globalThis.fetch = async () => "
            "({ ok: true, status: 200, text: async () => '// no chunk-map pattern here' });\n"
            f"await import({script_js});\n"
        )
        result = subprocess.run(
            ["node", str(harness)],
            capture_output=True,
            text=True,
            cwd=str(tmp_path),
            env={**os.environ},
            timeout=30,
        )
        assert result.returncode != 0, "Expected non-zero exit when chunk-map parse fails"
        error_out = result.stderr + result.stdout
        assert any(
            kw in error_out.lower()
            for kw in ("chunk-map", "chunk map", "component chunk", "parse")
        ), f"Expected descriptive chunk-map error, got: {error_out[:300]!r}"
