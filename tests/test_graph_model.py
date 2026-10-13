import json

import pytest

from repolens.graph import SCHEMA_VERSION, CodeGraph, Edge, Node


def test_round_trip(sample_graph, tmp_path):
    path = tmp_path / "graph.json"
    sample_graph.write(path)
    loaded = CodeGraph.read(path)
    assert loaded.nodes == sample_graph.nodes
    assert loaded.edges == sample_graph.edges
    assert loaded.root_name == sample_graph.root_name


def test_output_is_sorted_and_versioned(sample_graph):
    data = json.loads(sample_graph.to_json())
    assert data["schema_version"] == SCHEMA_VERSION
    ids = [n["id"] for n in data["nodes"]]
    assert ids == sorted(ids)
    keys = [(e["kind"], e["source"], e["target"]) for e in data["edges"]]
    assert keys == sorted(keys)


def test_same_code_gives_same_graph(sample_graph):
    from conftest import SAMPLE_PROJECT

    from repolens.builder import build_graph

    again = json.loads(build_graph(SAMPLE_PROJECT).to_json())
    first = json.loads(sample_graph.to_json())
    first.pop("created_at"), again.pop("created_at")
    assert first == again


def test_empty_fields_are_omitted():
    assert Node(id="x", kind="module", name="x.py").to_dict() == {
        "id": "x",
        "kind": "module",
        "name": "x.py",
    }


def test_duplicate_edges_merge():
    graph = CodeGraph(root_name="r")
    graph.add_edge(Edge("a", "b", "calls", "guessed", line=3))
    graph.add_edge(Edge("a", "b", "calls", "resolved", line=9))
    merged = graph.edges[("calls", "a", "b")]
    assert merged.confidence == "resolved"
    assert merged.line == 3
    assert merged.attrs["count"] == 2


def test_rejects_unknown_schema_version():
    with pytest.raises(ValueError, match="schema version"):
        CodeGraph.from_dict({"schema_version": 999, "root_name": "r", "nodes": [], "edges": []})
