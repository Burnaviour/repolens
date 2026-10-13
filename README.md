# repolens

**See how your (vibe-coded) codebase fits together: offline, interactive, AI optional.**

[![CI](https://github.com/Burnaviour/repolens/actions/workflows/ci.yml/badge.svg)](https://github.com/Burnaviour/repolens/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

When agents write your code, you end up shipping code you have never read. `repolens`
gives you back the mental map. Point it at a repository and it produces an interactive
page that shows which files depend on which, what every file, class and function does,
how calls flow, and where the risky parts are.

> **Status: early development (pre-alpha).** The CLI skeleton exists, but the features
> below are being built milestone by milestone. See the [roadmap](#roadmap).

## Planned features

- **Works with no AI at all.** Static analysis (Python `ast`) builds the code graph from
  imports, calls, inheritance, docstrings and metrics.
- **Local AI (optional).** Summaries from Ollama, LM Studio or llama.cpp, so your
  code never leaves your machine.
- **Cloud and agentic AI (optional, opt-in).** Claude or any OpenAI-compatible API for
  deeper explanations, guided tours and "ask your codebase" Q&A.
- **One offline HTML file.** Architecture map, file inspector, call graph explorer,
  treemap, and a health view (hotspots, import cycles, dead code). There are no CDN
  calls, so you can open it from disk or host it on GitHub Pages.
- **Architecture diff.** See what an agent's branch changed *structurally*: new files,
  new dependencies, new cycles.

## Planned usage

```bash
# no AI, no install
uvx repolens ./my-project --open

# local AI through Ollama
uvx repolens ./my-project --ai ollama --model qwen2.5-coder:7b
```

## Roadmap

| Milestone | Deliverable | Status |
|---|---|---|
| M0 Setup | uv project, CI, license | ✅ |
| M1 Graph | Scanner + Python parser + `graph.json` | ⏳ next |
| M2 Viewer | Offline `report.html`: architecture map, file inspector, search | |
| M3 Insight | Call graph, metrics, hotspots, cycles, `ARCHITECTURE.md` | |
| M4 Local AI | Ollama summaries: bottom-up, cached | |
| M5 Cloud + Agent | Claude / OpenAI-compatible, guided tour, `serve` + Ask box | |
| M6 Extras | `diff` mode, JS/TS support, framework plugins, MCP server, GitHub Action | |

The full design is in [docs/PROPOSAL.md](docs/PROPOSAL.md).

## Development

You need [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/Burnaviour/repolens.git
cd repolens
uv sync
uv run repolens --version
uv run pytest
uv run ruff check . && uv run ruff format --check .
```

## License

[MIT](LICENSE)
