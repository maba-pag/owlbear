"""Browser configuration model (re-exported from owlbear.config).

:class:`BrowserConfig` is defined in ``owlbear.config`` to keep that module
a leaf node with no dependency on the tools layer.  This module re-exports
it so that existing imports from ``owlbear.tools.browser.config`` continue
to work unchanged.
"""

from __future__ import annotations

from owlbear.config import BrowserConfig

__all__ = ["BrowserConfig"]
