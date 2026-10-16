"""The code graph: the single data structure every wiringmap feature reads and writes.

Node ids follow one scheme so they are readable and never collide across kinds:

* ``dir:<path>``          a directory (``dir:.`` is the repository root)
* ``file:<path>``         a non-Python file
* ``<module>``            a Python module, by dotted name (``shop.service``)
* ``<module>:<qualname>`` a class, function or method (``shop.service:OrderService.place``)
* ``ext:<name>``          an external top-level package (``ext:requests``, ``ext:json``)
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1


class NodeKind:
    DIRECTORY = "directory"
    FILE = "file"
    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    EXTERNAL = "external"


class EdgeKind:
    CONTAINS = "contains"
    IMPORTS = "imports"
    CALLS = "calls"
    INHERITS = "inherits"
    DECORATES = "decorates"


class Confidence:
    RESOLVED = "resolved"  # the name resolves directly through scopes and imports
    INFERRED = "inferred"  # resolved through a type: an annotation or a constructor assignment
    GUESSED = "guessed"  # only a unique method name matched; the receiver type is unknown


@dataclass
class Node:
    id: str
    kind: str
    name: str
    path: str | None = None
    line: int | None = None
    end_line: int | None = None
    loc: int | None = None
    docstring: str | None = None
    signature: str | None = None
    attrs: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"id": self.id, "kind": self.kind, "name": self.name}
        for key in ("path", "line", "end_line", "loc", "docstring", "signature"):
            value = getattr(self, key)
            if value is not None:
                data[key] = value
        if self.attrs:
            data["attrs"] = self.attrs
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Node:
        return cls(**{**data, "attrs": dict(data.get("attrs", {}))})


@dataclass
class Edge:
    source: str
    target: str
    kind: str
    confidence: str | None = None
    line: int | None = None
    attrs: dict[str, Any] = field(default_factory=dict)

    @property
    def key(self) -> tuple[str, str, str]:
        return (self.kind, self.source, self.target)

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"source": self.source, "target": self.target, "kind": self.kind}
        if self.confidence is not None:
            data["confidence"] = self.confidence
        if self.line is not None:
            data["line"] = self.line
        if self.attrs:
            data["attrs"] = self.attrs
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Edge:
        return cls(**{**data, "attrs": dict(data.get("attrs", {}))})


@dataclass
class CodeGraph:
    root_name: str
    nodes: dict[str, Node] = field(default_factory=dict)
    edges: dict[tuple[str, str, str], Edge] = field(default_factory=dict)
    meta: dict[str, Any] = field(default_factory=dict)

    def add_node(self, node: Node) -> Node:
        """Add ``node`` unless a node with the same id exists; return the stored node."""
        return self.nodes.setdefault(node.id, node)

    def add_edge(self, edge: Edge) -> Edge:
        """Add ``edge``, merging it with an existing edge of the same kind between the same nodes.

        Merging keeps the first line, counts repeats in ``attrs["count"]`` and keeps the
        strongest confidence.
        """
        existing = self.edges.get(edge.key)
        if existing is None:
            self.edges[edge.key] = edge
            return edge
        existing.attrs["count"] = existing.attrs.get("count", 1) + 1
        if _CONFIDENCE_RANK.get(edge.confidence, 0) > _CONFIDENCE_RANK.get(existing.confidence, 0):
            existing.confidence = edge.confidence
        for key, value in edge.attrs.items():
            if isinstance(value, list):
                merged = existing.attrs.setdefault(key, [])
                merged.extend(v for v in value if v not in merged)
            else:
                existing.attrs.setdefault(key, value)
        return existing

    def stats(self) -> dict[str, Any]:
        calls = Counter(e.confidence for e in self.edges.values() if e.kind == EdgeKind.CALLS)
        return {
            "nodes": dict(sorted(Counter(n.kind for n in self.nodes.values()).items())),
            "edges": dict(sorted(Counter(e.kind for e in self.edges.values()).items())),
            "calls_by_confidence": dict(sorted(calls.items())),
            "parse_errors": sum(1 for n in self.nodes.values() if "parse_error" in n.attrs),
        }

    def to_dict(self) -> dict[str, Any]:
        from wiringmap import __version__

        return {
            "schema_version": SCHEMA_VERSION,
            "generator": {"name": "wiringmap", "version": __version__},
            "root_name": self.root_name,
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "meta": self.meta,
            "stats": self.stats(),
            # Sorted so two scans of the same code give identical, diffable output.
            "nodes": [self.nodes[k].to_dict() for k in sorted(self.nodes)],
            "edges": [self.edges[k].to_dict() for k in sorted(self.edges)],
        }

    def to_json(self, indent: int | None = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json() + "\n", encoding="utf-8")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CodeGraph:
        version = data.get("schema_version")
        if version != SCHEMA_VERSION:
            raise ValueError(f"unsupported graph schema version {version!r}")
        graph = cls(root_name=data["root_name"], meta=dict(data.get("meta", {})))
        for raw in data["nodes"]:
            graph.add_node(Node.from_dict(raw))
        for raw in data["edges"]:
            edge = Edge.from_dict(raw)
            graph.edges[edge.key] = edge
        return graph

    @classmethod
    def read(cls, path: Path) -> CodeGraph:
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))


_CONFIDENCE_RANK = {
    None: 0,
    Confidence.GUESSED: 1,
    Confidence.INFERRED: 2,
    Confidence.RESOLVED: 3,
}
