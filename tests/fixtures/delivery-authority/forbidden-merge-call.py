"""Application-module fixture: only an allowlisted owner may use ``provider.request_merge(...)``."""

from typing import Protocol


class MergeProvider(Protocol):
    def request_merge(self, request, *, body_path, release):
        """Declaration only; callers write ``provider.request_merge(request, body_path=..., release=...)``."""
        ...


class PortfolioApplication:
    def __init__(self, provider):
        self._provider = provider

    def approve_and_merge(self, request, body_path):
        return self._provider.request_merge(request, body_path=body_path, release=self._record_release)

    def merge_through_alias(self, provider, request, body_path):
        send = provider.request_merge
        return send(request, body_path=body_path, release=None)

    def merge_dynamically(self, provider, request, body_path):
        return getattr(provider, "request_merge")(request, body_path=body_path, release=None)  # noqa: B009


MERGED_AT_IMPORT = request_merge(None, body_path=None, release=None)  # noqa: F821
