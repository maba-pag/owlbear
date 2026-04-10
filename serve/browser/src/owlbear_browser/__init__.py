"""OwlBear browser package — authenticated web content extraction via Edge CDP."""

from owlbear_browser._errors import AuthenticationRequired, CDPConnectionError, EdgeNotFoundError
from owlbear_browser.cdp import CDPConnectionManager
from owlbear_browser.edge_launcher import EdgeCDPLauncher
from owlbear_browser.launcher import build_launch_args, find_edge_binary, launch_edge

resolve_edge_binary = find_edge_binary

__all__ = [
    "AuthenticationRequired",
    "CDPConnectionError",
    "CDPConnectionManager",
    "EdgeCDPLauncher",
    "EdgeNotFoundError",
    "build_launch_args",
    "find_edge_binary",
    "launch_edge",
    "resolve_edge_binary",
]
