"""A chat outside registered projects has no state or tools that can change it."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable


class Closed:
    """A folder that is no OwlBear project: every tool says so and nothing is written."""

    def __init__(self, why: str) -> None:
        self.why = why

    def __getattr__(self, _name: str) -> Callable[..., dict[str, Any]]:
        return lambda *_args, **_kwargs: {"error": self.why}
