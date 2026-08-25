import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ReleaseEvidenceBuilderTests(unittest.TestCase):
    def test_every_required_requirement_gets_an_external_acceptance_gate(self):
        manifest = {
            "requirements": [
                {"id": "GEN-001", "level": "MUST", "section": "General", "short_requirement": "Works"},
                {"id": "QA-001", "level": "SHOULD", "section": "QA", "short_requirement": "Evidence"},
                {"id": "GEN-999", "level": "MAY", "section": "General", "short_requirement": "Optional"},
            ]
        }
        with tempfile.TemporaryDirectory() as raw:
            temp = Path(raw)
            manifest_path = temp / "manifest.json"
            registry_path = temp / "registry.json"
            results_path = temp / "results.json"
            checklist_path = temp / "checklist.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            run = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "build-release-evidence.py"),
                    "--manifest",
                    str(manifest_path),
                    "--registry",
                    str(registry_path),
                    "--results",
                    str(results_path),
                    "--checklist",
                    str(checklist_path),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            registry = json.loads(registry_path.read_text(encoding="utf-8"))["tests"]
            results = json.loads(results_path.read_text(encoding="utf-8"))["tests"]
            mapped = {req for test in registry for req in test["requirements"]}
            self.assertEqual(mapped, {"GEN-001", "QA-001"})
            self.assertTrue(all(row["status"] == "BLOCKED_EXTERNAL" for row in results))
            self.assertIn("Production acceptance", checklist_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
