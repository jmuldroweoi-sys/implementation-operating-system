# Changelog

This file tracks two separate versions: the repository version (headings below) and the shared-standard version (stated in each entry). See `standard/version-policy.md`.

## [0.1.0] Unreleased (pre-release, not tagged)

Shared standard 1.0.0. R1 core record schemas 0.1.0.

### Added

- Shared standard 1.0.0 established in `standard/`: glossary, ID registry, field conventions, mandatory label rules, severity scale, readiness categories, lifecycle terms, status vocabularies, organization stages, event catalog, version policy, and four shared schemas (event, approval record, recommendation, metric definition).
- R1 v0.1 operating core:
  - `lifecycle/lifecycle.yaml` (ten phases with criteria, artifacts, owner roles, events, legal moves, and stage behavior) and `lifecycle/gates.yaml` (nine gates with evidence, deterministic checks, approver roles, and human-recorded outcomes).
  - Ten record schemas in `schemas/`: project, phase, milestone, task, gate assessment, request, handoff, risk, issue, and readiness scorecard, with CSV column contracts.
  - Configuration in `config/`: request state machine, SLA rules, risk rules, lead-time rules, and readiness weights.
  - Profile schema and four illustrative example profiles in `profiles/`.
  - Synthetic data set in `data/synthetic/`: three projects, their records, three readiness scorecards, and 38 events.
  - `tools/r1_rules.py`: every deterministic rule as a function.
  - Documentation in `docs/`: architecture, authority boundaries, lifecycle overview, scaling model, practical workflow, and portfolio integration.
  - Verification records in `verification/`.
- Customer boundary: projects carry `customer_reference` and `customer_label`; there is no customer entity or customer ID prefix.
- `tools/validate.py` checks V25 to V41 for the core, and new tests for every deterministic rule.
- Repository foundation: README, license, contributing guide, CI workflow, and verification records.

### Not yet included

- Later-version R1 features (per-phase files, decision, configuration-item, environment, promotion, and improvement-item schemas, templates, and the large-scale go-live pack). No release or tag exists yet.
