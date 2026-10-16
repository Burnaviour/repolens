from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from wiringmap.builder import build_graph
from wiringmap.graph import CodeGraph

SAMPLE_PROJECT = Path(__file__).parent / "fixtures" / "sample_project"


@pytest.fixture(scope="session")
def sample_graph() -> CodeGraph:
    return build_graph(SAMPLE_PROJECT)


@pytest.fixture
def make_repo(tmp_path: Path):
    """Write ``{relative path: source}`` into a temporary repository and return its root."""

    def make(files: dict[str, str]) -> Path:
        for rel, content in files.items():
            path = tmp_path / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(textwrap.dedent(content), encoding="utf-8")
        return tmp_path

    return make


@pytest.fixture
def graph_of(make_repo):
    """Build the graph of a temporary repository made from ``{path: source}``."""

    def build(files: dict[str, str]) -> CodeGraph:
        return build_graph(make_repo(files))

    return build


def edge(graph: CodeGraph, kind: str, source: str, target: str):
    return graph.edges.get((kind, source, target))


def call_targets(graph: CodeGraph, source: str) -> dict[str, str]:
    """``{target: confidence}`` for every call edge leaving ``source``."""
    return {
        e.target: e.confidence
        for e in graph.edges.values()
        if e.kind == "calls" and e.source == source
    }
