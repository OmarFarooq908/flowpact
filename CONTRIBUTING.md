# Contributing to Flowpact

Thanks for contributing. Flowpact is a small CLI: keep changes focused and within the [non-goals](README.md#non-goals).

## Development setup

```bash
git clone https://github.com/OmarFarooq908/flowpact.git
cd flowpact
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## Checks (run before opening a PR)

```bash
ruff check .
ruff format .
pytest -q
flowpact validate examples/draft-vs-gold/pact.yaml
```

CI runs the same lint + tests on Python 3.11, 3.12, and 3.13.

## Scope rules

**In scope:** pact schema, validation, asks / no-claim / render / export-eng, templates, docs.

**Out of scope:** SQL/data-warehouse contracts, LLM judges, SaaS/UI, pipeline orchestration, scoring engines (those belong elsewhere).

Do not add examples that mirror a real client’s field names or workflows — use synthetic domains only.

## Pull requests

1. Open an issue first for larger design changes (schema fields, new commands).
2. Keep PRs small and reviewable.
3. Use the PR checklist template.
4. Update docs/examples when behavior changes.

## License

By contributing, you agree your contributions are licensed under the Apache-2.0 license (see [`LICENSE`](LICENSE)).
