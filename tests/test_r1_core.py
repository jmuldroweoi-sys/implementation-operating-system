"""Tests for the R1 v0.1 core: deterministic rules (tools/r1_rules.py) and the core
checks in tools/validate.py (V25 to V41).

Rule tests call the rule functions directly with fixed inputs. Validator tests copy the
repository into a temporary folder, break exactly one thing, and confirm the matching
check fails. No test uses AI, the network, or the current clock. All content is
illustrative example content built on synthetic data.
"""

from __future__ import annotations

import json
import sys
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import r1_rules as R  # noqa: E402
import validate  # noqa: E402
from test_validate import Sandbox  # noqa: E402


def cfg(rel: str):
    return yaml.safe_load((ROOT / rel).read_text(encoding="utf-8"))


RISK = cfg("config/risk-rules.yaml")
MACHINE = cfg("config/request-state-machine.yaml")
WEIGHTS = cfg("config/readiness-weights.yaml")
LIFECYCLE = cfg("lifecycle/lifecycle.yaml")
SLA = cfg("config/sla-rules.yaml")
LEAD = cfg("config/lead-time-rules.yaml")
GATES = {g["gate_id"]: g for g in cfg("lifecycle/gates.yaml")["gates"]}
OUTCOMES = cfg("standard/lifecycle-terms.yaml")["gate_outcomes"]


def load_data(root: Path = ROOT) -> dict:
    data = {}
    for fname, (schema, key, _) in validate.CSV_SPEC.items():
        doc = json.loads((root / f"schemas/{schema}.schema.json").read_text(encoding="utf-8"))
        _, data[key] = R.read_csv_records(root / "data/synthetic" / fname, doc)
    cards: dict = {}
    for row in data["readiness"]:
        card = cards.setdefault(row["readiness_scorecard_id"], {f: row.get(f) for f in validate.SCORECARD_FIELDS})
        card.setdefault("categories", []).append(row)
    data["scorecards"] = list(cards.values())
    return data


def entries(spec: dict) -> dict:
    return {c: {"criteria_total_count": t, "criteria_met_count": m, "required_evidence_complete_flag": f}
            for c, (t, m, f) in spec.items()}


C_SPEC = {"people": (4, 4, True), "process": (4, 4, True), "technology": (5, 5, True),
          "data": (4, 3, True), "training": (4, 3, False), "support": (4, 4, True)}


