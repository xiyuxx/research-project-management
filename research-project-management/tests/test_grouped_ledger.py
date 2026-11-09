import concurrent.futures
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "assets/project/tools/research.py"


@unittest.skipUnless(os.name == "posix", "research.py requires POSIX file locks")
class GroupedLedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "tools").mkdir()
        (self.root / "experiments").mkdir()
        shutil.copyfile(SCRIPT, self.root / "tools/research.py")
        shutil.copyfile(SCRIPT.parents[1] / "experiments/_group_template.md",
                        self.root / "experiments/_group_template.md")
        (self.root / "CURRENT.md").write_text("# Current\n", encoding="utf-8")
        (self.root / "experiments/_template.md").write_text(
            "---\nid: template\n---\n# Experiment\n\n"
            "<!-- ledger:result:start -->\n<!-- ledger:result:end -->\n", encoding="utf-8")

    def invoke(self, *args, ok=True):
        proc = subprocess.run([sys.executable, str(self.root / "tools/research.py"), *args],
                              cwd=self.root, text=True, capture_output=True)
        if ok:
            self.assertEqual(proc.returncode, 0, proc.stderr)
        else:
            self.assertNotEqual(proc.returncode, 0, proc.stdout)
        return proc

    def expected(self, changes, identifier="auto", name="expected.json"):
        path = self.root / name
        path.write_text(json.dumps({"experiment_id": identifier, "changes": changes}), encoding="utf-8")
        return path

    def test_grouped_and_legacy_records_indexes_and_snapshot(self):
        self.invoke("group-new", "--slug", "learning-rate", "--title", "Learning rate")
        group = self.root / "experiments/GRP-001-learning-rate"
        readme = group / "README.md"
        readme.write_text(readme.read_text(encoding="utf-8") + "\nManual notes.\n", encoding="utf-8")
        source = self.expected({"optimizer.lr": 0.001, "config.layers": [1, 2]})
        original = source.read_bytes()
        result = self.invoke("new", "--group", "GRP-001", "--expected", str(source),
                             "--name-field", "optimizer.lr", "--label", "optimizer.lr=lr")
        record = self.root / result.stdout.strip()
        self.assertIn("lr-1e-3", record.name)
        self.assertEqual(source.read_bytes(), original)
        snapshot = record.with_suffix("") / "config.expected.json"
        self.assertEqual(json.loads(snapshot.read_text(encoding="utf-8")),
                         {"experiment_id": "EXP-0001", "changes": {"optimizer.lr": 0.001, "config.layers": [1, 2]}})
        self.assertIn(snapshot.relative_to(self.root).as_posix(), record.read_text(encoding="utf-8"))
        self.invoke("new", "--slug", "legacy", "--title", "Old")
        self.invoke("set", "EXP-0001", "status=running")
        self.assertEqual(json.loads(snapshot.read_text(encoding="utf-8"))["changes"]["config.layers"], [1, 2])
        self.invoke("reindex")
        self.assertIn("Manual notes.", readme.read_text(encoding="utf-8"))
        self.assertIn("[%s](%s)" % (record.stem, record.name), readme.read_text(encoding="utf-8"))
        index = (self.root / "experiments/INDEX.md").read_text(encoding="utf-8")
        self.assertIn("GRP-001-learning-rate/" + record.name, index)
        self.assertIn("EXP-0002-legacy.md", index)
        entries = json.loads(self.invoke("list", "--json").stdout)
        self.assertEqual([item["id"] for item in entries], ["EXP-0001", "EXP-0002"])
        self.assertIn("EXP-0001", self.invoke("show", "1").stdout)
        self.assertIn("EXP-0001", self.invoke("status", "1").stdout)
        self.invoke("set", "1", "expected_snapshot=other", ok=False)
        self.assertEqual(source.read_bytes(), original)

    def test_naming_types_and_expected_rejections(self):
        names = []
        for index, value in enumerate((0.001, -0.001, "0.001", True, "true")):
            source = self.expected({"a.b": value}, name="source%d.json" % index)
            record = self.invoke("new", "--expected", str(source)).stdout.strip()
            names.append(Path(record).name.split("-", 2)[2])
        self.assertEqual(len(set(names)), len(names))
        self.assertIn("1e-3", names[0])
        source = self.expected({"different.field": 0.001})
        self.assertNotEqual(names[0], Path(self.invoke("new", "--expected", str(source)).stdout.strip()).name.split("-", 2)[2])
        source = self.expected({"x": [1, 2]})
        self.invoke("new", "--expected", str(source), ok=False)
        self.invoke("new", "--expected", str(source), "--slug", "bypass", ok=False)
        self.invoke("new", "--expected", str(source), "--name-field", "missing", ok=False)
        source = self.expected({"x": 1}, identifier="EXP-0001")
        self.invoke("new", "--expected", str(source), ok=False)
        source = self.expected({"x": 1}, identifier="EXP-0007")
        self.assertIn("EXP-0007", self.invoke("new", "--expected", str(source)).stdout)

    def test_equivalent_number_spelling_and_readable_category(self):
        source = self.root / "source.json"
        source.write_text('{\"experiment_id\":\"auto\",\"changes\":{\"lr\":1e-3}}', encoding="utf-8")
        first = Path(self.invoke("new", "--expected", str(source)).stdout.strip()).name.split("-", 2)[2]
        source.write_text('{\"experiment_id\":\"auto\",\"changes\":{\"lr\":0.001}}', encoding="utf-8")
        second = Path(self.invoke("new", "--expected", str(source)).stdout.strip()).name.split("-", 2)[2]
        self.assertEqual(first, second)
        self.assertEqual(first, "lr-1e-3.md")
        source = self.expected({"fusion": "concat"})
        self.assertIn("fusion-concat", self.invoke("new", "--expected", str(source)).stdout)

    def test_review_and_duplicate_tasks(self):
        self.invoke("new", "--slug", "tasks", "--next", "same", "--next", "same")
        self.invoke("set", "1", "review_status=done")
        self.invoke("set", "1", "--result", "new evidence")
        self.assertIn("review_status: pending", self.invoke("show", "1").stdout)
        self.invoke("set", "1", "review_status=done")
        self.invoke("set", "1", "--result", "new evidence")
        self.assertIn("review_status: done", self.invoke("show", "1").stdout)
        self.invoke("set", "1", "review_status=done", "--result", "different", ok=False)
        self.invoke("set", "1", "--complete-next", "same")
        contents = self.invoke("show", "1").stdout
        self.assertEqual(contents.count("next: same"), 1)
        self.assertEqual(contents.count("next_done: same"), 1)
        self.invoke("set", "1", "--complete-next", "same")
        contents = self.invoke("show", "1").stdout
        self.assertEqual(contents.count("next: same"), 0)
        self.assertEqual(contents.count("next_done: same"), 2)
        self.invoke("set", "1", "--complete-next", "same", ok=False)

    def test_counter_corruption_and_marker_integrity(self):
        self.invoke("group-new", "--slug", "a", "--title", "A")
        group = self.root / "experiments/GRP-001-a"
        readme = group / "README.md"
        readme.write_text("Manual\n<!-- ledger:group:start -->\n", encoding="utf-8")
        self.invoke("new", "--group", "GRP-001", "--slug", "one", ok=False)
        self.assertFalse((self.root / "experiments/.next-id").exists())
        (self.root / "experiments/.next-group-id").write_text("broken", encoding="utf-8")
        self.invoke("group-new", "--slug", "b", "--title", "B", ok=False)
        self.assertEqual(readme.read_text(encoding="utf-8"), "Manual\n<!-- ledger:group:start -->\n")

    def test_parallel_global_and_group_numbering(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(self.invoke, "group-new", "--slug", "topic%d" % n,
                                   "--title", "Topic %d" % n) for n in range(4)]
            groups = [Path(f.result().stdout.strip()).name for f in futures]
        self.assertEqual(len({name.split("-")[1] for name in groups}), 4)
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(self.invoke, "new", "--group", groups[n % 4], "--slug", "trial%d" % n)
                       for n in range(8)]
            records = [Path(f.result().stdout.strip()).name for f in futures]
        self.assertEqual(len({name.split("-")[1] for name in records}), 8)
        self.assertEqual(len(json.loads(self.invoke("list", "--json").stdout)), 8)

    def test_bom_and_duplicate_expected_json(self):
        source = self.root / "bom.json"
        source.write_bytes(b"\xef\xbb\xbf" + json.dumps(
            {"experiment_id": "auto", "changes": {"optimizer.lr": 0.001}}).encode("utf-8"))
        record = Path(self.invoke("new", "--expected", str(source)).stdout.strip())
        snapshot = (self.root / record).with_suffix("") / "config.expected.json"
        self.assertEqual(json.loads(snapshot.read_text(encoding="utf-8"))["changes"]["optimizer.lr"],
                         0.001)
        record_path = self.root / record
        record_path.write_bytes(b"\xef\xbb\xbf" + record_path.read_bytes())
        self.assertIn("EXP-0001", self.invoke("show", "1").stdout)
        self.invoke("reindex")
        duplicate = self.root / "duplicate.json"
        duplicate.write_text('{"experiment_id":"auto","changes":{"a":1,"a":2}}',
                             encoding="utf-8")
        self.invoke("new", "--expected", str(duplicate), ok=False)

    def test_config_snapshot_and_explicit_run_dir(self):
        config = self.root / "real.yaml"
        config.write_text("optimizer:\n  lr: 0.001\n", encoding="utf-8")
        record = Path(self.invoke("new", "--slug", "snapshot", "--title", "Snapshot",
                                  "--config", str(config)).stdout.strip())
        record_path = self.root / record
        self.assertIn("config_hash:", record_path.read_text(encoding="utf-8"))
        snapshot = next(record_path.with_suffix("").glob("config-*.snapshot"))
        self.assertEqual(snapshot.read_bytes(), config.read_bytes())
        run = self.root / "custom-run"
        run.mkdir()
        self.invoke("set", "1", "run_dir=" + str(run))
        output = self.invoke("status", "1").stdout
        self.assertIn(str(run), output)
        self.assertIn("目录存在", output)


if __name__ == "__main__":
    unittest.main()
