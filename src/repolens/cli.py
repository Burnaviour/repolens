"""Command-line entry point."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.progress import BarColumn, MofNCompleteColumn, Progress, TextColumn
from rich.table import Table

from repolens import __version__
from repolens.builder import build_graph
from repolens.graph import CodeGraph

OUTPUT_DIR = ".repolens"

app = typer.Typer(
    name="repolens",
    help="See how your codebase fits together: offline, interactive, AI optional.",
    no_args_is_help=True,
    add_completion=False,
    pretty_exceptions_show_locals=False,
)
err = Console(stderr=True)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"repolens {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-V",
            callback=_version_callback,
            is_eager=True,
            help="Show the version and exit.",
        ),
    ] = False,
) -> None:
    """repolens turns a repository into an interactive map of its files, classes and functions."""


@app.command()
def scan(
    path: Annotated[
        Path,
        typer.Argument(exists=True, file_okay=False, resolve_path=True, help="Repository to scan."),
    ] = Path("."),
    output: Annotated[
        str | None,
        typer.Option(
            "--output",
            "-o",
            help=f"Output file, or '-' for stdout. Default: <path>/{OUTPUT_DIR}/graph.json",
        ),
    ] = None,
    exclude: Annotated[
        list[str] | None,
        typer.Option("--exclude", "-e", help="Extra gitignore-style pattern to skip. Repeatable."),
    ] = None,
    quiet: Annotated[bool, typer.Option("--quiet", "-q", help="Only print errors.")] = False,
) -> None:
    """Analyse a repository and write its code graph (graph.json)."""
    started = time.perf_counter()
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        console=err,
        transient=True,
        disable=quiet,
    ) as bar:
        task = bar.add_task("Parsing Python files", total=None)
        graph = build_graph(
            path,
            exclude or [],
            progress=lambda done, total: bar.update(task, completed=done, total=total),
        )
    elapsed = time.perf_counter() - started

    if output == "-":
        typer.echo(graph.to_json())
    else:
        target = Path(output) if output else _default_output(path)
        try:
            graph.write(target)
        except OSError as exc:
            err.print(f"[red]Could not write {target}:[/red] {exc.strerror or exc}")
            raise typer.Exit(1) from None
        if not quiet:
            err.print(f"[green]Wrote[/green] {target}")
    if not quiet:
        _print_summary(graph, elapsed)


def _default_output(repo: Path) -> Path:
    out_dir = repo / OUTPUT_DIR
    out_dir.mkdir(exist_ok=True)
    # Like .pytest_cache: the folder ignores itself, so it is never committed by accident.
    ignore = out_dir / ".gitignore"
    if not ignore.exists():
        ignore.write_text("# Created by repolens\n*\n", encoding="utf-8")
    return out_dir / "graph.json"


def _print_summary(graph: CodeGraph, elapsed: float) -> None:
    stats = graph.stats()
    table = Table(title=f"{graph.root_name} — scanned in {elapsed:.1f}s", title_justify="left")
    table.add_column("What")
    table.add_column("Count", justify="right")
    for kind, count in stats["nodes"].items():
        table.add_row(f"{kind} nodes", str(count))
    for kind, count in stats["edges"].items():
        table.add_row(f"{kind} edges", str(count))
    calls = stats["calls_by_confidence"]
    if calls:
        table.add_row("calls", ", ".join(f"{n} {conf}" for conf, n in calls.items()))
    if stats["parse_errors"]:
        table.add_row("[yellow]files not parsed[/yellow]", str(stats["parse_errors"]))
    err.print(table)
