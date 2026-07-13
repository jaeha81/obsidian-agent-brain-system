"""scripts/knowledge_distiller.py 단위 테스트 — Stage 20 provenance 배관 (conversation_id 전파,
빌드 노트 신규 필드, 사이드카 processed_index.jsonl, 01_RAW 불변성 회귀).

모든 파일 I/O는 tempfile.TemporaryDirectory()에 한정한다 — 실 Vault, 실
data/memory/processed_index.jsonl은 절대 건드리지 않는다.
"""

import hashlib
import json
import re
import sys
import tempfile
import types
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# knowledge_distiller는 최상위에서 anthropic SDK를 임포트하지만, 여기서 검증하는
# provenance 헬퍼는 SDK를 쓰지 않는다. SDK 미설치 환경(클린 clone·Task Scheduler)에서도
# 테스트가 실행되도록 부재 시에만 스텁을 끼운다. 생성자는 호출 시 즉시 실패시켜
# 테스트가 실제 API를 부르는 경로로 새면 조용히 통과하지 않고 드러나게 한다.
if "anthropic" not in sys.modules:
    try:
        import anthropic  # noqa: F401
    except ModuleNotFoundError:
        _stub = types.ModuleType("anthropic")

        class _StubAnthropic:
            def __init__(self, *args, **kwargs):
                raise RuntimeError("anthropic SDK 미설치 — 이 테스트는 API를 호출하지 않아야 한다")

        _stub.Anthropic = _StubAnthropic
        sys.modules["anthropic"] = _stub

from scripts import knowledge_distiller as kd

RAW_FIXTURE = """---
source: Claude
date: 2026-04-18
conversation_id: eb129928-3609-46d4-9dd6-406bd7af3b8d
message_count: 23
topics: []
updated: 2026-04-19T21:09:59
---

본문 내용 — 테스트용 01_RAW 픽스처.
"""


class ProvenanceTestCase(unittest.TestCase):
    """PROCESSED_INDEX_FILE을 매 테스트마다 임시 경로로 교체 — 실 인덱스 보호."""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._orig_index_file = kd.PROCESSED_INDEX_FILE
        kd.PROCESSED_INDEX_FILE = Path(self._tmpdir.name) / "data" / "memory" / "processed_index.jsonl"

    def tearDown(self):
        kd.PROCESSED_INDEX_FILE = self._orig_index_file
        self._tmpdir.cleanup()


class ExtractConversationIdTests(ProvenanceTestCase):
    def test_extracts_uuid_from_real_fixture_frontmatter(self):
        result = kd.extract_conversation_id(RAW_FIXTURE)
        self.assertEqual(result, "eb129928-3609-46d4-9dd6-406bd7af3b8d")

    def test_returns_none_without_frontmatter(self):
        result = kd.extract_conversation_id("그냥 본문 텍스트, frontmatter 없음.")
        self.assertIsNone(result)

    def test_returns_none_without_conversation_id_key(self):
        text = """---
source: Claude
date: 2026-04-18
topics: []
---

본문.
"""
        result = kd.extract_conversation_id(text)
        self.assertIsNone(result)

    def test_handles_leading_bom(self):
        bom_text = "﻿" + RAW_FIXTURE
        result = kd.extract_conversation_id(bom_text)
        self.assertEqual(result, "eb129928-3609-46d4-9dd6-406bd7af3b8d")


class BuildOutputNoteTests(ProvenanceTestCase):
    def _minimal_result(self):
        return {
            "topics": ["test-topic"],
            "confidence": 0.9,
            "insights": ["insight one"],
            "related_knowledge": [],
            "tasks": [],
            "summary": "테스트 요약",
        }

    def test_includes_new_provenance_fields_when_conversation_id_given(self):
        source_path = Path("ObsidianVault") / "01_RAW" / "test-source.md"
        note = kd.build_output_note(
            self._minimal_result(),
            source_path,
            "2026-07-12",
            "claude",
            source_conversation_id="test-conv-id-123",
        )

        self.assertIn('source_conversation_id: "test-conv-id-123"', note)
        self.assertIn(f'source_file: "{source_path}"', note)
        # 기존 original_file 라인은 형식 그대로 유지되어야 한다 (하위호환).
        self.assertIn(f'original_file: "{source_path}"', note)

    def test_conversation_id_none_does_not_raise_and_field_is_present_but_empty(self):
        source_path = Path("ObsidianVault") / "01_RAW" / "test-source.md"
        note = kd.build_output_note(
            self._minimal_result(),
            source_path,
            "2026-07-12",
            "claude",
            # source_conversation_id 미지정 -> 기본값 None
        )

        self.assertRegex(note, re.compile(r"^source_conversation_id:\s*$", re.MULTILINE), msg=note)
        self.assertIn(f'original_file: "{source_path}"', note)


class AppendProcessedIndexTests(ProvenanceTestCase):
    def test_two_calls_append_two_valid_json_lines(self):
        raw_file = Path("ObsidianVault") / "01_RAW" / "a.md"
        kd.append_processed_index(raw_file, "conv-1", Path("out") / "note-1.md")
        kd.append_processed_index(raw_file, "conv-2", Path("out") / "note-2.md")

        lines = kd.PROCESSED_INDEX_FILE.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 2)

        expected_keys = {"file", "conversation_id", "output_path", "processed_at"}
        for line in lines:
            entry = json.loads(line)
            self.assertEqual(set(entry.keys()), expected_keys)

        first = json.loads(lines[0])
        second = json.loads(lines[1])
        self.assertEqual(first["conversation_id"], "conv-1")
        self.assertEqual(second["conversation_id"], "conv-2")
        self.assertNotEqual(first["output_path"], second["output_path"])


class RawImmutabilityRegressionTests(ProvenanceTestCase):
    def test_raw_file_hash_unchanged_after_extract_and_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw_file = Path(tmp) / "01_RAW" / "2026-04-18-session.md"
            raw_file.parent.mkdir(parents=True, exist_ok=True)
            raw_file.write_text(RAW_FIXTURE, encoding="utf-8")

            before_hash = hashlib.sha256(raw_file.read_bytes()).hexdigest()

            content = raw_file.read_text(encoding="utf-8")
            conversation_id = kd.extract_conversation_id(content)
            kd.append_processed_index(raw_file, conversation_id, Path(tmp) / "out" / "note.md")

            after_hash = hashlib.sha256(raw_file.read_bytes()).hexdigest()

            self.assertEqual(before_hash, after_hash)
            self.assertEqual(conversation_id, "eb129928-3609-46d4-9dd6-406bd7af3b8d")


if __name__ == "__main__":
    unittest.main()
