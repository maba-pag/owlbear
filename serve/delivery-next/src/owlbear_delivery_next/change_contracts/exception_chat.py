"""The chat's bounded, external exception request; proposed exceptions are advice only."""

from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Proposed(BaseModel):
    """One proposed suppression, before the chat edits the code."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    file: str = Field(
        min_length=1,
        max_length=4096,
        description="Repository-relative file, 1-4096 characters; no parent traversal",
        examples=["src/edge.py"],
    )
    line: int = Field(ge=1, le=1_000_000, description="Existing source line, 1-1000000", examples=[42])
    directive: str = Field(
        min_length=1,
        max_length=1000,
        description="Proposed directive, 1-1000 characters",
        examples=["# noqa: C901"],
    )
    reason: str = Field(
        min_length=1,
        max_length=4000,
        description="Why the rule does not fit this code, 1-4000 characters",
        examples=["This generated protocol dispatcher preserves the upstream cases."],
    )

    @field_validator("file")
    @classmethod
    def relative(cls, value: str) -> str:
        """The host reads only within the requested checkout."""
        if Path(value).is_absolute() or ".." in Path(value).parts:
            msg = "use a repository-relative file without '..'"
            raise ValueError(msg)
        return value


class Request(BaseModel):
    """Committed additions, or up to 20 proposed suppressions, in a chat's checkout."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    path: str = Field(
        min_length=1,
        max_length=4096,
        description="Absolute checkout root, 1-4096 characters",
        examples=["/Users/me/Projects/shop"],
    )
    base: str = Field(
        min_length=1,
        max_length=256,
        description="Ref the chat branched from, 1-256 characters",
        examples=["origin/main"],
    )
    proposed: Annotated[
        list[Proposed] | None,
        Field(
            max_length=20,
            description="Omit for committed additions; otherwise 1-20 proposals, advice only, no ledger write",
            min_length=1,
            examples=[
                [
                    {
                        "file": "src/edge.py",
                        "line": 42,
                        "directive": "# noqa: C901",
                        "reason": "This generated dispatcher preserves upstream cases.",
                    }
                ]
            ],
        ),
    ] = None

    @field_validator("path")
    @classmethod
    def absolute(cls, value: str) -> str:
        """A relative checkout could resolve against the host rather than the chat."""
        if not Path(value).is_absolute():
            msg = "use an absolute checkout root"
            raise ValueError(msg)
        return value
