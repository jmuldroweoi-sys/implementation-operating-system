# Scaling model

R1 uses one model for every organization stage. The ten phases, the record schemas, the deterministic rules, and the human decision points stay the same from a one-person startup to a mature delivery organization. What changes is how much evidence each gate needs, how formally it is recorded, which optional rules are switched on, and how many roles are held by different people.

The four stages come from `standard/org-stages.yaml`. A person chooses the stage that describes the organization; no rule assigns it from headcount. The stage descriptions are not measured benchmarks.

## What changes and what never changes

| Never changes | Changes by stage, through profiles and configuration |
|---|---|
| Ten phases, their order, and legal moves | Gate formality (lightweight, standard, formal) |
| Record schemas and their minimum required fields | Extra required fields (a profile can add, never remove) |
| ID formats and the event contract | Which waivable evidence is optional |
| Gate outcomes recorded by a named human | Who holds the approver role |
| Deterministic formulas (risk, readiness, timers) | Parameter values such as timer durations and lead times |
| No AI authority | Which optional SLA rules are switched on |

## Startup

One person, or a few people, run implementations alongside other customer work.

- **Fewer required fields.** Only each schema's minimum is required. Planned hours, for example, are optional until a complexity profile asks for them.
- **One person may hold all internal roles.** The implementer is implementation lead, technical specialist, enablement lead, and support owner. Records still name the role that owns each task, so work can be handed over later.
- **Lighter gates.** The `org-stage-startup` profile records every gate at lightweight formality and marks waivable evidence optional (for example the kickoff record and the test plan). Evidence that is not waivable, such as the design approval and acceptance sign-off, stays required. The outcome is still recorded by a named person.
- **Plain files or the R3 workbook.** A startup can run R1 from the CSV files and this validator, or use the R3 workbook, whose Starter Mode works on the same fields.
- **Rules.** Request timers are optional; the startup example profile relaxes the triage timer. Issue response rules for sev1 stay required at every stage.

## Early scale

A small team of generalists runs several projects at once.

- **Shared lifecycle.** Everyone uses the same ten phases and the same gate checklist, so delivery quality varies less between people.
- **Explicit owner roles.** Each phase, task, request, and risk names an owner role, and different people start to hold different roles.
- **Consistent gate evidence.** Gates are recorded at standard formality: evidence is attached, not just remembered.
- **Rules.** Blocked-request escalation and sev2 issue response become required. Complexity tiers start to matter, for example asking for planned hours on tasks.

## Structured growth

The function has leads, first specialists, and emerging enablement and operations roles.

- **More required controls.** Profiles add required fields and evidence. Every SLA rule for requests and handoffs is required.
- **Specialist roles.** Technical specialists, enablement leads, and support owners are usually different people from the implementation lead.
- **More formal handoffs.** Handoffs are accepted by a named person in the receiving role, and the open items list is part of the transition gate.
- **Stronger auditability.** Gates are recorded at formal level. The launch gate is recorded by a named approver in the delivery leadership role, separate from the project owner.

## Mature

Multiple teams deliver in a segmented way with dedicated operations and enablement functions.

- **Segmented delivery.** Segment and service profiles tune evidence and timers for different customer groups without changing the lifecycle.
- **Portfolio governance.** Events from every project feed portfolio reporting. R2 consumes task hours and request workload for capacity planning.
- **Operations integration.** Delivery operations own the configuration files. Changes to rules and profiles are versioned and released like any other configuration.
- **Formal change control.** Design changes after approval go through requests in `awaiting_approval` with an approval record. Large launches may add the optional large-scale go-live pack when it exists (not installed in version 0.1).

## How the synthetic data shows this

| Scenario | Stage | What it shows |
|---|---|---|
| Synthetic Project A | startup | One person (Person A) holds every internal role and records the initiate gate as a lightweight self-assessment |
| Synthetic Project B | early_scale | A shared lifecycle with explicit roles; a design gate passed with a tracked condition; a blocked request escalated by rule |
| Synthetic Project C | structured_growth | A rework loop from Validate to Build, formal evidence, and a launch gate waiting for a named approver |

All three use the same schemas, rules, and validator.
