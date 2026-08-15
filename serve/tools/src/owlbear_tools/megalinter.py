"""MegaLinter image configuration shared by workspace commands."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

_REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
_CONFIG_PATH = _REPOSITORY_ROOT / ".mega-linter.yml"
_BASE_IMAGE_REPOSITORY = "ghcr.io/oxsecurity/megalinter"
_IMAGE_COMPONENT_RE = re.compile(r"^[a-z0-9]+(?:[-_][a-z0-9]+)*$")
_IMAGE_TAG_RE = re.compile(r"^v[0-9]+\.[0-9]+\.[0-9]+$")


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
    """Derive and validate the MegaLinter image from native configuration."""
    content = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(content, dict):
        msg = f"{path} must contain a YAML mapping"
        raise TypeError(msg)

    flavor = content.get("MEGALINTER_FLAVOR", "all")
    version = content.get("MEGALINTER_VERSION")
    if not isinstance(flavor, str) or not _IMAGE_COMPONENT_RE.fullmatch(flavor):
        msg = f"{path} has an invalid MEGALINTER_FLAVOR"
        raise ValueError(msg)
    if not isinstance(version, str) or not _IMAGE_TAG_RE.fullmatch(version):
        msg = f"{path} has an invalid MEGALINTER_VERSION"
        raise ValueError(msg)

    repository = _BASE_IMAGE_REPOSITORY
    if flavor != "all":
        repository = f"{repository}-{flavor}"
    reference = f"{repository}:{version}"
    return MegaLinterImage(reference=reference)
