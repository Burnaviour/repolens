# Contributing to wiringmap

Thanks for helping. Bug reports, ideas and pull requests are all welcome.

## Reporting a bug

[Open an issue](https://github.com/Burnaviour/wiringmap/issues/new/choose) with the
command you ran, what happened, and your Python version. If a specific project maps
badly, a link to it (when it is public) is the most useful thing you can share.
Please do not paste private code.

## Setting up

You need [uv](https://docs.astral.sh/uv/). Nothing else: the viewer has no build step,
so there is no Node toolchain.

```bash
git clone https://github.com/Burnaviour/wiringmap.git
cd wiringmap
uv sync
uv run pytest
uv run ruff check . && uv run ruff format --check .
```

## Working on it

- **Analysis** (`src/wiringmap/scanner.py`, `src/wiringmap/parsers/`): add a small case
  to `tests/fixtures/sample_project/` or a focused test with the `graph_of` fixture in
  `tests/conftest.py`, then make it pass.
- **Viewer** (`src/wiringmap/render/static/`): edit `app.js` or `app.css`, then rebuild
  a report and look at it:

  ```bash
  uv run wiringmap build . -o /tmp/wiringmap.html --open
  ```

  Try a small project and a large one, in light and dark mode, and at phone width.

[docs/architecture.md](docs/architecture.md) explains how the pieces fit together, and
[docs/graph-schema.md](docs/graph-schema.md) describes the data format.

## Pull requests

- Keep each pull request focused on one change, with tests for analysis changes.
- CI runs the tests on Python 3.10–3.13 and on Linux, macOS and Windows, plus `ruff`.
- Vendored libraries in `src/wiringmap/render/static/vendor/` are unmodified copies; see
  the README there before updating one.

## Releasing (maintainers)

1. Update `version` in `pyproject.toml` and move the notes in `CHANGELOG.md` under the
   new version.
2. Tag and push: `git tag v0.1.0 && git push origin v0.1.0`.
3. The release workflow builds the package, publishes it to PyPI through trusted
   publishing, and creates the GitHub release.

## Code of conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md).
