# Vendored libraries

These files are inlined into every `report.html` so the report works offline. They are
unmodified copies of the published npm packages.

| File | Package | Version | License |
|---|---|---|---|
| `htm-preact-standalone.umd.js` | `htm` (`preact/standalone.umd.js`, which bundles Preact 10 and its hooks) | 3.1.1 | Apache-2.0 (htm), MIT (Preact) |
| `cytoscape.min.js` | `cytoscape` (`dist/cytoscape.min.js`) | 3.34.3 | MIT |
| `layout-base.js` | `layout-base` | 2.0.1 | MIT |
| `cose-base.js` | `cose-base` | 2.2.0 | MIT |
| `cytoscape-fcose.js` | `cytoscape-fcose` | 2.2.0 | MIT |

License texts are in [`licenses/`](licenses).

To update one, run `npm pack <package>@<version>`, copy the file listed above out of
the tarball, update this table, and check the result with `uv run repolens build . --open`.
