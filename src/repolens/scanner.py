"""Find the files that make up a repository, the way git would see them."""

from __future__ import annotations

import os
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import pathspec

DEFAULT_MAX_FILE_SIZE = 1_000_000  # bytes; larger files are listed but not parsed

# Skipped even without a .gitignore, e.g. when scanning a plain folder.
DEFAULT_IGNORED_DIRS = frozenset(
    {
        "__pycache__",
        "node_modules",
        "site-packages",
        "build",
        "dist",
        "htmlcov",
    }
)

LANGUAGES_BY_SUFFIX = {
    ".py": "python",
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".scss": "css",
    ".json": "json",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".toml": "toml",
    ".ini": "ini",
    ".cfg": "ini",
    ".md": "markdown",
    ".rst": "restructuredtext",
    ".xml": "xml",
    ".sql": "sql",
    ".sh": "shell",
    ".bash": "shell",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".kt": "kotlin",
    ".c": "c",
    ".h": "c",
    ".cc": "cpp",
    ".cpp": "cpp",
    ".hpp": "cpp",
    ".cs": "csharp",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
}

LANGUAGES_BY_NAME = {
    "Dockerfile": "dockerfile",
    "Makefile": "makefile",
}


@dataclass(frozen=True)
class SourceFile:
    path: str  # repository-relative, always with forward slashes
    language: str
    size: int

    @property
    def parsable(self) -> bool:
        return self.size <= DEFAULT_MAX_FILE_SIZE


def detect_language(name: str) -> str | None:
    if name in LANGUAGES_BY_NAME:
        return LANGUAGES_BY_NAME[name]
    return LANGUAGES_BY_SUFFIX.get(os.path.splitext(name)[1].lower())


def scan_repository(root: Path, exclude: Iterable[str] = ()) -> list[SourceFile]:
    """Return every recognised source file under ``root``, sorted by path.

    Honours ``.gitignore`` files at every level and ``.git/info/exclude``, skips hidden
    entries, virtualenvs, symlinks and the usual build/cache directories. ``exclude``
    takes extra gitignore-style patterns relative to ``root``.
    """
    root = root.resolve()
    extra = pathspec.GitIgnoreSpec.from_lines(list(exclude))
    # Each entry is (directory relative to root, spec of the .gitignore in that directory).
    # Git ranks .git/info/exclude below every .gitignore, so it goes first.
    specs: list[tuple[str, pathspec.GitIgnoreSpec]] = []
    info_exclude = root / ".git" / "info" / "exclude"
    if info_exclude.is_file():
        lines = info_exclude.read_text(encoding="utf-8", errors="replace").splitlines()
        specs.append(("", pathspec.GitIgnoreSpec.from_lines(lines)))
    found: list[SourceFile] = []

    def ignored(rel: str, is_dir: bool) -> bool:
        probe = rel + "/" if is_dir else rel
        if extra.match_file(probe):
            return True
        # Like git, a deeper .gitignore overrides a shallower one (e.g. with a "!" rule).
        # `specs` is ordered root-first because os.walk is top-down.
        verdict = None
        for base, spec in specs:
            if base == "":
                include = spec.check_file(probe).include
            elif probe.startswith(base + "/"):
                include = spec.check_file(probe[len(base) + 1 :]).include
            else:
                continue
            if include is not None:
                verdict = include
        return verdict is True

    for dirpath, dirnames, filenames in os.walk(root):
        current = Path(dirpath)
        rel_dir = current.relative_to(root).as_posix()
        rel_dir = "" if rel_dir == "." else rel_dir

        if ".gitignore" in filenames:
            lines = (current / ".gitignore").read_text(encoding="utf-8", errors="replace")
            specs.append((rel_dir, pathspec.GitIgnoreSpec.from_lines(lines.splitlines())))

        kept = []
        for name in sorted(dirnames):
            child = current / name
            rel = f"{rel_dir}/{name}" if rel_dir else name
            if (
                name.startswith(".")
                or name in DEFAULT_IGNORED_DIRS
                or name.endswith(".egg-info")
                or child.is_symlink()
                or (child / "pyvenv.cfg").exists()
                or ignored(rel, is_dir=True)
            ):
                continue
            kept.append(name)
        dirnames[:] = kept  # os.walk only descends into what is left here

        for name in filenames:
            if name.startswith("."):
                continue
            language = detect_language(name)
            if language is None:
                continue
            path = current / name
            rel = f"{rel_dir}/{name}" if rel_dir else name
            if path.is_symlink() or ignored(rel, is_dir=False):
                continue
            found.append(SourceFile(path=rel, language=language, size=path.stat().st_size))

    found.sort(key=lambda f: f.path)
    return found
