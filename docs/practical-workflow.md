# Practical workflow: running one implementation with R1

How can one implementation professional use this directly in their job? By running each project through this workflow, using the R1 files as the project record and the validator as the check that the record is right.

This page is an illustrative example built on synthetic data. It follows **Synthetic Project A** (`PRJ-000001`, customer label "Synthetic Organization A", organization stage `startup`) from intake to review. One person, Person A (`PER-000001`), holds every internal role. No real company, customer, or result is represented.

Steps 1 to 5 match the records in [`data/synthetic/`](../data/synthetic/), which hold Project A as of 2026-10-05, in its Discover phase. Steps 6 to 17 continue Project A as an illustrative example beyond the data set. Project A has not reached those phases in the data, so where a later step has a rule you can check, a separate **Data-set comparison** note under the step points to Synthetic Project B or C, which already hold that situation. Those notes are comparisons only; the story stays with Project A.

## Trigger

A signed intake arrives from the role that closed the agreement (the commercial owner role, `ROL-000008`). In a startup, the implementer usually starts the workflow personally on the day the intake arrives.

## Inputs

| Input | Where it goes |
|---|---|
| Project name, customer reference, customer label | `projects.csv` (`customer_reference` is a pointer to the customer record in your own system, such as `SYN-CUSTOMER-A`; R1 does not own that record) |
| Organization stage and the complexity, service, and segment profiles | `projects.csv` (`org_stage`, `complexity_profile_id`, `service_profile_id`, `segment_profile_id`) |
| Target launch date | `projects.csv` (`target_launch_date`), set by a person, never predicted |
| Owner roles | `ROL-` IDs on every record; the synthetic role list is in [`data/synthetic/README.md`](../data/synthetic/README.md) |
| Milestones and tasks, with dates, hours, and predecessors | `milestones.csv`, `tasks.csv` |
| Requests, risks, issues as they arise | `requests.csv`, `risks.csv`, `issues.csv` |
| Readiness criteria counts per category | `readiness.csv` |
| Rule parameters | `config/` (each a user-configurable parameter) |

## Steps

Each step lists the user action, the record that changes, the deterministic rule that applies, the event emitted, the human decision, and the downstream consumer.

### Step 1. Intake received

- **User action:** Person A reads the intake and checks it names the scope, a target launch date, and the customer reference.
- **Record changed:** none yet. The intake stays in the organization's own system.
- **Deterministic rule:** none.
- **Event emitted:** none.
- **Human decision:** Person A decides the intake is complete enough to start.
- **Downstream consumer:** none yet.

### Step 2. Project created

- **User action:** add one row to `projects.csv`.
- **Record changed:** `PRJ-000001`, status `active`, stage `startup`, target launch `2026-12-01`, owner role `ROL-000001` (implementation lead), profiles `PRF-000002`, `PRF-000003`, `PRF-000004`.
- **Deterministic rule:** the project schema requires the minimum fields; the segment profile `PRF-000004` adds `target_launch_date` as required.
- **Event emitted:** `project.created` (`EVT-000001`).
- **Human decision:** Person A chooses the organization stage and the profiles.
- **Downstream consumer:** R2 (future workload), R3 (Projects tab), R6 (status drafts).

### Step 3. Initiate entered

- **User action:** add the Initiate phase instance and record the intake handoff as accepted.
- **Record changed:** `PHS-000001` (initiate, `active`); handoff `HND-000001` from `ROL-000008` (commercial owner) to `ROL-000001`, accepted by `PER-000001`.
- **Deterministic rule:** the `handoff_acceptance` timer (`RUL-000004`, 72 hours, a user-configurable parameter) would notify delivery leadership if the handoff sat unaccepted.
- **Event emitted:** `phase.entered` (`EVT-000002`), `handoff.completed` (`EVT-000003`).
- **Human decision:** Person A accepts the handoff by name. A rule never accepts a handoff.
- **Downstream consumer:** R2 and R3 (phase position), R4 (phase events tell enablement when training is coming).

### Step 4. Milestone and task records created

