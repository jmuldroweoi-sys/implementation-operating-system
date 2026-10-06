# Referential integrity

Verification record for the R1 v0.1 synthetic data set. Enforced by `tools/validate.py` check V37 (using `reference_problems` in `tools/r1_rules.py`), with event subjects checked by V39. All data is synthetic data.

**Result: 0 orphan references.**

## Record references

| Reference | Count checked | Rule | Orphans |
|---|---|---|---|
| `projects.current_phase_id` to a phase | 3 | Exists, same project, and is the project's latest phase instance (V38) | 0 |
| Project profile references (`complexity_profile_id`, `service_profile_id`, `segment_profile_id`) | 9 | Each resolves to a profile in `profiles/examples/` | 0 |
| `phases.project_id` | 15 | Project exists | 0 |
| `milestones.project_id`, `milestones.phase_id` | 12, 12 | Project exists; phase exists in the same project | 0 |
| `tasks.project_id`, `tasks.phase_id` | 30, 30 | Project exists; phase exists in the same project | 0 |
| `tasks.milestone_id` | 29 (one task has no milestone) | Milestone exists in the same project | 0 |
| `tasks.predecessor_task_ids` | 29 references | Each task exists in the same project and is not the task itself | 0 |
| `requests.project_id` | 8 | Project exists | 0 |
| `risks.project_id`, `risks.phase_id` | 6, 6 | Project exists; phase exists in the same project | 0 |
| `issues.project_id`, `issues.phase_id` | 5, 5 | Project exists; phase exists in the same project | 0 |
| Readiness scorecard `project_id` | 3 scorecards (18 rows) | Project exists | 0 |
| Readiness `evidence_refs` | 17 references | Each resolves to a record of the same project | 0 |
| `phases.gate_id` | 15 | Equals the gate for that phase in `lifecycle/gates.yaml` (none for review) | 0 |
| Role references (`*_role_id`) | 87 | Each matches the registered `ROL-NNNNNN` pattern | 0 |
| Total record references | 219 | | 0 |

## Event references

| Reference | Count | Rule | Orphans |
|---|---|---|---|
| Event subjects with a CSV record (`PRJ`, `PHS`, `MLS`, `TSK`, `REQ`, `RSK`, `ISS`, `RDS`) | 32 events | Subject exists and its prefix matches the catalog subject type | 0 |
| Gate assessment subjects (`GAT-000001` to `GAT-000004`) | 4 events | Each recorded once; each `phase.exited` that cites one resolves to it, for the same project and phase | 0 |
| Handoff subjects (`HND-000001`, `HND-000002`) | 2 events | Each completed once; roles are `ROL-` IDs; accepted by a `PER-` human | 0 |
| Payload `project_id` | 30 events | Project exists and equals the subject's project | 0 |
| Gate conditions (`RSK-000002` on `GAT-000002`) | 1 | Resolves in the same project | 0 |
| Escalation rule (`RUL-000003`) and role (`ROL-000003`) | 1 event | Rule exists in `config/sla-rules.yaml` and the role matches it | 0 |
| System actors (`RUL-000003`, `RUL-000301`) | 4 events | Each is a configured rule | 0 |
| Human actors | 34 events | Each is a `PER-` ID | 0 |

Gate assessments and handoffs have no CSV file in version 0.1, by a recorded scope decision for this version. They are represented by their events and by the examples in their schemas.

## How the check detects orphans

The tests break the data on purpose and confirm the check fails:

- a task pointing at a milestone that does not exist (`test_rejects_orphan_reference_in_csv`);
- a task pointing at a phase of another project (`test_rejects_cross_project_reference`);
- readiness evidence pointing at a task that does not exist (`test_rejects_orphan_readiness_evidence`);
- an event whose subject does not exist (`test_rejects_event_subject_that_does_not_exist`);
- an event payload naming a different project from its subject (`test_rejects_event_payload_project_mismatch`);
- missing milestone, predecessor, project, and cross-project references in the rule function itself (`test_orphan_references_detected`).
