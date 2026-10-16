# Changelog

## 0.1.0 (2026-10-16)

First public preview.

### Added

- `wiringmap build`: an interactive, offline map of a Python project in one HTML file,
  with a folder map, file and function details, search, source view, entry points and
  web routes, and light and dark themes.
- `wiringmap scan`: the code graph as `graph.json` (format in `docs/graph-schema.md`).
- Python analysis: imports, relative imports, re-exports, inheritance, decorators, and
  call links marked resolved, inferred or guessed. Files written with Python 3.14
  syntax parse on older Python versions too.
- Scanning honours `.gitignore` files at every level and `.git/info/exclude`.