- **User action:** plan the first two milestones and six tasks with owners, dates, hours, and predecessors.
- **Record changed:** `MLS-000001` (Kickoff completed), `MLS-000002` (Current-state discovery signed off), `TSK-000001` to `TSK-000006`. `TSK-000006` depends on `TSK-000004` and `TSK-000005`.
- **Deterministic rule:** a task cannot be in progress or completed while a predecessor is not completed (validator V38). Lead-time rule `RUL-000104` flags `TSK-000006`, which is planned to start on 2026-10-07, before its predecessor `TSK-000005` is due on 2026-10-08. The flag asks Person A to re-plan; it changes nothing.
- **Event emitted:** `task.status_changed` when work moves (`EVT-000005`: `TSK-000001` completed), and `milestone.achieved` (`EVT-000006`: `MLS-000001` on 2026-09-10).
- **Human decision:** Person A sets every date, estimate, and dependency.
- **Downstream consumer:** R2 reads `planned_hours` and `actual_hours` (R1 never turns them into capacity); R3 Tasks tab.

### Step 5. Discover

- **User action:** record the Initiate gate, move to Discover, and start discovery work.
- **Record changed:** gate assessment `GAT-000001` (outcome `pass`, assessor `PER-000001`); `PHS-000001` completed; `PHS-000002` (discover) active; request `REQ-000001` from the customer sponsor role, now `in_progress`; risk `RSK-000001` (likelihood 3, impact 2).
- **Deterministic rule:** the gate checks `critical_tasks_closed` and `critical_milestones_achieved` were met; a forward move needs `pass` or `pass_with_conditions` (`phase_move_allowed`); `risk_score` = 3 x 2 = 6, band `moderate`, severity `sev3` (`config/risk-rules.yaml`); the request followed the legal path submitted, triaged, accepted, in_progress (`config/request-state-machine.yaml`).
- **Event emitted:** `gate.assessed` (`EVT-000013`), `phase.exited` (`EVT-000014`, citing `GAT-000001`), `phase.entered` (`EVT-000015`), `risk.logged` (`EVT-000020`, severity `sev3`).
- **Human decision:** Person A records the gate outcome as a lightweight self-assessment (the startup profile), and chooses the risk's likelihood and impact.
- **Downstream consumer:** R3 (gate and risk tabs), R6 (may draft a status note for Person A to review).

Project A is here in the data set. Its pre-assessment readiness scorecard `RDS-000001` scores 16.25 with required evidence incomplete, which is expected this early; a pre-assessment shows gaps and feeds no gate.

### Step 6. Design

- **User action:** write the solution design, get the customer sponsor's approval, and record the Design gate.
- **Record changed:** a Design phase instance; a gate assessment for `design_gate`. If a requested change needs a decision, its request goes to `awaiting_approval`.
- **Deterministic rule:** leaving `awaiting_approval` needs an approval record by a named approver. The `request_approval_wait` timer (`RUL-000002`, 72 hours) escalates a request that waits too long.
- **Event emitted:** `phase.exited`, `phase.entered`, `request.status_changed`, `gate.assessed`.
- **Human decision:** the sponsor approves the design; Person A records the gate.
- **Downstream consumer:** R3, R6.

> **Data-set comparison (Synthetic Project B):** request `REQ-000003` waits in `awaiting_approval` with `escalation_due_at` = `status_changed_at` + 72 hours, and design gate `GAT-000002` records `pass_with_conditions`, with its condition tracked as risk `RSK-000002`.

### Step 7. Build

- **User action:** configure, build integrations, and log issues as they appear.
- **Record changed:** Build tasks move through their statuses; issues are logged with a severity from the shared scale.
- **Deterministic rule:** if a request is `blocked` for longer than `RUL-000003` allows (48 hours, a user-configurable parameter), the rule escalates it to the delivery leadership role with severity `sev2`. Issue timers `RUL-000005` to `RUL-000008` notify by severity.
- **Event emitted:** `task.status_changed`, `request.status_changed`, `request.escalated`, `issue.logged`, `issue.resolved`, `milestone.missed` when a date passes.
- **Human decision:** the role receiving an escalation decides what to do; the rule only notifies.
- **Downstream consumer:** R2 (request workload and blocked work), R3 (overdue and escalation flags).

