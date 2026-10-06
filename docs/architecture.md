# Architecture

R1 is an operating model for implementation work, written as files: a lifecycle, gates, record schemas, deterministic rules, configuration profiles, synthetic data, and a validator. It runs from plain files today, and the R3 workbook will implement it in a spreadsheet next. This page explains how the parts fit.

## Three layers

```text
standard/        shared vocabulary for six repositories (version 1.0.0, frozen)
   |
core             lifecycle/, schemas/, the rule logic in tools/r1_rules.py
   |
configuration    config/ rule parameters and profiles/ chosen by an organization
   |
(scenario packs) not installed in version 0.1
```

### Core

The universal operating model. It is the same for every organization:

- `lifecycle/lifecycle.yaml`: the ten phases, their entry and exit criteria, expected artifacts, owner roles, emitted events, and legal next phases.
- `lifecycle/gates.yaml`: one gate per phase from Initiate to Transition, with required evidence, deterministic checks, the approver role, and the rule that a named human records every outcome.
- `schemas/`: ten JSON Schemas for the operational records (project, phase, milestone, task, gate assessment, request, handoff, risk, issue, readiness scorecard).
- `tools/r1_rules.py`: every calculation and rule check as a plain function. Same inputs, same outputs, no AI.

The core reuses `standard/` for every shared term: ID prefixes, phase keys, phase statuses, gate outcomes, severities, readiness categories, organization stages, and the event contract. It never redefines them.

### Configuration

Organization-selected parameters and rules:

- `config/request-state-machine.yaml`: request statuses and legal transitions.
- `config/sla-rules.yaml`: timers and escalation for requests, handoffs, and issue severities.
- `config/risk-rules.yaml`: likelihood and impact scales, the score formula, and bands.
- `config/lead-time-rules.yaml`: how far ahead planned work must finish.
- `config/readiness-weights.yaml`: readiness weights and required evidence per category.
- `profiles/`: organization stage, complexity, service, and segment profiles that tune the same model.

Every number in configuration is labeled as a proposed design value, not a measured result, and as a user-configurable parameter. None of them is a benchmark.

### Optional scenario packs

Scenario packs add depth for specific situations, such as a large-scale go-live with rehearsals, a cutover runbook, and a command center. The event catalog already reserves their event names, but no pack is installed in version 0.1, and the validator rejects any pack event in the synthetic data. The core must keep passing with every pack removed.

## Authority

R1 owns implementation operational state: the lifecycle, projects, phases, milestones, tasks, requests, handoffs, risks, issues, gates, readiness, and the SLA and escalation rules. Other repositories read R1 records and events; they never change them. The full boundary is in [authority-boundaries.md](authority-boundaries.md).

Three authority rules run through every file:

1. **Humans decide.** A named person (`PER-`) records every gate outcome, every handoff acceptance, and every approval. A rule may time, score, flag, or escalate; it never decides.
2. **Rules are deterministic.** Risk scores, readiness scores, SLA timers, escalation times, lead-time flags, and gate checks come from configuration through `tools/r1_rules.py`. The validator recomputes them and fails on any difference.
3. **AI has no authority here.** No R1 rule, score, or outcome uses AI. A later repository (R6) may read R1 outputs and draft proposals; a proposal changes nothing until a named human approves it, and the change is then made through R1.

## Records and events

Each operational record has an ID in the `TYPE-NNNNNN` format from `standard/id-registry.yaml`. Records hold current state. Events (`EVT-`) record what happened, using the ten-field event contract and only event types from `standard/event-catalog.yaml`. R1 produces every core event; other repositories consume them.

```text
person or rule acts --> record changes (CSV row or schema-valid JSON) --> event appended (events.jsonl)
                                                                             |
                                                  R2, R3, R4, R6, analytics read it later
```

## Customer boundary

R1 owns implementation projects, not the customer master. A project carries two plain fields:

- `customer_reference`: an optional external reference to the customer record in whatever system the adopting organization uses (synthetic example: `SYN-CUSTOMER-A`). It is not an R1 ID, R1 does not validate it against any system, and it can never take the `TYPE-NNNNNN` form.
- `customer_label`: a display label (synthetic example: `Synthetic Organization A`).

R1 holds no customer legal record, account record, billing account, contract master, or personal data. There is no customer ID prefix.

## Scaling

The same model serves four organization stages: startup, early scale, structured growth, and mature. Smaller organizations use fewer required fields, lighter gates, and fewer active rules. They do not get a different architecture: the ten phases, the record schemas, the rules, and the human decision points stay the same. Profiles change evidence depth and parameters only. See [scaling-model.md](scaling-model.md).

## Solo IC mode

One person can hold every internal role. That is why every record assigns work to a role (`ROL-`), not to a named employee:

- A solo implementer holds implementation lead, technical specialist, enablement lead, and support owner at once. The records still say which role owns each task, so the work can be handed to a new person later without rewriting history.
- Gates still need a named human outcome. In solo mode that person is usually the implementer, recording a lightweight self-assessment against the checklist.
- Handoffs still exist. When the same person receives the work, the handoff record still states what moved and what stays open.

## Files and checks

| Concern | File | Checked by |
|---|---|---|
| Shared vocabulary | `standard/` | `tools/validate.py` V01 to V24 |
| Lifecycle and gates | `lifecycle/` | V28, V29 |
| Record shapes | `schemas/`, `profiles/profile.schema.json` | V26, V36 |
| Rules | `config/`, `tools/r1_rules.py` | V30 to V34, V38, tests |
| Profiles | `profiles/examples/` | V35 |
| Synthetic data and events | `data/synthetic/` | V36 to V39 |
| Labels, docs, genericity | all files | V15, V17, V40, V41 |
