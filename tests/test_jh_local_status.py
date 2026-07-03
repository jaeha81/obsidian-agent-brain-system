import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import jh_local_status


class JhLocalStatusTests(unittest.TestCase):
    def test_cpu_load_percent_reads_runner_output(self):
        result = jh_local_status.cpu_load_percent(command_runner=lambda args: (0, "17"))

        self.assertEqual(result, "17%")

    def test_cpu_load_percent_returns_unknown_on_failure(self):
        result = jh_local_status.cpu_load_percent(command_runner=lambda args: (1, ""))

        self.assertEqual(result, "unknown")

    def test_bot_process_alive_true_when_pid_in_tasklist(self, tmp_pid=Path("test_pid.tmp")):
        tmp_pid.write_text("3788")
        try:
            alive = jh_local_status.bot_process_alive(
                pid_file=tmp_pid,
                command_runner=lambda args: (0, '"python.exe","3788","Console","1","591,232 K"'),
            )
            self.assertTrue(alive)
        finally:
            tmp_pid.unlink(missing_ok=True)

    def test_bot_process_alive_false_when_pid_file_missing(self):
        alive = jh_local_status.bot_process_alive(
            pid_file=Path("does_not_exist.tmp"),
            command_runner=lambda args: (0, "should not be called"),
        )

        self.assertFalse(alive)

    def test_pipeline_status_parses_dotnet_json_dates(self):
        response = (
            0,
            '{"LastRunTime":"\\/Date(943887600000)\\/",'
            '"LastTaskResult":267011,'
            '"NextRunTime":"\\/Date(1783119600000)\\/"}',
        )
        report = jh_local_status.pipeline_status(
            task_name="BuckyDailyPlusPipeline",
            command_runner=lambda args: response,
        )

        self.assertEqual(report["task"], "BuckyDailyPlusPipeline")
        self.assertEqual(report["last_result"], 267011)
        self.assertIn("1999-11-30", report["last_run"])
        self.assertIn("2026-", report["next_run"])

    def test_pipeline_status_reports_not_found_on_failure(self):
        report = jh_local_status.pipeline_status(
            task_name="MissingTask",
            command_runner=lambda args: (1, ""),
        )

        self.assertEqual(report["status"], "not_found")

    def test_git_ahead_behind_parses_left_right_counts(self):
        responses = {
            ("git", "rev-parse", "--abbrev-ref", "HEAD"): (0, "master"),
            ("git", "rev-list", "--left-right", "--count", "origin/master...master"): (0, "2\t1"),
        }

        def runner(args):
            return responses.get(tuple(args), (1, "unknown"))

        result = jh_local_status.git_ahead_behind(command_runner=runner)

        self.assertEqual(result["branch"], "master")
        self.assertEqual(result["behind"], "2")
        self.assertEqual(result["ahead"], "1")

    def test_format_text_includes_all_sections(self):
        report = {
            "cpu_load": "12%",
            "disks": [
                {"path": "D:\\", "total_gb": 100.0, "free_gb": 50.0, "percent_used": 50.0},
                {"path": "X:\\", "error": "unavailable"},
            ],
            "discord_bot_alive": True,
            "daily_plus_pipeline": {
                "task": "BuckyDailyPlusPipeline",
                "last_run": "2026-07-03 08:00",
                "last_result": 0,
                "next_run": "2026-07-04 08:00",
            },
            "git": {"branch": "master", "ahead": "0", "behind": "0"},
        }

        text = jh_local_status.format_text(report)

        self.assertIn("CPU 사용률: 12%", text)
        self.assertIn("D:\\", text)
        self.assertIn("조회 불가", text)
        self.assertIn("실행 중", text)
        self.assertIn("ahead 0 / behind 0", text)


if __name__ == "__main__":
    unittest.main()
