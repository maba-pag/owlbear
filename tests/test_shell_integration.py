"""Durable structural guard for Shell health badge integration.

Promoted from archived task #1162 during test curation.
"""

from __future__ import annotations

import pathlib


ROOT = pathlib.Path(__file__).parent.parent
SHELL_PATH = ROOT / "serve/cockpit/web/src/Shell.tsx"
TEST_PATH = ROOT / "serve/cockpit/web/src/__tests__/Shell_1162.test.tsx"

# Promoted from archived task #1162.
