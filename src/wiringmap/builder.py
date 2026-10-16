"""Build the code graph for a repository: scan, extract, resolve."""

from __future__ import annotations

import posixpath
import sys
from collections import Counter
from collections.abc import Callable, Iterable
from pathlib import Path

from wiringmap.graph import CodeGraph, Edge, EdgeKind, Node, NodeKind
from wiringmap.parsers.python_ast import ModuleInfo, extract_module, read_source
from wiringmap.parsers.python_resolve import PyModule, PythonResolver, assign_module_names
from wiringmap.scanner import DEFAULT_MAX_FILE_SIZE, SourceFile, scan_repository

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib

ProgressCallback = Callable[[int, int], None]


def build_graph(
    root: Path,
    exclude: Iterable[str] = (),
    progress: ProgressCallback | None = None,
) -> CodeGraph:
    root = root.resolve()
    files = scan_repository(root, exclude)
    graph = CodeGraph(root_name=root.name)
    graph.meta = {
        "file_count": len(files),
        "languages": dict(Counter(f.language for f in files).most_common()),
    }

    _add_directories(graph, files)
    for f in files:
        if f.language != "python":
            graph.add_node(
                Node(
                    id=f"file:{f.path}",
                    kind=NodeKind.FILE,
                    name=posixpath.basename(f.path),
                    path=f.path,
                    attrs={"language": f.language, "size": f.size},
                )
            )
            graph.add_edge(
                Edge(_dir_id(posixpath.dirname(f.path)), f"file:{f.path}", EdgeKind.CONTAINS)
            )

    py_files = [f for f in files if f.language == "python"]
    names = assign_module_names([f.path for f in py_files], root.name)
    modules = []
    for done, f in enumerate(py_files, start=1):
        name = names[f.path]
        modules.append(
            PyModule(
                id=name.id,
                path=f.path,
                path_name=name.path_name,
                is_package=name.is_package,
                loose=name.loose,
                info=_extract(root, f),
            )
        )
        if progress:
            progress(done, len(py_files))

    PythonResolver(modules, graph).build(_project_scripts(root, files))
    return graph


def _extract(root: Path, f: SourceFile) -> ModuleInfo:
    if not f.parsable:
        info = ModuleInfo(qualname="", path=f.path)
        info.error = f"skipped: larger than {DEFAULT_MAX_FILE_SIZE // 1_000_000} MB"
        return info
    try:
        source = read_source((root / f.path).read_bytes())
    except (OSError, SyntaxError, UnicodeDecodeError, LookupError) as exc:
        info = ModuleInfo(qualname="", path=f.path)
        info.error = f"{type(exc).__name__}: {exc}"
        return info
    return extract_module(f.path, source)


def _dir_id(path: str) -> str:
    return f"dir:{path or '.'}"


def _add_directories(graph: CodeGraph, files: list[SourceFile]) -> None:
    graph.add_node(Node(id="dir:.", kind=NodeKind.DIRECTORY, name=graph.root_name, path="."))
    for f in files:
        directory = posixpath.dirname(f.path)
        while directory and _dir_id(directory) not in graph.nodes:
            graph.add_node(
                Node(
                    id=_dir_id(directory),
                    kind=NodeKind.DIRECTORY,
                    name=posixpath.basename(directory),
                    path=directory,
                )
            )
            parent = posixpath.dirname(directory)
            graph.add_edge(Edge(_dir_id(parent), _dir_id(directory), EdgeKind.CONTAINS))
            directory = parent


def _project_scripts(root: Path, files: list[SourceFile]) -> dict[str, str]:
    """Console scripts declared in any pyproject.toml, e.g. {"shop": "shop.cli:main"}."""
    scripts: dict[str, str] = {}
    for f in files:
        if posixpath.basename(f.path) != "pyproject.toml":
            continue
        try:
            data = tomllib.loads((root / f.path).read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
            continue
        project = data.get("project", {})
        poetry = data.get("tool", {}).get("poetry", {})
        for table in (project.get("scripts"), project.get("gui-scripts"), poetry.get("scripts")):
            if isinstance(table, dict):
                scripts.update({k: v for k, v in table.items() if isinstance(v, str)})
    return scripts
