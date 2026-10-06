# implementation-operating-system

A vendor-neutral operating system for running software implementation projects: one lifecycle, deterministic rules, shared data contracts, and practical tools that one implementation professional can run directly and a larger team can scale.

> **Build status: pre-release.** Only the shared standard (`standard/`, version 1.0.0) exists so far. The operating system core described below is not built yet. Nothing here is a finished product, and nothing here reports a historical result.

## What this repository will become

The first of six connected repositories for implementation work. When the core is built (repository version 0.1), it will provide:

- one reference lifecycle of ten phases (Initiate, Discover, Design, Build, Validate, Enable, Launch, Stabilize, Transition, Review) with gate checklists
- schemas for projects, phases, milestones, tasks, gate assessments, requests, handoffs, risks, issues, and readiness scorecards
- deterministic SLA, escalation, risk, and readiness rules in configuration
- configuration profiles for different organization stages
- synthetic data and a working validation script

The companion repositories cover a spreadsheet tracker, capacity and organization design, an enablement program, a team management toolkit, and a governed AI assistance framework. Each one pins the shared standard in this repository.

## Current build status

| Part | Status |
|---|---|
| `standard/` shared standard 1.0.0 | Built and validated |
| Lifecycle, gates, operational schemas, rules, profiles | Not started (next build) |
| Synthetic data, scenario packs | Not started |
| Practical workflow guide (`docs/practical-workflow.md`) | Not started; arrives with the core |
| Public release | Not authorized. See `verification/release-gate.md` |

## What `standard/` provides

The shared contract every repository uses: one glossary, one ID registry (`TYPE-NNNNNN`), field naming conventions, four mandatory labels, a severity scale, six readiness categories, lifecycle terms, shared status vocabularies, four organization stages, one event catalog, and four shared schemas (event, approval record, recommendation, metric definition). Start with [standard/README.md](standard/README.md).

## What is intentionally not built yet

The lifecycle files, gate criteria, operational schemas, SLA and risk rules, readiness weights, profiles, scenario packs, and synthetic project data. They are built next, on top of this standard, so they cannot drift from it.

## Why a hands-on implementer needs a shared standard

If you run implementations yourself, you already juggle a tracker, status notes, training records, and maybe an AI assistant. When each of them uses its own words and IDs, the same project, task, risk, readiness score, training record, or AI recommendation ends up meaning something different depending on which tool is open. The shared standard fixes that at the source: one name and one ID for each thing, one list of statuses, and one record of what happened. That is what lets a solo implementer keep a clean tracker today and lets the same records feed capacity planning, training, and reporting later without rework.

## Genericity and public safety

- Industry-neutral and vendor-neutral. No real company, customer, vendor, product, or employer appears anywhere.
- No fictional company or product premise either. Examples use neutral scenario labels (Scenario A to E) and role labels with IDs, never human-style names.
- All data is synthetic data. Every design number is labeled as a proposed design value, not a measured result.
- Everything is freshly written. No source document, training material, or screenshot from any organization is reproduced.

## Deterministic authority

Every calculation, score, and status in this system comes from documented rules and formulas that give the same answer every time. Records owned by one repository are never recalculated or redefined by another.

## AI boundary

AI may draft, summarize, explain, organize, flag, and recommend. It never calculates an authoritative number, changes an authoritative status, decides a gate or a go or no-go, passes or fails a learner, rates or ranks a person, or makes a hiring, staffing, customer, or contract decision. AI proposals are recommendation records with status proposed, approved, or rejected, and only a named human approves them through an approval record. The approval schema allows only a human approver.

## Versioning

| Version | Value |
|---|---|
| Shared standard | 1.0.0 (`standard/version-policy.md`) |
| Repository | 0.1.0, pre-release, not tagged (`CHANGELOG.md`) |

The two versions are tracked separately. Downstream repositories pin the standard version.

## Validate

Python 3.12:

```bash
python -m pip install -r requirements.txt
python tools/validate.py
python -m unittest discover -s tests -v
```

## Limitations

- Only the shared standard exists. There is no lifecycle, gate, schema for operational records, rule, profile, or synthetic dataset yet, so nothing can be run against a project.
- Payload fields in the event catalog are named but not yet typed; each producing repository types them when it is built.
- Prefixes owned by the other five repositories are registered now so IDs never collide, but their records are defined only when those repositories are built.
- Nothing here has been used on a real project, and nothing claims a measured result.

## AI assistance

This repository was drafted with Claude (Anthropic) under the author's direction and review. The author defined the architecture, the rules, and the approval of every change; AI assistance was used for drafting text, schemas, and tests, which were checked by the automated validator and by human review. AI produced no data about real people or organizations.

## License

MIT. See [LICENSE](LICENSE).
