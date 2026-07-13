"""scripts/knowledge_distiller.py 단위 테스트 — Stage 20 provenance 배관 (conversation_id 전파,
빌드 노트 신규 필드, 사이드카 processed_index.jsonl, 01_RAW 불변성 회귀).

모든 파일 I/O는 tempfile.TemporaryDirectory()에 한정한다 — 실 Vault, 실
data/memory/processed_index.jsonl은 절대 건드리지 않는다.
"""

import hashlib
import json
import os
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


class MergeIdempotencyTests(ProvenanceTestCase):
    """반복 병합(--reset/--retry 재처리)이 태스크·연결개념을 중복 누적하지 않는다.

    과거에는 insights만 중복 제거돼, tasks가 하나라도 있으면 매 재처리마다 병합 블록과
    태스크·연결개념이 다시 쌓였다.
    """

    def test_repeated_merge_with_same_result_adds_nothing_the_second_time(self):
        result = {
            "topics": ["t1", "t2"],
            "insights": ["인사이트 하나"],
            "tasks": ["- [ ] 태스크 하나"],
            "related_knowledge": ["연결개념 하나"],
        }
        with tempfile.TemporaryDirectory() as tmp:
            note = Path(tmp) / "note.md"
            note.write_text("---\ntopics: [t1, t2]\n---\n\n본문.\n", encoding="utf-8")
            raw = Path(tmp) / "raw.md"

            kd.merge_into_existing_note(note, result, raw, source_conversation_id="conv-1")
            after_first = note.read_text(encoding="utf-8")

            kd.merge_into_existing_note(note, result, raw, source_conversation_id="conv-1")
            after_second = note.read_text(encoding="utf-8")

            self.assertEqual(after_first, after_second, "두 번째 병합이 내용을 중복 추가했다")
            self.assertEqual(after_second.count("태스크 하나"), 1)
            self.assertEqual(after_second.count("연결개념 하나"), 1)
            self.assertEqual(after_second.count("인사이트 하나"), 1)


