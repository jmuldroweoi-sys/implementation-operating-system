"""Validator for the shared standard (standard/) of implementation-operating-system.

Mechanically checks that standard/ is complete, internally consistent, and equal to the
locked 1.0.0 contract. It reads files only; it never publishes, pushes, or changes
anything.

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
    re.compile(r"\billustrative-example\b", re.I),
    re.compile(r"\bsynthetic-data\b", re.I),
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

    res.rows.sort(key=lambda r: r[0])
    return res


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
