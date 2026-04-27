"""Pydantic response models for the cockpit read API."""

from __future__ import annotations

from pydantic import BaseModel


class BoardOut(BaseModel):
    """Board configuration response model."""

    statuses: list[dict]
    priorities: list[str]
    valid_transitions: dict[str, list[str]]
