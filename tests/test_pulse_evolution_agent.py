import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import pulse_evolution_agent as pea


SAMPLE_NOTE = """---
date: 2026-05-27
source: ChatGPT Pulse
source_url: https://chatgpt.com/pulse
card_count: 2
---

# ChatGPT Pulse - 2026-05-27

## Overview

Pulse
5월 27일
요약입니다.

## Pulse Cards

### 1. 버키용 최소 명령 페이로드

버키가 검증과 중복검출을 처리하도록 하는 명령 포맷입니다.

#### Detail

명령 페이로드는 실행 전 검증, 중복 감지, 재시도 규칙을 포함해야 합니다.

### 2. 음성노트 저장 안전 템플릿

음성노트 전용 메타와 리플레이 예제를 묶습니다.

#### Detail

음성 메모는 원본, 전사, 저장 상태, 리플레이 키를 남겨 데이터 손실을 막아야 합니다.
"""


class PulseEvolutionAgentTests(unittest.TestCase):
    def test_parse_daily_note_reads_all_cards_and_details(self):
        capture = pea.parse_daily_note(SAMPLE_NOTE)

        self.assertEqual(capture.date, "2026-05-27")
        self.assertEqual(len(capture.cards), 2)
        self.assertEqual(capture.cards[0].title, "버키용 최소 명령 페이로드")
        self.assertIn("중복 감지", capture.cards[0].detail)
        self.assertIn("음성 메모", capture.cards[1].detail)

    def test_build_candidates_classifies_command_and_voice_cards(self):
        capture = pea.parse_daily_note(SAMPLE_NOTE)

        candidates = pea.build_candidates(capture)

        self.assertEqual(len(candidates), 2)
        self.assertEqual(candidates[0].category, "command-payload")
        self.assertEqual(candidates[0].owner, "distiller")
        self.assertEqual(candidates[1].category, "voice-pipeline")
        self.assertEqual(candidates[1].priority, "P1")

    def test_evolve_note_file_writes_report_index_and_agentbus_task(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = root / "ObsidianVault"
            note = vault / "04_Wiki" / "daily-plus" / "2026-05-27.md"
            note.parent.mkdir(parents=True, exist_ok=True)
            note.write_text(SAMPLE_NOTE, encoding="utf-8")

            result = pea.evolve_note_file(note, vault=vault, force=False)

            self.assertEqual(result["status"], "created")
            report_path = Path(result["report_path"])
            task_path = Path(result["task_path"])
            self.assertTrue(report_path.exists())
            self.assertTrue(task_path.exists())
            report = report_path.read_text(encoding="utf-8")
            task = task_path.read_text(encoding="utf-8")
            self.assertIn("Pulse Evolution Report - 2026-05-27", report)
            self.assertIn("command-payload", report)
            self.assertIn("voice-pipeline", report)
            self.assertIn("Pulse Evolution Agent", task)
            self.assertIn("source_note:", task)
            index = (vault / "00_UPGRADE" / "PULSE_EVOLUTION_INDEX.md").read_text(encoding="utf-8")
            self.assertIn("2026-05-27", index)


if __name__ == "__main__":
    unittest.main()
