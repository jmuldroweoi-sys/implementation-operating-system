# Changelog

This file tracks two separate versions: the repository version (headings below) and the shared-standard version (stated in each entry). See `standard/version-policy.md`.

## [0.1.0] Unreleased (pre-release, not tagged)

### Added

- Shared standard 1.0.0 established in `standard/`: glossary, ID registry, field conventions, mandatory label rules, severity scale, readiness categories, lifecycle terms, status vocabularies, organization stages, event catalog, version policy, and four shared schemas (event, approval record, recommendation, metric definition).
- `tools/validate.py`, which checks the standard against the locked 1.0.0 contract, and its tests.
- Repository foundation: README, license, contributing guide, CI workflow, and verification records.

### Not yet included

- The operating system core (lifecycle files, gates, operational schemas, rules, profiles, synthetic data). Repository version 0.1.0 is completed by that build; no release or tag exists yet.
