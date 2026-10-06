# Deterministic rules

Every calculation and rule in R1 v0.1, where it is configured, where it is implemented, and how it is tested. Each rule is a plain function in `tools/r1_rules.py`; the validator and the tests call the same functions, so they cannot disagree. No rule and no test uses AI, randomness, the network, or the current clock.

Every number named below is a proposed design value, not a measured result, and a user-configurable parameter.

| # | Rule | Configuration | Function | Validator | Tests |
|---|---|---|---|---|---|
| 1 | Risk score = likelihood x impact, each on the configured scale (1 to 5) | `config/risk-rules.yaml` | `risk_score` | V32, V38 | `test_risk_score_is_likelihood_times_impact`, `test_rejects_risk_score_that_is_not_the_product` |
| 2 | Risk band and severity: 1 to 4 low (sev4), 5 to 9 moderate (sev3), 10 to 15 high (sev2), 16 to 25 critical (sev1); bands cover every score once | `config/risk-rules.yaml` | `risk_band`, `risk_band_problems` | V32, V39 | `test_risk_bands_and_severity`, `test_rejects_risk_severity_that_differs_from_its_band` |
| 3 | Illegal request transitions are rejected | `config/request-state-machine.yaml` | `request_transition_allowed` | V30, V39 | `test_illegal_request_transitions_rejected`, `test_rejects_illegal_request_transition_event` |
| 4 | Legal request transitions are accepted (16 transitions, 9 statuses) | `config/request-state-machine.yaml` | `request_transition_allowed` | V30, V39 | `test_legal_request_transitions_accepted` |
| 5 | Leaving `awaiting_approval` needs a named human approver | `config/request-state-machine.yaml` | (configuration rule) | V30 | `test_leaving_approval_needs_a_named_human`, `test_rejects_approval_without_named_approver` |
| 6 | Request schema statuses equal the state machine | both files | (configuration rule) | V30 | `test_rejects_state_machine_and_schema_drift` |
| 7 | Readiness: achieved_rate = met / total; category_score = weight x rate; overall = 100 x sum(weight x rate) / sum(weight); half-up rounding to 2 places | `config/readiness-weights.yaml` | `readiness_scorecard` | V38, V39 | `test_readiness_weighted_calculation`, `test_readiness_rounds_half_up_deterministically`, `test_rejects_wrong_readiness_score`, `test_rejects_readiness_event_score_mismatch` |
| 8 | Readiness weights: exactly the six canonical categories, positive, total 100 | `config/readiness-weights.yaml` | `readiness_weight_problems` | V34 | `test_readiness_weights_total`, `test_rejects_weights_that_do_not_total` |
| 9 | Incomplete required evidence: the flag is true when any category lacks its required evidence; it never changes the score | `config/readiness-weights.yaml` | `readiness_scorecard` | V38 | `test_incomplete_required_evidence_flag`, `test_rejects_hidden_incomplete_evidence` |
| 10 | Valid gate outcomes are exactly pass, pass_with_conditions, hold | `standard/lifecycle-terms.yaml`, `lifecycle/gates.yaml` | `gate_outcome_valid` | V29, V39 | `test_valid_gate_outcomes` |
| 11 | Invalid gate outcomes are rejected | same | `gate_outcome_valid` | V29, V39 | `test_invalid_gate_outcomes_rejected`, `test_rejects_invalid_gate_outcome_in_gates`, `test_rejects_invalid_gate_outcome_event` |
| 12 | Gate outcomes are recorded by a named human, never by a score, rule, or agent | `lifecycle/gates.yaml` | (configuration rule) | V29, V39 | `test_rejects_gate_outcome_not_recorded_by_a_person`, `test_rejects_ai_gate_assessor` |
| 13 | Gate checks inform the assessor and return only met or not met | `lifecycle/gates.yaml` | `GATE_CHECKS`, `gate_check_results` | V29 | `test_launch_gate_checks_inform_but_do_not_decide` |
| 14 | Phase order is the ten standard phases, 1 to 10 | `lifecycle/lifecycle.yaml` | `phase_move_allowed` | V28 | `test_phase_order`, `test_rejects_reordered_lifecycle` |
| 15 | Illegal phase moves are rejected: no skipping, no forward move without pass or pass_with_conditions, no backward move except validate to build, nothing after review | `lifecycle/lifecycle.yaml` | `phase_move_allowed` | V28, V38 | `test_illegal_phase_moves_rejected`, `test_rejects_unlisted_backward_move_in_lifecycle`, `test_rejects_illegal_phase_sequence_in_data` |
| 16 | SLA timers: due_at = entered status + target_duration; warning_at = due_at - warning_offset; ISO 8601 durations only | `config/sla-rules.yaml` | `parse_duration`, `sla_rule_for`, `sla_timer` | V31 | `test_sla_timer_parsing`, `test_rejects_unparseable_sla_duration`, `test_rejects_escalation_without_role` |
| 17 | Request escalation_due_at = status_changed_at + the target_duration of the rule for the current status; escalation fires at that time | `config/sla-rules.yaml` | `expected_escalation_due_at` | V38, V39 | `test_sla_timer_parsing`, `test_rejects_wrong_escalation_due_at`, `test_rejects_escalation_at_wrong_time` |
| 18 | Lead-time flags: due before target launch minus lead time, due before milestone minus lead time, start on or after predecessors' due dates plus lead time | `config/lead-time-rules.yaml` | `lead_time_flags` | V33, V38 | `test_lead_time_rules_parse_and_flag`, `test_rejects_unparseable_lead_time` |
| 19 | Task dependencies: a task cannot be in progress or completed while a predecessor is not completed | `schemas/task.schema.json` | (validator rule) | V38 | `test_rejects_task_started_before_its_predecessor_finished` |
| 20 | Referential integrity: zero orphans, children in the same project | all schemas | `reference_problems` | V37 | `test_orphan_references_detected`, `test_rejects_orphan_reference_in_csv`, `test_rejects_cross_project_reference`, `test_rejects_orphan_readiness_evidence` |
| 21 | Severity values come only from `standard/severity-scale.yaml` | `schemas/issue.schema.json` | (schema rule) | V36, V39 | `test_rejects_invalid_issue_severity`, `test_rejects_invalid_event_severity` |
| 22 | Project status comes only from the project schema enum | `schemas/project.schema.json` | (schema rule) | V36 | `test_rejects_invalid_project_status` |
| 23 | Events: registered type, R1 producer, no scenario-pack event, required payload, subject exists, payload matches the record, status chains end at the record status, time order | `standard/event-catalog.yaml` | (validator rule) | V39 | `test_rejects_event_subject_that_does_not_exist`, `test_rejects_event_missing_required_payload`, `test_rejects_event_payload_project_mismatch`, `test_rejects_scenario_pack_event`, `test_rejects_unregistered_event_type`, `test_rejects_event_status_chain_mismatch`, `test_rejects_out_of_order_events` |
| 24 | Profiles configure the same model: no waiving non-waivable evidence, no disabling a rule required at the profile's stage, no lifecycle fields, no removing the approver | `profiles/profile.schema.json` | (validator rule) | V35 | `test_profile_cannot_waive_non_waivable_evidence`, `test_profile_cannot_disable_a_required_rule`, `test_profile_cannot_redefine_the_lifecycle`, `test_profile_cannot_remove_the_approver` |

