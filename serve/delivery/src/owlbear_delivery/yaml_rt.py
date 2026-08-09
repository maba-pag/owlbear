"""Shared ruamel.yaml round-trip factory for the Delivery package.

Every module that reads or writes YAML should use :func:`make_yaml` to
get a consistently configured ``YAML`` instance:

* Round-trip mode (``typ="rt"``) — preserves comments and key order.
* Timestamp resolver disabled — date-like strings stay as ``str``.
* Indent: 2-space mappings, sequences indented with dash at column 2
  (``indent(mapping=2, sequence=4, offset=2)``), matching yamllint's
  ``indent-sequences: true`` default.
"""

from __future__ import annotations

from ruamel.yaml import YAML

_TIMESTAMP_TAG = "tag:yaml.org,2002:timestamp"


def make_yaml(*, explicit_start: bool = False) -> YAML:
    """Return a pre-configured round-trip ``YAML`` instance.

    Parameters
    ----------
    explicit_start:
        Emit ``---`` document-start marker.  Use ``True`` for standalone
        YAML files (``config.yml``); leave ``False`` for frontmatter
        snippets that are wrapped in ``---`` delimiters by the caller.
    """
    y = YAML(typ="rt")

    # Instance-level copy of the implicit-resolver table without the
    # timestamp tag — no global side effects.
    y.resolver.yaml_implicit_resolvers = {
        char: [(tag, regexp) for tag, regexp in pairs if tag != _TIMESTAMP_TAG]
        for char, pairs in y.resolver.yaml_implicit_resolvers.items()
    }

    y.indent(mapping=2, sequence=4, offset=2)

    if explicit_start:
        y.explicit_start = True

    return y
