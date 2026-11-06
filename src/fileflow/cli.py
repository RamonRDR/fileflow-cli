"""FileFlow's Typer entrypoint and Rich terminal reporting."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from fileflow.executor import execute_plan
from fileflow.models import Plan, SortMode
from fileflow.planner import build_plan

app = typer.Typer(
    name="fileflow",
    help="Organize files cautiously. Start with --dry-run to preview every move.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()


@app.callback()
def main() -> None:
    """Command group entry point."""


def _show_plan(plan: Plan, *, dry_run: bool) -> None:
    table = Table(title="Planned moves" if dry_run else "FileFlow operations")
    table.add_column("From", overflow="fold")
    table.add_column("To", overflow="fold")
    for move in plan.moves:
        table.add_row(str(move.source), str(move.destination))
    console.print(table)


@app.command()
def organize(
    source: Annotated[Path, typer.Argument(help="Directory containing files to organize.")],
    destination: Annotated[
        Path, typer.Option("--destination", "-d", help="Separate destination directory.")
    ],
    mode: Annotated[
        SortMode, typer.Option("--mode", "-m", help="Group by extension or category.")
    ] = SortMode.extension,
    by_date: Annotated[
        bool, typer.Option("--by-date", help="Add UTC YYYY/MM directories within each group.")
    ] = False,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Preview only. Never create, copy, or remove files.")
    ] = False,
    category: Annotated[
        list[str] | None,
        typer.Option(
            "--category",
            help="Custom mapping, e.g. --category 'Research=.pdf,.md'. Repeatable; category mode only.",
        ),
    ] = None,
) -> None:
    """Organize immediate child files without overwriting existing files."""
    try:
        plan = build_plan(
            source,
            destination,
            mode=mode,
            by_date=by_date,
            category_rules=tuple(category or ()),
        )
    except (ValueError, OSError) as exc:
        console.print(f"[red]Cannot plan: {exc}[/red]")
        raise typer.Exit(code=2) from exc

    _show_plan(plan, dry_run=dry_run)
    if dry_run:
        console.print(
            f"[cyan]Dry run:[/cyan] {len(plan.moves)} planned, {plan.ignored} ignored, 0 moved."
        )
        return

    result = execute_plan(plan)
    console.print(
        f"[bold]Finished:[/bold] {len(result.moved)} moved, {result.ignored} ignored, "
        f"{len(result.failed)} failed."
    )
    for failure in result.failed:
        console.print(f"[red]FAILED[/red] {failure.move.source}: {failure.reason}")
    if result.failed:
        raise typer.Exit(code=1)
