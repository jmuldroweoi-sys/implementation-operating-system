# Version policy

Standard version: 1.0.0

## Two separate versions

| Version | What it tracks | Where it is stated | Current |
|---|---|---|---|
| Shared-standard version | The cross-repository contract in `standard/` | `standard_version` in every YAML file in `standard/`, `standard/README.md`, and `schema_version` in every event | 1.0.0 |
| Repository version | This repository as a whole: documentation, tools, and later the operating system core | `CHANGELOG.md` | 0.1.0, pre-release, not yet tagged |

A repository release does not change the standard version unless `standard/` changed, and a standard change is always recorded in `CHANGELOG.md` with both versions.

## Rules

1. The shared standard uses Semantic Versioning (`MAJOR.MINOR.PATCH`).
2. The initial shared standard is 1.0.0.
3. Every downstream repository pins the exact standard version it targets in `standard/standard-reference.yaml`, and its validator fails on a mismatch.
4. A breaking change raises the major version. Breaking changes include removing or renaming a field, prefix, event, label, vocabulary value, phase, stage, or category; narrowing an allowed value; making an optional field required; and changing the meaning of anything.
5. A backward-compatible addition raises the minor version. Examples: a new optional field, a new event, a new prefix, a new vocabulary.
6. A correction that does not change contract meaning raises the patch version. Examples: wording, typos, clearer descriptions, additional examples.
7. A retired prefix or event is never reused, under any version.
8. An event's meaning never changes silently. A changed meaning is a new event type, or a new major standard version with the old meaning retired.
9. All files in `standard/` carry the same version. The validator fails if they disagree.

## Change process

1. Propose the change with the reason and the affected repositories.
2. Classify it as major, minor, or patch using the rules above.
3. Update every file in `standard/` together, including `standard_version`.
4. Update `CHANGELOG.md` with the new standard version.
5. Run `tools/validate.py` and the tests.
6. A named human reviews and approves the change before it merges. Downstream repositories update their pins in their own reviewed changes.
