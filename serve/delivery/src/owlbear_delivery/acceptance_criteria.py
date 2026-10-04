"""Stable acceptance-criterion identities and content versions derived from admitted contracts."""

from __future__ import annotations

import hashlib
import re
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from owlbear_delivery.target_contract import DeliveryContract

ACCEPTANCE_ID_PATTERN = r"^(?:AC-[0-9]{3}|OUT-[0-9]{3}\.[0-9]{2,3})$"
_AUTHORED_ITEM = re.compile(r"(AC-[0-9]{3}): (\S.*)", re.DOTALL)
_NEAR_MISS = re.compile(r"AC-[0-9]")


class _AcceptanceModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class DeliveryAcceptanceRef(_AcceptanceModel):
    """One exact acceptance criterion version that evidence or a confirmation names."""

    acceptance_id: str = Field(pattern=ACCEPTANCE_ID_PATTERN)
    acceptance_version: str = Field(pattern=r"^[0-9a-f]{64}$")


class DeliveryAcceptanceCriterion(_AcceptanceModel):
    """One admitted acceptance criterion with its stable identity and content version."""

    acceptance_id: str = Field(pattern=ACCEPTANCE_ID_PATTERN)
    acceptance_version: str = Field(pattern=r"^[0-9a-f]{64}$")
    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    statement: str = Field(min_length=1)
    identity_source: Literal["authored", "legacy-position"]

    @property
    def ref(self) -> DeliveryAcceptanceRef:
        """Return the exact identity and version reference of this criterion."""
        return DeliveryAcceptanceRef(acceptance_id=self.acceptance_id, acceptance_version=self.acceptance_version)


def parse_acceptance_item(text: str) -> tuple[str | None, str]:
    """Return the authored ``AC-NNN`` identity, if any, and the statement it versions."""
    match = _AUTHORED_ITEM.fullmatch(text)
    if match is None:
        return None, text
    return match[1], match[2]


def is_near_miss_acceptance_item(text: str) -> bool:
    """Return whether an item looks like an ``AC-`` identity but does not match the authored form."""
    return _NEAR_MISS.match(text) is not None and _AUTHORED_ITEM.fullmatch(text) is None


def acceptance_version(statement: str) -> str:
    """Return the content version of one acceptance statement."""
    return hashlib.sha256(statement.encode()).hexdigest()


def is_authored_contract(contract: DeliveryContract) -> bool:
    """Return whether every acceptance item of the contract declares an authored identity."""
    return all(
        parse_acceptance_item(item)[0] is not None for outcome in contract.outcomes for item in outcome.acceptance
    )


def acceptance_criteria(contract: DeliveryContract) -> tuple[DeliveryAcceptanceCriterion, ...]:
    """Derive every criterion of one admitted contract in outcome and authored order."""
    authored = is_authored_contract(contract)
    criteria: list[DeliveryAcceptanceCriterion] = []
    for outcome in contract.outcomes:
        for position, item in enumerate(outcome.acceptance, start=1):
            identity, statement = parse_acceptance_item(item)
            if authored and identity is not None:
                criteria.append(
                    DeliveryAcceptanceCriterion(
                        acceptance_id=identity,
                        acceptance_version=acceptance_version(statement),
                        outcome_id=outcome.outcome_id,
                        statement=statement,
                        identity_source="authored",
                    )
                )
                continue
            if identity is not None:
                message = "Delivery contract mixes authored and legacy acceptance identities"
                raise ValueError(message)
            criteria.append(
                DeliveryAcceptanceCriterion(
                    acceptance_id=f"{outcome.outcome_id}.{position:02d}",
                    acceptance_version=acceptance_version(item),
                    outcome_id=outcome.outcome_id,
                    statement=item,
                    identity_source="legacy-position",
                )
            )
    identities = [criterion.acceptance_id for criterion in criteria]
    if len(identities) != len(set(identities)):
        message = "Delivery contract acceptance identities must be unique"
        raise ValueError(message)
    return tuple(criteria)


__all__ = [
    "ACCEPTANCE_ID_PATTERN",
    "DeliveryAcceptanceCriterion",
    "DeliveryAcceptanceRef",
    "acceptance_criteria",
    "acceptance_version",
    "is_authored_contract",
    "is_near_miss_acceptance_item",
    "parse_acceptance_item",
]
