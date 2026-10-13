from typer.testing import CliRunner

from repolens import __version__
from repolens.cli import app

runner = CliRunner()


def test_version_flag():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.output.strip() == f"repolens {__version__}"


def test_no_args_shows_help():
    result = runner.invoke(app, [])
    assert "Usage" in result.output
