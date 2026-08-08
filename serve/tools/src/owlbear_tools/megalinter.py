"""MegaLinter image configuration shared by workspace commands."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

_REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
_CONFIG_PATH = _REPOSITORY_ROOT / ".mega-linter.yml"


@dataclass(frozen=True)
class MegaLinterImage:
    """Pinned MegaLinter runtime image."""

    reference: str

    @property
    def repository(self) -> str:
        """Return the image repository without its tag."""
        return self.reference.rsplit(":", 1)[0]

    @property
    def tag(self) -> str:
        """Return the image tag."""
        return self.reference.rsplit(":", 1)[1]


def load_megalinter_image(path: Path = _CONFIG_PATH) -> MegaLinterImage:
    """Load and validate OwlBear's image pin from MegaLinter configuration."""
    content = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(content, dict):
        msg = f"{path} must contain a YAML mapping"
        raise TypeError(msg)
    reference = content.get("OWLBEAR_MEGALINTER_IMAGE")
    if not isinstance(reference, str) or ":" not in reference:
        msg = f"{path} has an invalid OWLBEAR_MEGALINTER_IMAGE"
        raise ValueError(msg)
    return MegaLinterImage(reference=reference)
