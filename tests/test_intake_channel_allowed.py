"""Tests: intake 채널 ID가 ALLOWED_CHANNELS에 등록되는지 검증.

discord_bot 모듈을 직접 임포트하지 않고, 등록 로직만 순수 Python으로 검증한다.
"""
import sys
import unittest
from unittest.mock import MagicMock

_INTAKE_KEYS = (
    "JH_REPO_DASHBOARD_CHANNEL_ID",
    "JH_WISHKET_CHANNEL_ID",
    "JH_DAILYPLUS_CHANNEL_ID",
    "JH_TASKBOARD_CHANNEL_ID",
    "JH_CHRIS_CHANNEL_ID",
)


def _run_intake_registration(channel_ids: dict, allowed: set, persist_fn) -> None:
    """_init_jh_channels 내 intake 등록 블록 로직.

    discord_bot 모듈의 코드와 1:1 대응한다:
        for _env_key, _ch_id in _intake_env_keys:
            if _ch_id:
                ALLOWED_CHANNELS.add(_ch_id)
                _persist_env_key(_env_key, _ch_id)
    """
    for env_key in _INTAKE_KEYS:
        ch_id = channel_ids.get(env_key, "")
        if ch_id:
            allowed.add(ch_id)
            persist_fn(env_key, ch_id)


class IntakeChannelRegistrationTests(unittest.TestCase):
    """intake 채널 ALLOWED_CHANNELS 등록 로직 단위 테스트."""

    def test_non_empty_ids_added_to_allowed(self):
        """비어있지 않은 채널 ID는 ALLOWED_CHANNELS에 추가된다."""
        channel_ids = {
            "JH_REPO_DASHBOARD_CHANNEL_ID": "1111111111111111111",
            "JH_WISHKET_CHANNEL_ID":        "2222222222222222222",
            "JH_DAILYPLUS_CHANNEL_ID":      "3333333333333333333",
            "JH_TASKBOARD_CHANNEL_ID":      "4444444444444444444",
            "JH_CHRIS_CHANNEL_ID":          "5555555555555555555",
        }
        allowed = set()
        persist = MagicMock()

        _run_intake_registration(channel_ids, allowed, persist)

        for env_key, ch_id in channel_ids.items():
            self.assertIn(ch_id, allowed, f"{env_key}={ch_id} not in ALLOWED_CHANNELS")

    def test_persist_called_for_each_non_empty_id(self):
        """비어있지 않은 채널 ID마다 _persist_env_key가 호출된다."""
        channel_ids = {
            "JH_REPO_DASHBOARD_CHANNEL_ID": "1111111111111111111",
            "JH_WISHKET_CHANNEL_ID":        "2222222222222222222",
            "JH_DAILYPLUS_CHANNEL_ID":      "",                    # 빈값
            "JH_TASKBOARD_CHANNEL_ID":      "4444444444444444444",
        }
        allowed = set()
        persist = MagicMock()

        _run_intake_registration(channel_ids, allowed, persist)

        called_keys = [c.args[0] for c in persist.call_args_list]
        self.assertIn("JH_REPO_DASHBOARD_CHANNEL_ID", called_keys)
        self.assertIn("JH_WISHKET_CHANNEL_ID", called_keys)
        self.assertIn("JH_TASKBOARD_CHANNEL_ID", called_keys)
        self.assertNotIn("JH_DAILYPLUS_CHANNEL_ID", called_keys)

    def test_empty_ids_not_added(self):
        """모든 채널 ID가 비어있으면 ALLOWED_CHANNELS에 추가하지 않는다."""
        channel_ids = {k: "" for k in _INTAKE_KEYS}
        allowed = set()
        persist = MagicMock()

        _run_intake_registration(channel_ids, allowed, persist)

        persist.assert_not_called()
        self.assertNotIn("", allowed)
        self.assertEqual(len(allowed), 0)

    def test_partial_ids_partially_added(self):
        """일부 채널 ID만 있으면 해당 ID만 추가된다."""
        channel_ids = {
            "JH_REPO_DASHBOARD_CHANNEL_ID": "1111111111111111111",
            "JH_WISHKET_CHANNEL_ID":        "",
            "JH_DAILYPLUS_CHANNEL_ID":      "",
            "JH_TASKBOARD_CHANNEL_ID":      "4444444444444444444",
        }
        allowed = set()
        persist = MagicMock()

        _run_intake_registration(channel_ids, allowed, persist)

        self.assertIn("1111111111111111111", allowed)
        self.assertIn("4444444444444444444", allowed)
        self.assertEqual(len(allowed), 2)
        self.assertEqual(persist.call_count, 2)


if __name__ == "__main__":
    unittest.main()
