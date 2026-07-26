# No-claim report (hand-derived spike)

**Source:** `examples/draft-vs-gold/pact.yaml`  
**Rule:** For each `success.claims[]`, list blocking undelivered evidence, open policies, and open slots that reference the claim.

> Synthetic spike. CLI `flowpact no-claim` (and `--strict`) should match this verdict.

---

## Claim: `answer_quality`

**Statement:** Draft answer quality vs SME gold on English in-scope benefits topics — not auto-publish. Binding recipe: `citation_url` hard gate + `answer_body` / `topic_tag` soft; aggregate `mean_score >= 0.90`.

### Status: **BLOCKED — cannot claim**

### Blockers

| Kind | Id | Status | Owner | Why it blocks |
| --- | --- | --- | --- | --- |
| evidence | `labeled_holdout` | missing | Benefits Ops Lead | No holdout ⇒ accuracy not measurable |
| evidence | `citation_pages` | partial | Benefits Ops Lead | Citation hard gate incomplete |
| evidence | `sample_questions` | partial | Benefits Ops Lead | End-to-end draft path still thin |
| policy | `incomplete_policy` | open | Benefits Ops Lead | Skip vs caveat undecided |
| policy | `locale_scope` | open | Benefits Ops Lead | Population locale undecided |
| open_slot | `holdout_access` | open | Benefits Ops Lead | Same as holdout evidence |
| open_slot | `citation_canon` | open | Benefits Ops Lead | Same as citation evidence |

### Does **not** block this claim

| Kind | Id | Note |
| --- | --- | --- |
| evidence | `retrieval_labels` | `required_for: [retrieval_recall]` only |
| open_slot | `retrieval_label_set` | blocks `retrieval_recall` only |
| policy | `accuracy_method` | resolved |
| open_slot | `sample_queue_access` | resolved |

### Can say today

- Retrieval + draft prototyping on redacted samples.
- Engineering retrieval recall is a tuning baseline — **not** this claim.

### Cannot say today

- Binding English benefits **answer quality** ≥ 0.90 on holdout.
- Auto-publish readiness for the help center.

---

## Engineering track: `retrieval_recall` (not a success claim)

| Kind | Id | Status |
| --- | --- | --- |
| evidence | `retrieval_labels` | missing |
| open_slot | `retrieval_label_set` | open |

Does **not** change the `answer_quality` no-claim verdict.

---

## Strict mode

`flowpact no-claim --strict` → **exit 1** (claim `answer_quality` has blockers).
