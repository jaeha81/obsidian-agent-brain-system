import io
import unittest

from scripts import work_done_alarm


class WorkDoneAlarmTests(unittest.TestCase):
    def test_alarm_enabled_defaults_to_true(self):
        self.assertTrue(work_done_alarm.alarm_enabled({}))

    def test_alarm_enabled_accepts_false_values(self):
        for value in ("0", "false", "no", "off", "disabled"):
            with self.subTest(value=value):
                self.assertFalse(work_done_alarm.alarm_enabled({"WORK_DONE_ALARM_ENABLED": value}))

    def test_play_terminal_bell_writes_requested_count(self):
        stream = io.StringIO()

        work_done_alarm.play_terminal_bell(count=3, gap_ms=0, stream=stream)

        self.assertEqual(stream.getvalue(), "\a\a\a")

    def test_clamp_int_bounds_values(self):
        self.assertEqual(work_done_alarm._clamp_int(1, minimum=10, maximum=20), 10)
        self.assertEqual(work_done_alarm._clamp_int(30, minimum=10, maximum=20), 20)
        self.assertEqual(work_done_alarm._clamp_int(15, minimum=10, maximum=20), 15)


if __name__ == "__main__":
    unittest.main()
