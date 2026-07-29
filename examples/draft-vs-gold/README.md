# Flowpact — draft-vs-gold example

Synthetic worked example: Northwind Benefits policy-answer copilot. Used only to exercise the schema and CLI — not based on a real engagement.

| File | Role |
| --- | --- |
| `pact.yaml` | Source of truth |
| `gold.jsonl` / `drafts.jsonl` | Tiny holdout for optional `flowpact-score` |
| `asks.hand.md` | Hand-derived ask list (schema spike) |
| `no-claim.hand.md` | Hand-derived no-claim report (schema spike) |

## Core CLI

```bash
flowpact validate examples/draft-vs-gold/pact.yaml
flowpact asks examples/draft-vs-gold/pact.yaml
flowpact no-claim examples/draft-vs-gold/pact.yaml --strict
flowpact render examples/draft-vs-gold/pact.yaml
flowpact export-eng examples/draft-vs-gold/pact.yaml -o /tmp/export-eng.json
```

## Optional score (`flowpact[score]`)

Population / gate `rule` strings use a small executable DSL (`equals …`, `in a, b, c`, or a bare token). Soft methods in this example are offline (`token_overlap`, `exact_match`).

```bash
pip install 'flowpact[score]'   # score modules ship with the package; extra is the install contract

flowpact export-eng examples/draft-vs-gold/pact.yaml -o /tmp/export-eng.json

flowpact-score run \
  --export-eng /tmp/export-eng.json \
  --gold examples/draft-vs-gold/gold.jsonl \
  --drafts examples/draft-vs-gold/drafts.jsonl \
  --out /tmp/score_run/

# q4 has a wrong citation_url → hard-gate zero; mean may FAIL the 0.90 aggregate.
# Artifacts: manifest.json, scorecard.json, scorecard.md, failure_cards.md, population_audit.json

flowpact-score diff \
  --baseline /tmp/score_run/manifest.json \
  --candidate /tmp/score_run/manifest.json
```

`q5` (locale `es`) and `q6` (topic `payroll`) are excluded from the scored population; see `population_audit.json`.
