"""FileFlow's Typer entrypoint and Rich terminal reporting."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from fileflow.config import Settings, load_config
from fileflow.journal import execute_recorded, undo_manifest
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
        SortMode | None, typer.Option("--mode", "-m", help="Group by extension or category.")
    ] = None,
    by_date: Annotated[
        bool, typer.Option("--by-date", help="Add UTC YYYY/MM directories within each group.")
    ] = False,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Preview only. Never create, copy, or remove files.")
    ] = False,
    category: Annotated[
        list[str] | None,
        typer.Option("--category", help="Custom mapping Name=.pdf,.md (repeatable)."),
    ] = None,
    config: Annotated[
        Path | None, typer.Option("--config", help="Versioned YAML configuration file.")
    ] = None,
    recursive: Annotated[
        bool, typer.Option("--recursive", "-r", help="Include files in subdirectories.")
    ] = False,
    exclude: Annotated[
        list[str] | None,
        typer.Option("--exclude", help="Skip matching file/directory glob pattern; repeatable."),
    ] = None,
) -> None:
    """Organize files without overwriting existing files."""
    try:
        settings = load_config(config) if config is not None else Settings()
        plan = build_plan(
            source,
            destination,
            mode=mode if mode is not None else settings.mode,
            by_date=by_date or settings.by_date,
            category_rules=(*settings.category_rules, *(category or ())),
            recursive=recursive or settings.recursive,
            exclude_patterns=(*settings.exclude, *(exclude or ())),
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

    try:
        recorded = execute_recorded(plan, source, destination)
    except ValueError as exc:
        console.print(f"[red]Cannot execute safely: {exc}[/red]")
        raise typer.Exit(code=2) from exc
    except (OSError, RuntimeError) as exc:
        console.print(f"[red]Cannot execute safely: {exc}[/red]")
        raise typer.Exit(code=1) from exc
    result = recorded.result
    console.print(
        f"[bold]Finished:[/bold] {len(result.moved)} moved, {result.ignored} ignored, "
        f"{len(result.failed)} failed."
    )
    if recorded.manifest is not None:
        console.print(f"[cyan]Manifest:[/cyan] {recorded.manifest}")
    for failure in result.failed:
        console.print(f"[red]FAILED[/red] {failure.move.source}: {failure.reason}")
    if result.failed:
        raise typer.Exit(code=1)


@app.command()
def undo(
    manifest: Annotated[Path, typer.Argument(help="Operation manifest from an organize run.")],
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Check conflicts without restoring or deleting files.")
    ] = False,
) -> None:
    """Restore successfully moved files, refusing conflicts and changed content."""
    try:
        result = undo_manifest(manifest, dry_run=dry_run)
    except (ValueError, OSError) as exc:
        console.print(f"[red]Cannot undo: {exc}[/red]")
        raise typer.Exit(code=2) from exc
    action = "Ready to restore" if dry_run else "Restored"
    total = result.planned if dry_run else result.undone
    console.print(
        f"[bold]{action}:[/bold] {total}, {result.skipped} skipped, "
        f"{len(result.conflicts)} conflicts, {len(result.failed)} failed."
    )
    for message in result.conflicts:
        console.print(f"[yellow]CONFLICT[/yellow] {message}")
    for message in result.failed:
        console.print(f"[red]FAILED[/red] {message}")
    if result.conflicts or result.failed:
        raise typer.Exit(code=1)
