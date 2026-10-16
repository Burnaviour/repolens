"""Command-line entry point."""

from __future__ import annotations

import time
import webbrowser
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.progress import BarColumn, MofNCompleteColumn, Progress, TextColumn
from rich.table import Table

from wiringmap import __version__
from wiringmap.builder import build_graph
from wiringmap.graph import CodeGraph
from wiringmap.render.html import SOURCE_BUDGET, collect_sources, render_report

OUTPUT_DIR = ".wiringmap"

app = typer.Typer(
    name="wiringmap",
    help="See how your code is wired: offline, interactive, AI optional.",
    no_args_is_help=True,
    add_completion=False,
    pretty_exceptions_show_locals=False,
)
err = Console(stderr=True)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"wiringmap {__version__}")
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
    """wiringmap turns a repository into an interactive map of its files, classes and functions."""


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
    graph, elapsed = _scan(path, exclude, quiet)
    if output == "-":
        typer.echo(graph.to_json())
    else:
        target = Path(output) if output else _output_dir(path) / "graph.json"
        _write(target, graph.to_json() + "\n", quiet)
    if not quiet:
        _print_summary(graph, elapsed)


@app.command()
def build(
    path: Annotated[
        Path,
        typer.Argument(exists=True, file_okay=False, resolve_path=True, help="Repository to map."),
    ] = Path("."),
    output: Annotated[
        Path | None,
        typer.Option(
            "--output", "-o", help=f"Report file. Default: <path>/{OUTPUT_DIR}/report.html"
        ),
    ] = None,
    exclude: Annotated[
        list[str] | None,
        typer.Option("--exclude", "-e", help="Extra gitignore-style pattern to skip. Repeatable."),
    ] = None,
    source: Annotated[
        bool | None,
        typer.Option(
            "--source/--no-source",
            help="Embed source code so the report can show it. Default: only up to 8 MB of Python.",
        ),
    ] = None,
    open_report: Annotated[
        bool, typer.Option("--open", help="Open the report in your browser when done.")
    ] = False,
    quiet: Annotated[bool, typer.Option("--quiet", "-q", help="Only print errors.")] = False,
) -> None:
    """Build an interactive map of a repository as one offline HTML file."""
    graph, elapsed = _scan(path, exclude, quiet)
    sources = None
    if source is not False:
        sources = collect_sources(path, graph, limit=None if source else SOURCE_BUDGET)
        if sources is None and not quiet:
            err.print(
                "[yellow]Source code not embedded:[/yellow] more than "
                f"{SOURCE_BUDGET // 1_000_000} MB of Python. Use --source to include it anyway."
            )
    if output is None:
        out_dir = _output_dir(path)
        _write(out_dir / "graph.json", graph.to_json() + "\n", quiet=True)
        target = out_dir / "report.html"
    else:
        target = output
    _write(target, render_report(graph, sources), quiet)
    if not quiet:
        _print_summary(graph, elapsed)
    if open_report:
        webbrowser.open(target.resolve().as_uri())


def _scan(path: Path, exclude: list[str] | None, quiet: bool) -> tuple[CodeGraph, float]:
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
    return graph, time.perf_counter() - started


def _output_dir(repo: Path) -> Path:
    out_dir = repo / OUTPUT_DIR
    out_dir.mkdir(exist_ok=True)
    # Like .pytest_cache: the folder ignores itself, so it is never committed by accident.
    ignore = out_dir / ".gitignore"
    if not ignore.exists():
        ignore.write_text("# Created by wiringmap\n*\n", encoding="utf-8")
    return out_dir


def _write(target: Path, text: str, quiet: bool) -> None:
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    except OSError as exc:
        err.print(f"[red]Could not write {target}:[/red] {exc.strerror or exc}")
        raise typer.Exit(1) from None
    if not quiet:
        size = len(text.encode("utf-8"))
        err.print(f"[green]Wrote[/green] {target} ({_human_size(size)})")


def _human_size(size: int) -> str:
    for unit in ("B", "KB", "MB"):
        if size < 1024 or unit == "MB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size} B"  # pragma: no cover


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
