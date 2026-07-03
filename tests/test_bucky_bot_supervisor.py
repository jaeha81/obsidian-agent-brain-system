import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


class BuckyBotSupervisorTests(unittest.TestCase):
    def test_reconcile_legacy_pid_file_kills_live_discord_bot(self):
        import bucky_bot_supervisor

        legacy_pid = mock.Mock()
        legacy_pid.exists.return_value = True
        legacy_pid.read_text.return_value = "12345"
        killed: list[int] = []

        with (
            mock.patch.object(bucky_bot_supervisor, "LEGACY_PID_FILE", legacy_pid),
            mock.patch.object(bucky_bot_supervisor, "is_pid_running", return_value=True),
            mock.patch.object(
                bucky_bot_supervisor,
                "process_command_line",
                return_value='C:\\Python314\\python.exe -X utf8 "G:\\repo\\scripts\\discord_bot.py"',
            ),
            mock.patch.object(bucky_bot_supervisor, "kill_pid", side_effect=killed.append),
            mock.patch.object(bucky_bot_supervisor.time, "sleep", return_value=None),
        ):
            reconciled = bucky_bot_supervisor.reconcile_legacy_pid_file()

        self.assertEqual(reconciled, [12345])
        self.assertEqual(killed, [12345])
        legacy_pid.unlink.assert_called_once_with(missing_ok=True)

    def test_reconcile_legacy_pid_file_removes_non_discord_stale_pid(self):
        import bucky_bot_supervisor

        legacy_pid = mock.Mock()
        legacy_pid.exists.return_value = True
        legacy_pid.read_text.return_value = "12345"

        with (
            mock.patch.object(bucky_bot_supervisor, "LEGACY_PID_FILE", legacy_pid),
            mock.patch.object(bucky_bot_supervisor, "is_pid_running", return_value=True),
            mock.patch.object(
                bucky_bot_supervisor,
                "process_command_line",
                return_value='C:\\Windows\\System32\\notepad.exe',
            ),
            mock.patch.object(bucky_bot_supervisor, "kill_pid") as kill_pid,
        ):
            reconciled = bucky_bot_supervisor.reconcile_legacy_pid_file()

        self.assertEqual(reconciled, [])
        kill_pid.assert_not_called()
        legacy_pid.unlink.assert_called_once_with(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