class RuleTest(unittest.TestCase):
    """Deterministic rules, called directly."""

    # 1. risk score calculation
    def test_risk_score_is_likelihood_times_impact(self) -> None:
        self.assertEqual(R.risk_score(4, 3, RISK), 12)
        self.assertEqual(R.risk_score(1, 1, RISK), 1)
        self.assertEqual(R.risk_score(5, 5, RISK), 25)
        for bad in ((0, 3), (6, 1), (3, 6), (2.5, 2), (True, 2)):
            with self.assertRaises(ValueError):
                R.risk_score(*bad, RISK)

    def test_risk_bands_and_severity(self) -> None:
        cases = {1: ("low", "sev4"), 4: ("low", "sev4"), 5: ("moderate", "sev3"), 9: ("moderate", "sev3"),
                 10: ("high", "sev2"), 15: ("high", "sev2"), 16: ("critical", "sev1"), 25: ("critical", "sev1")}
        for score, (band, sev) in cases.items():
            got = R.risk_band(score, RISK)
            self.assertEqual((got["band"], got["severity"]), (band, sev), score)
        self.assertEqual(R.risk_band_problems(RISK), [])
        gap = json.loads(json.dumps(RISK))
        gap["bands"][1]["min_score"] = 6
        self.assertTrue(R.risk_band_problems(gap))

    # 2. illegal request transition rejection
    def test_illegal_request_transitions_rejected(self) -> None:
        for frm, to in (("submitted", "in_progress"), ("closed", "triaged"), ("triaged", "handed_off"),
                        ("awaiting_approval", "in_progress"), ("blocked", "handed_off"), ("submitted", "submitted"),
                        ("submitted", "escalated")):
            self.assertFalse(R.request_transition_allowed(frm, to, MACHINE), (frm, to))

    # 3. legal request transition
    def test_legal_request_transitions_accepted(self) -> None:
        path = ["submitted", "triaged", "accepted", "in_progress", "blocked", "in_progress", "ready_for_handoff", "handed_off", "closed"]
        for frm, to in zip(path, path[1:]):
            self.assertTrue(R.request_transition_allowed(frm, to, MACHINE), (frm, to))
        self.assertTrue(R.request_transition_allowed("triaged", "awaiting_approval", MACHINE))
        self.assertTrue(R.request_transition_allowed("awaiting_approval", "accepted", MACHINE))

    def test_leaving_approval_needs_a_named_human(self) -> None:
        for t in MACHINE["transitions"]:
            if t["from_status"] == "awaiting_approval":
                self.assertEqual(t["performed_by"], "approver")
                self.assertTrue(t["human_action_required"])

    # 4. readiness weighted calculation
    def test_readiness_weighted_calculation(self) -> None:
        out = R.readiness_scorecard(entries(C_SPEC), WEIGHTS)
        self.assertEqual(out["overall_score"], Decimal("91.25"))
        self.assertEqual(out["categories"]["training"]["category_score"], Decimal("11.25"))
        self.assertEqual(out["categories"]["data"]["achieved_rate"], Decimal("0.75"))
        a = {"people": (4, 2, False), "process": (4, 1, False), "technology": (5, 0, False),
             "data": (4, 1, False), "training": (4, 0, False), "support": (4, 0, False)}
        self.assertEqual(R.readiness_scorecard(entries(a), WEIGHTS)["overall_score"], Decimal("16.25"))

    def test_readiness_rounds_half_up_deterministically(self) -> None:
        third = dict(C_SPEC, support=(3, 1, True))
        first = R.readiness_scorecard(entries(third), WEIGHTS)
        self.assertEqual(first["categories"]["support"]["category_score"], Decimal("3.33"))
        self.assertEqual(first, R.readiness_scorecard(entries(third), WEIGHTS))
        with self.assertRaises(ValueError):
            R.readiness_scorecard(entries(dict(C_SPEC, data=(4, 5, True))), WEIGHTS)
        with self.assertRaises(ValueError):
            R.readiness_scorecard({k: v for k, v in entries(C_SPEC).items() if k != "data"}, WEIGHTS)

    # 5. readiness weights total validation
    def test_readiness_weights_total(self) -> None:
        canonical = validate.CONTRACT["readiness_categories"]
        self.assertEqual(R.readiness_weight_problems(WEIGHTS, canonical), [])
        self.assertEqual(sum(c["weight"] for c in WEIGHTS["categories"]), WEIGHTS["total_weight"])
        bad = json.loads(json.dumps(WEIGHTS))
        bad["categories"][0]["weight"] = 20
        self.assertTrue(any("total" in p for p in R.readiness_weight_problems(bad, canonical)))
        renamed = json.loads(json.dumps(WEIGHTS))
        renamed["categories"][0]["category"] = "staffing"
        self.assertTrue(R.readiness_weight_problems(renamed, canonical))

    # 6. incomplete-required-evidence behavior
    def test_incomplete_required_evidence_flag(self) -> None:
        self.assertTrue(R.readiness_scorecard(entries(C_SPEC), WEIGHTS)["incomplete_required_evidence_flag"])
        complete = {k: (t, m, True) for k, (t, m, _) in C_SPEC.items()}
        out = R.readiness_scorecard(entries(complete), WEIGHTS)
        self.assertFalse(out["incomplete_required_evidence_flag"])
        self.assertEqual(out["overall_score"], Decimal("91.25"), "evidence completeness never changes the score")

    def test_launch_gate_checks_inform_but_do_not_decide(self) -> None:
        data = load_data()
        ctx = {"risk_rules": RISK}
        checks = R.gate_check_results(GATES["launch_gate"], "PRJ-000003", "PHS-000015", data, ctx)
        self.assertEqual(checks, {"readiness_scored": True, "required_evidence_complete": False,
                                  "no_open_sev1_sev2_issues": True, "no_open_critical_risks": True, "no_blocked_requests": True})
        self.assertEqual(GATES["launch_gate"]["recorded_by"], "human")
        self.assertFalse(any(isinstance(v, str) and v in OUTCOMES for v in checks.values()))

    # 7. valid gate outcome
    def test_valid_gate_outcomes(self) -> None:
        self.assertEqual(OUTCOMES, ["pass", "pass_with_conditions", "hold"])
        for outcome in OUTCOMES:
            self.assertTrue(R.gate_outcome_valid(outcome, OUTCOMES))
        for gate in GATES.values():
            self.assertEqual(gate["allowed_outcomes"], OUTCOMES)

    # 8. invalid gate outcome rejection
    def test_invalid_gate_outcomes_rejected(self) -> None:
        for outcome in ("approved", "go", "no_go", "Pass", "", None, 1):
            self.assertFalse(R.gate_outcome_valid(outcome, OUTCOMES), outcome)

    # 9. phase order
    def test_phase_order(self) -> None:
        keys = [p["phase_id"] for p in LIFECYCLE["phases"]]
        self.assertEqual(keys, validate.CONTRACT["phases"])
        self.assertEqual([p["order"] for p in LIFECYCLE["phases"]], list(range(1, 11)))
        for a, b in zip(keys, keys[1:]):
            self.assertTrue(R.phase_move_allowed(a, b, "pass", LIFECYCLE), (a, b))
            self.assertTrue(R.phase_move_allowed(a, b, "pass_with_conditions", LIFECYCLE), (a, b))

    # 10. illegal phase move
    def test_illegal_phase_moves_rejected(self) -> None:
        self.assertFalse(R.phase_move_allowed("initiate", "design", "pass", LIFECYCLE), "skipping a phase")
        self.assertFalse(R.phase_move_allowed("build", "validate", "hold", LIFECYCLE), "forward move on hold")
        self.assertFalse(R.phase_move_allowed("build", "validate", None, LIFECYCLE), "forward move without a gate")
        self.assertFalse(R.phase_move_allowed("enable", "build", "pass", LIFECYCLE), "unlisted backward move")
        self.assertFalse(R.phase_move_allowed("review", "initiate", "pass", LIFECYCLE), "nothing follows review")
        self.assertFalse(R.phase_move_allowed("launch", "planning", "pass", LIFECYCLE), "unknown phase")
        self.assertTrue(R.phase_move_allowed("validate", "build", "hold", LIFECYCLE), "rework is the only backward move")

    # 11. SLA timer configuration parsing
    def test_sla_timer_parsing(self) -> None:
        self.assertEqual(R.parse_duration("PT48H").total_seconds(), 48 * 3600)
        self.assertEqual(R.parse_duration("PT15M").total_seconds(), 900)
        self.assertEqual(R.parse_duration("P1DT4H").total_seconds(), 28 * 3600)
        for bad in ("48h", "P", "PT", "P1W", "PT1.5H", "", "P1DT"):
            with self.assertRaises(ValueError):
                R.parse_duration(bad)
        rule = R.sla_rule_for("request", "blocked", None, SLA)
        self.assertEqual(rule["rule_id"], "RUL-000003")
        warn, due = R.sla_timer(rule, datetime(2026, 9, 24, 15, tzinfo=timezone.utc))
        self.assertEqual(R.format_timestamp(due), "2026-09-26T15:00:00Z")
        self.assertEqual(R.format_timestamp(warn), "2026-09-26T07:00:00Z")
        self.assertEqual(R.sla_rule_for("issue", "open", "sev1", SLA)["key"], "sev1")
        self.assertIsNone(R.sla_rule_for("request", "in_progress", None, SLA))
        req = {"status": "blocked", "status_changed_at": "2026-09-24T15:00:00Z"}
        self.assertEqual(R.expected_escalation_due_at(req, SLA), "2026-09-26T15:00:00Z")
        self.assertIsNone(R.expected_escalation_due_at({"status": "accepted", "status_changed_at": "2026-09-24T15:00:00Z"}, SLA))

    # 12. lead-time rule parsing
    def test_lead_time_rules_parse_and_flag(self) -> None:
        for rule in LEAD["rules"]:
            R.parse_duration(rule["lead_time"])
        flags = R.lead_time_flags(load_data(), LEAD)
        self.assertEqual([(f[0], f[1]) for f in flags], [("RUL-000104", "TSK-000006")])
        data = load_data()
        enable_task = next(t for t in data["tasks"] if t["task_id"] == "TSK-000024")
        enable_task["planned_due_date"] = "2026-10-16"
        flags = R.lead_time_flags(data, LEAD)
        self.assertIn(("RUL-000101", "TSK-000024"), [(f[0], f[1]) for f in flags])
        bad = json.loads(json.dumps(LEAD))
        bad["rules"][0]["rule_type"] = "predict_launch_date"
        with self.assertRaises(ValueError):
            R.lead_time_flags(load_data(), bad)

    # 13. orphan-reference detection
    def test_orphan_references_detected(self) -> None:
        profile_ids = {"PRF-000001", "PRF-000002", "PRF-000003", "PRF-000004"}
        self.assertEqual(R.reference_problems(load_data(), profile_ids), [])
        data = load_data()
        data["tasks"][0]["milestone_id"] = "MLS-000099"
        data["tasks"][1]["predecessor_task_ids"] = ["TSK-000099"]
        data["risks"][0]["project_id"] = "PRJ-000099"
        data["milestones"][0]["phase_id"] = "PHS-000015"
        problems = R.reference_problems(data, profile_ids)
        self.assertTrue(any("MLS-000099" in p for p in problems))
        self.assertTrue(any("TSK-000099" in p for p in problems))
        self.assertTrue(any("PRJ-000099" in p for p in problems))
        self.assertTrue(any("another project" in p for p in problems))


