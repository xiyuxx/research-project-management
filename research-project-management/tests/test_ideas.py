"""Idea parking lot: numbering, template, and isolation from the experiment ledger."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ASSETS = Path(__file__).resolve().parents[1] / "template"
SCRIPT = ASSETS / "tools" / "research.py"


class IdeaTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "tools").mkdir()
        (self.root / "experiments").mkdir()
        shutil.copyfile(SCRIPT, self.root / "tools/research.py")
        shutil.copytree(ASSETS / "ideas", self.root / "ideas")
        (self.root / "CURRENT.md").write_text("# Current\n", encoding="utf-8")
        (self.root / "experiments/_template.md").write_text(
            "---\nid: template\n---\n# Experiment\n\n"
            "<!-- ledger:result:start -->\n<!-- ledger:result:end -->\n", encoding="utf-8")

    def invoke(self, *args, ok=True):
        proc = subprocess.run([sys.executable, str(self.root / "tools/research.py"), *args],
                              cwd=self.root, text=True, encoding="utf-8", capture_output=True)
        if ok:
            self.assertEqual(proc.returncode, 0, proc.stderr)
        else:
            self.assertNotEqual(proc.returncode, 0, proc.stdout)
        return proc

    def test_idea_new_allocates_numbers_and_keeps_template_sections(self):
        self.invoke("idea-new", "--slug", "moe-fusion", "--title", "MoE routing")
        path = self.root / "ideas/IDEA-0001-moe-fusion.md"
        text = path.read_text(encoding="utf-8")
        self.assertIn("id: IDEA-0001", text)
        self.assertIn("status: parked", text)
        self.assertIn("title: MoE routing", text)
        for heading in ("## 想法", "## 动机与依据", "## 与当前方案的关系",
                        "## 重新评估的条件", "## 相关记录"):
            self.assertIn(heading, text)
        self.assertEqual((self.root / "ideas/.next-idea-id").read_text().strip(), "2")
        self.invoke("idea-new", "--slug", "distill", "--title", "Distill")
        self.assertTrue((self.root / "ideas/IDEA-0002-distill.md").is_file())

    def test_ideas_stay_out_of_derived_ledger_views(self):
        self.invoke("idea-new", "--slug", "moe-fusion", "--title", "MoE routing")
        self.invoke("reindex")
        self.assertEqual(json.loads(self.invoke("list", "--json").stdout), [])
        self.assertNotIn("IDEA-0001", (self.root / "experiments/INDEX.md").read_text(encoding="utf-8"))
        self.assertNotIn("IDEA-0001", (self.root / "experiments/NEXT.md").read_text(encoding="utf-8"))
        self.assertNotIn("IDEA-0001", (self.root / "experiments/registry.json").read_text(encoding="utf-8"))

    def test_manual_idea_is_counted_and_invalid_ones_are_rejected(self):
        manual = self.root / "ideas/IDEA-0007-handed.md"
        manual.write_text("---\nid: IDEA-0007\nslug: handed\ntitle: Handed\n"
                          "status: parked\ncreated: 2026-11-12\nupdated: 2026-11-12\n---\n# 想法\n",
                          encoding="utf-8")
        self.assertIn("IDEA-0008", self.invoke("idea-new", "--slug", "next", "--title", "Next").stdout)
        manual.write_text(manual.read_text(encoding="utf-8").replace("status: parked", "status: planned"),
                          encoding="utf-8")
        self.invoke("idea-new", "--slug", "broken", "--title", "Broken", ok=False)
        self.assertFalse((self.root / "ideas/IDEA-0009-broken.md").exists())
        (self.root / "ideas/IDEA-0009-wrong-id.md").write_text(
            "---\nid: IDEA-0010\nslug: wrong-id\ntitle: Wrong\nstatus: parked\n---\n# 想法\n",
            encoding="utf-8")
        self.invoke("idea-new", "--slug", "still", "--title", "Still", ok=False)

    def test_invalid_input_and_missing_directory_are_rejected(self):
        self.invoke("idea-new", "--slug", "中文", "--title", "CJK slug", ok=False)
        self.invoke("idea-new", "--slug", "empty", "--title", "  ", ok=False)
        self.assertFalse((self.root / "ideas/IDEA-0001-empty.md").exists())
        shutil.rmtree(self.root / "ideas")
        proc = self.invoke("idea-new", "--slug", "gone", "--title", "Gone", ok=False)
        self.assertIn("ideas/_template.md", proc.stderr)


if __name__ == "__main__":
    unittest.main()
