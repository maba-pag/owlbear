"""Merge approval owner: one Cockpit approval sends one ``sha``-fenced request (N05 D5, D14, D16, 1.12)."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from owlbear_delivery.application_models import PortfolioApplicationError
from owlbear_delivery.delivery_runtime import DeliveryAcceptanceAttentionReason, DeliveryAcceptanceWaitingError
from owlbear_delivery.merge_approval import (
    ApproveChangeMerge,
    MergeApprovalResult,
    MergeAttemptRecord,
    MergeAttemptState,
    MergeAttemptStore,
    MergeRace,
    approval_id,
    new_merge_attempt,
    settle_merge_attempt,
)
from owlbear_delivery.merge_offer import MergeBlockReason
from owlbear_delivery.publication_provider import (
    PublicationMergeProvider,
    PublicationMergeRequestResult,
    PublicationProviderError,
    merge_request_body,
)
from owlbear_delivery.storage_io import atomic_write, locked_roots

if TYPE_CHECKING:
    from owlbear_delivery.delivery_runtime import DeliveryRuntime
    from owlbear_delivery.draft_pull_request import PublicationPullRequestObservationReceipt
    from owlbear_delivery.merge_offer import MergeOffer
    from owlbear_delivery.work_items import DeliveryReadiness

ERR_MERGE_IN_PROGRESS = "ERR_DELIVERY_MERGE_IN_PROGRESS"
ERR_MERGE_OFFER_STALE = "ERR_DELIVERY_MERGE_OFFER_STALE"
ERR_MERGE_UNAVAILABLE = "ERR_DELIVERY_MERGE_UNAVAILABLE"
_RACE_DIAGNOSTICS = {
    MergeRace.TARGET_ADVANCED: "target-advanced-during-merge",
    MergeRace.SCOPE_CHANGED: "scope-changed-during-merge",
}


class DeliveryMergeError(PortfolioApplicationError):
    """Typed merge refusal; ``readiness`` carries the fresh offer or block of a stale or unavailable offer."""

    def __init__(self, code: str, message: str, *, readiness: DeliveryReadiness | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.readiness = readiness


class _MergeMixin:
    """Approve-and-execute owner, owner fence and acceptance-path settlement."""

    def approve_merge(self, request: ApproveChangeMerge) -> MergeApprovalResult:
        """Approve one exact offer and send its single request; only Cockpit's HTTP route calls this (D14)."""
        change_id = request.change_id
        runtime = self._runtime(change_id, for_mutation=True)
        store = MergeAttemptStore(self._target_root, change_id)
        with locked_roots((self._checkpoint_lock_root(change_id),)):
            existing = store.read(approval_id(request.offer_id, request.submission_id))
            if existing is not None:
                return MergeApprovalResult(attempt=existing)
            self._require_no_merge_in_flight(change_id)
            offer, provider = self._fresh_merge_offer(runtime, request.offer_id)
            attempt = store.write(new_merge_attempt(request, offer, self._clock()), expected=None)
            attempt = self._send_merge_request(store, attempt, provider)
        completion_id = None
        if attempt.state is MergeAttemptState.MERGED and attempt.race is MergeRace.NONE:
            completion_id = self._complete_after_merge(change_id)
        return MergeApprovalResult(attempt=attempt, completion_id=completion_id)

    def _require_no_merge_in_flight(self, change_id: str) -> None:
        """Refuse before any effect while one approval's request is unsettled (I11, 1.12)."""
        if MergeAttemptStore(self._target_root, change_id).nonterminal() is not None:
            message = "a merge request for this Change is not settled yet (merge-in-progress)"
            raise DeliveryMergeError(ERR_MERGE_IN_PROGRESS, message)

    def _fresh_merge_offer(
        self, runtime: DeliveryRuntime, offer_id: str
    ) -> tuple[MergeOffer, PublicationMergeProvider]:
        """Recompute readiness from fresh provider reads; the offer must equal the one the user saw (I1, I9)."""
        change_id = runtime.contract.change_id
        publisher = self._draft_pull_request_publisher
        provider = publisher.provider if publisher is not None else None
        if not isinstance(provider, PublicationMergeProvider):
            message = "Delivery cannot merge through this provider; merge in GitHub"
            raise DeliveryMergeError(ERR_MERGE_UNAVAILABLE, message)
        self._publication_observation_cache.pop(change_id, None)
        self._merge_facts_cache.pop(change_id, None)
        snapshot = self._delivery_snapshot(runtime)
        readiness = self._selected_change_card(snapshot, self._read_projector(snapshot).group_view().items).readiness
        block = readiness.merge_block if readiness is not None else None
        observed = self._publication_observation_cache.get(change_id)
        # A read observation that no longer binds the published head is a changed offer, not an outage.
        head_moved = observed is not None and observed[2] is None
        if readiness is None or (
            not head_moved
            and (
                readiness.reason_code == "provider-unavailable"
                or (block is not None and block.reason is MergeBlockReason.CAPABILITY_UNAVAILABLE)
            )
        ):
            message = "the merge offer cannot be verified with GitHub right now"
            raise DeliveryMergeError(ERR_MERGE_UNAVAILABLE, message, readiness=readiness)
        offer = readiness.merge_offer
        if readiness.reason_code != "merge-approval-required" or offer is None or offer.offer_id != offer_id:
            message = "the merge offer changed since it was shown; review the current offer"
            raise DeliveryMergeError(ERR_MERGE_OFFER_STALE, message, readiness=readiness)
        return offer, provider

    def _send_merge_request(
        self,
        store: MergeAttemptStore,
        attempt: MergeAttemptRecord,
        provider: PublicationMergeProvider,
    ) -> MergeAttemptRecord:
        """Send the one request; ``released`` is durable before the launcher's token (D16)."""
        current = [attempt]

        def release(group_id: int, started_at: str) -> None:
            released = current[0].model_copy(
                update={
                    "state": MergeAttemptState.RELEASED,
                    "released_at": self._clock(),
                    "group_id": group_id,
                    "group_started_at": started_at,
                }
            )
            current[0] = store.write(released, expected=current[0])

        request = attempt.request()
        with tempfile.TemporaryDirectory(prefix="owlbear-merge-") as directory:
            body_path = Path(directory) / "merge-body.json"
            atomic_write(body_path, merge_request_body(request).decode())
            try:
                result = provider.request_merge(request, body_path=body_path, release=release)
            except Exception:
                self._settle_after_request(store, current[0], provider, None)
                raise
        return self._settle_after_request(store, current[0], provider, result)

    @staticmethod
    def _settle_after_request(
        store: MergeAttemptStore,
        attempt: MergeAttemptRecord,
        provider: PublicationMergeProvider,
        result: PublicationMergeRequestResult | None,
    ) -> MergeAttemptRecord:
        try:
            evidence = provider.read_merge_evidence(attempt.repository, attempt.number)
        except OSError, PublicationProviderError, RuntimeError, subprocess.SubprocessError, ValueError:
            evidence = None
        settled = settle_merge_attempt(attempt, evidence, result)
        return attempt if settled == attempt else store.write(settled, expected=attempt)

    def _complete_after_merge(self, change_id: str) -> str | None:
        """Observe acceptance once after a merged response; later reads complete when this one cannot."""
        try:
            return self.observe_acceptance(change_id).completion_id
        except DeliveryAcceptanceWaitingError, PortfolioApplicationError, PublicationProviderError:
            return None

    def _settle_merge_for_acceptance(self, change_id: str) -> None:
        """Settle an open attempt from one fresh read before acceptance reads or classifies anything (D6)."""
        store = MergeAttemptStore(self._target_root, change_id)
        attempt = store.nonterminal()
        publisher = self._draft_pull_request_publisher
        provider = publisher.provider if publisher is not None else None
        if attempt is None or not isinstance(provider, PublicationMergeProvider):
            return
        evidence = provider.read_merge_evidence(attempt.repository, attempt.number)
        result = None
        if (
            attempt.request_id is not None
            and evidence.state == "open"
            and not evidence.merged
            and evidence.head_sha == attempt.head_sha
        ):
            result = provider.read_merge_request(attempt.repository, attempt.number, attempt.request_id)
        settled = settle_merge_attempt(attempt, evidence, result)
        if settled != attempt:
            store.write(settled, expected=attempt)

    def _refuse_raced_merge(
        self,
        change_id: str,
        runtime: DeliveryRuntime,
        observation: PublicationPullRequestObservationReceipt,
    ) -> None:
        """A merge at another target or scope is acceptance attention, never completion (I4, Q4)."""
        raced = MergeAttemptStore(self._target_root, change_id).raced()
        if raced is None or raced.race is None:
            return
        runtime.capture_acceptance_attention(
            observation,
            (f"{_RACE_DIAGNOSTICS[raced.race]}:{raced.approval_id}",),
            reason=DeliveryAcceptanceAttentionReason.IDENTITY_MISMATCH,
        )
        self._publish_attention_best_effort(change_id, runtime, f"acceptance-attention-{observation.observation_id}")
        message = "the merge ran after the approved target or scope changed; it is not attributed to the proof"
        raise PortfolioApplicationError(message)


__all__ = [
    "ERR_MERGE_IN_PROGRESS",
    "ERR_MERGE_OFFER_STALE",
    "ERR_MERGE_UNAVAILABLE",
    "DeliveryMergeError",
]
