# Shared standard 1.0.0 checklist

Verification record for `standard/` version 1.0.0. Automated items are enforced by `tools/validate.py` (check IDs V01 to V24) and `tests/test_validate.py`; run both to reproduce every result. Human items are confirmed by the reviewer named in `release-gate.md`.

## Files

| File | Purpose | Verified by |
|---|---|---|
| `standard/README.md` | Purpose, version, authority, consumer rule, breaking changes, non-authority | V04, V20 |
| `standard/glossary.md` | 33 canonical terms with authority | V04, V23 |
| `standard/id-registry.yaml` | 86 active prefixes, 9 retired, six registered repositories | V05, V06, V07 |
| `standard/field-conventions.md` | Naming, timestamps, dates, periods, hours, rates, ratios, flags, common fields, enums, nulls, arrays, payloads | V04, V20 |
| `standard/label-rules.yaml` | The four mandatory labels | V15 |
| `standard/severity-scale.yaml` | `sev1` to `sev4`, no timers | V22 |
| `standard/readiness-categories.yaml` | Six categories, no weights | V21 |
| `standard/lifecycle-terms.yaml` | Ten phases, five phase statuses, three gate outcomes | V13 |
| `standard/status-vocabularies.yaml` | Configuration, content, recommendation, learning result | V16 |
| `standard/org-stages.yaml` | Four descriptive stages, no headcount thresholds | V14 |
| `standard/event-catalog.yaml` | 60 events with producer, consumers, subject, payload fields, effect | V08 to V11, V24 |
| `standard/version-policy.md` | SemVer rules, repository versus standard version | V04, V20 |

## Schemas

| Schema | Key rules | Verified by |
|---|---|---|
| `event.schema.json` | Exactly ten fields; `EVT-` IDs; dot-notation types; UTC `Z` timestamps; `actor_type` human, system, ai_agent; human actors are `PER-`, AI actors `AGT-`; `source_repo` limited to the six repositories | V02, V07, V12; schema behavior tests |
| `approval-record.schema.json` | `APR-` IDs; decision approved or rejected; approver is a `PER-` human and `approver_type` is fixed to human | V02, V12; schema behavior tests |
| `recommendation.schema.json` | `REC-` IDs; status proposed, approved, rejected; approved or rejected requires an approval record; at least one source reference; AI origin requires a task run | V02; schema behavior tests |
| `metric-definition.schema.json` | `MTR-` IDs; metadata only, no values (`MTV-` reserved, no schema in 1.0.0) | V02; schema behavior tests |

All four are valid draft 2020-12 schemas, and every embedded illustrative example validates (V02).

## Vocabularies

| Vocabulary | Values | Check |
|---|---|---|
| Lifecycle phases | initiate, discover, design, build, validate, enable, launch, stabilize, transition, review | V13 |
| Phase statuses | not_started, active, awaiting_gate, completed, blocked | V13 |
| Gate outcomes | pass, pass_with_conditions, hold | V13 |
| Configuration | draft, in_review, released, deprecated | V16 |
| Content | draft, in_review, published, retired | V16 |
| Recommendation | proposed, approved, rejected | V16 |
| Learning result | pass, not_yet | V16 |
| Organization stages | startup, early_scale, structured_growth, mature | V14 |
| Readiness categories | people, process, technology, data, training, support | V21 |
| Severities | sev1, sev2, sev3, sev4 | V22 |
| Actor types | human, system, ai_agent | V12 |

## Counts

| Item | Count |
|---|---|
| Glossary terms | 33 |
| Active ID prefixes | 86 (operating system 29, capacity 12, tracker 3, enablement 22, team management 15, AI framework 5) |
| Retired prefixes | 9 |
| Events | 60 (operating system 25 including 4 large-scale go-live pack events, capacity 7, enablement 11, team management 11, AI framework 6) |
| Shared schemas | 4 |

## Validation tests

`tests/test_validate.py`, 39 tests. Negative tests run on a temporary copy, so the real files never change.

| Required rejection | Test |
|---|---|
| Duplicate ID prefix | `test_rejects_duplicate_id_prefix` |
| Retired prefix reactivation | `test_rejects_retired_prefix_reactivation` |
| Malformed ID | `test_rejects_malformed_id`, `test_rejects_unregistered_prefix_in_example` |
| Malformed event name | `test_rejects_malformed_event_name` |
| Unregistered producer | `test_rejects_unregistered_producer` (and `test_rejects_unregistered_consumer`) |
| Invalid actor_type | `test_rejects_invalid_actor_type`, `test_rejects_invalid_actor_type_in_example` |
| Changed mandatory-label wording | `test_rejects_changed_label_wording`, `test_rejects_label_near_variant_in_documents` |
| Invalid organization stage | `test_rejects_invalid_organization_stage` |
| Missing standard file | `test_rejects_missing_standard_file` |
| Em dash | `test_rejects_em_dash` |
| Injected blocklisted term | `test_rejects_injected_blocklisted_term`, `test_rejects_blocklist_inside_repository` |

Further protections: event ownership change, retired event alias, unregistered subject type, lifecycle change, vocabulary change, version inconsistency, secret, non-human approver, severity timer, readiness weights, missing glossary term, and eight schema behavior tests (approval required for decided recommendations, task run required for AI recommendations, sources required, human-only approver, person-only human actor, no renamed event fields, UTC-only timestamps, no values in metric definitions).

## Cross-checks

| Area | Result | How |
|---|---|---|
| Compatibility audit | PASS: every shared-contract mismatch between earlier plans and V4 resolved to the V4 form; no V4 contradiction | Private build record in the author's workspace |
| Genericity | PASS: no company, product, customer, vendor, or industry premise; examples use IDs and neutral wording | Human review; publication gate warning list |
| Public safety | PASS: freshly written; no names, metrics, or source material; validator secret scan, gitleaks, publication gate | V18, V19, gitleaks, publication gate |
| AI boundary | PASS: recommendations proposed until a human approves; approver fixed to human; events never grant authority | V12, schema behavior tests, `authoritative_effect` in every event |
| ID uniqueness | PASS | V05, V06 |
| Event uniqueness | PASS | V08, V24 |
| Version consistency | PASS: standard 1.0.0 everywhere; repository 0.1.0 pre-release | V20 |
