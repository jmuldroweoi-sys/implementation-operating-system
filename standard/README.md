# Shared standard

Shared-standard version: 1.0.0

## Purpose

`standard/` is the shared contract used by all six implementation portfolio repositories (R1 to R6). It makes sure a project, task, risk, readiness score, training record, or recommendation means the same thing in every tool that reads it.

## Version

Shared-standard version: 1.0.0. See [version-policy.md](version-policy.md). The standard version is separate from the repository version in `../CHANGELOG.md`.

## Authority

`standard/` is the single authority for:

| Concept | File |
|---|---|
| Glossary | [glossary.md](glossary.md) |
| ID prefixes | [id-registry.yaml](id-registry.yaml) |
| Field conventions | [field-conventions.md](field-conventions.md) |
| Mandatory labels | [label-rules.yaml](label-rules.yaml) |
| Severity scale | [severity-scale.yaml](severity-scale.yaml) |
| Readiness categories | [readiness-categories.yaml](readiness-categories.yaml) |
| Lifecycle terminology | [lifecycle-terms.yaml](lifecycle-terms.yaml) |
| Common status vocabularies | [status-vocabularies.yaml](status-vocabularies.yaml) |
| Organization stages | [org-stages.yaml](org-stages.yaml) |
| Event catalog | [event-catalog.yaml](event-catalog.yaml) |
| Event schema | [schemas/event.schema.json](schemas/event.schema.json) |
| Approval-record schema | [schemas/approval-record.schema.json](schemas/approval-record.schema.json) |
| Recommendation schema | [schemas/recommendation.schema.json](schemas/recommendation.schema.json) |
| Metric-definition schema | [schemas/metric-definition.schema.json](schemas/metric-definition.schema.json) |
| Cross-repository version policy | [version-policy.md](version-policy.md) |

## Consumer rule

Downstream repositories pin the standard version in their own `standard/standard-reference.yaml` and reference these files by `$ref` or a pinned copy. They may reference these definitions. They may not redefine them.

## Breaking changes

Breaking shared-contract changes require a new major standard version (see [version-policy.md](version-policy.md)).

## Non-authority

`standard/` does not own:

| Concept | Owner |
|---|---|
| Capacity formulas | R2 `implementation-capacity-and-org-design` |
| Curriculum rules | R4 `implementation-enablement-program` |
| Management judgments | R5 `implementation-team-management-toolkit` |
| AI task workflow | R6 `implementation-ai-agent-framework` |

It also does not define the operating system core of this repository (lifecycle criteria, gates, operational schemas, SLA and risk rules, readiness weights). Those are built next, in R1 v0.1.

## Validate

```bash
python tools/validate.py
```