## Values the rules produce on the synthetic data

| Output | Value | Check |
|---|---|---|
| Risk scores `RSK-000001` to `RSK-000006` | 6, 12, 9, 8, 12, 10 (bands moderate, high, moderate, moderate, high, high) | V38 |
| Readiness `RDS-000001` (A, pre_assessment) | 16.25, incomplete required evidence | V38, V39 |
| Readiness `RDS-000002` (B, pre_assessment) | 37.5, incomplete required evidence | V38, V39 |
| Readiness `RDS-000003` (C, launch_review) | 91.25, incomplete required evidence (training) | V38, V39 |
| Escalation due times | `REQ-000002` 2026-09-26T15:00:00Z, `REQ-000003` 2026-10-06T15:00:00Z, `REQ-000008` 2026-10-06T14:00:00Z; none for the other five | V38 |
| Escalation fired | `REQ-000002` by `RUL-000003` at 2026-09-26T15:00:00Z, exactly 48 hours after it was blocked | V39 |
| Lead-time flags | 1: `RUL-000104` on `TSK-000006` (starts 2026-10-07 before `TSK-000005` is due 2026-10-08) | V38 and `test_lead_time_rules_parse_and_flag` |
| Launch gate checks for `PRJ-000003` | readiness_scored met; required_evidence_complete not met; no_open_sev1_sev2_issues met; no_open_critical_risks met; no_blocked_requests met. No outcome recorded. | `test_launch_gate_checks_inform_but_do_not_decide` |
