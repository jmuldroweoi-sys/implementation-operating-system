# Contributing

This repository holds the shared standard for six connected repositories, so changes here affect all of them. Every change is reviewed by a human before it merges.

## Shared-standard ownership

`standard/` is the single authority for the glossary, ID prefixes, field conventions, mandatory labels, severity scale, readiness categories, lifecycle terms, shared status vocabularies, organization stages, the event catalog, and the event, approval-record, recommendation, and metric-definition schemas. Other repositories reference these definitions and pin a version. They never copy and edit them.

## No duplicated definitions

- Define each concept once. If a concept is already in `standard/`, reference it.
- Do not add a synonym, a second ID prefix, a second event name, or a second schema for something that already exists.
- Do not reuse a retired prefix or event name.

## Compatibility expectations

Follow `standard/version-policy.md`. Breaking changes raise the major version, backward-compatible additions raise the minor version, and corrections that do not change meaning raise the patch version. Every file in `standard/` carries the same `standard_version`.

## Schema-change process

1. Describe the change, the reason, and every repository it affects.
2. Classify it (major, minor, patch).
3. Update the schema, its `$id` version, its examples, and every related file in `standard/`.
4. Update `tools/validate.py` where the locked contract changes, and add or update tests.
5. Record the change in `CHANGELOG.md` with both the repository and standard versions.
6. A named human reviews and approves the change.

## Event-catalog change process

1. A new event needs one producer repository, at least one consumer, a registered subject entity, payload field names that follow `standard/field-conventions.md`, a description, and an authoritative effect.
2. An existing event never changes meaning or producer under the same name. A changed meaning is a new event or a new major version.
3. Update the event lock in `tools/validate.py` together with the catalog, and add tests.

## Public-safety requirements

- Write everything freshly. Never copy wording, structure, or screenshots from any organization's documents, training materials, or systems.
- Never include real names of people, customers, employers, vendors, products, or internal tools, and never include real metrics.
- Run the validator with the private blocklist before any change intended for publication. The blocklist itself never enters this repository.

## Label requirements

Use the four mandatory labels exactly as written in `standard/label-rules.yaml`: `proposed design value, not a measured result`, `synthetic data`, `illustrative example`, `user-configurable parameter`. Never shorten or reword them.

## Genericity

Industry-neutral and vendor-neutral only. No fictional company or product premise. Examples use neutral scenario labels (Scenario A to E) and role labels with IDs.

## Testing

```bash
python -m pip install -r requirements.txt
python tools/validate.py
python -m unittest discover -s tests -v
```

Every check must pass. A bug fix adds a test that fails before the fix.

## Writing style

No em dashes anywhere. The validator rejects them.

## Human review

Every change is reviewed and approved by a named human before it merges. AI assistance may draft changes; it never approves them.
