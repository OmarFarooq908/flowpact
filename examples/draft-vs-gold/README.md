# Flowpact — draft-vs-gold example

Synthetic worked example: Northwind Benefits policy-answer copilot. Used only to exercise the schema and CLI — not based on a real engagement.

| File | Role |
| --- | --- |
| `pact.yaml` | Source of truth |
| `asks.hand.md` | Hand-derived ask list (schema spike) |
| `no-claim.hand.md` | Hand-derived no-claim report (schema spike) |

```bash
flowpact validate examples/draft-vs-gold/pact.yaml
flowpact asks examples/draft-vs-gold/pact.yaml
flowpact no-claim examples/draft-vs-gold/pact.yaml --strict
flowpact render examples/draft-vs-gold/pact.yaml
flowpact export-eng examples/draft-vs-gold/pact.yaml -o /tmp/export-eng.json
```
