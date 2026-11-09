"""Cross-platform initialization behavior; standard library only."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


INIT = Path(__file__).resolve().parents[1] / "scripts" / "init_project.py"


class InitProjectTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="init-project-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def invoke(self, *args, ok=True):
        process = subprocess.run([sys.executable, "-B", str(INIT), *args],
                                 capture_output=True, text=True)
        if ok:
            self.assertEqual(process.returncode, 0, process.stderr)
        else:
            self.assertNotEqual(process.returncode, 0, process.stdout)
        return process

    def test_existing_empty_target_is_initialized(self):
        target = self.root / "empty"
        target.mkdir()
        self.invoke(str(target), "--name", "Existing")
        self.assertTrue((target / "tools/research.py").is_file())
        self.assertTrue((target / "tools/check_config.py").is_file())
        self.assertTrue((target / "tools/run_with_gate.py").is_file())
        self.assertIn("# Existing", (target / "README.md").read_text(encoding="utf-8"))
        agents = (target / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("research-project-management v0.2.1", agents)
        self.assertNotIn("{{SKILL_VERSION}}", agents)

    def test_dry_run_and_nonempty_target_leave_no_files(self):
        preview = self.root / "preview"
        self.invoke(str(preview), "--name", "Preview", "--dry-run")
        self.assertFalse(preview.exists())
        target = self.root / "occupied"
        target.mkdir()
        (target / "keep.txt").write_text("keep", encoding="utf-8")
        self.invoke(str(target), "--name", "Occupied", ok=False)
        self.assertEqual(sorted(path.name for path in target.iterdir()), ["keep.txt"])

    def test_symlink_and_invalid_name_are_rejected(self):
        real = self.root / "real"
        real.mkdir()
        link = self.root / "link"
        try:
            link.symlink_to(real)
        except OSError:
            self.skipTest("当前环境不允许创建符号链接")
        self.invoke(str(link), "--name", "Link", ok=False)
        self.invoke(str(self.root / "bad"), "--name", "bad\nname", ok=False)
        self.assertFalse((self.root / "bad").exists())


if __name__ == "__main__":
    unittest.main()
