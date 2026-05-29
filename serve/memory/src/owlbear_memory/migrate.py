"""memory-migrate: migrate legacy memory entries to score-based fields."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from owlbear_memory.engine import MemoryEngine


def _resolve_memory_dir(value: Path | None) -> Path:
    if value is not None:
        return value

    env_value = os.environ.get("OWLBEAR_MEMORY_DIR")
    if env_value:
        return Path(env_value)

    return Path(".owlbear") / "memory"


def main() -> None:
    """Entry point for ``uv run memory-migrate``."""
    parser = argparse.ArgumentParser(description="Migrate memory score and counter fields.")
    parser.add_argument(
        "--memory-dir",
        type=Path,
        default=None,
        help="Path to memory directory (default: OWLBEAR_MEMORY_DIR or .owlbear/memory).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report the migration count without writing changes.",
    )
    args = parser.parse_args()

    memory_dir = _resolve_memory_dir(args.memory_dir)
    engine = MemoryEngine(memory_dir=memory_dir)
    migrated = engine.migrate_scores(dry_run=args.dry_run)

    print(migrated)  # noqa: T201
    sys.exit(0)


if __name__ == "__main__":
    main()
