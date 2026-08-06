"""RED tests — guidance text update across all emission points (#1183).

AC5 coverage (td:1):
- `_DR_REQUIRED_MSG` in guidance.py equals the new canonical text
- `AgentView._BLOCK_AR_HINT` in engine.py equals the new canonical text
- h-delivery-mcp/SKILL.md agent-obligation prose references create_dr tool, not scribe agent

All tests must FAIL (RED phase) — current code still has old text.
"""

from __future__ import annotations

import pathlib

_REPO_ROOT = pathlib.Path(__file__).parent.parent

# The new canonical guidance text per AC5.
_NEW_DR_MSG = (
    "⚠️ ACTION REQUIRED: Create a Decision Request via the create_dr tool."
    " Blocks without a DR are invisible to the pipeline."
)
