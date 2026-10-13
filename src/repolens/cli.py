"""Command-line entry point."""

import typer

from repolens import __version__

app = typer.Typer(
    name="repolens",
    help="See how your codebase fits together: offline, interactive, AI optional.",
    no_args_is_help=True,
    add_completion=False,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"repolens {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        callback=_version_callback,
        is_eager=True,
        help="Show the version and exit.",
    ),
) -> None:
    """repolens turns a repository into an interactive map of its files, classes and functions."""
