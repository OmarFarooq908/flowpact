# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-07-29

### Added

- Optional `flowpact[score]` execution layer with console script `flowpact-score` (`run`, `diff`)
- Offline soft methods: `exact_match`, `token_overlap`; stubs for `embedding_similarity` / `llm_judge` behind `[score-embed]` / `[score-llm]`
- Score report schemas (manifest, scorecard, population audit) and Northwind `gold.jsonl` / `drafts.jsonl`
- Additive `export_schema: "1"` on `flowpact export-eng` output (authoring `flowpact: "0.1"` unchanged)

### Changed

- Example / template soft method for answer body: `token_overlap` (CI-friendly offline)
- README positioning: Flowpact defines → score executes; Trustline / RAGAS adjacent
- CONTRIBUTING: optional score extra in scope; base package still excludes required LLM/embed deps

## [0.1.0] - 2026-07-29

### Added

- Initial CLI: `init`, `validate`, `asks`, `no-claim`, `render`, `export-eng`
- Pact schema `flowpact: "0.1"` and `ai-draft-vs-gold` template
- Synthetic `examples/draft-vs-gold` worked example
- GitHub Actions CI (ruff + pytest on Python 3.11–3.13)
- Dependabot for Actions and pip
- Contributing guide, issue templates, and PR template
- PyPI publish workflow (Trusted Publishing on `v*` tags)
