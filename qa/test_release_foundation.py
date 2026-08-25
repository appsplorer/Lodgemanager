import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ReleaseFoundationTests(unittest.TestCase):
    """QA-001/QA-010: evidence must identify and execute real tests."""

    def test_qa_001_decorator_records_stable_requirement_metadata(self):
        from qa.test_registry import requirement_test

        @requirement_test("UT-QA-QA-001", ["QA-001", "QA-010"], "unit")
        def example():
            return True

        self.assertEqual(example.requirement_test_id, "UT-QA-QA-001")
        self.assertEqual(example.requirement_ids, ("QA-001", "QA-010"))
        self.assertEqual(example.evidence_kind, "unit")

    def test_qa_001_runner_executes_behavior_and_writes_results(self):
        runner = ROOT / "scripts" / "run-source-tests.py"
        with tempfile.TemporaryDirectory() as raw:
            temp = Path(raw)
            sample = temp / "test_sample.py"
            results = temp / "results.json"
            sample.write_text(
                "def test_observable_behavior():\n"
                "    assert 2 + 2 == 4\n",
                encoding="utf-8",
            )
            run = subprocess.run(
                [sys.executable, str(runner), str(sample), "--output", str(results)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            payload = json.loads(results.read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"], {"passed": 1, "failed": 0, "errors": 0, "total": 1})
            self.assertEqual(payload["tests"][0]["name"], "test_observable_behavior")
            self.assertEqual(payload["tests"][0]["status"], "PASS")

    def test_qa_010_generator_rejects_unknown_acceptance_test_id(self):
        generator = ROOT / "scripts" / "generate-traceability.py"
        with tempfile.TemporaryDirectory() as raw:
            temp = Path(raw)
            manifest = temp / "manifest.json"
            registry = temp / "registry.json"
            results = temp / "results.json"
            output = temp / "trace.json"
            manifest.write_text(json.dumps({"requirements": [{"id": "QA-010", "level": "MUST", "short_requirement": "Runtime evidence"}]}))
            registry.write_text(json.dumps({"tests": [{"id": "UT-QA-QA-010", "requirements": ["QA-010"], "kind": "unit"}]}))
            results.write_text(json.dumps({"tests": [{"id": "UNKNOWN-ID", "status": "PASS", "evidence": "result.xml"}]}))
            run = subprocess.run(
                [sys.executable, str(generator), "--manifest", str(manifest), "--registry", str(registry), "--results", str(results), "--output", str(output)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(run.returncode, 0)
            self.assertIn("unknown test id", (run.stdout + run.stderr).lower())

    def test_qa_010_generator_never_promotes_pass_without_evidence(self):
        generator = ROOT / "scripts" / "generate-traceability.py"
        with tempfile.TemporaryDirectory() as raw:
            temp = Path(raw)
            manifest = temp / "manifest.json"
            registry = temp / "registry.json"
            results = temp / "results.json"
            output = temp / "trace.json"
            manifest.write_text(json.dumps({"requirements": [{"id": "QA-010", "level": "MUST", "short_requirement": "Runtime evidence"}]}))
            registry.write_text(json.dumps({"tests": [{"id": "UT-QA-QA-010", "requirements": ["QA-010"], "kind": "unit"}]}))
            results.write_text(json.dumps({"tests": [{"id": "UT-QA-QA-010", "status": "PASS", "evidence": ""}]}))
            run = subprocess.run(
                [sys.executable, str(generator), "--manifest", str(manifest), "--registry", str(registry), "--results", str(results), "--output", str(output)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(run.returncode, 0)
            self.assertIn("evidence", (run.stdout + run.stderr).lower())

    def test_qa_010_strict_gate_does_not_require_optional_may_evidence(self):
        generator = ROOT / "scripts" / "generate-traceability.py"
        with tempfile.TemporaryDirectory() as raw:
            temp = Path(raw)
            manifest = temp / "manifest.json"
            registry = temp / "registry.json"
            results = temp / "results.json"
            output = temp / "trace.json"
            manifest.write_text(json.dumps({"requirements": [{"id": "GEN-999", "level": "MAY", "short_requirement": "Optional extension"}]}))
            registry.write_text(json.dumps({"tests": []}))
            results.write_text(json.dumps({"tests": []}))
            run = subprocess.run(
                [sys.executable, str(generator), "--manifest", str(manifest), "--registry", str(registry), "--results", str(results), "--output", str(output), "--strict"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)


if __name__ == "__main__":
    unittest.main()
