# Flowpact

[![CI](https://github.com/OmarFarooq908/flowpact/actions/workflows/ci.yml/badge.svg)](https://github.com/OmarFarooq908/flowpact/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/flowpact.svg)](https://pypi.org/project/flowpact/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

Human-writable **workflow + success contracts** for AI products.

Non-engineers (Workflow Contract Authors) capture process stages, scope boundaries, policies, success recipes, and evidence requirements in one `pact.yaml`. The CLI validates the pact and derives **client ask lists** and **no-claim** gates — so teams stop reverse-engineering client workflow from meetings and arguing about accuracy without a shared definition of done.

**One-line positioning.** Data contracts certify seams; eval kits score outputs; Flowpact certifies that the engagement has defined the client’s workflow and success rules — and knows what is still missing.

## Non-goals

| Adjacent tool | Why Flowpact is not that |
| --- | --- |
| Trustline / Great Expectations | Does not query warehouses or compile SQL |
| RAGAS / DeepEval | Does not run LLM judges or embeddings |
| OpenAPI / JSON Schema (runtime) | Does not validate HTTP or candidate payloads at runtime |
| Orchestrators (Airflow, etc.) | Does not schedule or execute generation |
| StructGate (future sibling) | Only **defines** the success recipe; exports JSON for a later scorer |

## Install

From PyPI:

```bash
pip install flowpact
```

From source (development):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Releases are published from `v*` tags via GitHub Actions (Trusted Publishing). See [`CONTRIBUTING.md`](CONTRIBUTING.md#releasing-pypi).

## Commands

```bash
flowpact init --template ai-draft-vs-gold
flowpact validate pact.yaml
flowpact asks pact.yaml
flowpact no-claim pact.yaml --strict
flowpact render pact.yaml
flowpact export-eng pact.yaml -o export-eng.json
```

## Example (synthetic draft-vs-gold)

Northwind Benefits policy-answer copilot — synthetic domain only, for schema/CLI demos.

```bash
flowpact validate examples/draft-vs-gold/pact.yaml
flowpact asks examples/draft-vs-gold/pact.yaml
flowpact no-claim examples/draft-vs-gold/pact.yaml --strict
```

Hand-derived spike reports: [`examples/draft-vs-gold/asks.hand.md`](examples/draft-vs-gold/asks.hand.md), [`examples/draft-vs-gold/no-claim.hand.md`](examples/draft-vs-gold/no-claim.hand.md).

## Schema

Frozen format `flowpact: "0.1"` — JSON Schema at [`schemas/pact.schema.json`](schemas/pact.schema.json) (also shipped in the package). Design plan: [`docs/design/FLOWPACT_PLAN.md`](docs/design/FLOWPACT_PLAN.md).

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). CI runs ruff + pytest on Python 3.11–3.13.

## License

Apache-2.0 — see [`LICENSE`](LICENSE).
