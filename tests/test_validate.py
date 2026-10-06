"""Tests for tools/validate.py.

Every negative test copies the repository into a temporary folder, breaks exactly one
thing there, and confirms the matching check fails. The real files are never changed,
so the clean state is restored by construction. All test content is illustrative
example content.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import validate  # noqa: E402

COPY = ("standard", "tools", "CHANGELOG.md", "README.md", "CONTRIBUTING.md")


class Sandbox:
    def __init__(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "repo"
        self.root.mkdir()
        for item in COPY:
            src = ROOT / item
            if src.is_dir():
                shutil.copytree(src, self.root / item, ignore=shutil.ignore_patterns("__pycache__"))
            else:
                shutil.copy2(src, self.root / item)

    def path(self, rel: str) -> Path:
        return self.root / rel

    def edit_yaml(self, rel: str, change) -> None:
        doc = yaml.safe_load(self.path(rel).read_text(encoding="utf-8"))
        change(doc)
        self.path(rel).write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")

    def edit_json(self, rel: str, change) -> None:
        doc = json.loads(self.path(rel).read_text(encoding="utf-8"))
        change(doc)
        self.path(rel).write_text(json.dumps(doc, indent=2), encoding="utf-8")

    def replace(self, rel: str, old: str, new: str) -> None:
        text = self.path(rel).read_text(encoding="utf-8")
        assert old in text, old
        self.path(rel).write_text(text.replace(old, new, 1), encoding="utf-8")

    def run(self, blocklist: list[str] | None = None) -> dict[str, bool]:
        res = validate.validate(self.root, blocklist)
        return {check.split(" ")[0]: ok for check, ok, _ in res.rows}

    def close(self) -> None:
        self.tmp.cleanup()


class ValidatorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.box = Sandbox()

    def tearDown(self) -> None:
        self.box.close()

    def assertFails(self, check: str, results: dict[str, bool]) -> None:
        self.assertIn(check, results)
        self.assertFalse(results[check], f"{check} should fail")

    # Positive

    def test_real_repository_passes(self) -> None:
        res = validate.validate(ROOT)
        failed = [(c, n) for c, ok, n in res.rows if not ok]
        self.assertEqual(failed, [])
        self.assertEqual(len(res.rows), 24)

    def test_sandbox_copy_passes(self) -> None:
        self.assertTrue(all(self.box.run().values()))

    def test_clean_blocklist_passes_and_reports_count(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bl = Path(tmp) / "blocklist.txt"
            bl.write_text("# illustrative example\nExampleCorpZeta\n", encoding="utf-8")
            res = validate.validate(self.box.root, [str(bl)])
            row = next(r for r in res.rows if r[0].startswith("V18"))
            self.assertTrue(row[1])
            self.assertIn("1 private terms loaded; 0 hits", row[2])

    def test_cli_exit_codes(self) -> None:
        cmd = [sys.executable, str(self.box.path("tools/validate.py")), "--root", str(self.box.root)]
        self.assertEqual(subprocess.run(cmd, capture_output=True).returncode, 0)
        self.box.path("standard/org-stages.yaml").unlink()
        self.assertEqual(subprocess.run(cmd, capture_output=True).returncode, 1)

    # Required negative tests

    def test_rejects_duplicate_id_prefix(self) -> None:
        def change(doc):
            dup = dict(doc["prefixes"][0])
            dup["entity"] = "duplicate_project"
            doc["prefixes"].append(dup)

        self.box.edit_yaml("standard/id-registry.yaml", change)
        self.assertFails("V05", self.box.run())

    def test_rejects_retired_prefix_reactivation(self) -> None:
        def change(doc):
            for p in doc["prefixes"]:
                if p["prefix"] == "AIR":
                    p["status"] = "active"

        self.box.edit_yaml("standard/id-registry.yaml", change)
        self.assertFails("V06", self.box.run())

    def test_rejects_malformed_id(self) -> None:
        self.box.replace("standard/schemas/approval-record.schema.json", '"subject_id": "REC-000007"', '"subject_id": "REC-7"')
        self.assertFails("V07", self.box.run())

    def test_rejects_unregistered_prefix_in_example(self) -> None:
        self.box.replace("standard/schemas/recommendation.schema.json", '"source_id": "TSK-000021"', '"source_id": "XYZ-000021"')
        self.assertFails("V07", self.box.run())

    def test_rejects_malformed_event_name(self) -> None:
        def change(doc):
            doc["events"][0]["event_type"] = "ProjectCreated"

        self.box.edit_yaml("standard/event-catalog.yaml", change)
        results = self.box.run()
        self.assertFails("V09", results)
        self.assertFails("V24", results)

    def test_rejects_unregistered_producer(self) -> None:
        def change(doc):
            doc["events"][0]["producer_repo"] = "unregistered-repository"

        self.box.edit_yaml("standard/event-catalog.yaml", change)
        results = self.box.run()
        self.assertFails("V10", results)
        self.assertFails("V24", results)

    def test_rejects_unregistered_consumer(self) -> None:
        def change(doc):
            doc["events"][0]["consumer_repos"].append("unregistered-repository")

        self.box.edit_yaml("standard/event-catalog.yaml", change)
        self.assertFails("V11", self.box.run())

    def test_rejects_invalid_actor_type(self) -> None:
        self.box.edit_json(
            "standard/schemas/event.schema.json",
            lambda d: d["properties"]["actor_type"].__setitem__("enum", ["human", "system", "ai_agent", "bot"]),
        )
        self.assertFails("V12", self.box.run())

    def test_rejects_invalid_actor_type_in_example(self) -> None:
        self.box.replace("standard/schemas/event.schema.json", '"actor_type": "system"', '"actor_type": "robot"')
        self.assertFails("V02", self.box.run())

    def test_rejects_changed_label_wording(self) -> None:
        def change(doc):
            doc["labels"][0]["label"] = "proposed value, not measured"

        self.box.edit_yaml("standard/label-rules.yaml", change)
        self.assertFails("V15", self.box.run())

    def test_rejects_label_near_variant_in_documents(self) -> None:
        self.box.replace("standard/glossary.md", "## Rules", "Timers here are a proposed design value only.\n\n## Rules")
        self.assertFails("V15", self.box.run())

    def test_rejects_invalid_organization_stage(self) -> None:
        def change(doc):
            doc["stages"][0]["stage_id"] = "seed"

        self.box.edit_yaml("standard/org-stages.yaml", change)
        self.assertFails("V14", self.box.run())

    def test_rejects_missing_standard_file(self) -> None:
        self.box.path("standard/severity-scale.yaml").unlink()
        self.assertFails("V04", self.box.run())

    def test_rejects_em_dash(self) -> None:
        self.box.replace("standard/glossary.md", "## Rules", "## Rules " + chr(0x2014))
        self.assertFails("V17", self.box.run())

    def test_rejects_injected_blocklisted_term(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bl = Path(tmp) / "blocklist.txt"
            bl.write_text("ExampleCorpZeta\n", encoding="utf-8")
            self.box.replace("standard/glossary.md", "## Rules", "Built at ExampleCorpZeta.\n\n## Rules")
            res = validate.validate(self.box.root, [str(bl)])
            row = next(r for r in res.rows if r[0].startswith("V18"))
            self.assertFalse(row[1])
            self.assertNotIn("ExampleCorpZeta", row[2])

    def test_rejects_blocklist_inside_repository(self) -> None:
        inside = self.box.path("blocklist.txt")
        inside.write_text("ExampleCorpZeta\n", encoding="utf-8")
        res = validate.validate(self.box.root, [str(inside)])
        self.assertFalse(next(r for r in res.rows if r[0].startswith("V18"))[1])

    # Further contract protections

    def test_rejects_event_ownership_change(self) -> None:
        def change(doc):
            for e in doc["events"]:
                if e["event_type"] == "credential.granted":
                    e["producer_repo"] = "implementation-enablement-program"
                    e["consumer_repos"] = ["implementation-tracker-workbook"]

        self.box.edit_yaml("standard/event-catalog.yaml", change)
        self.assertFails("V24", self.box.run())

    def test_rejects_retired_event_alias(self) -> None:
        def change(doc):
            alias = dict(doc["events"][-1])
            alias["event_type"] = "trainer.credentialed"
            doc["events"].append(alias)

        self.box.edit_yaml("standard/event-catalog.yaml", change)
        self.assertFails("V24", self.box.run())

    def test_rejects_unregistered_subject_type(self) -> None:
        def change(doc):
            doc["events"][0]["subject_type"] = "account"

        self.box.edit_yaml("standard/event-catalog.yaml", change)
        self.assertFails("V24", self.box.run())

    def test_rejects_lifecycle_change(self) -> None:
        def change(doc):
            doc["phases"][4]["phase_key"] = "test"

        self.box.edit_yaml("standard/lifecycle-terms.yaml", change)
        self.assertFails("V13", self.box.run())

    def test_rejects_vocabulary_change(self) -> None:
        def change(doc):
            doc["vocabularies"][2]["values"] = ["proposed", "approved", "rejected", "auto_approved"]

        self.box.edit_yaml("standard/status-vocabularies.yaml", change)
        self.assertFails("V16", self.box.run())

    def test_rejects_version_inconsistency(self) -> None:
        self.box.replace("standard/org-stages.yaml", 'standard_version: "1.0.0"', 'standard_version: "1.1.0"')
        self.assertFails("V20", self.box.run())

    def test_rejects_secret(self) -> None:
        # Built from parts so this test file holds no secret-shaped literal.
        fake = "api" + "_key: " + '"' + "abcdefghijklmnop" + "qrstuvwxyz0123456789" + '"'
        self.box.replace("standard/glossary.md", "## Rules", fake + "\n\n## Rules")
        self.assertFails("V19", self.box.run())

    def test_rejects_non_human_approver(self) -> None:
        self.box.edit_json(
            "standard/schemas/approval-record.schema.json",
            lambda d: d["properties"]["approver_type"].__setitem__("const", "ai_agent"),
        )
        self.assertFails("V12", self.box.run())

    def test_rejects_response_timer_in_severity(self) -> None:
        def change(doc):
            doc["severities"][0]["response_hours"] = 4

        self.box.edit_yaml("standard/severity-scale.yaml", change)
        self.assertFails("V22", self.box.run())

    def test_rejects_readiness_weights(self) -> None:
        def change(doc):
            doc["categories"][0]["weight"] = 0.2

        self.box.edit_yaml("standard/readiness-categories.yaml", change)
        self.assertFails("V21", self.box.run())

    def test_rejects_missing_glossary_term(self) -> None:
        self.box.replace("standard/glossary.md", "| capacity gap |", "| shortfall |")
        self.assertFails("V23", self.box.run())


class SchemaBehaviorTest(unittest.TestCase):
    """The shared schemas themselves enforce the human-approval and source rules."""

    @staticmethod
    def schema(name: str) -> Draft202012Validator:
        doc = json.loads((ROOT / "standard" / "schemas" / name).read_text(encoding="utf-8"))
        return Draft202012Validator(doc, format_checker=FormatChecker())

    def example(self, name: str, index: int = 0) -> dict:
        doc = json.loads((ROOT / "standard" / "schemas" / name).read_text(encoding="utf-8"))
        return json.loads(json.dumps(doc["examples"][index]))

    def test_recommendation_cannot_be_approved_without_approval_record(self) -> None:
        rec = self.example("recommendation.schema.json")
        rec["status"] = "approved"
        self.assertFalse(self.schema("recommendation.schema.json").is_valid(rec))
        rec["approval_id"] = "APR-000009"
        self.assertTrue(self.schema("recommendation.schema.json").is_valid(rec))

    def test_ai_recommendation_requires_task_run(self) -> None:
        rec = self.example("recommendation.schema.json")
        del rec["task_run_id"]
        self.assertFalse(self.schema("recommendation.schema.json").is_valid(rec))

    def test_recommendation_requires_sources(self) -> None:
        rec = self.example("recommendation.schema.json")
        rec["source_references"] = []
        self.assertFalse(self.schema("recommendation.schema.json").is_valid(rec))

    def test_approval_requires_human_person(self) -> None:
        apr = self.example("approval-record.schema.json")
        apr["approver_id"] = "AGT-000001"
        self.assertFalse(self.schema("approval-record.schema.json").is_valid(apr))
        apr = self.example("approval-record.schema.json")
        apr["approver_type"] = "ai_agent"
        self.assertFalse(self.schema("approval-record.schema.json").is_valid(apr))

    def test_event_human_actor_must_be_person(self) -> None:
        evt = self.example("event.schema.json")
        evt["actor_id"] = "AGT-000001"
        self.assertFalse(self.schema("event.schema.json").is_valid(evt))

    def test_event_rejects_extra_or_renamed_fields(self) -> None:
        evt = self.example("event.schema.json")
        evt["entity_type"] = evt.pop("subject_type")
        self.assertFalse(self.schema("event.schema.json").is_valid(evt))

    def test_event_timestamp_must_be_utc(self) -> None:
        evt = self.example("event.schema.json")
        evt["occurred_at"] = "2026-03-02T14:30:00+02:00"
        self.assertFalse(self.schema("event.schema.json").is_valid(evt))

    def test_metric_definition_rejects_values(self) -> None:
        mtr = self.example("metric-definition.schema.json")
        mtr["value"] = 1.2
        self.assertFalse(self.schema("metric-definition.schema.json").is_valid(mtr))


if __name__ == "__main__":
    unittest.main()
