import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import bucky_client


class BuckyClientCommandResolutionTests(unittest.TestCase):
    def test_claude_cmd_falls_back_to_user_npm_path_when_not_on_path(self):
        temp_root = Path("C:/tmp")
        temp_root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=str(temp_root)) as tmp:
            npm_dir = Path(tmp) / "npm"
            npm_dir.mkdir()
            claude_cmd = npm_dir / "claude.cmd"
            claude_cmd.write_text("@echo off\n", encoding="utf-8")

            with mock.patch.dict(
                bucky_client.os.environ,
                {"CLAUDE_COMMAND": "claude.cmd", "APPDATA": tmp},
                clear=False,
            ):
                with mock.patch.object(bucky_client.shutil, "which", return_value=None):
                    self.assertEqual(bucky_client.bucky_command(), str(claude_cmd))

    def test_explicit_claude_command_path_is_preserved(self):
        explicit = r"C:\Tools\Claude\claude.cmd"
        with mock.patch.dict(
            bucky_client.os.environ,
            {"CLAUDE_COMMAND": explicit},
            clear=False,
        ):
            self.assertEqual(bucky_client.bucky_command(), explicit)


if __name__ == "__main__":
    unittest.main()
