"""Resolve current accepted dependencies with causal closure coverage."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from functools import cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from owlbear_kanban.change import ChangeRevision
    from owlbear_kanban.jobs import JobRecord
    from owlbear_kanban.receipt import ImpactClosure, ReceiptStore, RepositoryHistory


class AcceptedDependencyStatus(StrEnum):
    """Classify one requested node's acceptance state."""

    CURRENT = "current"
    NOT_YET_ACCEPTED = "not-yet-accepted"
    INVALID_EXISTING = "invalid-existing"
    AMBIGUOUS_CURRENT = "ambiguous-current"


@dataclass(frozen=True)
class ProspectiveAcceptance:
    """Describe an acceptance participating in the current transaction."""

    job: JobRecord
    impact_closure: ImpactClosure


@dataclass(frozen=True)
class AcceptedDependency:
    """Resolve one node to its current acceptance or stable failure class."""

    node_id: str
    status: AcceptedDependencyStatus
    job: JobRecord | None = None
    impact_closure: ImpactClosure | None = None

    @property
    def current(self) -> bool:
        """Return whether this node has one current acceptance."""
        return self.status is AcceptedDependencyStatus.CURRENT


@dataclass(frozen=True)
class AcceptedDependencySet:
    """Retain requested accepted dependencies in caller-supplied order."""

    entries: tuple[AcceptedDependency, ...]

    @property
    def current_jobs(self) -> tuple[JobRecord, ...]:
        """Return current acceptance jobs in caller-supplied order."""
        return tuple(entry.job for entry in self.entries if entry.current and entry.job is not None)


def resolve_accepted_dependencies(  # noqa: C901, PLR0913, PLR0917
    revision: ChangeRevision,
    accept_jobs: Iterable[JobRecord],
    receipts: ReceiptStore,
    history: RepositoryHistory,
    candidate_revision: str,
    node_ids: Sequence[str],
    *,
    prospective: ProspectiveAcceptance | None = None,
) -> AcceptedDependencySet:
    """Resolve an accepted set while allowing only causal full-closure coverage."""
    requested = tuple(node_ids)
    nodes = {node.id: node for node in revision.graph.nodes}
    candidates: dict[str, list[JobRecord]] = {node_id: [] for node_id in requested}
    for job in accept_jobs:
        if (
            job.kind == "accept"
            and job.delivery_digest == revision.delivery_digest
            and job.target_node_id in candidates
        ):
            candidates[job.target_node_id].append(job)

    @cache
    def causally_depends_on(descendant_id: str, ancestor_id: str) -> bool:
        dependencies = nodes[descendant_id].dependencies
        return ancestor_id in dependencies or any(
            causally_depends_on(dependency_id, ancestor_id) for dependency_id in dependencies
        )

    resolved: dict[str, AcceptedDependency] = {}

    def resolve(node_id: str) -> AcceptedDependency:  # noqa: C901, PLR0912
        existing = resolved.get(node_id)
        if existing is not None:
            return existing
        descendants = tuple(
            resolve(descendant_id)
            for descendant_id in requested
            if descendant_id != node_id and causally_depends_on(descendant_id, node_id)
        )
        if prospective is not None and prospective.job.target_node_id == node_id:
            result = AcceptedDependency(
                node_id=node_id,
                status=AcceptedDependencyStatus.CURRENT,
                job=prospective.job,
                impact_closure=prospective.impact_closure,
            )
            resolved[node_id] = result
            return result

        current: list[AcceptedDependency] = []
        for job in candidates[node_id]:
            if job.receipt_id is None:
                continue
            validity = receipts.evaluate_currentness(job.receipt_id, history, candidate_revision)
            if not validity.current:
                for descendant in descendants:
                    if not descendant.current or descendant.impact_closure is None:
                        continue
                    validity = receipts.evaluate_currentness(
                        job.receipt_id,
                        history,
                        candidate_revision,
                        successor_closure=descendant.impact_closure,
                    )
                    if validity.current:
                        break
            receipt = receipts.read(job.receipt_id).receipt if validity.current else None
            if receipt is not None and receipt.impact_closure is not None:
                current.append(
                    AcceptedDependency(
                        node_id=node_id,
                        status=AcceptedDependencyStatus.CURRENT,
                        job=job,
                        impact_closure=receipt.impact_closure,
                    )
                )

        if len(current) == 1:
            result = current[0]
        elif len(current) > 1:
            result = AcceptedDependency(node_id=node_id, status=AcceptedDependencyStatus.AMBIGUOUS_CURRENT)
        elif candidates[node_id]:
            result = AcceptedDependency(node_id=node_id, status=AcceptedDependencyStatus.INVALID_EXISTING)
        else:
            result = AcceptedDependency(node_id=node_id, status=AcceptedDependencyStatus.NOT_YET_ACCEPTED)
        resolved[node_id] = result
        return result

    return AcceptedDependencySet(entries=tuple(resolve(node_id) for node_id in requested))
