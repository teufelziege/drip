import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTALLER = (ROOT / "bin/install").read_text()
SCRIPT = INSTALLER.split("python3 - <<'PY'\\n", 1)[1].split("\\nPY", 1)[0]


class InstallerTests(unittest.TestCase):
    def run_installer(self, home, work, fail_replace=False):
        injection = ""
        if fail_replace:
            injection = """
from pathlib import Path
_original_replace = Path.replace
def fail_shell_swap(self, target):
    if self.name == 'shell.json.drip.tmp':
        raise OSError('simulated configuration replacement failure')
    return _original_replace(self, target)
Path.replace = fail_shell_swap
"""
        env = dict(os.environ, HOME=str(home))
        return subprocess.run([sys.executable, "-c", injection + SCRIPT],
                              cwd=work, env=env, capture_output=True, text=True)

    def fixture(self, root):
        home = root / "home"
        config = home / ".config/omarchy"
        config.mkdir(parents=True)
        shell = config / "shell.json"
        original = '{"bar":{"layout":{"centerBegin":[]}}}\\n'
        shell.write_text(original)
        work = root / "work"
        (work / "plugin").mkdir(parents=True)
        (work / "plugin/BarWidget.qml").write_text("widget")
        (work / "build").mkdir()
        (work / "build/drip").write_text("binary")
        target = config / "plugins/tlindsey.drip"
        target.mkdir(parents=True)
        (target / "old.txt").write_text("previous")
        return home, work, shell, target, original

    def test_successful_upgrade_preserves_backup(self):
        with tempfile.TemporaryDirectory() as d:
            home, work, shell, target, original = self.fixture(Path(d))
            result = self.run_installer(home, work)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((target / "drip").read_text(), "binary")
            self.assertEqual((target.with_name(target.name + ".previous") / "old.txt").read_text(), "previous")
            layout = json.loads(shell.read_text())["bar"]["layout"]
            self.assertEqual(layout["centerBegin"], [{"id": "tlindsey.drip"}])
            self.assertEqual(len(list(shell.parent.glob("shell.json.bak.drip.*"))), 1)
            self.assertFalse(target.with_name(target.name + ".staging").exists())

    def test_failed_shell_swap_restores_plugin_and_config(self):
        with tempfile.TemporaryDirectory() as d:
            home, work, shell, target, original = self.fixture(Path(d))
            result = self.run_installer(home, work, fail_replace=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(shell.read_text(), original)
            self.assertEqual((target / "old.txt").read_text(), "previous")
            self.assertFalse((target / "drip").exists())
            self.assertFalse(target.with_name(target.name + ".staging").exists())

    def test_invalid_configuration_does_not_replace_plugin(self):
        with tempfile.TemporaryDirectory() as d:
            home, work, shell, target, _ = self.fixture(Path(d))
            shell.write_text("{invalid")
            result = self.run_installer(home, work)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(shell.read_text(), "{invalid")
            self.assertEqual((target / "old.txt").read_text(), "previous")


if __name__ == "__main__":
    unittest.main()
