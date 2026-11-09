"""Gate wrapper behavior: the command only runs after a passing check."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

GATE = Path(__file__).resolve().parents[1] / "scripts" / "run_with_gate.py"


class RunWithGateTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="gate-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.expected = self.root / "expected.json"
        self.effective = self.root / "effective.json"
        self.marker = self.root / "ran.txt"
        self.expected.write_text(json.dumps({"experiment_id": "EXP-0001", "changes": {
            "optimizer.lr": 0.001}}), encoding="utf-8")
        self.effective.write_text(json.dumps({"experiment_id": "EXP-0001", "config": {
            "optimizer": {"lr": 0.001}}}), encoding="utf-8")

    def invoke(self, *extra, command=None):
        if command is None:
            command = [sys.executable, "-c",
                       "open(%r, 'w').write('ran')" % str(self.marker)]
        process = subprocess.run([sys.executable, "-B", str(GATE),
                                  "--expected", str(self.expected),
                                  "--effective", str(self.effective), *extra, "--", *command],
                                 capture_output=True, text=True)
        return process

    def test_matching_conditions_launch_the_command(self):
        process = self.invoke("--receipt", str(self.root / "check.json"))
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertTrue(self.marker.is_file())
        self.assertTrue((self.root / "check.json").is_file())

    def test_mismatch_refuses_to_launch(self):
        self.effective.write_text(json.dumps({"experiment_id": "EXP-0001", "config": {
            "optimizer": {"lr": 0.01}}}), encoding="utf-8")
        process = self.invoke()
        self.assertEqual(process.returncode, 1)
        self.assertFalse(self.marker.exists())
        self.assertIn("门禁未通过", process.stderr)

    def test_invalid_input_returns_two_and_does_not_launch(self):
        self.effective.write_text("{not json", encoding="utf-8")
        process = self.invoke()
        self.assertEqual(process.returncode, 2)
        self.assertFalse(self.marker.exists())

    def test_missing_command_is_rejected(self):
        process = subprocess.run([sys.executable, "-B", str(GATE),
                                  "--expected", str(self.expected),
                                  "--effective", str(self.effective)],
                                 capture_output=True, text=True)
        self.assertEqual(process.returncode, 2)

    def test_export_command_runs_first(self):
        exporter = self.root / "export.py"
        exporter.write_text("import json,sys;"
                            "open(sys.argv[1], 'w').write(json.dumps("
                            "{'experiment_id': 'EXP-0001', 'config': {'optimizer': {'lr': 0.001}}}))"
                            "\n", encoding="utf-8")
        self.effective.unlink()
        process = self.invoke("--export-cmd",
                              "%s %s %s" % (sys.executable, exporter, self.effective))
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertTrue(self.marker.is_file())

    def test_command_exit_code_propagates(self):
        process = self.invoke(command=[sys.executable, "-c", "raise SystemExit(7)"])
        self.assertEqual(process.returncode, 7)


if __name__ == "__main__":
    unittest.main()
