# Synthetic data check

Verification record for `data/synthetic/`. All files are synthetic data; no company, customer, or person is represented and no value is a measured result. Checks V36 to V39 in `tools/validate.py` enforce every item, and `test_real_core_counts_are_locked` locks the counts.

## Row counts (exact)

| File | Rows | IDs | Required |
|---|---|---|---|
| `projects.csv` | 3 | `PRJ-000001` to `PRJ-000003` | exactly 3 |
| `phases.csv` | 15 | `PHS-000001` to `PHS-000015` | 15 |
| `milestones.csv` | 12 | `MLS-000001` to `MLS-000012` | exactly 12 |
| `tasks.csv` | 30 | `TSK-000001` to `TSK-000030` | exactly 30 |
| `requests.csv` | 8 | `REQ-000001` to `REQ-000008` | exactly 8 |
| `risks.csv` | 6 | `RSK-000001` to `RSK-000006` | exactly 6 |
| `issues.csv` | 5 | `ISS-000001` to `ISS-000005` | exactly 5 |
| `readiness.csv` | 18 | `RDE-000001` to `RDE-000018` in scorecards `RDS-000001` to `RDS-000003` | exactly 18 (3 projects x 6 categories) |
| `events.jsonl` | 38 | `EVT-000001` to `EVT-000038`, sequential and in time order | 30 to 45; locked at 38 |

Every CSV header equals the `x-csv-columns` list of its schema, and every row validates against its schema (`schema_version` 0.1.0). Every event validates against `standard/schemas/event.schema.json` (`schema_version` 1.0.0).

## Relationships

| Project | Phases | Milestones | Tasks | Requests | Risks | Issues | Readiness rows | Events |
|---|---|---|---|---|---|---|---|---|
| A `PRJ-000001` | 2 (`PHS-000001` to `PHS-000002`) | 2 | 6 | 1 | 1 | 0 | 6 (`RDS-000001`) | 10 |
| B `PRJ-000002` | 4 (`PHS-000003` to `PHS-000006`) | 4 | 10 | 3 | 3 | 2 | 6 (`RDS-000002`) | 15 |
| C `PRJ-000003` | 9 (`PHS-000007` to `PHS-000015`) | 6 | 14 | 4 | 2 | 3 | 6 (`RDS-000003`) | 13 |

Zero orphan references (see `referential-integrity.md`).

## Scenario purpose

| Scenario | Stage | Position on 2026-10-05 | What it demonstrates |
|---|---|---|---|
| A: Synthetic Project A | startup | Discover, active | Solo mode (Person A holds every internal role); intake handoff; lightweight initiate gate; moderate risk; a request in progress; one lead-time flag; a pre-assessment readiness scorecard (16.25) |
| B: Synthetic Project B | early_scale | Build, active | Design gate passed with a condition tracked as a risk; high risk mitigating; request blocked, then escalated by `RUL-000003` 48 hours later; blocked task; request awaiting approval; open sev2 issue; missed milestone; pre-assessment scorecard (37.5) |
| C: Synthetic Project C | structured_growth | Launch, awaiting_gate | Rework loop (validate, build, validate); formal gates; request handed off and accepted by a named support owner; resolved issues; launch-review scorecard (91.25) with incomplete training evidence; no launch decision recorded |

## Coverage of statuses and events

| Item | Coverage |
|---|---|
| Phase statuses | completed, active, awaiting_gate |
| Task statuses | completed 19, not_started 6, in_progress 4, blocked 1 |
| Request statuses | eight of nine in final records (submitted, triaged, awaiting_approval, accepted, in_progress, blocked, handed_off, closed); ready_for_handoff appears in a transition |
| Milestone statuses | achieved, planned, missed |
| Risk statuses | open, mitigating, accepted, closed |
| Issue statuses and severities | open, in_progress, resolved, closed; sev2, sev3, sev4 |
| Gate outcomes in events | pass (3), pass_with_conditions (1). Project C's rework loop implies an earlier hold on its first validate gate, which is outside the event sample |
| Event types (16) | project.created 1, phase.entered 5, phase.exited 4, gate.assessed 4, task.status_changed 2, milestone.achieved 2, milestone.missed 1, request.submitted 2, request.status_changed 5, request.escalated 1, handoff.completed 2, risk.logged 2, risk.status_changed 1, issue.logged 2, issue.resolved 1, readiness.scored 3 |
| Actors | 34 human (`PER-`), 4 system (`RUL-000003`, `RUL-000301`), 0 AI |
| Scenario-pack events | 0 |

## Honesty checks

- The readiness rows for Projects A and B are `pre_assessment` scorecards. They feed no gate and are not launch results.
- Project C's launch gate is not recorded. Its phase is `awaiting_gate`, so the data never fakes a launch decision.
- `events.jsonl` is a deterministic sample, not a complete audit log; every event in it is consistent with the records.
