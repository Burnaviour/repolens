import json

from conftest import SAMPLE_PROJECT
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


def test_scan_writes_default_output_that_ignores_itself(make_repo):
    root = make_repo({"app.py": "def main():\n    pass\n"})
    result = runner.invoke(app, ["scan", str(root)])
    assert result.exit_code == 0, result.output
    graph = json.loads((root / ".repolens" / "graph.json").read_text())
    assert "app:main" in {n["id"] for n in graph["nodes"]}
    assert (root / ".repolens" / ".gitignore").read_text().splitlines()[-1] == "*"


def test_scan_to_stdout_prints_only_json():
    result = runner.invoke(app, ["scan", str(SAMPLE_PROJECT), "-o", "-", "-q"])
    assert result.exit_code == 0
    assert json.loads(result.stdout)["root_name"] == "sample_project"


def test_scan_exclude(make_repo, tmp_path_factory):
    root = make_repo({"app.py": "", "tests/test_app.py": ""})
    out = tmp_path_factory.mktemp("out") / "g.json"
    result = runner.invoke(app, ["scan", str(root), "-o", str(out), "-q", "-e", "tests/"])
    assert result.exit_code == 0
    assert {n["id"] for n in json.loads(out.read_text())["nodes"]} >= {"app"}
    assert "test_app" not in out.read_text()


def test_scan_reports_unwritable_output_cleanly(make_repo):
    root = make_repo({"app.py": ""})
    blocker = root / "not_a_dir"
    blocker.write_text("")
    result = runner.invoke(app, ["scan", str(root), "-o", str(blocker / "g.json")])
    assert result.exit_code == 1
    assert "Could not write" in result.output
    assert "Traceback" not in result.output
