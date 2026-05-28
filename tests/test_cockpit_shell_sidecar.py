"""Source-level shell and sidecar inspector regression tests."""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SHELL_TSX = _REPO_ROOT / "serve" / "cockpit" / "web" / "src" / "Shell.tsx"


