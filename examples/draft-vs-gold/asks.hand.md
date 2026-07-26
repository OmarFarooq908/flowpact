# Ask list (hand-derived spike)

**Source:** `examples/draft-vs-gold/pact.yaml`  
**Rule:** evidence with `status != delivered` + policies/open_slots with status in `{open, blocked_on_client}`  
**Sorted:** severity (critical → high → medium), then items that block `answer_quality` first.

> Synthetic spike to prove schema completeness. CLI `flowpact asks` should reproduce this shape.

---

## Critical

### E · labeled_holdout (missing) → blocks `answer_quality`
**Owner:** Benefits Ops Lead  
**Ask:** Deliver programmatic access to the labeled holdout — N, format, English in-scope slice, access method, owner, and date.

### S · holdout_access (open) → blocks `answer_quality`
**Owner:** Benefits Ops Lead  
**Ask:** Programmatic labeled holdout (N, format, English slice, access).

---

## High

### E · citation_pages (partial) → blocks `answer_quality`
**Owner:** Benefits Ops Lead  
**Ask:** Confirm canonical policy URLs for in-scope topics and provide a redirect map for retired pages.

### E · sample_questions (partial) → blocks `answer_quality`
**Owner:** Benefits Ops Lead  
**Ask:** Deliver a redacted sample of recent member questions with topic and locale.

### P · incomplete_policy (open) → blocks `answer_quality`
**Owner:** Benefits Ops Lead  
**Options:** Skip until policy is complete | Draft with explicit caveat flag  
**Ask:** Decide behavior when retrieved policy is incomplete.

### P · locale_scope (open) → blocks `answer_quality`
**Owner:** Benefits Ops Lead  
**Options:** English only | English + Spanish  
**Ask:** Decide which locales are in the headline claim for MVP.

### S · citation_canon (open) → blocks `answer_quality`
**Owner:** Benefits Ops Lead  
**Ask:** Canonical policy URLs + redirect map for citation hard gate.

### E · retrieval_labels (missing) → blocks `retrieval_recall` only
**Owner:** Benefits Ops Lead  
**Ask:** Provide labeled relevant passages for the retrieval engineering track. Does **not** block `answer_quality`.

---

## Medium

### S · retrieval_label_set (open) → blocks `retrieval_recall`
**Owner:** Benefits Ops Lead  
**Ask:** Labeled passages for retrieval recall@k.

---

## Intentionally omitted (resolved)

| Item | Why omitted |
| --- | --- |
| P · accuracy_method | `resolved` |
| S · sample_queue_access | `resolved` |
