"""The GitHub account a repository's writes are made by (TD-402): a project's setting, else the repository owner's.

The setting names a login, or ``repository-owner``: the account ``gh`` holds for the repository's owner, else
``maba-pag`` (D-01M5DW3X00RAVF1FZF19GBJ7KX).
"""

from __future__ import annotations

import re

REPOSITORY_OWNER = "repository-owner"
FALLBACK = "maba-pag"
LOGIN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,38}")  # GitHub's logins; enterprise-managed ones hold an underscore