class CoreValidatorTest(unittest.TestCase):
    """Core checks in tools/validate.py, each broken once in a sandbox copy."""

    def setUp(self) -> None:
        self.box = Sandbox()

    def tearDown(self) -> None:
        self.box.close()

    def assertFails(self, check: str, contains: str | None = None) -> None:
        res = validate.validate(self.box.root)
        row = next((r for r in res.rows if r[0].split(" ")[0] == check), None)
        self.assertIsNotNone(row, check)
        self.assertFalse(row[1], f"{check} should fail")
        if contains:
            self.assertIn(contains, row[2])

    def edit_events(self, change) -> None:
        path = self.box.path("data/synthetic/events.jsonl")
        events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        change(events)
        path.write_text("".join(json.dumps(e) + "\n" for e in events), encoding="utf-8")

    def event(self, events, event_id):
        return next(e for e in events if e["event_id"] == event_id)

    def test_real_core_counts_are_locked(self) -> None:
        data = load_data()
        self.assertEqual({k: len(data[k]) for k in ("projects", "phases", "milestones", "tasks", "requests", "risks", "issues", "readiness")},
                         {"projects": 3, "phases": 15, "milestones": 12, "tasks": 30, "requests": 8, "risks": 6, "issues": 5, "readiness": 18})
        lines = (ROOT / "data/synthetic/events.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 38)
        self.assertEqual(len({json.loads(x)["event_type"] for x in lines}), 16)

    def test_rejects_missing_core_file(self) -> None:
        self.box.path("docs/practical-workflow.md").unlink()
        self.assertFails("V25")

    # 2 (validator side). illegal request transition in the event stream
    def test_rejects_illegal_request_transition_event(self) -> None:
        def change(events):
            self.event(events, "EVT-000018")["payload"] = {"from_status": "triaged", "to_status": "handed_off"}
        self.edit_events(change)
        self.assertFails("V39")

    def test_rejects_state_machine_and_schema_drift(self) -> None:
        self.box.edit_yaml("config/request-state-machine.yaml", lambda d: d["statuses"].append("escalated"))
        self.assertFails("V30")

    def test_rejects_approval_without_named_approver(self) -> None:
        def change(d):
            for t in d["transitions"]:
                if t["from_status"] == "awaiting_approval":
                    t["performed_by"] = "owner"
        self.box.edit_yaml("config/request-state-machine.yaml", change)
        self.assertFails("V30")

    # 4 and 6 (validator side). readiness values must equal the calculation
    def test_rejects_wrong_readiness_score(self) -> None:
        self.box.replace("data/synthetic/readiness.csv", "people,15,4,4,1,15,true,TSK-000028,91.25", "people,15,4,4,1,15,true,TSK-000028,95")
        self.assertFails("V38")

    def test_rejects_hidden_incomplete_evidence(self) -> None:
        text = self.box.path("data/synthetic/readiness.csv").read_text(encoding="utf-8")
        lines = [ln.replace(",91.25,true,", ",91.25,false,") if "RDS-000003" in ln else ln for ln in text.splitlines()]
        self.box.path("data/synthetic/readiness.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")
        self.assertFails("V38")

    # 5 (validator side)
    def test_rejects_weights_that_do_not_total(self) -> None:
        self.box.replace("config/readiness-weights.yaml", "weight: 25", "weight: 30")
        self.assertFails("V34")

    # 8 (validator side). invalid gate outcome in configuration and in events
    def test_rejects_invalid_gate_outcome_in_gates(self) -> None:
        self.box.edit_yaml("lifecycle/gates.yaml", lambda d: d["gates"][0]["allowed_outcomes"].append("approved"))
        self.assertFails("V29")

    def test_rejects_invalid_gate_outcome_event(self) -> None:
        self.edit_events(lambda ev: self.event(ev, "EVT-000013")["payload"].update(outcome="go"))
        self.assertFails("V39")

    def test_rejects_gate_outcome_not_recorded_by_a_person(self) -> None:
        self.box.edit_yaml("lifecycle/gates.yaml", lambda d: d["gates"][6].update(recorded_by="readiness_score"))
        self.assertFails("V29")

    def test_rejects_ai_gate_assessor(self) -> None:
        def change(events):
            e = self.event(events, "EVT-000013")
            e["actor_type"], e["actor_id"] = "ai_agent", "AGT-000001"
            e["payload"]["assessor_id"] = "AGT-000001"
        self.edit_events(change)
        self.assertFails("V39")

    # 9 and 10 (validator side)
    def test_rejects_reordered_lifecycle(self) -> None:
        def change(d):
            d["phases"][1], d["phases"][2] = d["phases"][2], d["phases"][1]
        self.box.edit_yaml("lifecycle/lifecycle.yaml", change)
        self.assertFails("V28")

    def test_rejects_unlisted_backward_move_in_lifecycle(self) -> None:
        self.box.edit_yaml("lifecycle/lifecycle.yaml", lambda d: d["phases"][5]["legal_next_phase_ids"].append("build"))
        self.assertFails("V28")

    def test_rejects_illegal_phase_sequence_in_data(self) -> None:
        self.box.replace("data/synthetic/phases.csv", "PHS-000004,PRJ-000002,discover", "PHS-000004,PRJ-000002,validate")
        self.box.replace("data/synthetic/phases.csv", "validate,completed,2026-06-12T17:05:00Z,2026-07-03T16:00:00Z,ROL-000001,discover_gate",
                         "validate,completed,2026-06-12T17:05:00Z,2026-07-03T16:00:00Z,ROL-000001,validate_gate")
        self.assertFails("V38")

    # 11 (validator side)
    def test_rejects_unparseable_sla_duration(self) -> None:
        self.box.replace("config/sla-rules.yaml", "target_duration: PT48H", "target_duration: 48 hours")
        self.assertFails("V31")

    def test_rejects_escalation_without_role(self) -> None:
        self.box.edit_yaml("config/sla-rules.yaml", lambda d: d["rules"][2].pop("escalation_role_id"))
        self.assertFails("V31")

    def test_rejects_wrong_escalation_due_at(self) -> None:
        self.box.replace("data/synthetic/requests.csv", "2026-09-24T15:00:00Z,2026-09-26T15:00:00Z", "2026-09-24T15:00:00Z,2026-09-27T15:00:00Z")
        self.assertFails("V38")

    # 12 (validator side)
    def test_rejects_unparseable_lead_time(self) -> None:
        self.box.replace("config/lead-time-rules.yaml", "lead_time: P5D", "lead_time: five days")
        self.assertFails("V33")

    # 13 (validator side)
    def test_rejects_orphan_reference_in_csv(self) -> None:
        self.box.replace("data/synthetic/tasks.csv", "TSK-000012,PRJ-000002,PHS-000006,MLS-000005", "TSK-000012,PRJ-000002,PHS-000006,MLS-000099")
        self.assertFails("V37")

    def test_rejects_cross_project_reference(self) -> None:
        self.box.replace("data/synthetic/tasks.csv", "TSK-000012,PRJ-000002,PHS-000006", "TSK-000012,PRJ-000002,PHS-000002")
        self.assertFails("V37")

    def test_rejects_orphan_readiness_evidence(self) -> None:
        self.box.replace("data/synthetic/readiness.csv", "MLS-000011;TSK-000024", "MLS-000011;TSK-000099")
        self.assertFails("V37")

    # 14
    def test_rejects_invalid_issue_severity(self) -> None:
        self.box.replace("data/synthetic/issues.csv", ",sev2,in_progress,", ",sev5,in_progress,")
        self.assertFails("V36")

    def test_rejects_invalid_event_severity(self) -> None:
        self.edit_events(lambda ev: self.event(ev, "EVT-000026")["payload"].update(severity="critical"))
        self.assertFails("V39")

    # 15
    def test_rejects_invalid_project_status(self) -> None:
        self.box.replace("data/synthetic/projects.csv", "PHS-000002,active,startup", "PHS-000002,paused,startup")
        self.assertFails("V36")

    def test_rejects_customer_reference_shaped_like_an_r1_id(self) -> None:
        self.box.replace("data/synthetic/projects.csv", "SYN-CUSTOMER-A", "CUS-000001")
        self.assertFails("V36")

    def test_rejects_wrong_row_count(self) -> None:
        path = self.box.path("data/synthetic/risks.csv")
        lines = path.read_text(encoding="utf-8").splitlines()
        path.write_text("\n".join(lines[:-1]) + "\n", encoding="utf-8")
        self.assertFails("V36")

    def test_rejects_changed_csv_header(self) -> None:
        self.box.replace("data/synthetic/tasks.csv", "planned_hours,actual_hours", "hours_planned,actual_hours")
        self.assertFails("V36")

    # 16. event payload and reference validity
    def test_rejects_event_subject_that_does_not_exist(self) -> None:
        self.edit_events(lambda ev: self.event(ev, "EVT-000001").update(subject_id="PRJ-000099"))
        self.assertFails("V39")

    def test_rejects_event_missing_required_payload(self) -> None:
        self.edit_events(lambda ev: self.event(ev, "EVT-000020")["payload"].pop("severity"))
        self.assertFails("V39")

    def test_rejects_event_payload_project_mismatch(self) -> None:
        self.edit_events(lambda ev: self.event(ev, "EVT-000024")["payload"].update(project_id="PRJ-000001"))
        self.assertFails("V39")

    def test_rejects_scenario_pack_event(self) -> None:
        def change(events):
            e = self.event(events, "EVT-000038")
            e.update(event_type="rehearsal.completed", subject_type="rehearsal", subject_id="RHR-000001", payload={"project_id": "PRJ-000003"})
        self.edit_events(change)
        self.assertFails("V39")

    def test_rejects_unregistered_event_type(self) -> None:
        self.edit_events(lambda ev: self.event(ev, "EVT-000038").update(event_type="request.created"))
        self.assertFails("V39")

    def test_rejects_risk_severity_that_differs_from_its_band(self) -> None:
        self.edit_events(lambda ev: self.event(ev, "EVT-000004")["payload"].update(severity="sev4"))
        self.assertFails("V39")

    def test_rejects_readiness_event_score_mismatch(self) -> None:
        self.edit_events(lambda ev: self.event(ev, "EVT-000034")["payload"].update(readiness_score=99.0))
        self.assertFails("V39")

    def test_rejects_event_status_chain_mismatch(self) -> None:
        self.box.replace("data/synthetic/tasks.csv", "Obtain integration credentials from the customer,blocked", "Obtain integration credentials from the customer,in_progress")
        self.assertFails("V39")

    def test_rejects_escalation_at_wrong_time(self) -> None:
        self.edit_events(lambda ev: self.event(ev, "EVT-000027").update(occurred_at="2026-09-25T15:00:00Z"))
        self.assertFails("V39")

    def test_rejects_out_of_order_events(self) -> None:
        self.edit_events(lambda ev: self.event(ev, "EVT-000002").update(occurred_at="2026-10-05T23:00:00Z"))
        self.assertFails("V39")

    def test_rejects_risk_score_that_is_not_the_product(self) -> None:
        self.box.replace("data/synthetic/risks.csv", ",4,3,12,mitigating,", ",4,3,16,mitigating,")
        self.assertFails("V38")

    def test_rejects_task_started_before_its_predecessor_finished(self) -> None:
        self.box.replace("data/synthetic/tasks.csv", "Build integration mappings,not_started", "Build integration mappings,in_progress")
        self.assertFails("V38")

    # Profiles
    def test_profile_cannot_waive_non_waivable_evidence(self) -> None:
        self.box.replace("profiles/examples/org-stage-startup.yaml", "{gate_id: design_gate, formality: lightweight}",
                         "{gate_id: design_gate, formality: lightweight, optional_evidence_types: [design_approval]}")
        self.assertFails("V35", "design_approval is not waivable")

    def test_profile_cannot_disable_a_required_rule(self) -> None:
        self.box.replace("profiles/examples/org-stage-startup.yaml", "value: PT48H}",
                         "value: PT48H}\n  - {config_file: config/sla-rules.yaml, rule_id: RUL-000005, field: enabled_flag, value: false}")
        self.assertFails("V35", "cannot disable RUL-000005")

    def test_profile_cannot_redefine_the_lifecycle(self) -> None:
        self.box.replace("profiles/examples/segment-mid-market.yaml", "parameter_overrides: []", "parameter_overrides: []\nphases: [initiate, launch]")
        self.assertFails("V35", "Additional properties")

    def test_profile_cannot_remove_the_approver(self) -> None:
        self.box.replace("profiles/examples/segment-mid-market.yaml", "approver_role: delivery_leadership}", "approver_role: null}")
        self.assertFails("V35", "None is not of type")

    def test_example_profile_needs_label(self) -> None:
        self.box.replace("profiles/examples/service-tier-standard.yaml", "# illustrative example: shows", "# Shows")
        self.assertFails("V35")

    # Documentation, labels, genericity
    def test_rejects_readme_without_ai_assistance(self) -> None:
        self.box.replace("README.md", "## AI assistance", "## Tools used")
        self.assertFails("V40")

    def test_rejects_synthetic_folder_without_label(self) -> None:
        text = self.box.path("data/synthetic/README.md").read_text(encoding="utf-8")
        self.box.path("data/synthetic/README.md").write_text(text.replace("synthetic data", "sample records").replace("Synthetic data", "Sample records"), encoding="utf-8")
        self.assertFails("V40")

    def test_rejects_practical_workflow_without_required_section(self) -> None:
        self.box.replace("docs/practical-workflow.md", "## Human decisions", "## People")
        self.assertFails("V40")

    def test_rejects_config_without_design_value_label(self) -> None:
        text = self.box.path("config/risk-rules.yaml").read_text(encoding="utf-8")
        self.box.path("config/risk-rules.yaml").write_text(
            text.replace("proposed design value, not a measured result", "configured value"), encoding="utf-8")
        self.assertFails("V40")

    def test_vendor_matcher_is_whole_word_and_case_sensitive(self) -> None:
        # The list is stored as hashes, so these assertions pin its matching behavior.
        self.assertTrue(validate.names_listed_vendor("We track work in " + "Hub" + "Spot today."))
        self.assertTrue(validate.names_listed_vendor("Boards like " + "Monday" + ".com are out of scope."))
        self.assertFalse(validate.names_listed_vendor("the no" + "tion of a sl" + "ack schedule"))  # common words, lowercase
        self.assertFalse(validate.names_listed_vendor("Salesforcelike tooling"))

    def test_rejects_vendor_name(self) -> None:
        vendor = "Sales" + "force"  # assembled so this file never spells out a vendor name
        self.assertTrue(validate.names_listed_vendor(vendor))
        self.box.replace("docs/scaling-model.md", "One person, or a few people", f"One person using {vendor}, or a few people")
        self.assertFails("V41")


if __name__ == "__main__":
    unittest.main()
