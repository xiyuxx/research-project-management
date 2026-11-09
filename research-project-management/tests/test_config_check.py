"""Consumer-visible configuration gate behavior; standard library only."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

CHECKER = Path(__file__).resolve().parents[1] / "scripts" / "check_config.py"


class ConfigCheckTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="config-check-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.expected = self.root / "expected.json"
        self.effective = self.root / "effective.json"
        self.expected.write_text(json.dumps({"experiment_id": "EXP-0001", "changes": {
            "optimizer.lr": 0.001}}), encoding="utf-8")
        self.effective.write_text(json.dumps({"experiment_id": "EXP-0001", "config": {
            "optimizer": {"lr": 0.001}}}), encoding="utf-8")

    def invoke(self, *extra):
        process = subprocess.run([sys.executable, "-B", str(CHECKER),
                                  "--expected", str(self.expected),
                                  "--effective", str(self.effective), *extra],
                                 capture_output=True, text=True)
        return process.returncode, json.loads(process.stdout)

    def test_utf8_bom_is_accepted(self):
        expected = json.dumps({"experiment_id": "EXP-0001", "changes": {
            "optimizer.lr": 0.001}})
        effective = json.dumps({"experiment_id": "EXP-0001", "config": {
            "optimizer": {"lr": 1e-3}}})
        self.expected.write_bytes(b"\xef\xbb\xbf" + expected.encode("utf-8"))
        self.effective.write_bytes(b"\xef\xbb\xbf" + effective.encode("utf-8"))
        code, report = self.invoke()
        self.assertEqual(code, 0)
        self.assertEqual(report["status"], "passed")

    def test_equivalent_numbers_and_nested_values_match(self):
        self.expected.write_text('{"experiment_id":"EXP-0001","changes":'
                                 '{"optimizer.lr":1e-3,"settings":{"enabled":true,"devices":[0,1]}}}',
                                 encoding="utf-8")
        self.effective.write_text('{"experiment_id":"EXP-0001","config":'
                                  '{"optimizer":{"lr":0.001},"settings":{"devices":[0,1],"enabled":true},'
                                  '"unselected":42}}', encoding="utf-8")
        code, report = self.invoke()
        self.assertEqual(code, 0)
        self.assertEqual(report["status"], "passed")

    def test_changed_and_missing_conditions_fail_together(self):
        self.expected.write_text(json.dumps({"experiment_id": "EXP-0001", "changes": {
            "optimizer.lr": 0.001, "fusion.method": "concat"}}), encoding="utf-8")
        self.effective.write_text(json.dumps({"experiment_id": "EXP-0001", "config": {
            "optimizer": {"lr": 0.0001}}}), encoding="utf-8")
        code, report = self.invoke()
        self.assertEqual(code, 1)
        self.assertEqual({item["field"]: item["status"] for item in report["checks"]},
                         {"optimizer.lr": "different", "fusion.method": "missing"})

    def test_wrong_experiment_cannot_pass_matching_parameters(self):
        document = json.loads(self.effective.read_text(encoding="utf-8"))
        document["experiment_id"] = "EXP-0002"
        self.effective.write_text(json.dumps(document), encoding="utf-8")
        code, report = self.invoke()
        self.assertEqual(code, 1)
        self.assertIn("experiment_id", [item["field"] for item in report["checks"]
                                        if item["status"] == "different"])

    def test_types_and_array_order_are_not_coerced(self):
        for expected, actual in ((1, True), (False, 0), (0.001, "0.001"),
                                 ([True], [1]), ([0, 1], [1, 0]),
                                 ({"enabled": True}, {"enabled": 1}),
                                 ("concat", "add")):
            with self.subTest(expected=expected, actual=actual):
                self.expected.write_text(json.dumps({"experiment_id": "EXP-0001",
                                                     "changes": {"value": expected}}), encoding="utf-8")
                self.effective.write_text(json.dumps({"experiment_id": "EXP-0001",
                                                      "config": {"value": actual}}), encoding="utf-8")
                self.assertEqual(self.invoke()[0], 1)

    def test_auto_experiment_id_is_not_a_real_execution_identity(self):
        self.expected.write_text(json.dumps({"experiment_id": "auto", "changes": {"optimizer.lr": 0.001}}), encoding="utf-8")
        self.effective.write_text(json.dumps({"experiment_id": "auto", "config": {"optimizer": {"lr": 0.001}}}), encoding="utf-8")
        code, report = self.invoke()
        self.assertEqual(code, 2)
        self.assertEqual(report["status"], "invalid")

    def test_array_field_and_missing_index(self):
        self.expected.write_text(json.dumps({"experiment_id": "EXP-0001", "changes": {
            "groups.0.lr": 0.001, "groups.1.lr": 0.001}}), encoding="utf-8")
        self.effective.write_text(json.dumps({"experiment_id": "EXP-0001", "config": {
            "groups": [{"lr": 0.001}]}}), encoding="utf-8")
        code, report = self.invoke()
        self.assertEqual(code, 1)
        self.assertEqual([item["status"] for item in report["checks"]], ["match", "missing"])

    def test_empty_duplicate_nonfinite_and_bad_input_are_invalid(self):
        documents = [
            '{"experiment_id":"EXP-0001","changes":{}}',
            '{"experiment_id":"EXP-0001","changes":{"a":1,"a":2}}',
            '{"experiment_id":"EXP-0001","changes":{"a":NaN}}',
            '{"experiment_id":"EXP-0001","changes":{"a":1e9999}}',
            '{"experiment_id":"EXP-0001","changes":{"a..b":1}}',
            '{"changes":{"a":1}}', '[]', '{broken',
        ]
        for document in documents:
            with self.subTest(document=document):
                self.expected.write_text(document, encoding="utf-8")
                code, report = self.invoke()
                self.assertEqual(code, 2)
                self.assertEqual(report["status"], "invalid")

    def test_effective_config_is_required_and_must_be_valid(self):
        for document in ('{"experiment_id":"EXP-0001"}',
                         '{"experiment_id":"EXP-0001","config":{"a":1,"a":2}}',
                         '{"experiment_id":"EXP-0001","config":{"a":Infinity}}'):
            with self.subTest(document=document):
                self.effective.write_text(document, encoding="utf-8")
                self.assertEqual(self.invoke()[0], 2)
        self.effective.unlink()
        self.assertEqual(self.invoke()[0], 2)

    def test_receipt_cannot_replace_history_or_input(self):
        receipt = self.root / "receipt.json"
        receipt.write_bytes(b"previous attempt evidence\n")
        before = self.expected.read_bytes(), self.effective.read_bytes()
        self.assertEqual(self.invoke("--receipt", str(receipt))[0], 2)
        self.assertEqual(receipt.read_bytes(), b"previous attempt evidence\n")
        self.assertEqual(self.invoke("--receipt", str(self.expected))[0], 2)
        self.assertEqual((self.expected.read_bytes(), self.effective.read_bytes()), before)

    def test_mismatch_receipt_is_not_a_success_marker(self):
        self.effective.write_text('{"experiment_id":"EXP-0001","config":{}}', encoding="utf-8")
        receipt = self.root / "receipt.json"
        code, _ = self.invoke("--receipt", str(receipt))
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(receipt.read_text(encoding="utf-8"))["status"], "mismatch")


if __name__ == "__main__":
    unittest.main()
