# Authority boundaries

Each fact in the portfolio has exactly one owner. Other repositories may read it, mirror it, or report on it; only the owner changes it. This page states what R1 owns and what it deliberately does not.

## R1 owns

| Concept | Where it is defined | What owning it means |
|---|---|---|
| Lifecycle | `lifecycle/lifecycle.yaml` (phase vocabulary in `standard/lifecycle-terms.yaml`) | The ten phases, their criteria, and the legal moves between them |
| Project | `schemas/project.schema.json` | The project record and the only project status vocabulary |
| Phase | `schemas/phase.schema.json` | Phase instances per project, with entry and exit times |
| Milestone | `schemas/milestone.schema.json` | Dated checkpoints and whether they were achieved or missed |
| Task | `schemas/task.schema.json` | Work items, owners, dependencies, and planned and actual hours as operational data |
| Requests | `schemas/request.schema.json`, `config/request-state-machine.yaml` | Request records, statuses, and legal transitions |
| Handoffs | `schemas/handoff.schema.json` | Transfers of responsibility and their named acceptance |
| Risks | `schemas/risk.schema.json`, `config/risk-rules.yaml` | Risk records, the score formula, and the bands |
| Issues | `schemas/issue.schema.json` | Issue records using the shared severity values |
| Gates | `lifecycle/gates.yaml`, `schemas/gate-assessment.schema.json` | Gate evidence, checks, and the human-recorded outcome |
| Readiness | `config/readiness-weights.yaml`, `schemas/readiness-scorecard.schema.json` | Weights, required evidence, and the readiness calculation |
| SLA and escalation rules | `config/sla-rules.yaml`, `config/lead-time-rules.yaml` | Timers, escalation roles, and lead-time flags |
| Shared standard | `standard/` | Vocabulary, IDs, labels, and the event contract for all six repositories |

## R1 does not own

| Concept | Owner | How R1 relates to it |
|---|---|---|
| Staffing and capacity calculations | R2 (`implementation-capacity-and-org-design`) | R1 supplies task hours, phase positions, and request workload as data. R1 never calculates capacity, load, or staffing. |
| Spreadsheet implementation | R3 (`implementation-tracker-workbook`) | R3 implements R1 with the same field names and mirrors R1 formulas. R3 owns no rule, weight, or status of its own for R1 concepts. |
| Curriculum and proficiency | R4 (`implementation-enablement-program`) | R1's Enable phase and training readiness accept R4 completion evidence. R1 never grades learners. |
| People judgments | R5 (`implementation-team-management-toolkit`) | R5 may use R1 records as context. R1 holds no performance rating, competency score, or personal judgment, and R5 never changes R1 project facts. |
| AI workflow | R6 (`implementation-ai-agent-framework`) | R6 may read permitted R1 outputs and draft recommendations. R1 grants AI no authority over any record, score, or outcome. |
| Customer master record | The adopting organization's own customer system | R1 stores only `customer_reference` (a free-form pointer) and `customer_label` (a display label). |
| Contracts and billing | The adopting organization's commercial and finance systems | R1 holds no contract terms, prices, invoices, or billing accounts. |
| HR records | The adopting organization's people systems | R1 identifies people only by `PER-` ID and assigns work to roles. It holds no names, contact details, or employment data. |

## Decision rights inside R1

| Decision | Made by | Never made by |
|---|---|---|
| Gate outcome (pass, pass_with_conditions, hold) | A named human holding the gate's approver role | A readiness score, a rule, a check, or AI |
| Launch decision | A named human recording the launch gate | The readiness score |
| Request approval (leaving awaiting_approval) | A named approver, through an approval record (`APR-`) | The request owner alone, a timer, or AI |
| Handoff acceptance | A named person in the receiving role | The sender, a rule, or AI |
| Likelihood and impact of a risk | The risk owner role | A formula (the formula only multiplies) |
| Organization stage and profiles | A person choosing for the organization | Headcount or any automatic rule |
| Escalation of a stalled request | The deterministic SLA rule, which only notifies a named role | AI |

## Where a conflict would be resolved

If another repository needs a new R1 field, status, or rule, the change is made in R1 (and in `standard/` when it is shared vocabulary) under `standard/version-policy.md`, then consumed downstream. A downstream copy that diverges from R1 is a defect in the downstream repository.
