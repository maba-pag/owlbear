"""The machine host's own environment (TD-242): no credential or repository selector leaks into a project.

The ``owlbear`` command drops them before anything else, so registration probes and the host it starts see the
same environment. Transport settings stay: ``SSH_AUTH_SOCK``, ``GIT_SSH`` and ``GIT_SSH_COMMAND`` are the
owner's, not a project's; a project that needs its own SSH identity sets ``core.sshCommand`` in its Git config.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import MutableMapping

DROPPED = frozenset(
    {
        "GH_TOKEN",
        "GITHUB_TOKEN",
        "GH_ENTERPRISE_TOKEN",
        "GITHUB_ENTERPRISE_TOKEN",
        "GH_HOST",
        "GH_REPO",
        "GH_CONFIG_DIR",
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_COMMON_DIR",
        "GIT_INDEX_FILE",
        "GIT_OBJECT_DIRECTORY",
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    }
)
PREFIX = "GIT_CONFIG"  # GIT_CONFIG, GIT_CONFIG_GLOBAL, GIT_CONFIG_COUNT, GIT_CONFIG_KEY_0, ...


def scrub(env: MutableMapping[str, str] | None = None) -> list[str]:
    """Drop the selectors from *env* (this process's environment by default); return the dropped names."""
    env = os.environ if env is None else env
    names = sorted(n for n in env if n in DROPPED or n.startswith(PREFIX))
    for name in names:
        del env[name]
    return names
