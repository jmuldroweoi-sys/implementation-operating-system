"""Validator for implementation-operating-system: the shared standard and the R1 core.

Mechanically checks that standard/ is complete, internally consistent, and equal to the
locked 1.0.0 contract, and that the R1 v0.1 core (lifecycle, gates, schemas,
configuration, profiles, synthetic data, and events) is valid and consistent. It
reads files only; it never publishes, pushes, or changes anything.

Checks (each prints PASS or FAIL):
  V01 JSON files parse
  V02 JSON Schemas are valid draft 2020-12 schemas and their examples validate
  V03 YAML files parse
  V04 expected standard files exist
  V05 ID prefixes are unique and entity names are unique
  V06 retired prefixes are never active
  V07 IDs and ID examples use the TYPE-NNNNNN pattern with registered prefixes
  V08 event types are unique
  V09 event types use dot notation
  V10 producer repositories are registered
  V11 consumer repositories are registered
  V12 actor types match the shared contract
  V13 lifecycle terms exist exactly once and match the contract
  V14 organization stages exist exactly once and match the contract
  V15 mandatory label text matches exactly, with no near-variants anywhere
  V16 status vocabularies contain the approved values
  V17 no em dash character exists
  V18 no private blocklist term appears (when a private blocklist is supplied)
  V19 no credential or secret pattern is detected
  V20 the standard version is internally consistent
  V21 readiness categories match the contract
  V22 severity scale matches the contract and holds no response timers
  V23 the glossary defines every required term
  V24 the event catalog is complete, with unchanged ownership and valid subjects

R1 v0.1 core (rules come from tools/r1_rules.py):
  V25 the R1 core files exist
  V26 R1 schemas are valid, their examples validate, and their CSV contracts match
  V27 lifecycle, configuration, and profile YAML parse and pin the versions
  V28 the lifecycle has exactly ten phases in standard order with legal moves only
  V29 gates reference valid phases, use only standard outcomes, and need a human
  V30 the request state machine is authoritative, complete, and matches the schema
  V31 SLA rules are configurable and well formed, with parseable durations
  V32 risk rules are deterministic and their bands cover every score once
  V33 lead-time rules are deterministic and parse
  V34 readiness weights use the six canonical categories and total correctly
  V35 profiles configure the same model and stay inside their limits
  V36 synthetic CSVs match the schemas, column contracts, and exact row counts
  V37 synthetic references resolve with zero orphans
  V38 synthetic data obeys the deterministic rules
  V39 synthetic events are valid against standard 1.0.0 and match the records
  V40 required labels and documentation are present
  V41 the repository names no listed real vendor or product

Private blocklist: --blocklist FILE ... or the PORTFOLIO_GATE_BLOCKLIST environment
variable (os.pathsep-separated). The file must be outside this repository. Matched
terms are never printed; only counts are.

Usage:
    python tools/validate.py [--root PATH] [--blocklist FILE ...]

Exit codes: 0 pass, 1 one or more failures.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator, FormatChecker

STANDARD_VERSION = "1.0.0"
BLOCKLIST_ENV = "PORTFOLIO_GATE_BLOCKLIST"
EM_DASH = chr(0x2014)
ID_PATTERN = "^[A-Z]{3}-[0-9]{6}$"
ID_RE = re.compile(ID_PATTERN)
ID_LIKE = re.compile(r"^[A-Z]{2,5}-[0-9]+$")
EVENT_TYPE_RE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")
SNAKE_RE = re.compile(r"^[a-z][a-z0-9_]*$")

EXPECTED_FILES = (
    "standard/README.md",
    "standard/glossary.md",
    "standard/id-registry.yaml",
    "standard/field-conventions.md",
    "standard/label-rules.yaml",
    "standard/severity-scale.yaml",
    "standard/readiness-categories.yaml",
    "standard/lifecycle-terms.yaml",
    "standard/status-vocabularies.yaml",
    "standard/org-stages.yaml",
    "standard/event-catalog.yaml",
    "standard/version-policy.md",
    "standard/schemas/event.schema.json",
    "standard/schemas/approval-record.schema.json",
    "standard/schemas/recommendation.schema.json",
    "standard/schemas/metric-definition.schema.json",
)

R1 = "implementation-operating-system"
R2 = "implementation-capacity-and-org-design"
R3 = "implementation-tracker-workbook"
R4 = "implementation-enablement-program"
R5 = "implementation-team-management-toolkit"
R6 = "implementation-ai-agent-framework"
REPOS = (R1, R2, R3, R4, R5, R6)

# The locked 1.0.0 contract. Changing any value here, or the matching standard file,
# is a contract change and follows standard/version-policy.md.
CONTRACT = {
    "retired_prefixes": {"AIR", "AUD", "USR", "EXM", "KPI", "ERL", "QAO", "TCR", "CRT"},
    "labels": [
        "proposed design value, not a measured result",
        "synthetic data",
        "illustrative example",
        "user-configurable parameter",
    ],
    "phases": [
        "initiate", "discover", "design", "build", "validate",
        "enable", "launch", "stabilize", "transition", "review",
    ],
    "phase_statuses": ["not_started", "active", "awaiting_gate", "completed", "blocked"],
    "gate_outcomes": ["pass", "pass_with_conditions", "hold"],
    "org_stages": ["startup", "early_scale", "structured_growth", "mature"],
    "readiness_categories": ["people", "process", "technology", "data", "training", "support"],
    "severities": ["sev1", "sev2", "sev3", "sev4"],
    "vocabularies": {
        "configuration": ["draft", "in_review", "released", "deprecated"],
        "content": ["draft", "in_review", "published", "retired"],
        "recommendation": ["proposed", "approved", "rejected"],
        "learning_result": ["pass", "not_yet"],
    },
    "actor_types": ["human", "system", "ai_agent"],
    "event_fields": [
        "event_id", "event_type", "occurred_at", "actor_id", "actor_type",
        "subject_type", "subject_id", "payload", "source_repo", "schema_version",
    ],
    "authoritative_effects": {"records_authoritative_transition", "records_proposal", "informational"},
    "retired_events": {
        "training.session_completed",
        "session_completed",
        "proficiency.summary_updated",
        "assessment_scored",
        "trainer.credentialed",
        "trainer.certified",
    },
    "glossary_terms": [
        "customer", "implementation project", "phase", "milestone", "task", "dependency",
        "request", "handoff", "risk", "issue", "SLA rule", "gate", "gate assessment",
        "configuration item", "environment", "readiness", "event", "recommendation",
        "approval", "metric definition", "metric value", "role", "person", "profile",
        "scenario", "demand", "supply", "capacity", "capacity gap", "load ratio",
        "proficiency", "competency", "credential",
    ],
}

EVENT_LOCK = {
    "project.created": "R1",
    "project.status_changed": "R1",
    "phase.entered": "R1",
    "phase.exited": "R1",
    "gate.assessed": "R1",
    "task.status_changed": "R1",
    "milestone.achieved": "R1",
    "milestone.missed": "R1",
    "request.submitted": "R1",
    "request.status_changed": "R1",
    "request.escalated": "R1",
    "approval.recorded": "R1",
    "handoff.completed": "R1",
    "risk.logged": "R1",
    "risk.status_changed": "R1",
    "issue.logged": "R1",
    "issue.resolved": "R1",
    "config_item.released": "R1",
    "environment.promoted": "R1",
    "readiness.scored": "R1",
    "improvement.logged": "R1",
    "rehearsal.completed": "R1",
    "cutover.task_completed": "R1",
    "golive.decision_recorded": "R1",
    "hypercare.exited": "R1",
    "capacity.snapshot_computed": "R2",
    "staffing_trigger.fired": "R2",
    "staffing_recommendation.recorded": "R2",
    "org_profile.selected": "R2",
    "training_capacity.computed": "R2",
    "golive_support.computed": "R2",
    "cost_to_serve.computed": "R2",
    "training.demand_forecasted": "R4",
    "curriculum.lesson_published": "R4",
    "training.session_delivered": "R4",
    "training.attendance_recorded": "R4",
    "training.completion_updated": "R4",
    "assessment.scored": "R4",
    "proficiency.recorded": "R4",
    "remediation.assigned": "R4",
    "deliverable.status_changed": "R4",
    "ramp.milestone_achieved": "R4",
    "trainer.requirements_met": "R4",
    "one_on_one.held": "R5",
    "development_goal.created": "R5",
    "development_goal.achieved": "R5",
    "competency.assessed": "R5",
    "qa_review.completed": "R5",
    "trainer.observed": "R5",
    "calibration.completed": "R5",
    "credential.reviewed": "R5",
    "credential.granted": "R5",
    "appeal.submitted": "R5",
    "appeal.resolved": "R5",
    "agent.task_started": "R6",
    "agent.recommendation_created": "R6",
    "agent.recommendation_approved": "R6",
    "agent.recommendation_rejected": "R6",
    "agent.task_failed": "R6",
    "agent.task_completed": "R6",
}

LABEL_VARIANTS = (
    re.compile(r"proposed\s+design\s+value(?!,\s+not\s+a\s+measured\s+result)", re.I),
    re.compile(r"\buser configurable parameter\b", re.I),
    # A hyphenated label is a near-variant; a file name that starts with the words
    # (for example synthetic-data-check.md) is not.
    re.compile(r"\billustrative-example\b(?!-[a-z0-9])", re.I),
    re.compile(r"\bsynthetic-data\b(?!-[a-z0-9])", re.I),
)
SECRET_PATTERNS = (
    re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_\w{40,})"),
    re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    re.compile(r"\bsk-(?:ant-)?[A-Za-z0-9_-]{20,}"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
    re.compile(r"\bxox[abposr]-[A-Za-z0-9-]{10,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(
        r"(?i)\b(?:api[_-]?key|secret|token|password|passwd)\b[\"']?\s*[:=]\s*[\"'][^\"'\s]{16,}[\"']"
    ),
)
SECRET_FILES = re.compile(r"(?:^|/)(?:\.env(?:\..+)?|id_rsa|id_ed25519|.+\.pem|.+\.key)$")
TEXT_SUFFIXES = {".md", ".yaml", ".yml", ".json", ".jsonl", ".csv", ".py", ".txt", ".toml", ".cfg", ""}
SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "dist", ".pytest_cache"}
# These tool and test files hold detection patterns or deliberately bad fixtures.
SCAN_EXEMPT = {"tools/validate.py"}


class Result:
    def __init__(self) -> None:
        self.rows: list[tuple[str, bool, str]] = []

    def add(self, check: str, problems: list[str], ok_note: str) -> None:
        self.rows.append((check, not problems, "; ".join(problems[:8]) if problems else ok_note))

    @property
    def failed(self) -> bool:
        return any(not ok for _, ok, _ in self.rows)


def repo_files(root: Path) -> list[Path]:
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            out.append(Path(dirpath, name))
    return sorted(out)


def rel(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def text_of(path: Path) -> str | None:
    if path.suffix.lower() not in TEXT_SUFFIXES:
        return None
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None


def walk_values(obj, key=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk_values(v, k)
    elif isinstance(obj, list):
        for v in obj:
            yield from walk_values(v, key)
    else:
        yield key, obj


def load_blocklist(given: list[str] | None, root: Path) -> tuple[list[str], list[str]]:
    names = list(given or [])
    if not names and os.environ.get(BLOCKLIST_ENV):
        names = [p for p in os.environ[BLOCKLIST_ENV].split(os.pathsep) if p]
    terms: list[str] = []
    problems: list[str] = []
    for name in names:
        path = Path(name).expanduser().resolve()
        if not path.is_file():
            problems.append("blocklist file not found")
            continue
        try:
            path.relative_to(root)
            problems.append("blocklist file must live outside this repository")
            continue
        except ValueError:
            pass
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                terms.append(line)
    return terms, problems


def validate(root: Path, blocklist: list[str] | None = None) -> Result:
    res = Result()
    std = root / "standard"

    missing = [f for f in EXPECTED_FILES if not (root / f).is_file()]
    res.add("V04 expected standard files exist", [f"missing {m}" for m in missing], f"{len(EXPECTED_FILES)} present")

    json_docs: dict[str, object] = {}
    problems = []
    for path in sorted(std.rglob("*.json")):
        try:
            json_docs[rel(root, path)] = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            problems.append(f"{rel(root, path)}: {exc.msg}")
    res.add("V01 JSON files parse", problems, f"{len(json_docs)} files")

    yaml_docs: dict[str, object] = {}
    problems = []
    for path in sorted(std.rglob("*.yaml")):
        try:
            yaml_docs[rel(root, path)] = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            problems.append(f"{rel(root, path)}: {exc.__class__.__name__}")
    res.add("V03 YAML files parse", problems, f"{len(yaml_docs)} files")

    def y(name: str) -> dict:
        doc = yaml_docs.get(f"standard/{name}")
        return doc if isinstance(doc, dict) else {}

    registry = y("id-registry.yaml")
    prefixes = registry.get("prefixes") or []
    active = {p.get("prefix"): p for p in prefixes if p.get("status") == "active"}
    entity_prefix = {p.get("entity"): p.get("prefix") for p in prefixes if p.get("status") == "active"}
    repo_names = {r.get("repo") for r in registry.get("repositories") or []}

    # V05
    problems = []
    seen: dict[str, int] = {}
    for p in prefixes:
        seen[p.get("prefix")] = seen.get(p.get("prefix"), 0) + 1
        for field in ("prefix", "entity", "owning_repo", "status", "description"):
            if not p.get(field):
                problems.append(f"{p.get('prefix')}: missing {field}")
        if p.get("status") not in ("active", "retired"):
            problems.append(f"{p.get('prefix')}: invalid status")
        if p.get("owning_repo") not in REPOS:
            problems.append(f"{p.get('prefix')}: unregistered owning_repo")
    problems += [f"duplicate prefix {k}" for k, n in seen.items() if n > 1]
    entities = [p.get("entity") for p in prefixes if p.get("status") == "active"]
    problems += [f"duplicate entity {e}" for e in sorted({e for e in entities if entities.count(e) > 1})]
    if repo_names != set(REPOS):
        problems.append("repositories list does not match the six registered repositories")
    res.add("V05 ID prefixes and entities are unique", problems, f"{len(active)} active prefixes")

    # V06
    retired = {p.get("prefix") for p in prefixes if p.get("status") == "retired"}
    problems = [f"retired prefix {r} is active" for r in sorted(CONTRACT["retired_prefixes"]) if r in active]
    problems += [f"retired prefix {r} missing from registry" for r in sorted(CONTRACT["retired_prefixes"] - retired - set(active))]
    problems += [f"{r} is retired but not in the locked retired list" for r in sorted(retired - CONTRACT["retired_prefixes"])]
    res.add("V06 retired prefixes are never active", problems, f"{len(retired)} retired")

    # V02 and V07 (schema examples)
    problems_schema: list[str] = []
    problems_ids: list[str] = []
    if registry.get("id_pattern") != ID_PATTERN:
        problems_ids.append("id_pattern differs from TYPE-NNNNNN")
    for p in prefixes:
        if not re.fullmatch(r"[A-Z]{3}", str(p.get("prefix"))):
            problems_ids.append(f"prefix {p.get('prefix')} is not three letters")
    examples_by_schema: dict[str, list] = {}
    for name, doc in json_docs.items():
        if not name.startswith("standard/schemas/"):
            continue
        try:
            Draft202012Validator.check_schema(doc)
        except Exception as exc:  # noqa: BLE001
            problems_schema.append(f"{name}: invalid schema ({exc.__class__.__name__})")
            continue
        validator = Draft202012Validator(doc, format_checker=FormatChecker())
        examples = doc.get("examples", []) if isinstance(doc, dict) else []
        if not examples:
            problems_schema.append(f"{name}: no examples")
        examples_by_schema[name] = examples
        for i, ex in enumerate(examples):
            errors = sorted(validator.iter_errors(ex), key=lambda e: e.path)
            if errors:
                problems_schema.append(f"{name} example {i}: {errors[0].message}")
            for key, value in walk_values(ex):
                if isinstance(value, str) and (key.endswith("_id") or ID_LIKE.match(value)):
                    if not ID_RE.match(value):
                        problems_ids.append(f"{name} example {i}: malformed ID in {key}")
                    elif value[:3] not in active:
                        problems_ids.append(f"{name} example {i}: unregistered prefix {value[:3]}")
            for tkey, ikey in (("subject_type", "subject_id"), ("source_type", "source_id")):
                if isinstance(ex, dict) and tkey in ex and ikey in ex:
                    if entity_prefix.get(ex[tkey]) != str(ex[ikey])[:3]:
                        problems_ids.append(f"{name} example {i}: {ikey} prefix does not match {tkey}")
            for ref in ex.get("source_references", []) if isinstance(ex, dict) else []:
                if entity_prefix.get(ref.get("source_type")) != str(ref.get("source_id"))[:3]:
                    problems_ids.append(f"{name} example {i}: source_id prefix does not match source_type")
    res.add("V02 JSON Schemas valid and examples validate", problems_schema, f"{len(examples_by_schema)} schemas")

    catalog = y("event-catalog.yaml")
    events = catalog.get("events") or []
    catalog_by_type = {e.get("event_type"): e for e in events}
    for i, ex in enumerate(examples_by_schema.get("standard/schemas/event.schema.json", [])):
        entry = catalog_by_type.get(ex.get("event_type"))
        if not entry:
            problems_ids.append(f"event example {i}: event_type not in catalog")
            continue
        if ex.get("source_repo") != entry.get("producer_repo"):
            problems_ids.append(f"event example {i}: source_repo is not the catalog producer")
        if ex.get("subject_type") != entry.get("subject_type"):
            problems_ids.append(f"event example {i}: subject_type differs from catalog")
        missing_fields = [f for f in entry.get("required_payload_fields") or [] if f not in ex.get("payload", {})]
        if missing_fields:
            problems_ids.append(f"event example {i}: payload missing {', '.join(missing_fields)}")
        if ex.get("schema_version") != STANDARD_VERSION:
            problems_ids.append(f"event example {i}: schema_version is not {STANDARD_VERSION}")
    res.add("V07 IDs and ID examples use registered TYPE-NNNNNN", problems_ids, "all example IDs resolve")

    # V08 to V11 and V24
    types = [e.get("event_type") for e in events]
    res.add("V08 event types are unique", [f"duplicate {t}" for t in sorted({t for t in types if types.count(t) > 1})], f"{len(types)} events")
    res.add("V09 event types use dot notation", [f"bad name {t}" for t in types if not EVENT_TYPE_RE.match(str(t))], "all dot notation")
    res.add(
        "V10 producer repositories are registered",
        [f"{e.get('event_type')}: unregistered producer" for e in events if e.get("producer_repo") not in REPOS],
        "all registered",
    )
    problems = []
    for e in events:
        consumers = e.get("consumer_repos") or []
        if not consumers:
            problems.append(f"{e.get('event_type')}: no consumers")
        problems += [f"{e.get('event_type')}: unregistered consumer" for c in consumers if c not in REPOS]
        if e.get("producer_repo") in consumers:
            problems.append(f"{e.get('event_type')}: producer listed as consumer")
    res.add("V11 consumer repositories are registered", problems, "all registered")

    problems = []
    if STANDARD_VERSION == "1.0.0":
        code = {"R1": R1, "R2": R2, "R4": R4, "R5": R5, "R6": R6}
        for t, owner in EVENT_LOCK.items():
            if t not in catalog_by_type:
                problems.append(f"locked event {t} missing")
            elif catalog_by_type[t].get("producer_repo") != code[owner]:
                problems.append(f"{t}: ownership changed")
        problems += [f"{t}: not in the locked 1.0.0 catalog" for t in types if t not in EVENT_LOCK]
    problems += [f"{t}: retired event alias" for t in types if t in CONTRACT["retired_events"]]
    required_keys = (
        "event_type", "version", "producer_repo", "consumer_repos", "subject_type",
        "required_payload_fields", "optional_payload_fields", "description", "authoritative_effect",
    )
    for e in events:
        problems += [f"{e.get('event_type')}: missing {k}" for k in required_keys if k not in e]
        if e.get("subject_type") not in entity_prefix:
            problems.append(f"{e.get('event_type')}: subject_type is not a registered entity")
        if e.get("authoritative_effect") not in CONTRACT["authoritative_effects"]:
            problems.append(f"{e.get('event_type')}: invalid authoritative_effect")
        for f in (e.get("required_payload_fields") or []) + (e.get("optional_payload_fields") or []):
            if not SNAKE_RE.match(str(f)):
                problems.append(f"{e.get('event_type')}: payload field {f} is not snake_case")
    res.add("V24 event catalog complete with unchanged ownership", problems, f"{len(EVENT_LOCK)} locked events present")

    # V12
    problems = []
    event_schema = json_docs.get("standard/schemas/event.schema.json") or {}
    props = event_schema.get("properties", {}) if isinstance(event_schema, dict) else {}
    if props.get("actor_type", {}).get("enum") != CONTRACT["actor_types"]:
        problems.append("event actor_type enum differs from the contract")
    if event_schema.get("required") != CONTRACT["event_fields"]:
        problems.append("event required fields differ from the ten contract fields")
    if sorted(props) != sorted(CONTRACT["event_fields"]):
        problems.append("event schema properties differ from the ten contract fields")
    if props.get("source_repo", {}).get("enum") != list(REPOS):
        problems.append("event source_repo enum differs from the registered repositories")
    rec = json_docs.get("standard/schemas/recommendation.schema.json") or {}
    if rec.get("properties", {}).get("origin_type", {}).get("enum") != CONTRACT["actor_types"]:
        problems.append("recommendation origin_type enum differs from the contract")
    apr = json_docs.get("standard/schemas/approval-record.schema.json") or {}
    if apr.get("properties", {}).get("approver_type", {}).get("const") != "human":
        problems.append("approval approver_type is not fixed to human")
    res.add("V12 actor types match the shared contract", problems, "human, system, ai_agent")

    # V13
    lc = y("lifecycle-terms.yaml")
    keys = [p.get("phase_key") for p in lc.get("phases") or []]
    orders = [p.get("order") for p in lc.get("phases") or []]
    problems = []
    if keys != CONTRACT["phases"]:
        problems.append("phase keys differ from the ten contract phases or their order")
    if orders != list(range(1, 11)):
        problems.append("phase order values are not 1 to 10")
    if lc.get("phase_statuses") != CONTRACT["phase_statuses"]:
        problems.append("phase statuses differ from the contract")
    if lc.get("gate_outcomes") != CONTRACT["gate_outcomes"]:
        problems.append("gate outcomes differ from the contract")
    res.add("V13 lifecycle terms exactly once", problems, "10 phases, 5 statuses, 3 gate outcomes")

    # V14
    stages = [s.get("stage_id") for s in y("org-stages.yaml").get("stages") or []]
    problems = [] if stages == CONTRACT["org_stages"] else ["organization stages differ from the contract"]
    for s in y("org-stages.yaml").get("stages") or []:
        for f in ("definition", "typical_characteristics", "becomes_more_formal"):
            if not s.get(f):
                problems.append(f"{s.get('stage_id')}: missing {f}")
    res.add("V14 organization stages exactly once", problems, "4 stages")

    # V15
    labels = [lab.get("label") for lab in y("label-rules.yaml").get("labels") or []]
    problems = [] if labels == CONTRACT["labels"] else ["label text differs from the four canonical labels"]
    for lab in y("label-rules.yaml").get("labels") or []:
        for f in ("label", "when_required", "valid_locations", "examples", "invalid_usage", "validation_behavior"):
            if not lab.get(f):
                problems.append(f"{lab.get('id')}: missing {f}")
    for path in repo_files(root):
        r = rel(root, path)
        if r in SCAN_EXEMPT or r.startswith("tests/"):
            continue
        text = text_of(path)
        if text is None:
            continue
        for pat in LABEL_VARIANTS:
            if pat.search(text):
                problems.append(f"{r}: label near-variant")
                break
    res.add("V15 mandatory labels exact", problems, "4 canonical labels")

    # V16
    vocab = {v.get("vocabulary_id"): v.get("values") for v in y("status-vocabularies.yaml").get("vocabularies") or []}
    problems = [f"{k}: values differ from the contract" for k, v in CONTRACT["vocabularies"].items() if vocab.get(k) != v]
    res.add("V16 status vocabularies approved", problems, f"{len(CONTRACT['vocabularies'])} vocabularies")

    # V17, V19, V18
    dash, secrets, block = [], [], []
    terms, block_problems = load_blocklist(blocklist, root)
    patterns = [re.compile(r"(?<![A-Za-z0-9])" + re.escape(t) + r"(?![A-Za-z0-9])", re.I) for t in terms]
    for path in repo_files(root):
        r = rel(root, path)
        if SECRET_FILES.search(r):
            secrets.append(f"{r}: secret-bearing file name")
        if any(p.search(r) for p in patterns):
            block.append("a path")
        text = text_of(path)
        if text is None:
            continue
        if EM_DASH in text:
            dash.append(r)
        if r in SCAN_EXEMPT or r.startswith("tests/"):
            continue
        if any(p.search(text) for p in SECRET_PATTERNS):
            secrets.append(r)
        if any(p.search(text) for p in patterns):
            block.append(r)
    res.add("V17 no em dash", [f"em dash in {d}" for d in dash], "none")
    if block_problems:
        res.add("V18 private blocklist", block_problems, "")
    elif not terms:
        res.add("V18 private blocklist", [], "no private blocklist supplied; check skipped (supply one before publication)")
    else:
        res.add("V18 private blocklist", [f"{len(block)} file(s) contain a private term" ] if block else [], f"{len(terms)} private terms loaded; 0 hits")
    res.add("V19 no credentials or secrets", secrets, "none")

    # V20
    problems = []
    for name, doc in yaml_docs.items():
        if not isinstance(doc, dict) or str(doc.get("standard_version")) != STANDARD_VERSION:
            problems.append(f"{name}: standard_version is not {STANDARD_VERSION}")
    for name, doc in json_docs.items():
        if f":{STANDARD_VERSION}:" not in str(doc.get("$id", "") if isinstance(doc, dict) else ""):
            problems.append(f"{name}: $id does not carry {STANDARD_VERSION}")
    for md in ("standard/README.md", "standard/glossary.md", "standard/field-conventions.md", "standard/version-policy.md"):
        path = root / md
        if path.is_file() and f"ersion: {STANDARD_VERSION}" not in path.read_text(encoding="utf-8"):
            problems.append(f"{md}: does not state version {STANDARD_VERSION}")
    changelog = root / "CHANGELOG.md"
    if not changelog.is_file() or f"Shared standard {STANDARD_VERSION}" not in changelog.read_text(encoding="utf-8"):
        problems.append(f"CHANGELOG.md does not record Shared standard {STANDARD_VERSION}")
    res.add("V20 standard version consistent", problems, STANDARD_VERSION)

    # V21
    cats = y("readiness-categories.yaml").get("categories") or []
    problems = [] if [c.get("category_id") for c in cats] == CONTRACT["readiness_categories"] else ["categories differ from the contract"]
    for c in cats:
        for f in ("name", "description", "evidence_examples", "owning_authority"):
            if not c.get(f):
                problems.append(f"{c.get('category_id')}: missing {f}")
        if any(k in c for k in ("weight", "weights")):
            problems.append(f"{c.get('category_id')}: weights do not belong in the standard")
    res.add("V21 readiness categories canonical", problems, "6 categories, no weights")

    # V22
    sevs = y("severity-scale.yaml").get("severities") or []
    problems = [] if [s.get("severity_id") for s in sevs] == CONTRACT["severities"] else ["severity ids differ from the contract"]
    for s in sevs:
        for f in ("display_name", "definition", "impact", "response_expectation_reference", "escalation_role"):
            if not s.get(f):
                problems.append(f"{s.get('severity_id')}: missing {f}")
        for k, v in s.items():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                problems.append(f"{s.get('severity_id')}: numeric value {k} (timers belong in configuration)")
    res.add("V22 severity scale generic", problems, "sev1 to sev4, no timers")

    # V23
    glossary = (root / "standard/glossary.md")
    gtext = glossary.read_text(encoding="utf-8") if glossary.is_file() else ""
    defined = {m.group(1).strip() for m in re.finditer(r"^\| ([^|]+) \|", gtext, re.MULTILINE)}
    problems = [f"term not defined: {t}" for t in CONTRACT["glossary_terms"] if t not in defined]
    res.add("V23 glossary defines required terms", problems, f"{len(CONTRACT['glossary_terms'])} terms")

    core_checks(root, res, catalog_by_type, entity_prefix, event_schema, lc)

    res.rows.sort(key=lambda r: r[0])
    return res

# ---------------------------------------------------------------------------
# R1 v0.1 core checks (V25 to V41). Deterministic rules live in tools/r1_rules.py;
# these checks call them so the validator and the rules can never disagree.

CORE_VERSION = "0.1.0"
CORE_FILES = (
    "docs/architecture.md",
    "docs/lifecycle-overview.md",
    "docs/scaling-model.md",
    "docs/practical-workflow.md",
    "docs/authority-boundaries.md",
    "docs/portfolio-integration.md",
    "lifecycle/lifecycle.yaml",
    "lifecycle/gates.yaml",
    "schemas/project.schema.json",
    "schemas/phase.schema.json",
    "schemas/milestone.schema.json",
    "schemas/task.schema.json",
    "schemas/gate-assessment.schema.json",
    "schemas/request.schema.json",
    "schemas/handoff.schema.json",
    "schemas/risk.schema.json",
    "schemas/issue.schema.json",
    "schemas/readiness-scorecard.schema.json",
    "config/request-state-machine.yaml",
    "config/sla-rules.yaml",
    "config/risk-rules.yaml",
    "config/lead-time-rules.yaml",
    "config/readiness-weights.yaml",
    "profiles/profile.schema.json",
    "profiles/examples/org-stage-startup.yaml",
    "profiles/examples/complexity-tier-standard.yaml",
    "profiles/examples/service-tier-standard.yaml",
    "profiles/examples/segment-mid-market.yaml",
    "data/synthetic/README.md",
    "data/synthetic/projects.csv",
    "data/synthetic/phases.csv",
    "data/synthetic/milestones.csv",
    "data/synthetic/tasks.csv",
    "data/synthetic/requests.csv",
    "data/synthetic/risks.csv",
    "data/synthetic/issues.csv",
    "data/synthetic/readiness.csv",
    "data/synthetic/events.jsonl",
    "verification/R1-V0.1-CHECKLIST.md",
    "verification/referential-integrity.md",
    "verification/deterministic-rules.md",
    "verification/synthetic-data-check.md",
    "verification/release-gate.md",
)
# file -> (schema, data key, exact row count)
CSV_SPEC = {
    "projects.csv": ("project", "projects", 3),
    "phases.csv": ("phase", "phases", 15),
    "milestones.csv": ("milestone", "milestones", 12),
    "tasks.csv": ("task", "tasks", 30),
    "requests.csv": ("request", "requests", 8),
    "risks.csv": ("risk", "risks", 6),
    "issues.csv": ("issue", "issues", 5),
    "readiness.csv": ("readiness-scorecard", "readiness", 18),
}
EVENT_COUNT_RANGE = (30, 45)
# CSV-backed prefixes whose records the synthetic data holds.
RECORD_PREFIX = {
    "PRJ": ("projects", "project_id"), "PHS": ("phases", "phase_id"), "MLS": ("milestones", "milestone_id"),
    "TSK": ("tasks", "task_id"), "REQ": ("requests", "request_id"), "RSK": ("risks", "risk_id"),
    "ISS": ("issues", "issue_id"), "RDS": ("scorecards", "readiness_scorecard_id"),
}
FORMALITY = {"lightweight", "standard", "formal"}
ACTIVATION = {"optional", "recommended", "required"}
PERFORMERS = {"owner", "approver", "receiving_role"}
SCORECARD_FIELDS = ("readiness_scorecard_id", "project_id", "assessment_purpose", "assessed_at", "calculation_version",
                    "overall_score", "incomplete_required_evidence_flag", "schema_version")
README_SECTIONS = (
    "Purpose", "Who this is for", "What problem it solves", "Practical IC use", "Architecture", "Ten-phase lifecycle",
    "Deterministic rules", "Data model", "Readiness", "Scaling", "Configuration", "Synthetic example",
    "Cross-repo integration", "What is not included yet", "Limitations", "Public-safety statement", "AI assistance",
    "Versioning", "License",
)
WORKFLOW_SECTIONS = (
    "trigger", "inputs", "steps", "deterministic rules", "outputs", "events", "human decisions",
    "downstream integrations", "verification", "solo", "early-scale", "structured-growth", "mature",
)
# Well-known vendor and product names that must not appear in the core. The private
# blocklist (V18) and the private workspace publication gate cover private and
# premise terms; they are never listed in this public file.
GENERICITY_TERMS = (
    "Salesforce", "HubSpot", "Zendesk", "ServiceNow", "Jira", "Asana", "Smartsheet", "Monday.com", "Workday",
    "Oracle", "SAP", "Microsoft", "Excel", "Google", "Slack", "Notion",
)


def _load_yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _guard(res: Result, check: str, ok_note: str, fn) -> None:
    """Run one check; any crash becomes a failure of that check, never of the run."""
    try:
        problems, note = fn()
    except Exception as exc:  # noqa: BLE001
        problems, note = [f"check could not run: {exc.__class__.__name__}: {exc}"], ""
    res.add(check, problems, note or ok_note)


def core_checks(root: Path, res: Result, catalog_by_type: dict, entity_prefix: dict, event_schema: dict, lc: dict) -> None:
    import r1_rules as rules  # tools/r1_rules.py

    std_phases = CONTRACT["phases"]
    stages = CONTRACT["org_stages"]
    ctx: dict = {}

    def y(rel_path: str):
        if rel_path not in ctx:
            ctx[rel_path] = _load_yaml(root / rel_path)
        return ctx[rel_path]

    def j(rel_path: str):
        key = "json:" + rel_path
        if key not in ctx:
            ctx[key] = json.loads((root / rel_path).read_text(encoding="utf-8"))
        return ctx[key]

    # V25
    def v25():
        missing = [f for f in CORE_FILES if not (root / f).is_file()]
        return [f"missing {m}" for m in missing], f"{len(CORE_FILES)} present"
    _guard(res, "V25 R1 core files exist", "", v25)

    # V26
    def v26():
        problems = []
        names = sorted((root / "schemas").glob("*.schema.json")) + [root / "profiles/profile.schema.json"]
        for path in names:
            r = rel(root, path)
            doc = j(r)
            Draft202012Validator.check_schema(doc)
            if f":{CORE_VERSION}:" not in doc.get("$id", "") or ":core:" not in doc.get("$id", ""):
                problems.append(f"{r}: $id does not carry core:{CORE_VERSION}")
            if doc.get("additionalProperties") is not False:
                problems.append(f"{r}: additionalProperties is not false")
            validator = Draft202012Validator(doc, format_checker=FormatChecker())
            if not doc.get("examples"):
                problems.append(f"{r}: no examples")
            for i, ex in enumerate(doc.get("examples", [])):
                errors = list(validator.iter_errors(ex))
                if errors:
                    problems.append(f"{r} example {i}: {errors[0].message}")
                for key, value in walk_values(ex):
                    if isinstance(value, str) and ID_LIKE.match(value):
                        if not ID_RE.match(value) or value[:3] not in entity_prefix.values():
                            problems.append(f"{r} example {i}: unregistered or malformed ID {value}")
            props = doc.get("properties", {})
            for key, spec in props.items():
                if not SNAKE_RE.match(key):
                    problems.append(f"{r}: field {key} is not snake_case")
                pat = spec.get("pattern", "")
                m = re.match(r"^\^([A-Z]{3})-\[0-9\]\{6\}\$$", pat)
                if m and m.group(1) not in entity_prefix.values():
                    problems.append(f"{r}: {key} uses unregistered prefix {m.group(1)}")
            cols = doc.get("x-csv-columns")
            if cols is not None:
                item_props = props.get("categories", {}).get("items", {}).get("properties", {})
                known = set(props) | set(item_props)
                if len(cols) != len(set(cols)):
                    problems.append(f"{r}: duplicate CSV columns")
                problems += [f"{r}: CSV column {c} is not a schema field" for c in cols if c not in known]
                needed = [f for f in doc.get("required", []) if f != "categories"]
                problems += [f"{r}: required field {f} has no CSV column" for f in needed if f not in cols]
        own = {"project": "project_id", "phase": "phase_id", "milestone": "milestone_id", "task": "task_id",
               "gate-assessment": "gate_assessment_id", "request": "request_id", "handoff": "handoff_id",
               "risk": "risk_id", "issue": "issue_id", "readiness-scorecard": "readiness_scorecard_id"}
        for name, key in own.items():
            doc = j(f"schemas/{name}.schema.json")
            if key not in doc.get("required", []):
                problems.append(f"schemas/{name}.schema.json: own ID {key} not required")
            if doc.get("properties", {}).get("schema_version", {}).get("const") != CORE_VERSION:
                problems.append(f"schemas/{name}.schema.json: schema_version is not fixed to {CORE_VERSION}")
        return problems, f"{len(names)} schemas"
    _guard(res, "V26 R1 schemas valid with CSV contracts", "", v26)

    # V27
    def v27():
        problems = []
        files = sorted(list((root / "lifecycle").glob("*.yaml")) + list((root / "config").glob("*.yaml"))
                       + list((root / "profiles/examples").glob("*.yaml")))
        for path in files:
            r = rel(root, path)
            doc = y(r)
            if not isinstance(doc, dict):
                problems.append(f"{r}: not a mapping")
                continue
            if r.startswith(("lifecycle/", "config/")):
                if str(doc.get("standard_version")) != STANDARD_VERSION:
                    problems.append(f"{r}: standard_version is not {STANDARD_VERSION}")
                if str(doc.get("core_version")) != CORE_VERSION:
                    problems.append(f"{r}: core_version is not {CORE_VERSION}")
            if r.startswith("lifecycle/"):
                problems += [f"{r}: empty value for {k}" for k, v in walk_values(doc) if v is None]
        return problems, f"{len(files)} files"
    _guard(res, "V27 R1 configuration YAML parses", "", v27)

    # V28
    def v28():
        doc = y("lifecycle/lifecycle.yaml")
        problems = []
        phases = doc.get("phases") or []
        ids = [p.get("phase_id") for p in phases]
        if ids != std_phases:
            problems.append("lifecycle phases differ from the ten standard phase keys or their order")
        if [p.get("order") for p in phases] != list(range(1, 11)):
            problems.append("phase order is not 1 to 10")
        names = {p["phase_key"]: p["name"] for p in lc.get("phases") or []}
        roles = {r.get("role_key") for r in doc.get("role_keys") or []}
        artifacts = {a.get("artifact_type") for a in doc.get("artifact_types") or []}
        rework = {(m["from_phase_id"], m["to_phase_id"]) for m in (doc.get("phase_move_rules") or {}).get("rework_moves") or []}
        if (doc.get("phase_move_rules") or {}).get("forward_move_requires_gate_outcomes") != ["pass", "pass_with_conditions"]:
            problems.append("forward moves must require pass or pass_with_conditions")
        keys = ("phase_id", "name", "order", "purpose", "entry_criteria", "exit_criteria", "expected_artifact_types",
                "owner_roles", "emitted_events", "legal_next_phase_ids", "stage_behavior")
        for i, p in enumerate(phases):
            pid = p.get("phase_id")
            problems += [f"{pid}: missing {k}" for k in keys if k not in p]
            if names.get(pid) != p.get("name"):
                problems.append(f"{pid}: name differs from standard")
            nxt = p.get("legal_next_phase_ids") or []
            problems += [f"{pid}: legal next {n} is not a phase" for n in nxt if n not in std_phases]
            expected_forward = std_phases[i + 1] if i + 1 < len(std_phases) else None
            if expected_forward and expected_forward not in nxt:
                problems.append(f"{pid}: the next phase {expected_forward} is not a legal next phase")
            for n in nxt:
                if n in std_phases and std_phases.index(n) <= i and (pid, n) not in rework:
                    problems.append(f"{pid}: backward move to {n} is not a listed rework move")
                if n in std_phases and std_phases.index(n) > i + 1:
                    problems.append(f"{pid}: skips to {n}")
            problems += [f"{pid}: owner role {r} unknown" for r in p.get("owner_roles") or [] if r not in roles]
            problems += [f"{pid}: artifact type {a} unknown" for a in p.get("expected_artifact_types") or [] if a not in artifacts]
            for ev in p.get("emitted_events") or []:
                entry = catalog_by_type.get(ev)
                if not entry:
                    problems.append(f"{pid}: event {ev} not in the catalog")
                elif entry.get("producer_repo") != R1 or entry.get("scenario_pack"):
                    problems.append(f"{pid}: event {ev} is not an R1 core event")
            sb = p.get("stage_behavior") or {}
            if list(sb) != stages or any((v or {}).get("formality") not in FORMALITY for v in sb.values()):
                problems.append(f"{pid}: stage_behavior must cover the four stages with a valid formality")
        if phases and phases[-1].get("legal_next_phase_ids"):
            problems.append("review must be the last phase")
        for f, t in rework:
            if t not in (next((p for p in phases if p.get("phase_id") == f), {}).get("legal_next_phase_ids") or []):
                problems.append(f"rework move {f} to {t} is not a legal next phase")
        return problems, "10 phases in standard order"
    _guard(res, "V28 lifecycle has ten valid phases", "", v28)

    # V29
    def v29():
        doc = y("lifecycle/gates.yaml")
        life = y("lifecycle/lifecycle.yaml")
        roles = {r.get("role_key") for r in life.get("role_keys") or []}
        artifacts = {a.get("artifact_type") for a in life.get("artifact_types") or []}
        checks = {c.get("check_id") for c in doc.get("check_definitions") or []}
        problems = [f"check {c} has no implementation in tools/r1_rules.py" for c in sorted(checks - set(rules.GATE_CHECKS))]
        gates = doc.get("gates") or []
        seen = [g.get("phase_id") for g in gates]
        if seen != std_phases[:-1]:
            problems.append("gates must cover initiate to transition, one per phase, in order (review has no gate)")
        for g in gates:
            gid = g.get("gate_id")
            if gid != f"{g.get('phase_id')}_gate":
                problems.append(f"{gid}: gate_id must be <phase_id>_gate")
            if g.get("phase_id") not in std_phases:
                problems.append(f"{gid}: phase_id is not a lifecycle phase")
            if g.get("allowed_outcomes") != CONTRACT["gate_outcomes"] or lc.get("gate_outcomes") != g.get("allowed_outcomes"):
                problems.append(f"{gid}: allowed_outcomes differ from the standard gate outcomes")
            if g.get("approver_role") not in roles:
                problems.append(f"{gid}: approver_role is not a role key")
            if g.get("recorded_by") != "human":
                problems.append(f"{gid}: outcome must be recorded_by human")
            if g.get("emitted_event") != "gate.assessed":
                problems.append(f"{gid}: emitted_event must be gate.assessed")
            for ev in g.get("required_evidence_types") or []:
                if ev.get("artifact_type") not in artifacts or not isinstance(ev.get("waivable_by_profile"), bool):
                    problems.append(f"{gid}: invalid evidence entry {ev}")
            problems += [f"{gid}: check {c} undefined" for c in g.get("required_checks") or [] if c not in checks]
            sb = g.get("stage_behavior") or {}
            if list(sb) != stages or any((v or {}).get("formality") not in FORMALITY for v in sb.values()):
                problems.append(f"{gid}: stage_behavior must cover the four stages with a valid formality")
            text = json.dumps(g).lower()
            if "ai_agent" in text or "agt-" in text:
                problems.append(f"{gid}: an agent cannot take part in a gate outcome")
        return problems, f"{len(gates)} gates, outcomes {', '.join(CONTRACT['gate_outcomes'])}"
    _guard(res, "V29 gates reference valid phases and human outcomes", "", v29)

    # V30
    def v30():
        sm = y("config/request-state-machine.yaml")
        schema_enum = j("schemas/request.schema.json")["properties"]["status"]["enum"]
        statuses = sm.get("statuses") or []
        problems = []
        if statuses != schema_enum:
            problems.append("request schema status enum differs from config/request-state-machine.yaml")
        if sm.get("initial_status") not in statuses or not set(sm.get("terminal_statuses") or []) <= set(statuses):
            problems.append("initial or terminal status unknown")
        for ev in (sm.get("initial_event"), sm.get("transition_event")):
            if ev not in catalog_by_type:
                problems.append(f"event {ev} not in the catalog")
        pairs = []
        for t in sm.get("transitions") or []:
            pair = (t.get("from_status"), t.get("to_status"))
            pairs.append(pair)
            if pair[0] not in statuses or pair[1] not in statuses or pair[0] == pair[1]:
                problems.append(f"invalid transition {pair}")
            if t.get("performed_by") not in PERFORMERS:
                problems.append(f"{pair}: performed_by must be one of {sorted(PERFORMERS)}")
            if not isinstance(t.get("human_action_required"), bool) or not t.get("requirements"):
                problems.append(f"{pair}: needs human_action_required and requirements")
            if t.get("emitted_event") != sm.get("transition_event"):
                problems.append(f"{pair}: emitted_event must be {sm.get('transition_event')}")
            if pair[0] == "awaiting_approval" and (t.get("performed_by") != "approver" or not t.get("human_action_required")):
                problems.append(f"{pair}: leaving awaiting_approval needs a named human approver")
        problems += [f"duplicate transition {p}" for p in sorted({p for p in pairs if pairs.count(p) > 1})]
        graph: dict = {}
        for a, b in pairs:
            graph.setdefault(a, set()).add(b)
        reach, queue = {sm.get("initial_status")}, [sm.get("initial_status")]
        while queue:
            for n in graph.get(queue.pop(), ()):
                if n not in reach:
                    reach.add(n)
                    queue.append(n)
        problems += [f"status {s} is unreachable" for s in statuses if s not in reach]
        for s in statuses:
            seen, queue = {s}, [s]
            while queue:
                for n in graph.get(queue.pop(), ()):
                    if n not in seen:
                        seen.add(n)
                        queue.append(n)
            if not seen & set(sm.get("terminal_statuses") or []):
                problems.append(f"status {s} cannot reach a terminal status")
        problems += [f"terminal status {s} has outgoing transitions" for s in sm.get("terminal_statuses") or [] if graph.get(s)]
        return problems, f"{len(statuses)} statuses, {len(pairs)} legal transitions"
    _guard(res, "V30 request state machine is authoritative and complete", "", v30)

    # V31
    def v31():
        sla = y("config/sla-rules.yaml")
        life = y("lifecycle/lifecycle.yaml")
        roles = {r.get("role_key") for r in life.get("role_keys") or []}
        entity_status = {
            "request": j("schemas/request.schema.json")["properties"]["status"]["enum"],
            "handoff": j("schemas/handoff.schema.json")["properties"]["status"]["enum"],
            "issue": j("schemas/issue.schema.json")["properties"]["status"]["enum"],
        }
        problems = []
        ids, keys, matches = [], [], []
        required = ("rule_id", "key", "applies_to_entity", "trigger", "timer_basis", "target_duration", "warning_offset",
                    "action", "enabled_flag", "stage_behavior")
        for rule in sla.get("rules") or []:
            rid = rule.get("rule_id")
            problems += [f"{rid}: missing {k}" for k in required if k not in rule]
            ids.append(rid)
            keys.append(rule.get("key"))
            if not re.fullmatch(r"RUL-[0-9]{6}", str(rid)):
                problems.append(f"{rid}: rule_id is not a RUL ID")
            ent = rule.get("applies_to_entity")
            trig = rule.get("trigger") or {}
            if ent not in entity_status:
                problems.append(f"{rid}: applies_to_entity {ent} has no timer support")
            elif trig.get("status") not in entity_status[ent]:
                problems.append(f"{rid}: trigger status {trig.get('status')} is not a {ent} status")
            if "severity" in trig and trig["severity"] not in CONTRACT["severities"]:
                problems.append(f"{rid}: trigger severity invalid")
            if rule.get("timer_basis") not in (sla.get("timer_basis_values") or []):
                problems.append(f"{rid}: timer_basis invalid")
            try:
                if rules.parse_duration(rule.get("warning_offset")) >= rules.parse_duration(rule.get("target_duration")):
                    problems.append(f"{rid}: warning_offset must be shorter than target_duration")
            except ValueError as exc:
                problems.append(f"{rid}: {exc}")
            action = rule.get("action")
            if action not in (sla.get("action_values") or []):
                problems.append(f"{rid}: action invalid")
            if action == "escalate" and (ent != "request" or rule.get("escalation_severity") not in CONTRACT["severities"]):
                problems.append(f"{rid}: escalate needs a request rule with an escalation_severity (request.escalated)")
            if action in ("escalate", "notify_role"):
                if not re.fullmatch(r"ROL-[0-9]{6}", str(rule.get("escalation_role_id"))) or rule.get("escalation_role_key") not in roles:
                    problems.append(f"{rid}: {action} needs escalation_role_id (ROL) and a valid escalation_role_key")
            elif "escalation_role_id" in rule:
                problems.append(f"{rid}: notify_owner takes no escalation role")
            if not isinstance(rule.get("enabled_flag"), bool):
                problems.append(f"{rid}: enabled_flag must be true or false")
            sb = rule.get("stage_behavior") or {}
            if list(sb) != stages or any(v not in ACTIVATION for v in sb.values()):
                problems.append(f"{rid}: stage_behavior must cover the four stages")
            if rule.get("enabled_flag"):
                matches.append((ent, trig.get("status"), trig.get("severity")))
        problems += [f"duplicate rule_id {i}" for i in sorted({i for i in ids if ids.count(i) > 1})]
        problems += [f"duplicate key {k}" for k in sorted({k for k in keys if keys.count(k) > 1})]
        problems += [f"two enabled rules match {m}" for m in sorted({m for m in matches if matches.count(m) > 1}, key=str)]
        problems += [f"severity key {s} missing (standard/severity-scale.yaml points to it)" for s in CONTRACT["severities"] if s not in keys]
        return problems, f"{len(ids)} rules, durations parse"
    _guard(res, "V31 SLA rules configurable and well formed", "", v31)

    # V32
    def v32():
        rr = y("config/risk-rules.yaml")
        life = y("lifecycle/lifecycle.yaml")
        roles = {r.get("role_key") for r in life.get("role_keys") or []}
        problems = list(rules.risk_band_problems(rr))
        if rr.get("formula") != "likelihood_times_impact":
            problems.append("formula must be likelihood_times_impact")
        if not re.fullmatch(r"RUL-[0-9]{6}", str(rr.get("rule_id"))):
            problems.append("rule_id is not a RUL ID")
        for name in ("likelihood_values", "impact_values"):
            scale = rr.get(name) or {}
            if not all(isinstance(scale.get(k), int) for k in ("min", "max")) or scale["min"] < 1 or scale["min"] > scale["max"]:
                problems.append(f"{name}: invalid scale")
            elif [m.get("value") for m in scale.get("meanings") or []] != list(range(scale["min"], scale["max"] + 1)):
                problems.append(f"{name}: every scale value needs a meaning")
        for band in rr.get("bands") or []:
            if band.get("severity") not in CONTRACT["severities"]:
                problems.append(f"band {band.get('band')}: severity invalid")
            if band.get("escalate_to_role_key") is not None and band.get("escalate_to_role_key") not in roles:
                problems.append(f"band {band.get('band')}: escalation role key invalid")
        return problems, f"{len(rr.get('bands') or [])} bands cover every score"
    _guard(res, "V32 risk rules deterministic", "", v32)

    # V33
    def v33():
        lt = y("config/lead-time-rules.yaml")
        problems = []
        ids = []
        for rule in lt.get("rules") or []:
            rid = rule.get("rule_id")
            ids.append(rid)
            if not re.fullmatch(r"RUL-[0-9]{6}", str(rid)):
                problems.append(f"{rid}: rule_id is not a RUL ID")
            if rule.get("rule_type") not in (lt.get("rule_type_values") or []):
                problems.append(f"{rid}: rule_type invalid")
            try:
                rules.parse_duration(rule.get("lead_time"))
            except ValueError as exc:
                problems.append(f"{rid}: {exc}")
            match = rule.get("match") or {}
            problems += [f"{rid}: phase key {k} invalid" for k in match.get("phase_keys") or [] if k not in std_phases]
            if not all(isinstance(match.get(k), bool) for k in ("critical_only", "open_only")) or not isinstance(rule.get("enabled_flag"), bool):
                problems.append(f"{rid}: flags must be true or false")
        problems += [f"duplicate rule_id {i}" for i in sorted({i for i in ids if ids.count(i) > 1})]
        return problems, f"{len(ids)} rules, durations parse"
    _guard(res, "V33 lead-time rules deterministic", "", v33)

    # V34
    def v34():
        rw = y("config/readiness-weights.yaml")
        problems = rules.readiness_weight_problems(rw, CONTRACT["readiness_categories"])
        if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", str(rw.get("calculation_version"))):
            problems.append("calculation_version is not SemVer")
        if not re.fullmatch(r"RUL-[0-9]{6}", str(rw.get("rule_id"))):
            problems.append("rule_id is not a RUL ID")
        return problems, f"6 canonical categories, total {rw.get('total_weight')}"
    _guard(res, "V34 readiness weights valid", "", v34)

    def all_rule_ids() -> dict[str, str]:
        out = {}
        for r in y("config/sla-rules.yaml").get("rules") or []:
            out[r["rule_id"]] = "config/sla-rules.yaml"
        for r in y("config/lead-time-rules.yaml").get("rules") or []:
            out[r["rule_id"]] = "config/lead-time-rules.yaml"
        out[y("config/risk-rules.yaml")["rule_id"]] = "config/risk-rules.yaml"
        out[y("config/readiness-weights.yaml")["rule_id"]] = "config/readiness-weights.yaml"
        return out

    # V35
    def v35():
        schema = j("profiles/profile.schema.json")
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        life = y("lifecycle/lifecycle.yaml")
        gates = {g["gate_id"]: g for g in y("lifecycle/gates.yaml")["gates"]}
        roles = {r.get("role_key") for r in life.get("role_keys") or []}
        artifacts = {a.get("artifact_type") for a in life.get("artifact_types") or []}
        entity_schema = {e.replace("-", "_"): j(f"schemas/{e}.schema.json") for e in (
            "project", "phase", "milestone", "task", "gate-assessment", "request", "handoff", "risk", "issue", "readiness-scorecard")}
        rule_files = all_rule_ids()
        cfg_rules = {}
        for f in ("config/sla-rules.yaml", "config/lead-time-rules.yaml"):
            for r in y(f).get("rules") or []:
                cfg_rules[r["rule_id"]] = (f, r)
        all_rules = {k for k in rule_files}
        problems = []
        ids, overrides = [], []
        files = sorted((root / "profiles/examples").glob("*.yaml"))
        for path in files:
            r = rel(root, path)
            text = path.read_text(encoding="utf-8")
            doc = y(r)
            errors = list(validator.iter_errors(doc))
            if errors:
                problems.append(f"{r}: {errors[0].message}")
                continue
            ids.append(doc["profile_id"])
            if CONTRACT["labels"][2] not in text:
                problems.append(f"{r}: lacks the illustrative example label")
            for label in (CONTRACT["labels"][0], CONTRACT["labels"][3]):
                if label not in text:
                    problems.append(f"{r}: lacks the label '{label}'")
            for rf in doc["required_fields"]:
                props = entity_schema[rf["entity"]].get("properties", {})
                item_props = props.get("categories", {}).get("items", {}).get("properties", {})
                if rf["field"] not in props and rf["field"] not in item_props:
                    problems.append(f"{r}: {rf['entity']}.{rf['field']} is not a schema field")
            for ga in doc["gate_adjustments"]:
                gate = gates.get(ga["gate_id"])
                if not gate:
                    problems.append(f"{r}: gate {ga['gate_id']} unknown")
                    continue
                waivable = {e["artifact_type"] for e in gate["required_evidence_types"] if e["waivable_by_profile"]}
                problems += [f"{r}: {ga['gate_id']} evidence {a} is not waivable" for a in ga.get("optional_evidence_types", []) if a not in waivable]
                problems += [f"{r}: artifact type {a} unknown" for a in ga.get("additional_evidence_types", []) if a not in artifacts]
                if "approver_role" in ga and ga["approver_role"] not in roles:
                    problems.append(f"{r}: approver_role {ga['approver_role']} unknown")
            for po in doc["parameter_overrides"]:
                overrides.append((po["rule_id"], po["field"]))
                if po["rule_id"] not in all_rules or cfg_rules.get(po["rule_id"], ("",))[0] != po["config_file"]:
                    problems.append(f"{r}: rule {po['rule_id']} is not in {po['config_file']}")
                    continue
                rule = cfg_rules[po["rule_id"]][1]
                if po["field"] not in rule:
                    problems.append(f"{r}: {po['rule_id']} has no field {po['field']}")
                elif po["field"] == "enabled_flag":
                    if not isinstance(po["value"], bool):
                        problems.append(f"{r}: enabled_flag override must be true or false")
                    elif po["value"] is False and doc["profile_type"] == "org_stage" and (rule.get("stage_behavior") or {}).get(doc.get("org_stage")) == "required":
                        problems.append(f"{r}: cannot disable {po['rule_id']}, which is required at {doc.get('org_stage')}")
                else:
                    try:
                        rules.parse_duration(po["value"])
                    except ValueError as exc:
                        problems.append(f"{r}: {exc}")
        problems += [f"duplicate profile_id {i}" for i in sorted({i for i in ids if ids.count(i) > 1})]
        problems += [f"two example profiles override {o}" for o in sorted({o for o in overrides if overrides.count(o) > 1})]
        types = {y(rel(root, p)).get("profile_type") for p in files}
        if types != {"org_stage", "complexity", "service", "segment"}:
            problems.append("examples must cover the four profile types")
        return problems, f"{len(files)} illustrative example profiles, 4 types"
    _guard(res, "V35 profiles configure the same model", "", v35)

    # Load the synthetic data once for V36 to V39.
    data: dict[str, list[dict]] = {}
    headers: dict[str, list[str]] = {}

    def load_data():
        if data:
            return
        for fname, (schema_name, key, _) in CSV_SPEC.items():
            schema = j(f"schemas/{schema_name}.schema.json")
            headers[fname], data[key] = rules.read_csv_records(root / "data/synthetic" / fname, schema)
        cards: dict[str, dict] = {}
        for row in data["readiness"]:
            card = cards.setdefault(row.get("readiness_scorecard_id"), {f: row.get(f) for f in SCORECARD_FIELDS if f in row})
            card.setdefault("categories", []).append({k: v for k, v in row.items() if k not in SCORECARD_FIELDS})
        data["scorecards"] = list(cards.values())

    # V36
    def v36():
        load_data()
        problems = []
        for fname, (schema_name, key, count) in CSV_SPEC.items():
            schema = j(f"schemas/{schema_name}.schema.json")
            if headers[fname] != schema["x-csv-columns"]:
                problems.append(f"{fname}: header differs from {schema_name}.schema.json x-csv-columns")
            if len(data[key]) != count:
                problems.append(f"{fname}: {len(data[key])} rows, expected exactly {count}")
            validator = Draft202012Validator(schema, format_checker=FormatChecker())
            rows = data["scorecards"] if key == "readiness" else data[key]
            for row in rows:
                errors = list(validator.iter_errors(row))
                if errors:
                    problems.append(f"{fname} {next(iter(row.values()), '?')}: {errors[0].message}")
            own = schema["x-csv-columns"][0]
            ids = [r.get(own) for r in data[key]]
            problems += [f"{fname}: duplicate {own} {i}" for i in sorted({i for i in ids if ids.count(i) > 1}, key=str)]
        return problems, "8 files, exact row counts 3, 15, 12, 30, 8, 6, 5, 18; every row validates"
    _guard(res, "V36 synthetic CSVs conform to the schemas", "", v36)

    # V37
    def v37():
        load_data()
        profile_ids = {y(rel(root, p)).get("profile_id") for p in (root / "profiles/examples").glob("*.yaml")}
        problems = list(rules.reference_problems(data, profile_ids))
        index = {pfx: {r.get(f): r for r in data.get(k, [])} for pfx, (k, f) in RECORD_PREFIX.items()}
        refs = 0
        for card in data["scorecards"]:
            for entry in card.get("categories", []):
                for ref in entry.get("evidence_refs") or []:
                    refs += 1
                    target = index.get(ref[:3], {}).get(ref)
                    if target is None:
                        problems.append(f"{card['readiness_scorecard_id']}: evidence {ref} does not resolve")
                    elif target.get("project_id", card["project_id"]) != card["project_id"]:
                        problems.append(f"{card['readiness_scorecard_id']}: evidence {ref} belongs to another project")
        gates = {g["gate_id"]: g["phase_id"] for g in y("lifecycle/gates.yaml")["gates"]}
        for p in data["phases"]:
            expected = f"{p['lifecycle_phase_key']}_gate" if p["lifecycle_phase_key"] in gates.values() else None
            if p.get("gate_id") != expected:
                problems.append(f"{p['phase_id']}: gate_id must be {expected}")
        counted = sum(len(v) for k, v in data.items() if k != "readiness")
        return problems, f"{counted} records and {refs} evidence references checked; 0 orphans"
    _guard(res, "V37 synthetic references resolve with zero orphans", "", v37)

    # V38
    def v38():
        load_data()
        problems = []
        rr = y("config/risk-rules.yaml")
        sla = y("config/sla-rules.yaml")
        rw = y("config/readiness-weights.yaml")
        life = y("lifecycle/lifecycle.yaml")
        for r in data["risks"]:
            try:
                if rules.risk_score(r["likelihood"], r["impact"], rr) != r["risk_score"]:
                    problems.append(f"{r['risk_id']}: risk_score is not likelihood x impact")
            except ValueError as exc:
                problems.append(f"{r['risk_id']}: {exc}")
        weights = {c["category"]: c["weight"] for c in rw["categories"]}
        for card in data["scorecards"]:
            cid = card["readiness_scorecard_id"]
            rows = [row for row in data["readiness"] if row.get("readiness_scorecard_id") == cid]
            for f in SCORECARD_FIELDS:
                if len({json.dumps(row.get(f)) for row in rows}) != 1:
                    problems.append(f"{cid}: {f} differs between its rows")
            cats = card.get("categories", [])
            if sorted(c.get("category") for c in cats) != sorted(CONTRACT["readiness_categories"]):
                problems.append(f"{cid}: categories are not exactly the six canonical categories")
                continue
            if card.get("calculation_version") != rw.get("calculation_version"):
                problems.append(f"{cid}: calculation_version differs from config")
            calc = rules.readiness_scorecard({c["category"]: c for c in cats}, rw)
            for c in cats:
                exp = calc["categories"][c["category"]]
                if c["weight"] != weights[c["category"]]:
                    problems.append(f"{cid} {c['category']}: weight differs from config")
                if rules.Decimal(str(c["achieved_rate"])) != exp["achieved_rate"].quantize(rules.Decimal("0.0001")):
                    problems.append(f"{cid} {c['category']}: achieved_rate is not met / total")
                if rules.Decimal(str(c["category_score"])) != exp["category_score"]:
                    problems.append(f"{cid} {c['category']}: category_score is not weight x achieved_rate")
            if rules.Decimal(str(card["overall_score"])) != calc["overall_score"]:
                problems.append(f"{cid}: overall_score differs from the calculation ({calc['overall_score']})")
            if card["incomplete_required_evidence_flag"] != calc["incomplete_required_evidence_flag"]:
                problems.append(f"{cid}: incomplete_required_evidence_flag differs from the calculation")
        for q in data["requests"]:
            if q.get("escalation_due_at") != rules.expected_escalation_due_at(q, sla):
                problems.append(f"{q['request_id']}: escalation_due_at differs from config/sla-rules.yaml")
            if q["status_changed_at"] < q["submitted_at"]:
                problems.append(f"{q['request_id']}: status changed before submission")
        tasks = {t["task_id"]: t for t in data["tasks"]}
        for t in data["tasks"]:
            if t["status"] in ("in_progress", "completed"):
                open_preds = [p for p in t.get("predecessor_task_ids") or [] if tasks.get(p, {}).get("status") != "completed"]
                if open_preds:
                    problems.append(f"{t['task_id']}: {t['status']} while predecessor {open_preds[0]} is not completed")
            if t.get("planned_start_date") and t.get("planned_due_date") and t["planned_start_date"] > t["planned_due_date"]:
                problems.append(f"{t['task_id']}: starts after it is due")
        for m in data["milestones"]:
            if m["status"] == "missed" and m.get("completed_date"):
                problems.append(f"{m['milestone_id']}: missed milestone has a completed_date")
        for i in data["issues"]:
            if i.get("resolved_at") and i["resolved_at"] < i["opened_at"]:
                problems.append(f"{i['issue_id']}: resolved before opened")
        projects = {p["project_id"]: p for p in data["projects"]}
        for pid, project in projects.items():
            seq = sorted((p for p in data["phases"] if p["project_id"] == pid), key=lambda p: p.get("entered_at") or "")
            if not seq:
                problems.append(f"{pid}: has no phase")
                continue
            if seq[0]["lifecycle_phase_key"] != "initiate":
                problems.append(f"{pid}: first phase is not initiate")
            for a, b in zip(seq, seq[1:]):
                if a["status"] != "completed":
                    problems.append(f"{a['phase_id']}: only the latest phase instance may be open")
                if not rules.phase_move_allowed(a["lifecycle_phase_key"], b["lifecycle_phase_key"], "pass", life):
                    problems.append(f"{pid}: illegal phase move {a['lifecycle_phase_key']} to {b['lifecycle_phase_key']}")
                if (a.get("exited_at") or "") > (b.get("entered_at") or ""):
                    problems.append(f"{b['phase_id']}: entered before the previous phase exited")
            if project["current_phase_id"] != seq[-1]["phase_id"]:
                problems.append(f"{pid}: current_phase_id is not the latest phase instance")
            if project["project_status"] == "active" and seq[-1]["status"] == "completed" and seq[-1]["lifecycle_phase_key"] != "review":
                problems.append(f"{pid}: active project has no open phase")
        flags = rules.lead_time_flags(data, y("config/lead-time-rules.yaml"))
        return problems, f"risk, readiness, escalation, dependency, and phase-sequence rules hold; {len(flags)} lead-time flag(s) raised for review"
    _guard(res, "V38 synthetic data obeys the deterministic rules", "", v38)

    # V39
    def v39():
        load_data()
        problems = []
        path = root / "data/synthetic/events.jsonl"
        events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        lo, hi = EVENT_COUNT_RANGE
        if not lo <= len(events) <= hi:
            problems.append(f"{len(events)} events; expected {lo} to {hi}")
        validator = Draft202012Validator(event_schema, format_checker=FormatChecker())
        index = {pfx: {r.get(f): r for r in data.get(k, [])} for pfx, (k, f) in RECORD_PREFIX.items()}
        rule_ids = all_rule_ids()
        sla = y("config/sla-rules.yaml")
        rr = y("config/risk-rules.yaml")
        machine = y("config/request-state-machine.yaml")
        gates = {g["phase_id"]: g for g in y("lifecycle/gates.yaml")["gates"]}
        gate_events: dict[str, dict] = {}
        handoffs: set[str] = set()
        chains: dict[str, list] = {}
        last_entered: dict[str, str] = {}
        submitted: set[str] = set()
        prev_time = ""
        for n, ev in enumerate(events, start=1):
            eid = ev.get("event_id")
            if eid != f"EVT-{n:06d}":
                problems.append(f"line {n}: event_id must be EVT-{n:06d} (sequential)")
            errors = list(validator.iter_errors(ev))
            if errors:
                problems.append(f"{eid}: {errors[0].message}")
                continue
            if ev["occurred_at"] < prev_time:
                problems.append(f"{eid}: events are not in time order")
            prev_time = ev["occurred_at"]
            et, entry = ev["event_type"], catalog_by_type.get(ev["event_type"])
            if not entry:
                problems.append(f"{eid}: event type {et} is not registered")
                continue
            if entry.get("scenario_pack"):
                problems.append(f"{eid}: {et} belongs to scenario pack {entry['scenario_pack']}, which is not installed")
            if entry.get("producer_repo") != R1 or ev["source_repo"] != R1:
                problems.append(f"{eid}: {et} is not produced by this repository")
            if ev["schema_version"] != STANDARD_VERSION:
                problems.append(f"{eid}: schema_version is not {STANDARD_VERSION}")
            if ev["subject_type"] != entry.get("subject_type") or entity_prefix.get(ev["subject_type"]) != ev["subject_id"][:3]:
                problems.append(f"{eid}: subject does not match the catalog")
            pay = ev["payload"]
            allowed = set(entry.get("required_payload_fields") or []) | set(entry.get("optional_payload_fields") or [])
            problems += [f"{eid}: payload missing {f}" for f in entry.get("required_payload_fields") or [] if f not in pay]
            problems += [f"{eid}: payload field {f} is not in the catalog" for f in pay if f not in allowed]
            actor, atype = ev["actor_id"], ev["actor_type"]
            if atype == "ai_agent":
                problems.append(f"{eid}: R1 v0.1 core events have no AI actor")
            if atype == "system" and actor not in rule_ids:
                problems.append(f"{eid}: system actor {actor} is not a configured rule")
            sid = ev["subject_id"]
            subject = index.get(sid[:3], {}).get(sid) if sid[:3] in RECORD_PREFIX else None
            if sid[:3] in RECORD_PREFIX and subject is None:
                problems.append(f"{eid}: subject {sid} does not exist")
                continue
            project_of = (subject or {}).get("project_id", sid if sid.startswith("PRJ") else None)
            if "project_id" in pay:
                if pay["project_id"] not in index["PRJ"]:
                    problems.append(f"{eid}: payload project_id {pay['project_id']} does not exist")
                elif project_of and pay["project_id"] != project_of:
                    problems.append(f"{eid}: payload project_id differs from the subject's project")
            if "severity" in pay and pay["severity"] not in CONTRACT["severities"]:
                problems.append(f"{eid}: severity {pay['severity']} invalid")
            if "phase_key" in pay and pay["phase_key"] not in std_phases:
                problems.append(f"{eid}: phase_key invalid")
            at = ev["occurred_at"]
            if et == "project.created":
                if at != subject["created_at"] or pay["status"] != "active":
                    problems.append(f"{eid}: does not match the project's creation")
            elif et == "phase.entered":
                if pay["phase_key"] != subject["lifecycle_phase_key"] or at != subject.get("entered_at"):
                    problems.append(f"{eid}: does not match {sid}")
                last_entered[subject["project_id"]] = sid
            elif et == "phase.exited":
                if pay["phase_key"] != subject["lifecycle_phase_key"] or at != subject.get("exited_at"):
                    problems.append(f"{eid}: does not match {sid}")
                gat = pay.get("gate_assessment_id")
                if gat:
                    g = gate_events.get(gat)
                    if not g or g["payload"]["phase_key"] != pay["phase_key"] or g["payload"]["project_id"] != pay["project_id"]:
                        problems.append(f"{eid}: gate assessment {gat} does not resolve to this phase")
                    elif g["payload"]["outcome"] not in ("pass", "pass_with_conditions"):
                        problems.append(f"{eid}: a forward exit needs pass or pass_with_conditions")
            elif et == "gate.assessed":
                if sid in gate_events:
                    problems.append(f"{eid}: gate assessment {sid} recorded twice")
                gate_events[sid] = ev
                if not rules.gate_outcome_valid(pay["outcome"], CONTRACT["gate_outcomes"]):
                    problems.append(f"{eid}: outcome {pay['outcome']} invalid")
                if atype != "human" or pay["assessor_id"] != actor or not actor.startswith("PER-"):
                    problems.append(f"{eid}: a named human (PER) must record the gate outcome")
                if pay["phase_key"] not in gates:
                    problems.append(f"{eid}: phase {pay['phase_key']} has no gate")
                if pay.get("outcome") == "pass_with_conditions" and not pay.get("conditions"):
                    problems.append(f"{eid}: pass_with_conditions needs conditions")
                for ref in pay.get("conditions") or []:
                    target = index.get(ref[:3], {}).get(ref)
                    if not target or target.get("project_id") != pay["project_id"]:
                        problems.append(f"{eid}: condition {ref} does not resolve in the project")
            elif et in ("task.status_changed", "request.status_changed", "risk.status_changed"):
                chain = chains.setdefault(sid, [])
                prev = chain[-1] if chain else ("submitted" if sid in submitted else None)
                if prev is not None and pay["from_status"] != prev:
                    problems.append(f"{eid}: from_status {pay['from_status']} does not follow {prev}")
                if et == "request.status_changed" and not rules.request_transition_allowed(pay["from_status"], pay["to_status"], machine):
                    problems.append(f"{eid}: illegal request transition {pay['from_status']} to {pay['to_status']}")
                chain.append(pay["to_status"])
                if et == "risk.status_changed" and "risk_score" in pay and pay["risk_score"] != subject["risk_score"]:
                    problems.append(f"{eid}: risk_score differs from {sid}")
            elif et == "request.submitted":
                submitted.add(sid)
                if at != subject["submitted_at"] or pay["request_type"] != subject["request_type"] or sid in chains:
                    problems.append(f"{eid}: does not match {sid}")
            elif et == "request.escalated":
                rule = next((r for r in sla.get("rules") or [] if r["rule_id"] == pay["rule_id"]), None)
                if not rule or rule["applies_to_entity"] != "request" or rule["action"] != "escalate":
                    problems.append(f"{eid}: rule {pay['rule_id']} is not a request escalation rule")
                    continue
                if actor != rule["rule_id"] or atype != "system":
                    problems.append(f"{eid}: the escalating rule must be the system actor")
                if pay["escalation_role_id"] != rule["escalation_role_id"] or pay["severity"] != rule["escalation_severity"]:
                    problems.append(f"{eid}: role or severity differs from {rule['rule_id']}")
                status_now = (chains.get(sid) or [None])[-1]
                if status_now != rule["trigger"]["status"]:
                    problems.append(f"{eid}: request is not in {rule['trigger']['status']}")
                elif subject.get("escalation_due_at") != at or subject["status"] != status_now:
                    problems.append(f"{eid}: escalation time differs from the request's escalation_due_at")
            elif et == "milestone.achieved":
                if subject["status"] != "achieved" or pay["achieved_date"] != subject.get("completed_date"):
                    problems.append(f"{eid}: does not match {sid}")
            elif et == "milestone.missed":
                if subject["status"] != "missed" or pay["due_date"] != subject["target_date"] or at[:10] <= pay["due_date"]:
                    problems.append(f"{eid}: does not match {sid}, or was recorded before the due date passed")
            elif et == "risk.logged":
                band = rules.risk_band(subject["risk_score"], rr)
                if pay["severity"] != band["severity"] or pay.get("risk_score", subject["risk_score"]) != subject["risk_score"] or at != subject["identified_at"]:
                    problems.append(f"{eid}: severity or score differs from {sid} and config/risk-rules.yaml")
            elif et == "issue.logged":
                if pay["severity"] != subject["severity"] or at != subject["opened_at"]:
                    problems.append(f"{eid}: does not match {sid}")
            elif et == "issue.resolved":
                if subject["status"] not in ("resolved", "closed") or at != subject.get("resolved_at"):
                    problems.append(f"{eid}: does not match {sid}")
            elif et == "readiness.scored":
                if actor != y("config/readiness-weights.yaml")["rule_id"] or atype != "system":
                    problems.append(f"{eid}: readiness.scored must come from the readiness rule")
                if rules.Decimal(str(pay["readiness_score"])) != rules.Decimal(str(subject["overall_score"])) or at != subject["assessed_at"]:
                    problems.append(f"{eid}: score or time differs from {sid}")
                for c, v in (pay.get("category_scores") or {}).items():
                    entry_c = next((x for x in subject["categories"] if x["category"] == c), None)
                    if not entry_c or rules.Decimal(str(v)) != rules.Decimal(str(entry_c["category_score"])):
                        problems.append(f"{eid}: category score {c} differs from {sid}")
            elif et == "handoff.completed":
                if sid in handoffs:
                    problems.append(f"{eid}: handoff {sid} completed twice")
                handoffs.add(sid)
                if atype != "human" or not actor.startswith("PER-"):
                    problems.append(f"{eid}: a named human (PER) must accept a handoff")
                for f in ("from_role_id", "to_role_id"):
                    if not re.fullmatch(r"ROL-[0-9]{6}", str(pay[f])):
                        problems.append(f"{eid}: {f} is not a role ID")
            else:
                problems.append(f"{eid}: {et} is not a v0.1 core event")
        for sid, chain in chains.items():
            record = index.get(sid[:3], {}).get(sid)
            if record and chain and chain[-1] != record["status"]:
                problems.append(f"{sid}: last event status {chain[-1]} differs from the record status {record['status']}")
            if sid.startswith("REQ") and record and record["status_changed_at"] != max(
                    e["occurred_at"] for e in events if e["subject_id"] == sid and e["event_type"] == "request.status_changed"):
                problems.append(f"{sid}: status_changed_at differs from its last status event")
        for sid in submitted - set(chains):
            if index["REQ"][sid]["status"] != "submitted":
                problems.append(f"{sid}: submitted event without later status events, but the record moved on")
        types = sorted({e.get("event_type") for e in events})
        return problems, f"{len(events)} events, {len(types)} event types, all subjects resolve"
    _guard(res, "V39 synthetic events valid against standard 1.0.0", "", v39)

    # V40
    def v40():
        problems = []
        labels = CONTRACT["labels"]
        readme = (root / "data/synthetic/README.md").read_text(encoding="utf-8")
        if labels[1] not in readme.lower():
            problems.append("data/synthetic/README.md lacks the synthetic data label")
        for f in ("config/sla-rules.yaml", "config/risk-rules.yaml", "config/lead-time-rules.yaml", "config/readiness-weights.yaml"):
            text = (root / f).read_text(encoding="utf-8")
            problems += [f"{f}: lacks the label '{lab}'" for lab in (labels[0], labels[3]) if lab not in text]
        text = (root / "README.md").read_text(encoding="utf-8")
        heads = [h.strip() for h in re.findall(r"^##\s+(.+)$", text, re.MULTILINE)]
        if [h.lower() for h in heads] != [s.lower() for s in README_SECTIONS]:
            problems.append("README.md level-2 sections differ from the required 19 sections in order")
        ai = text.split("## AI assistance", 1)[-1].split("\n## ", 1)[0].lower() if "## AI assistance" in text else ""
        if "reviewed" not in ai or "approved" not in ai:
            problems.append("README.md AI assistance section must state human review and approval")
        if "docs/practical-workflow.md" not in text:
            problems.append("README.md does not link docs/practical-workflow.md")
        wf = (root / "docs/practical-workflow.md").read_text(encoding="utf-8")
        wheads = {re.sub(r"[^a-z0-9 -]", "", h.strip().lower()) for h in re.findall(r"^#{2,4}\s+(.+)$", wf, re.MULTILINE)}
        problems += [f"docs/practical-workflow.md: missing section {s}" for s in WORKFLOW_SECTIONS if not any(s in h for h in wheads)]
        for label in (labels[1], labels[2]):
            if label not in wf:
                problems.append(f"docs/practical-workflow.md: lacks the label '{label}'")
        return problems, "labels, README sections, AI assistance, and practical workflow present"
    _guard(res, "V40 labels and required documentation present", "", v40)

    # V41
    def v41():
        problems = []
        terms = [re.compile(r"(?<![A-Za-z0-9])" + re.escape(t) + r"(?![A-Za-z0-9])") for t in GENERICITY_TERMS]
        for path in repo_files(root):
            r = rel(root, path)
            if r in SCAN_EXEMPT or r.startswith(("tests/", ".github/")):
                continue
            text = text_of(path)
            if text is None:
                continue
            if any(p.search(text) for p in terms):
                problems.append(f"{r}: names a real vendor or product")
        return problems, f"no listed vendor or product name ({len(GENERICITY_TERMS)} checked)"
    _guard(res, "V41 core is generic and vendor-neutral", "", v41)


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    parser = argparse.ArgumentParser(description="Validate the shared standard.")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--blocklist", nargs="*")
    args = parser.parse_args(argv)
    res = validate(Path(args.root).resolve(), args.blocklist)
    for check, ok, note in res.rows:
        print(f"{'PASS' if ok else 'FAIL'} {check}: {note}")
    failed = sum(1 for _, ok, _ in res.rows if not ok)
    print(f"RESULT: {'FAIL' if failed else 'PASS'} ({len(res.rows) - failed} passed, {failed} failed)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