> **Data-set comparison (Synthetic Project B):** `REQ-000002` was blocked at 2026-09-24T15:00:00Z and escalated by rule at 2026-09-26T15:00:00Z (`EVT-000027`), and milestone `MLS-000005` was missed.

### Step 8. Validate

- **User action:** run acceptance scenarios with the customer and record the Validate gate.
- **Record changed:** acceptance tasks; issues; a Validate gate assessment.
- **Deterministic rule:** the gate check `no_open_sev1_sev2_issues` must be met before a pass is sensible. A `hold` sends the project back to Build as a new phase instance (the only backward move).
- **Event emitted:** `gate.assessed`, `phase.exited`, `phase.entered`.
- **Human decision:** the customer sponsor accepts the build; Person A records the outcome.
- **Downstream consumer:** R3; R5 may use defect history as context for quality review, without changing it.

> **Data-set comparison (Synthetic Project C):** validate phase `PHS-000011` was followed by a rework build phase `PHS-000012` and a second validate phase `PHS-000013`, which passed (`GAT-000003`).

### Step 9. Enable

- **User action:** train each user group and publish the support runbook.
- **Record changed:** Enable tasks and the `Training delivered` milestone; training completion evidence.
- **Deterministic rule:** lead-time rule `RUL-000101` flags critical Enable tasks due less than 5 days before the target launch.
- **Event emitted:** `task.status_changed`, `milestone.achieved`, `gate.assessed`, `phase.exited`, `phase.entered`.
- **Human decision:** Person A records the Enable gate.
- **Downstream consumer:** R4 supplies training completion evidence; R1 never grades learners.

### Step 10. Readiness score calculated

- **User action:** count, for each of the six categories, how many readiness criteria are met and whether the required evidence is present.
- **Record changed:** a readiness scorecard (`RDS-`) with six entries (`RDE-`) and `assessment_purpose` `launch_review`.
- **Deterministic rule:** `config/readiness-weights.yaml`: `achieved_rate` = met / total, `category_score` = weight x `achieved_rate`, `overall_score` = 100 x sum(weight x rate) / sum(weight), and `incomplete_required_evidence_flag` is true if any category lacks its required evidence.
- **Event emitted:** `readiness.scored`, with the readiness rule `RUL-000301` as the system actor.
- **Human decision:** a person confirms which criteria are met. The score itself decides nothing.
- **Downstream consumer:** R2 (reporting), R3 (Readiness tab mirrors the formula), R6 (may summarize gaps).

> **Data-set comparison (Synthetic Project C):** scorecard `RDS-000003` scores 91.25 with the incomplete-evidence flag true, because training sign-offs are not complete.

### Step 11. Human Launch gate decision

- **User action:** review the scorecard and the launch gate checks, then record the outcome.
- **Record changed:** a gate assessment for `launch_gate`, with evidence references and, for `pass_with_conditions`, the records that track each condition.
- **Deterministic rule:** the launch checks are `readiness_scored`, `required_evidence_complete`, `no_open_sev1_sev2_issues`, `no_open_critical_risks`, and `no_blocked_requests`.
- **Event emitted:** `gate.assessed`.
- **Human decision:** **the launch decision.** A named person in the approver role records pass, pass_with_conditions, or hold. In a startup that is usually Person A with the sponsor. No score, rule, or AI makes this decision.
- **Downstream consumer:** R2 (launch support planning), R3, R6.

> **Data-set comparison (Synthetic Project C):** every launch check is met except `required_evidence_complete`, and the launch gate is deliberately unrecorded (`PHS-000015` is `awaiting_gate`), so the data never fakes a launch decision.

### Step 12. Launch

- **User action:** put the system into use and record the date.
- **Record changed:** `actual_launch_date` on the project; the Launch phase instance completes; a Stabilize phase instance starts.
- **Deterministic rule:** the forward move needs the launch gate outcome `pass` or `pass_with_conditions`.
- **Event emitted:** `phase.exited`, `phase.entered`, `milestone.achieved`.
- **Human decision:** carry out the launch plan.
- **Downstream consumer:** R2 (launch support signals), R3.

### Step 13. Stabilize

