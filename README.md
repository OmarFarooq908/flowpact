# Flowpact

[![CI](https://github.com/OmarFarooq908/flowpact/actions/workflows/ci.yml/badge.svg)](https://github.com/OmarFarooq908/flowpact/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/flowpact.svg)](https://pypi.org/project/flowpact/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

Human-writable **workflow + success contracts** for AI products.

Non-engineers (Workflow Contract Authors) capture process stages, scope boundaries, policies, success recipes, and evidence requirements in one `pact.yaml`. The CLI validates the pact and derives **client ask lists** and **no-claim** gates — so teams stop reverse-engineering client workflow from meetings and arguing about accuracy without a shared definition of done.

**One-line positioning.** Data contracts certify seams; eval kits score free-text answers; Flowpact certifies that the engagement has defined the client’s workflow and success rules — and knows what is still missing. Optional `flowpact-score` **executes** a structured draft-vs-gold claim from `export-eng.json`.

## Positioning matrix

| Layer | Role |
| --- | --- |
| **Flowpact** | Defines workflow + success recipe; validates; asks / no-claim; `export-eng` |
| **`flowpact-score`** (optional) | Executes the claim: frozen gold + drafts + recipe → field scores → pass/fail |
| **Trustline / GE** | Audits warehouse / data seams (not Flowpact) |
| **RAGAS / DeepEval** | Adjacent free-text / trace eval kits (not a structured field recipe runner) |

## Non-goals (base package)

| Adjacent tool | Why base Flowpact is not that |
| --- | --- |
| Trustline / Great Expectations | Does not query warehouses or compile SQL |
| RAGAS / DeepEval | Does not run LLM judges or embeddings in the base install |
| OpenAPI / JSON Schema (runtime) | Does not validate HTTP or candidate payloads at runtime |
| Orchestrators (Airflow, etc.) | Does not schedule or execute generation |
| Full RAGAS replacement | `flowpact-score` is structured draft-vs-gold only — not free-text Q&A eval |

Base `pip install flowpact` never pulls torch, OpenAI, or embedding models. Heavy methods live behind `flowpact[score-embed]` / `flowpact[score-llm]`.

## Install

From PyPI:

```bash
pip install flowpact
pip install 'flowpact[score]'          # optional draft-vs-gold runner (flowpact-score)
# pip install 'flowpact[score-embed]'  # embedding_similarity (stub / heavy deps)
# pip install 'flowpact[score-llm]'    # llm_judge (stub; off by default)
```

From source (development):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,score]"
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

### Optional score

```bash
flowpact-score run \
  --export-eng export-eng.json \
  --gold gold.jsonl \
  --drafts drafts.jsonl \
  --out reports/score_run/

flowpact-score diff \
  --baseline reports/score_run_a/manifest.json \
  --candidate reports/score_run_b/manifest.json
```

Exit codes: `0` pass, `1` claim fail / regression, `2` usage or input error.

Field paths are dotted (`a.b.0.c`). Population / gate rules use a small DSL (`equals …`, `in a, b, c`, bare token). See [`src/flowpact/score/README.md`](src/flowpact/score/README.md).

### Minimal CI snippet

```bash
flowpact validate pact.yaml
flowpact no-claim pact.yaml --strict
flowpact export-eng pact.yaml -o export-eng.json
flowpact-score run --export-eng export-eng.json --gold gold.jsonl --drafts drafts.jsonl --out reports/score_run/
flowpact-score diff --baseline reports/baseline/manifest.json --candidate reports/score_run/manifest.json
```

Prefer clearing no-claim blockers before scoring (`no-claim --strict`, or `flowpact-score run --require-claim-clear --pact pact.yaml`).

## Example (synthetic draft-vs-gold)

Northwind Benefits policy-answer copilot — synthetic domain only, for schema/CLI demos.

```bash
flowpact validate examples/draft-vs-gold/pact.yaml
flowpact asks examples/draft-vs-gold/pact.yaml
flowpact no-claim examples/draft-vs-gold/pact.yaml --strict
flowpact export-eng examples/draft-vs-gold/pact.yaml -o /tmp/export-eng.json
flowpact-score run \
  --export-eng /tmp/export-eng.json \
  --gold examples/draft-vs-gold/gold.jsonl \
  --drafts examples/draft-vs-gold/drafts.jsonl \
  --out /tmp/score_run/
```

Details: [`examples/draft-vs-gold/README.md`](examples/draft-vs-gold/README.md). Hand-derived spike reports: [`asks.hand.md`](examples/draft-vs-gold/asks.hand.md), [`no-claim.hand.md`](examples/draft-vs-gold/no-claim.hand.md).

## Schema

Frozen authoring format `flowpact: "0.1"` — JSON Schema at [`schemas/pact.schema.json`](schemas/pact.schema.json) (also shipped in the package). `export-eng` adds additive `export_schema: "1"`. Score report schemas: [`schemas/score-manifest.schema.json`](schemas/score-manifest.schema.json), [`schemas/score-scorecard.schema.json`](schemas/score-scorecard.schema.json), [`schemas/score-population-audit.schema.json`](schemas/score-population-audit.schema.json). Design plan: [`docs/design/FLOWPACT_PLAN.md`](docs/design/FLOWPACT_PLAN.md).

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). CI runs ruff + pytest on Python 3.11–3.13.

## License

Apache-2.0 — see [`LICENSE`](LICENSE).
