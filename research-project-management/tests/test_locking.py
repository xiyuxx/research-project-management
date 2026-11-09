"""Lock routing and concurrency behavior across the flock and SQLite backends."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

INIT = Path(__file__).resolve().parents[1] / "scripts" / "init_project.py"


class LockingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="locking-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.project = self.root / "project"
        subprocess.run([sys.executable, "-B", str(INIT), str(self.project),
                        "--name", "Locking"], check=True,
                       capture_output=True, text=True)
        self.research = self.project / "tools" / "research.py"

    def environment(self, backend):
        env = dict(os.environ)
        if backend is None:
            env.pop("RESEARCH_LOCK", None)
        else:
            env["RESEARCH_LOCK"] = backend
        return env

    def run_research(self, *args, backend=None):
        return subprocess.run([sys.executable, "-B", str(self.research), *args],
                              capture_output=True, text=True,
                              env=self.environment(backend))

    def test_auto_routing_picks_the_platform_backend(self):
        created = self.run_research("new", "--slug", "auto-route", "--title", "Auto")
        self.assertEqual(created.returncode, 0, created.stderr)
        ledger = self.project / "experiments"
        if os.name == "nt":
            self.assertTrue((ledger / ".ledger.lock.db").is_file())
            self.assertFalse((ledger / ".ledger.lock").exists())
        else:
            self.assertTrue((ledger / ".ledger.lock").is_file())
            self.assertFalse((ledger / ".ledger.lock.db").exists())

    def test_explicit_backend_override_uses_that_lock(self):
        created = self.run_research("new", "--slug", "forced", "--title", "Forced",
                                    backend="sqlite")
        self.assertEqual(created.returncode, 0, created.stderr)
        self.assertTrue((self.project / "experiments" / ".ledger.lock.db").is_file())
        second = self.run_research("new", "--slug", "forced-flock", "--title", "Forced flock",
                                   backend="flock")
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertTrue((self.project / "experiments" / ".ledger.lock").is_file())

    def test_unknown_backend_is_rejected(self):
        rejected = self.run_research("new", "--slug", "reject", "--title", "Reject",
                                     backend="portalocker")
        self.assertEqual(rejected.returncode, 1)
        self.assertIn("RESEARCH_LOCK", rejected.stderr)

    def test_concurrent_writers_get_unique_ids(self):
        for backend in ("flock", "sqlite"):
            with self.subTest(backend=backend):
                project = self.root / ("concurrent-" + backend)
                subprocess.run([sys.executable, "-B", str(INIT), str(project),
                                "--name", "Concurrent"], check=True,
                               capture_output=True, text=True)
                research = project / "tools" / "research.py"
                processes = [
                    subprocess.Popen([sys.executable, "-B", str(research), "new",
                                      "--slug", "race-%d" % index, "--title", "Race %d" % index],
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                     text=True, env=self.environment(backend))
                    for index in range(4)]
                for process in processes:
                    _, errors = process.communicate(timeout=120)
                    self.assertEqual(process.returncode, 0, errors)
                listed = subprocess.run([sys.executable, "-B", str(research), "list", "--json"],
                                        capture_output=True, text=True,
                                        env=self.environment(backend))
                self.assertEqual(listed.returncode, 0, listed.stderr)
                identifiers = sorted(row["id"] for row in json.loads(listed.stdout))
                self.assertEqual(identifiers, ["EXP-0001", "EXP-0002", "EXP-0003", "EXP-0004"])
                self.assertEqual((project / "experiments" / ".next-id").read_text(
                    encoding="utf-8").strip(), "5")
                records = list((project / "experiments").glob("EXP-*.md"))
                self.assertEqual(len({path.name.split("-", 2)[1] for path in records}), 4)


if __name__ == "__main__":
    unittest.main()
