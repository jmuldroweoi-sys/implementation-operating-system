# Field conventions

Standard version: 1.0.0

Every field in every schema, CSV header, YAML key, and event payload across the six repositories follows these conventions. The spreadsheet workbook (R3) copies field names from the operating system (R1) exactly; it never renames them.

## Names

| Kind | Rule | Example |
|---|---|---|
| All field names | snake_case, lowercase ASCII letters, digits, and underscores, starting with a letter | `target_launch_date` |
| IDs | End in `_id`; value matches `TYPE-NNNNNN` with a registered prefix | `project_id: PRJ-000001` |
| Own ID of a record | `<entity>_id`, matching the registry entity name | `risk_id` |
| Timestamps | End in `_at`; ISO 8601 in UTC, ending in `Z`; never a `_utc` suffix | `decided_at: 2026-03-06T17:20:00Z` |
| Dates | End in `_date`; ISO 8601 calendar date | `due_date: 2026-04-15` |
| Monthly periods | Field named `period` or ending in `_period`; `YYYY-MM` | `period: 2026-04` |
| Hours | End in `_hours`; decimal number of hours | `session_hours: 1.5` |
| Rates | End in `_rate`; decimal from 0 to 1 unless the field's own documentation states otherwise | `completion_rate: 0.75` |
| Ratios that may exceed 1 | End in `_ratio` | `load_ratio: 1.2` |
| Booleans | End in `_flag`; values `true` or `false` | `attended_flag: true` |
| Counts | End in `_count`; non-negative integer | `learner_count: 12` |

## Common fields

| Field | Rule |
|---|---|
| Version fields | Named `version` (the record's own version) or `<thing>_version` (for example `schema_version`). Values are SemVer strings `MAJOR.MINOR.PATCH`. |
| Source-reference fields | A single reference uses `<entity>_id`. A list of references uses `source_references`: an array of objects, each with `source_type` (a registered entity name) and `source_id` (an ID with that entity's prefix). |
| Status fields | Named `status`, or `<thing>_status` when a record has more than one. Values come from a vocabulary in `standard/` or from the owning repository's core. Transitions in events use `from_status` and `to_status`. |
| Type fields | Named `<thing>_type`, holding a registered entity name or an owning-repository code value. |
| Severity | Named `severity`; values `sev1` to `sev4` from `standard/severity-scale.yaml`. |
| Phase references | Named `phase_key`; values from `standard/lifecycle-terms.yaml`. |

## Enum serialization

- Enum values are lowercase snake_case strings, stored exactly as listed in the vocabulary (for example `pass_with_conditions`, `not_yet`, `sev2`).
- Display names (for example "Sev 2") are for people and are never stored as data.
- Never store an enum as a number or as a display label.

## Null versus blank

- A field that is not applicable or not yet known is omitted from JSON and JSONL, or written as an empty cell in CSV.
- `null` is used only when a schema explicitly allows it, to mean "known to be absent".
- An empty string is never used to mean "unknown". Zero means zero, never "missing".

## Arrays

- Arrays hold values of one type.
- Arrays of references use `source_references` or a plural name ending in `_ids` (for example `dependency_ids`).
- In CSV, an array is written as values separated by a semicolon with no spaces.

## Payload objects

- An event's `payload` holds only that event type's fields as listed in `standard/event-catalog.yaml`, plus listed optional fields.
- Payload field names follow every rule on this page.
- A change of value records `from_<field>` and `to_<field>` (for example `from_status`, `to_status`).
- Payloads never contain private notes, free-text personal judgments, credentials, or real names.
