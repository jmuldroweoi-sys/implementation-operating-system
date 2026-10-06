# Release gate

**This repository is not authorized for public release yet.**

| Item | Status |
|---|---|
| Repository | implementation-operating-system |
| Visibility | Private |
| Repository version | 0.1.0, pre-release, not tagged |
| Shared standard | 1.0.0, validated |
| Operating system core (required for version 0.1.0) | Not started |
| Practical workflow guide | Not started |
| Publication gate, pre-release profile (2026-10-06) | Every public-safety rule passes (blocklist with a temporary private term list, excluded names, em dashes, secrets, emails, claims, assistant names, unfinished markers, commit identity). One expected failure: `docs/practical-workflow.md` is a version 0.1.0 file that arrives with the operating system core |
| Publication gate, strict profile | Not run; runs when the repository version is complete |
| Human release review | Not done |
| Publication approval | None |

Publication requires, in order: the complete version 0.1.0 scope, a passing strict publication gate with the private blocklist and source fingerprints, a signed human review recorded in this file, and the author's explicit approval. No release, tag, or visibility change happens before all four.