class ProcessBatchIntegrationTests(unittest.TestCase):
    """process_batch() 전 경로(신규 생성·주제 병합·sidecar 실패) 통합 테스트.

    헬퍼 단위 테스트만으로는 01_RAW 불변 계약이 실제 배치 처리 경로에서 지켜지는지
    고정되지 않는다. 여기서는 distill_file만 스텁으로 대체(API 미호출)하고 나머지
    배치 로직은 실제로 실행하되, 모든 경로 상수를 임시 디렉터리로 격리한다.
    """

    DISTILL_RESULT = {
        "topics": ["bucky-os", "provenance"],
        "confidence": 0.9,
        "insights": ["신규 인사이트 하나"],
        "related_knowledge": [],
        "tasks": [],
        "summary": "테스트 요약",
    }

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        tmp = Path(self._tmpdir.name)

        self._orig = {
            name: getattr(kd, name)
            for name in (
                "VAULT_BASE", "OUTPUT_BASE", "STATE_FILE", "RETRY_QUEUE",
                "PROCESSED_INDEX_FILE", "CONTENT_HASH_REGISTRY", "ERROR_REPORT",
                "distill_file",
            )
        }

        vault = tmp / "vault"
        kd.VAULT_BASE            = vault
        kd.OUTPUT_BASE           = vault / "03_Knowledge" / "distilled"
        kd.ERROR_REPORT          = vault / "00_System" / "distiller-errors.md"
        kd.STATE_FILE            = tmp / ".distiller_cache.json"
        kd.RETRY_QUEUE           = tmp / ".distiller_retry_queue.json"
        kd.CONTENT_HASH_REGISTRY = tmp / ".distiller_content_hashes.json"
        kd.PROCESSED_INDEX_FILE  = tmp / "data" / "memory" / "processed_index.jsonl"

        kd.distill_file = lambda *args, **kwargs: dict(self.DISTILL_RESULT)

        self.raw_file = vault / "01_RAW" / "2026-04-18-session.md"
        self.raw_file.parent.mkdir(parents=True, exist_ok=True)
        self.raw_file.write_text(RAW_FIXTURE, encoding="utf-8")
        self.raw_hash_before = hashlib.sha256(self.raw_file.read_bytes()).hexdigest()

    def tearDown(self):
        for name, value in self._orig.items():
            setattr(kd, name, value)
        self._tmpdir.cleanup()

    def _run_batch(self, state=None):
        """state를 넘기면 이어서 실행한다(2차 실행 시뮬레이션)."""
        stats = {"processed": 0, "failed": 0, "skipped": 0}
        if state is None:
            state = {}
        success, fail = kd.process_batch(
            None, [self.raw_file], state, stats,
            batch_num=1, total_batches=1, content_hash_registry={},
        )
        return success, fail, state, stats

    def _sidecar_entries(self):
        text = kd.PROCESSED_INDEX_FILE.read_text(encoding="utf-8")
        return [json.loads(line) for line in text.splitlines() if line.strip()]

    def _assert_raw_unchanged(self):
        after = hashlib.sha256(self.raw_file.read_bytes()).hexdigest()
        self.assertEqual(self.raw_hash_before, after, "01_RAW 원본이 배치 처리 중 변경되었다")

    def test_new_note_path_records_provenance_and_leaves_raw_untouched(self):
        success, fail, state, _ = self._run_batch()

        self.assertEqual((success, fail), (1, 0))
        self._assert_raw_unchanged()

        notes = list((kd.OUTPUT_BASE / "2026-04").glob("*.md"))
        self.assertEqual(len(notes), 1)
        note_text = notes[0].read_text(encoding="utf-8")
        self.assertIn('source_conversation_id: "eb129928-3609-46d4-9dd6-406bd7af3b8d"', note_text)

        entries = self._sidecar_entries()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["conversation_id"], "eb129928-3609-46d4-9dd6-406bd7af3b8d")
        self.assertEqual(entries[0]["output_path"], str(notes[0]))
        self.assertEqual(state[str(self.raw_file)], kd.file_hash(self.raw_file))

    def test_merge_path_records_conversation_id_and_leaves_raw_untouched(self):
        # 토픽 2개가 겹치는 기존 노트를 미리 심어 find_existing_note_by_topic이 병합을 고르게 한다.
        out_dir = kd.OUTPUT_BASE / "2026-04"
        out_dir.mkdir(parents=True, exist_ok=True)
        existing = out_dir / "2026-04-01-earlier-note.md"
        existing.write_text(
            "---\n"
            "topics: [bucky-os, provenance]\n"
            'source_conversation_id: "older-conv-id"\n'
            "---\n\n"
            "- 기존 인사이트\n",
            encoding="utf-8",
        )

        success, fail, _, _ = self._run_batch()

        self.assertEqual((success, fail), (1, 0))
        self._assert_raw_unchanged()

        # 신규 노트를 만들지 않고 기존 노트에 병합했어야 한다.
        self.assertEqual(sorted(p.name for p in out_dir.glob("*.md")), [existing.name])

        merged_text = existing.read_text(encoding="utf-8")
        self.assertIn("## 병합 추가", merged_text)
        self.assertIn("**source_conversation_id**: `eb129928-3609-46d4-9dd6-406bd7af3b8d`", merged_text)
        self.assertIn(f"**source_file**: `{self.raw_file}`", merged_text)
        # 기존 frontmatter의 최초 원본 표기는 보존한다.
        self.assertIn('source_conversation_id: "older-conv-id"', merged_text)

        entries = self._sidecar_entries()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["output_path"], str(existing))

    def test_existing_note_with_same_filename_is_merged_never_overwritten(self):
        """파일명 일치 경로: state가 없어도 기존 노트를 덮어쓰지 않는다.

        과거 조건은 `output_path.exists() and state.get(raw_file)`이어서, state가 없으면
        신규 분기로 내려가 기존 노트를 write_text로 **덮어썼다**.
        """
        out_dir = kd.OUTPUT_BASE / "2026-04"
        out_dir.mkdir(parents=True, exist_ok=True)
        # determine_output_path가 고를 바로 그 경로에 노트를 미리 심는다.
        target = kd.determine_output_path("2026-04-18", self.raw_file)
        target.write_text(
            "---\ntopics: [무관토픽]\n---\n\n- 기존 인사이트\n\n사용자가 손으로 쓴 문장.\n",
            encoding="utf-8",
        )

        # state는 비어 있다 — 과거엔 이 조건에서 덮어쓰기가 났다.
        success, fail, _, _ = self._run_batch(state={})

        self.assertEqual((success, fail), (1, 0))
        merged = target.read_text(encoding="utf-8")
        self.assertIn("사용자가 손으로 쓴 문장.", merged, "기존 노트가 덮어써졌다")
        self.assertIn("## 병합 추가", merged)
        self.assertIn("**source_conversation_id**: `eb129928-3609-46d4-9dd6-406bd7af3b8d`", merged)
        self._assert_raw_unchanged()

    def test_note_created_between_check_and_write_is_merged_not_overwritten(self):
        """TOCTOU 경합: exists() 검사 통과 후 다른 프로세스가 노트를 만들어도 덮어쓰지 않는다.

        build_output_note가 호출되는 시점(= exists() 검사 직후, 쓰기 직전)에 파일을 만들어
        경쟁 쓰기를 재현한다. 원자적 생성(O_EXCL)이 이를 잡아 병합으로 넘겨야 한다.
        """
        target = kd.determine_output_path("2026-04-18", self.raw_file)
        real_build = kd.build_output_note

        def racing_build(*args, **kwargs):
            if not target.exists():
                target.write_text(
                    "---\ntopics: [무관토픽]\n---\n\n경쟁 프로세스가 먼저 쓴 문장.\n",
                    encoding="utf-8",
                )
            return real_build(*args, **kwargs)

        self.addCleanup(setattr, kd, "build_output_note", real_build)
        kd.build_output_note = racing_build

        success, fail, _, _ = self._run_batch()

        self.assertEqual((success, fail), (1, 0))
        text = target.read_text(encoding="utf-8")
        self.assertIn("경쟁 프로세스가 먼저 쓴 문장.", text, "생성 경합에서 기존 파일을 덮어썼다")
        self.assertIn("## 병합 추가", text)
        self._assert_raw_unchanged()

    def test_new_note_is_not_published_until_body_is_fully_written(self):
        """생성 경합 잔여분: 승자가 대상 경로를 만든 직후~본문 쓰기 완료 사이에 패자가
        병합해 넣어도, 승자의 본문 쓰기가 그 병합을 덮어써선 안 된다.

        구현이 대상 경로를 처음 건드리는 지점(구: target.open("x") / 현: os.link·os.rename)에
        패자의 완성 노트 쓰기를 주입한다. 미완성 노트를 대상 경로에 노출하지 않는 구현만 통과한다.
        """
        target = kd.determine_output_path("2026-04-18", self.raw_file)
        fired = []

        def loser_writes():
            if fired:
                return
            fired.append(True)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                "---\ntopics: [무관토픽]\n---\n\n패자가 먼저 완성해 둔 문장.\n",
                encoding="utf-8",
            )

        real_open, real_link, real_rename = Path.open, os.link, os.rename

        def racing_open(self, mode="r", *args, **kwargs):
            fh = real_open(self, mode, *args, **kwargs)
            if "x" in mode and Path(self) == target:
                loser_writes()   # 승자가 만든 빈 파일에 패자가 끼어드는 창
            return fh

        def racing_link(src, dst, *args, **kwargs):
            if Path(dst) == target:
                loser_writes()
            return real_link(src, dst, *args, **kwargs)

        def racing_rename(src, dst, *args, **kwargs):
            if Path(dst) == target:
                loser_writes()
            return real_rename(src, dst, *args, **kwargs)

        def _restore():
            Path.open, os.link, os.rename = real_open, real_link, real_rename

        self.addCleanup(_restore)
        Path.open, os.link, os.rename = racing_open, racing_link, racing_rename
        try:
            success, fail, _, _ = self._run_batch()
        finally:
            _restore()

        self.assertTrue(fired, "경합 주입이 실행되지 않았다 — 테스트 seam이 깨졌다")
        self.assertEqual((success, fail), (1, 0))
        text = target.read_text(encoding="utf-8")
        self.assertIn(
            "패자가 먼저 완성해 둔 문장.", text,
            "미완성 노트가 대상 경로에 노출돼 패자의 병합이 덮어써졌다",
        )
        self.assertIn("## 병합 추가", text)
        self._assert_raw_unchanged()

    def test_merge_adds_new_topic_even_when_body_has_nothing_new(self):
        """본문에 새로 추가할 게 없고 새 topic만 있는 병합도 frontmatter에 반영돼야 한다."""
        target = kd.OUTPUT_BASE / "기존노트.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            "---\ntopics: [t1]\n---\n\n- 이미 있는 인사이트\n", encoding="utf-8"
        )

        kd.merge_into_existing_note(
            target,
            {
                "topics": ["t1", "t2"],
                "insights": ["이미 있는 인사이트"],
                "related_knowledge": [],
                "tasks": [],
            },
            self.raw_file,
            source_conversation_id="cid",
        )

        text = target.read_text(encoding="utf-8")
        self.assertIn("topics: [t1, t2]", text, "새 topic이 frontmatter에 반영되지 않았다")
        self.assertNotIn("## 병합 추가", text, "본문 추가가 없는데 병합 블록이 생겼다")

    def test_sidecar_failure_is_not_counted_as_distill_failure(self):
        def _boom(*args, **kwargs):
            raise OSError("sidecar 쓰기 실패 (테스트)")

        self.addCleanup(setattr, kd, "append_processed_index", kd.append_processed_index)
        kd.append_processed_index = _boom

        success, fail, state, stats = self._run_batch()

        # 증류는 성공했다 — 실패로 집계하지 않는다.
        self.assertEqual((success, fail), (1, 0))
        self.assertEqual(stats["failed"], 0)
        self.assertEqual(stats["processed"], 1)

        # 노트는 디스크에 남아 있다.
        self.assertEqual(len(list((kd.OUTPUT_BASE / "2026-04").glob("*.md"))), 1)

        # state는 저장되지 않아야 다음 실행이 sidecar를 복구할 수 있다.
        self.assertNotIn(str(self.raw_file), state)
        # --retry 경로로도 복구 가능해야 한다.
        queued = json.loads(kd.RETRY_QUEUE.read_text(encoding="utf-8"))
        self.assertEqual([e["file"] for e in queued], [str(self.raw_file)])
        self._assert_raw_unchanged()

    def test_second_run_after_sidecar_failure_recovers_index_without_destroying_note(self):
        """sidecar 실패 → 재실행이 인덱스를 복구하되 기존 노트를 파괴하지 않는다.

        1차 실행에서 sidecar를 실패시키고, 사용자가 노트를 손으로 고친 뒤, 2차 실행이
        인덱스를 복구하면서 그 수정을 보존하는지 확인한다.
        """
        def _boom(*args, **kwargs):
            raise OSError("sidecar 쓰기 실패 (테스트)")

        real_append = kd.append_processed_index
        self.addCleanup(setattr, kd, "append_processed_index", real_append)

        # ── 1차 실행: sidecar 실패 ──
        kd.append_processed_index = _boom
        _, _, state, _ = self._run_batch()
        self.assertNotIn(str(self.raw_file), state)
        self.assertFalse(kd.PROCESSED_INDEX_FILE.exists())

        note = kd.determine_output_path("2026-04-18", self.raw_file)
        # 사용자가 노트를 손으로 고쳤다.
        with note.open("a", encoding="utf-8") as f:
            f.write("\n\n사용자가 1차 실행 후 손으로 추가한 문장.\n")

        # ── 2차 실행: sidecar 정상, 같은 state를 이어받는다 ──
        kd.append_processed_index = real_append
        success, fail, state, _ = self._run_batch(state=state)

        self.assertEqual((success, fail), (1, 0))

        # sidecar 인덱스가 복구됐다.
        entries = self._sidecar_entries()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["conversation_id"], "eb129928-3609-46d4-9dd6-406bd7af3b8d")

        # state도 이제 저장됐다 → 3차 실행은 스킵된다.
        self.assertEqual(state[str(self.raw_file)], kd.file_hash(self.raw_file))

        # 핵심: 사용자의 수정이 살아 있어야 한다 (덮어쓰기 금지).
        self.assertIn(
            "사용자가 1차 실행 후 손으로 추가한 문장.",
            note.read_text(encoding="utf-8"),
            "2차 실행이 기존 노트를 덮어써 사용자 수정을 파괴했다",
        )
        self._assert_raw_unchanged()


if __name__ == "__main__":
    unittest.main()
