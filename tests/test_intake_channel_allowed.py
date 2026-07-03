"""Tests for dashboard intake channel registration logic.

This keeps a pure-Python copy of the _init_jh_channels intake registration
block so we can verify channel IDs are added without importing discord_bot.
"""

import unittest
from unittest.mock import MagicMock

_INTAKE_KEYS = (
    "JH_CHAT_CHANNEL_ID",
    "JH_REPO_DASHBOARD_CHANNEL_ID",
    "JH_WISHKET_CHANNEL_ID",
    "JH_KMONG_CHANNEL_ID",
    "JH_MYINTRO_CHANNEL_ID",
    "JH_DAILYPLUS_CHANNEL_ID",
    "JH_TASKBOARD_CHANNEL_ID",
    "JH_CHRIS_CHANNEL_ID",
    "JH_CHARLIE_CHANNEL_ID",
    "JH_CLAUDE_CODE_CHANNEL_ID",
    "JH_CODEX_CHANNEL_ID",
)


def _run_intake_registration(channel_ids: dict, allowed: set, persist_fn) -> None:
    for env_key in _INTAKE_KEYS:
        ch_id = channel_ids.get(env_key, "")
        if ch_id:
            allowed.add(ch_id)
            persist_fn(env_key, ch_id)


class IntakeChannelRegistrationTests(unittest.TestCase):
    def test_non_empty_ids_added_to_allowed(self):
        channel_ids = {
            "JH_REPO_DASHBOARD_CHANNEL_ID": "1111111111111111111",
            "JH_WISHKET_CHANNEL_ID": "2222222222222222222",
            "JH_KMONG_CHANNEL_ID": "6666666666666666666",
            "JH_DAILYPLUS_CHANNEL_ID": "3333333333333333333",
            "JH_TASKBOARD_CHANNEL_ID": "4444444444444444444",
            "JH_CHRIS_CHANNEL_ID": "5555555555555555555",
        }
        allowed = set()
        persist = MagicMock()

        _run_intake_registration(channel_ids, allowed, persist)

        for env_key, ch_id in channel_ids.items():
            self.assertIn(ch_id, allowed, f"{env_key}={ch_id} not in ALLOWED_CHANNELS")

    def test_persist_called_for_each_non_empty_id(self):
        channel_ids = {
            "JH_REPO_DASHBOARD_CHANNEL_ID": "1111111111111111111",
            "JH_WISHKET_CHANNEL_ID": "2222222222222222222",
            "JH_KMONG_CHANNEL_ID": "6666666666666666666",
            "JH_DAILYPLUS_CHANNEL_ID": "",
            "JH_TASKBOARD_CHANNEL_ID": "4444444444444444444",
        }
        allowed = set()
        persist = MagicMock()

        _run_intake_registration(channel_ids, allowed, persist)

        called_keys = [c.args[0] for c in persist.call_args_list]
        self.assertIn("JH_REPO_DASHBOARD_CHANNEL_ID", called_keys)
        self.assertIn("JH_WISHKET_CHANNEL_ID", called_keys)
        self.assertIn("JH_KMONG_CHANNEL_ID", called_keys)
        self.assertIn("JH_TASKBOARD_CHANNEL_ID", called_keys)
        self.assertNotIn("JH_DAILYPLUS_CHANNEL_ID", called_keys)

    def test_empty_ids_not_added(self):
        channel_ids = {k: "" for k in _INTAKE_KEYS}
        allowed = set()
        persist = MagicMock()

        _run_intake_registration(channel_ids, allowed, persist)

        persist.assert_not_called()
        self.assertNotIn("", allowed)
        self.assertEqual(len(allowed), 0)

    def test_partial_ids_partially_added(self):
        channel_ids = {
            "JH_REPO_DASHBOARD_CHANNEL_ID": "1111111111111111111",
            "JH_WISHKET_CHANNEL_ID": "",
            "JH_KMONG_CHANNEL_ID": "6666666666666666666",
            "JH_DAILYPLUS_CHANNEL_ID": "",
            "JH_TASKBOARD_CHANNEL_ID": "4444444444444444444",
        }
        allowed = set()
        persist = MagicMock()

        _run_intake_registration(channel_ids, allowed, persist)

        self.assertIn("1111111111111111111", allowed)
        self.assertIn("6666666666666666666", allowed)
        self.assertIn("4444444444444444444", allowed)
        self.assertEqual(len(allowed), 3)
        self.assertEqual(persist.call_count, 3)


if __name__ == "__main__":
    unittest.main()
