from __future__ import annotations

import re
from datetime import timedelta

from owlbear_kanban.errors import ConfigError

_DURATION_RE = re.compile(r"^(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?$")


def _parse_duration(s: str) -> timedelta:
    """Parse a duration string like '1h', '30m', '2h30m', '30s', '2d'."""
    m = _DURATION_RE.match(s.strip())
    if not m or not any(m.groups()):
        raise ConfigError(
            code="ERR_INVALID_CLAIM_TIMEOUT",
            user_message=(f"Invalid claim_timeout format: {s!r} - expected e.g. '1h', '30m', '2h30m', '30s', '2d'"),
        )
    days = int(m.group(1) or 0)
    hours = int(m.group(2) or 0)
    minutes = int(m.group(3) or 0)
    seconds = int(m.group(4) or 0)
    return timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
