"""Decisions subcommands — manage async decision requests (list/show/resolve)."""

from __future__ import annotations

import re
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer
import yaml
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

from bearclaw.commands import _cli_error

# ---------------------------------------------------------------------------
# Module constants (relative to cwd)
# ---------------------------------------------------------------------------

DECISIONS_DIR = Path("docs/decisions")
PENDING = DECISIONS_DIR / "pending"
RESOLVED = DECISIONS_DIR / "resolved"

app = typer.Typer(
    name="decisions",
    help="Manage async decision requests.",
    no_args_is_help=True,
)

console = Console()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_decision_file(path: Path) -> tuple[dict, str]:
    """Parse a decision-request markdown file with YAML frontmatter.

    Returns:
        Tuple of (frontmatter dict, body string).

    Raises:
        ValueError: If frontmatter is missing, incomplete, or contains invalid YAML.
    """
    text = path.read_text(encoding="utf-8").lstrip()

    if not text.startswith("---"):
        msg = f"No YAML frontmatter found in {path}"
        raise ValueError(msg)

    end = text.find("---", 3)
    if end == -1:
        msg = f"No closing frontmatter delimiter in {path}"
        raise ValueError(msg)

    raw_yaml = text[3:end]
    try:
        data = yaml.safe_load(raw_yaml)
    except yaml.YAMLError as exc:
        msg = f"Malformed YAML frontmatter in {path}: {exc}"
        raise ValueError(msg) from exc

    if not isinstance(data, dict):
        msg = f"Malformed frontmatter in {path}: expected a mapping"
        raise ValueError(msg)  # noqa: TRY004 — AC requires ValueError for all malformed-frontmatter cases

    body = text[end + 3 :]
    body = body.removeprefix("\n")

    return data, body


def _find_decision_file(task_id: str) -> Path | None:
    """Find a pending decision file by scanning frontmatter ``task_id`` fields."""
    pending = DECISIONS_DIR / "pending"
    if not pending.is_dir():
        return None
    for md_path in pending.glob("*.md"):
        try:
            fm, _ = _parse_decision_file(md_path)
        except (ValueError, TypeError):
            continue
        if str(fm.get("task_id", "")) == task_id:
            return md_path
    return None


def _extract_h1_title(body: str) -> str:
    """Extract the first ``# Heading`` text from the body."""
    match = re.search(r"^\s*#\s+(.+)$", body, re.MULTILINE)
    return match.group(1).strip() if match else ""


def _extract_options(body: str) -> list[str]:
    """Extract option labels from ``### X: Label`` headings under ``## Options``."""
    options_match = re.search(r"^##\s+Options\s*$", body, re.MULTILINE)
    if not options_match:
        return []
    options_section = body[options_match.end() :]
    # Stop at the next ## section heading so we don't bleed into other sections.
    next_h2 = re.search(r"^##\s+", options_section, re.MULTILINE)
    if next_h2:
        options_section = options_section[: next_h2.start()]
    return re.findall(r"^###\s+(.+)$", options_section, re.MULTILINE)


def _compute_age_days(created_str: str) -> str:
    """Compute age in days from a date string."""
    try:
        created = datetime.fromisoformat(str(created_str)[:10]).date()
        delta = datetime.now(tz=UTC).date() - created
        return str(delta.days)
    except (ValueError, TypeError):
        return "?"


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@app.command("list")
def decisions_list() -> None:
    """List all pending decision requests."""
    pending = DECISIONS_DIR / "pending"
    if not pending.is_dir():
        typer.echo("No pending decisions directory found.")
        raise typer.Exit(code=1)

    files = sorted(pending.glob("*.md"))
    if not files:
        typer.echo("No pending decisions.")
        raise typer.Exit(code=1)

    table = Table(title="Pending Decisions")
    table.add_column("Task ID")
    table.add_column("Title")
    table.add_column("Age")
    table.add_column("Urgency")
    table.add_column("Type")

    found_any = False
    for md_path in files:
        try:
            fm, body = _parse_decision_file(md_path)
        except (ValueError, TypeError):
            continue  # skip malformed files gracefully
        title = _extract_h1_title(body)
        age = _compute_age_days(str(fm.get("created", "")))
        table.add_row(
            str(fm.get("task_id", "")),
            title,
            age,
            str(fm.get("urgency", "")),
            str(fm.get("decision_type", "")),
        )
        found_any = True

    if not found_any:
        typer.echo("No pending decisions.")
        raise typer.Exit(code=1)

    console.print(table)


@app.command("show")
def decisions_show(
    task_id: Annotated[str, typer.Argument(help="Task ID of the decision to show.")],
) -> None:
    """Show a pending decision request by task ID."""
    path = _find_decision_file(task_id)
    if path is None:
        _cli_error(f"Decision with task_id '{task_id}' not found.")

    content = path.read_text(encoding="utf-8")
    console.print(Markdown(content))


@app.command("resolve")
def decisions_resolve(
    task_id: Annotated[str, typer.Argument(help="Task ID of the decision to resolve.")],
) -> None:
    """Interactively resolve a pending decision request."""
    path = _find_decision_file(task_id)
    if path is None:
        _cli_error(f"Decision with task_id '{task_id}' not found.")

    _, body = _parse_decision_file(path)
    options = _extract_options(body)

    if options:
        typer.echo("Options:")
        for opt in options:
            typer.echo(f"  - {opt}")
        choice = typer.prompt("Choose an option")
    else:
        choice = typer.prompt("Enter your decision (free text)")

    notes = typer.prompt("Notes")

    typer.echo(f"\nChoice: {choice}")
    typer.echo(f"Notes: {notes}")
    if not typer.confirm("Confirm resolution?"):
        typer.echo("Cancelled.")
        return

    # Write resolution section and update frontmatter
    resolution_section = f"\n## Resolution\n\n**Choice:** {choice}\n\n**Notes:** {notes}\n"

    # Re-read file content to update
    text = path.read_text(encoding="utf-8")

    # Update frontmatter status to resolved
    text = text.replace("status: pending", "status: resolved", 1)

    # Append resolution section
    text = text.rstrip() + "\n" + resolution_section

    path.write_text(text, encoding="utf-8")

    # Move to resolved/
    resolved_dir = DECISIONS_DIR / "resolved"
    resolved_dir.mkdir(parents=True, exist_ok=True)
    shutil.move(str(path), str(resolved_dir / path.name))

    typer.echo(f"Decision '{task_id}' resolved and moved to resolved/.")