- **User action:** support early use and work the issue list.
- **Record changed:** issues and requests; the Stabilize gate assessment.
- **Deterministic rule:** issue response timers by severity (`sev1` to `sev4` keys in `config/sla-rules.yaml`); the gate checks `no_open_sev1_sev2_issues` and `no_blocked_requests`.
- **Event emitted:** `issue.logged`, `issue.resolved`, `request.submitted`, `request.status_changed`, `gate.assessed`.
- **Human decision:** Person A records when early use is stable enough to hand over.
- **Downstream consumer:** R2 (post-launch support load), R3.

### Step 14. Transition

- **User action:** request the transition handoff to the support owner role, listing the required artifacts and the open items.
- **Record changed:** a handoff (`HND-`) of type `transition`, status `requested`, with `required_artifact_refs` and `open_item_refs`.
- **Deterministic rule:** the `handoff_acceptance` timer (`RUL-000004`) starts at `requested_at`.
- **Event emitted:** `phase.entered` (transition).
- **Human decision:** Person A decides what is ready to hand over and what stays open.
- **Downstream consumer:** R3.

### Step 15. Handoff accepted

- **User action:** the person in the support owner role reviews the handoff and accepts it.
- **Record changed:** the handoff becomes `accepted`, with `accepted_at` and `acceptance_person_id`. In a startup that person may again be Person A; the record still exists.
- **Deterministic rule:** the transition gate check `handoff_accepted`.
- **Event emitted:** `handoff.completed`, then `gate.assessed` for `transition_gate`.
- **Human decision:** a named person accepts. A handoff is never accepted by a rule or an agent.
- **Downstream consumer:** R2 (ownership moves off the implementation team's workload), R3.

> **Data-set comparison (Synthetic Project C):** handoff `HND-000002` shows a request handoff accepted by `PER-000005`.

### Step 16. Review

- **User action:** hold the review, record lessons learned, and close the project.
- **Record changed:** a Review phase instance; `project_status` becomes `completed`.
- **Deterministic rule:** Review has no gate and no next phase.
- **Event emitted:** `phase.entered`, `phase.exited`, `project.status_changed` (active to completed).
- **Human decision:** Person A decides the project is complete.
- **Downstream consumer:** R2, R3, analytics.

### Step 17. Improvement signal captured

- **User action:** write each change to the delivery method that the review suggests, for example "plan discovery sessions two weeks ahead by default".
- **Record changed:** an improvement signal. Version 0.1 records it as the catalog event only; the improvement-item schema arrives in a later version.
- **Deterministic rule:** none. An improvement signal is information, not a rule change.
- **Event emitted:** `improvement.logged` (informational).
- **Human decision:** Person A decides whether a signal becomes a change to `config/` or to a profile, which is then versioned like any configuration change.
- **Downstream consumer:** R3, R5 (method context), R6 (may draft a proposed method change for a human to approve).

## Deterministic rules

| Rule | Owning file | Function in `tools/r1_rules.py` |
|---|---|---|
| Legal phase moves and the rework loop | `lifecycle/lifecycle.yaml` | `phase_move_allowed` |
| Gate outcomes are pass, pass_with_conditions, or hold | `standard/lifecycle-terms.yaml`, `lifecycle/gates.yaml` | `gate_outcome_valid` |
| Gate checks that inform the assessor | `lifecycle/gates.yaml` | `GATE_CHECKS`, `gate_check_results` |
| Legal request transitions | `config/request-state-machine.yaml` | `request_transition_allowed` |
| SLA timers and request escalation time | `config/sla-rules.yaml` | `sla_rule_for`, `sla_timer`, `expected_escalation_due_at` |
| Risk score and band | `config/risk-rules.yaml` | `risk_score`, `risk_band` |
| Lead-time flags | `config/lead-time-rules.yaml` | `lead_time_flags` |
| Readiness scorecard | `config/readiness-weights.yaml` | `readiness_scorecard` |
| Referential integrity | all schemas | `reference_problems` |

Every duration, weight, scale, and threshold in those files is a proposed design value, not a measured result, and a user-configurable parameter.

## Outputs

- Project, phase, milestone, task, request, risk, issue, and readiness records (`PRJ-`, `PHS-`, `MLS-`, `TSK-`, `REQ-`, `RSK-`, `ISS-`, `RDS-`, `RDE-`) in `data/synthetic/` or your own copy of those files.
- Gate assessments (`GAT-`) and handoffs (`HND-`), shaped by their schemas and recorded through their events.
- An event log (`events.jsonl`) that other repositories can read.
- Lead-time flags and gate check results, printed on demand, for the person to act on.

## Events

Project A's path uses only R1 core events from `standard/event-catalog.yaml`: `project.created`, `phase.entered`, `phase.exited`, `handoff.completed`, `task.status_changed`, `milestone.achieved`, `milestone.missed`, `gate.assessed`, `request.submitted`, `request.status_changed`, `request.escalated`, `risk.logged`, `risk.status_changed`, `issue.logged`, `issue.resolved`, `readiness.scored`, `project.status_changed`, and `improvement.logged`. No scenario-pack event is used, because no pack is installed.

## Human decisions

| Decision | Who records it |
|---|---|
| Start the project, choose the stage and profiles, set the target launch date | Person A (implementation lead role) |
| Every task date, estimate, and dependency | The task's owner role |
| Every gate outcome, including the launch decision | A named person in the gate's approver role |
| Approving a request that waits in `awaiting_approval` | A named approver, through an approval record |
| Accepting a handoff | A named person in the receiving role |
| Likelihood and impact of each risk | The risk's owner role |
| What to do about an escalation | The role that receives it |
| Whether an improvement signal changes the method | Person A, or the method owner at larger stages |

No AI makes any of these decisions, and no rule makes them either: rules only calculate, time, flag, and notify.

## Downstream integrations

- **R2 capacity:** reads task hours, phase positions, request workload, and launch support signals. It calculates capacity; R1 never does.
- **R3 workbook:** implements these records as tabs with the same field names and mirrors the formulas above.
- **R4 enablement:** supplies training completion evidence for Enable and for the training readiness category.
- **R5 team management:** may use R1 records as context; it never changes project facts.
- **R6 AI assistance:** may read permitted R1 outputs and draft proposals, such as a weekly status note; a named human approves anything that changes.

See [portfolio-integration.md](portfolio-integration.md).

## Verification

Run these from the repository root after every change to the records:

```text
python tools/validate.py
python -m unittest discover -s tests -v
```

The validator recomputes every risk score, readiness score, and escalation time; checks every reference (zero orphans); replays every event against the records and the request state machine; and reports how many lead-time flags are raised. A result of `RESULT: PASS` means the record is internally consistent. It does not mean the project is ready: that is still a human decision at each gate.

## What a solo IC does each week

One implementation professional running several projects can work through this list each week:

1. **Update tasks.** Move each task's status, record actual hours, and append a `task.status_changed` event for each move.
2. **Work the request queue.** Triage new requests, move each one only along a legal transition, and check `escalation_due_at` for anything close to its timer.
3. **Review risks and issues.** Re-score any risk whose likelihood or impact changed, and confirm every open sev1 and sev2 issue has an owner role and a next step.
4. **Check milestones.** Mark achieved milestones with their date, and record `milestone.missed` for any target date that has passed.
5. **Run the validator.** Fix any failure before trusting the record, and re-plan any task the lead-time flags name.
6. **Prepare the next gate.** For the phase that ends next, run its gate checks, collect the evidence types it requires, and book the gate with the approver.
7. **Send status.** Write a short status for each sponsor from the records (or review a draft that R6 prepared).

## Solo use

One person holds every internal role. The startup profile keeps gates lightweight and waivable evidence optional, but every gate outcome and handoff acceptance is still recorded by name. The plain files and the validator are enough; the R3 workbook's Starter Mode offers the same fields in a spreadsheet.

## Early-scale use

A small team shares one copy of the records. Each person owns roles, gates are recorded at standard formality with evidence attached, and blocked-request escalation is switched on, so stalled work reaches the delivery leadership role without anyone chasing it.

## Structured-growth use

Specialists hold separate roles. Gates are formal, the launch gate is recorded by a named approver in the delivery leadership role, handoffs are accepted by a named person in the receiving role, and every SLA rule for requests and handoffs is required.

## Mature use

Several teams use segment and service profiles on the same model. Events from every project feed portfolio reporting and R2 capacity planning, configuration changes are versioned and released through change control, and large launches can add the optional large-scale go-live pack when it exists.
