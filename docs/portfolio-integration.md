# Portfolio integration

R1 is the first of six connected repositories. This page states what each of the others takes from R1 and what each may never do with it. The authority rules are in [authority-boundaries.md](authority-boundaries.md). None of the other repositories is built yet; this page records the contract they will be built against.

```text
                       R1 records and events (authoritative)
          +-------------+-------------+-------------+-------------+
          |             |             |             |             |
         R2            R3            R4            R5            R6
      capacity      workbook     enablement    team mgmt.    AI drafts
     (reads)    (implements R1) (supplies    (context only) (recommends
                                 evidence)                    only)
```

## R2 consumes later

R2 (`implementation-capacity-and-org-design`) turns workload into capacity and staffing signals. It reads, and never writes:

| R1 data | Source | What R2 uses it for |
|---|---|---|
| Task hours | `planned_hours`, `actual_hours` in task records; `task.status_changed` events | Demand and effort trends. R1 stores hours as operational data and never calculates capacity from them. |
| Project phase | `current_phase_id`, phase instances, `phase.entered` and `phase.exited` events | Which projects need which kind of work, and when |
| Request workload | Request records, `request.submitted` and `request.status_changed` events | Volume and age of open requests by role |
| Launch support signals | `target_launch_date`, the launch gate (`gate.assessed`), `readiness.scored`, and Stabilize phase events | Planning support coverage around launches |
| Handoffs | `handoff.completed` events | When responsibility leaves the implementation team |

R2 may never recalculate R1 readiness, risk, or gate logic, or change any R1 record.

## R3 implements R1

R3 (`implementation-tracker-workbook`) is the spreadsheet reference implementation of R1. It uses the same field names, IDs, statuses, and formulas:

- Each CSV in `data/synthetic/` maps to a tab with identical columns (the `x-csv-columns` list in each schema).
- Risk score, readiness score, escalation due time, and lead-time flags are formulas that must return the same values as `tools/r1_rules.py`.
- R3 owns no weights, thresholds, statuses, or transitions of its own for R1 concepts. A difference between R3 and R1 is an R3 defect.
- Starter mode serves a solo implementer with each schema's minimum fields.

## R4 provides Enable and training evidence

R4 (`implementation-enablement-program`) supplies training completion and proficiency evidence:

- R1's Enable phase and the `training` readiness category accept R4 completion records as evidence.
- R4 consumes `phase.entered` and `gate.assessed` to know when training is needed.
- R1 never grades a learner; R4 never records a gate outcome.

## R5 uses R1 context

R5 (`implementation-team-management-toolkit`) may use R1 records and events as context, for example which projects a person's roles touched. It does not alter project truth: no R5 action changes an R1 status, score, date, or outcome, and R1 holds no people judgments.

## R6 recommends only

R6 (`implementation-ai-agent-framework`) may read permitted R1 authoritative outputs, such as records and events, and produce recommendations (`REC-`) only. A recommendation has no authority until a named human approves it through an approval record (`APR-`); the approved change is then made through R1 like any other change. R6 never records a gate outcome, accepts a handoff, scores readiness, or moves a request.

## Analytics

An analytics track may consume the synthetic R1 event data (`data/synthetic/events.jsonl`) and records later, to practice reporting on the shared event contract. Every chart or table built from them must carry the synthetic data label. Analytics results are never written back into R1.

## Contract stability

Consumers pin `standard/` version 1.0.0 and the R1 core record schemas at version 0.1.0 (`schema_version` on each record). Changes follow `standard/version-policy.md` and the R1 changelog.
