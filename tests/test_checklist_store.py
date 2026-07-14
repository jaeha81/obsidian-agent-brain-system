"""scripts/checklist_store.py 테스트 — 읽기 실패가 데이터 삭제로 번지지 않는지 검증.

핵심 회귀 가드: 2026-07-11 사고 재현.
discord_bot._cl_load()가 손상/부재한 정본을 만나면 빈 목록을 반환했고, 뒤이은
_cl_add() → _cl_save()가 그 빈 목록을 정본·미러 양쪽에 덮어써 태스크 75개가 1개로
소실됐다. 아래 test_손상된_정본으로_추가해도_기존_태스크가_사라지지_않는다 가 그 경로다.
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import checklist_crypto as crypto  # noqa: E402
import checklist_store as cs  # noqa: E402

PASSWORD = "테스트-비밀번호-1234"


def _sample(n: int = 3) -> dict:
    return {
        "meta": {"version": "2.0", "last_updated": "2026-07-01"},
        "tasks": [
            {"id": f"CL-{i:03d}", "title": f"할일 {i}", "status": "pending"}
            for i in range(1, n + 1)
        ],
    }


class ChecklistStoreTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        base = Path(self._tmp.name)
        self._orig = (cs.MASTER, cs.MIRROR)
        cs.MASTER = base / "data" / "user_checklist.json"
        cs.MIRROR = base / "docs" / "data" / "user_checklist.json"
        cs.MASTER.parent.mkdir(parents=True)
        cs.MIRROR.parent.mkdir(parents=True)

        self._prev_pw = os.environ.get("CHECKLIST_PASSWORD")
        os.environ["CHECKLIST_PASSWORD"] = PASSWORD

    def tearDown(self) -> None:
        cs.MASTER, cs.MIRROR = self._orig
        if self._prev_pw is None:
            os.environ.pop("CHECKLIST_PASSWORD", None)
        else:
            os.environ["CHECKLIST_PASSWORD"] = self._prev_pw
        self._tmp.cleanup()

    def _put(self, path: Path, data: dict) -> None:
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def _mirror(self) -> dict:
        """미러를 평문으로 되돌려 읽는다(미러는 암호문으로 저장된다)."""
        return crypto.decrypt_json(
            json.loads(cs.MIRROR.read_text(encoding="utf-8")), PASSWORD
        )

    # ── 정상 경로 ──────────────────────────────────────────────────────────

    def test_정본이_멀쩡하면_그대로_읽는다(self) -> None:
        self._put(cs.MASTER, _sample(3))
        self.assertEqual(len(cs.load()["tasks"]), 3)

    def test_저장하면_정본과_미러가_같은_내용이_된다(self) -> None:
        cs.save(_sample(2))
        master = json.loads(cs.MASTER.read_text(encoding="utf-8"))
        mirror = self._mirror()
        self.assertEqual(master, mirror)
        self.assertEqual(len(mirror["tasks"]), 2)

    def test_둘_다_없으면_진짜_첫실행이므로_빈_목록(self) -> None:
        self.assertEqual(cs.load()["tasks"], [])

    # ── 복구 경로 ──────────────────────────────────────────────────────────

    def test_정본이_없으면_미러에서_복구한다(self) -> None:
        self._put(cs.MIRROR, _sample(5))
        self.assertEqual(len(cs.load()["tasks"]), 5)
        self.assertTrue(cs.MASTER.exists(), "정본이 복원되지 않았다")
        self.assertEqual(len(json.loads(cs.MASTER.read_text(encoding="utf-8"))["tasks"]), 5)

    def test_정본이_깨졌으면_미러에서_복구한다(self) -> None:
        cs.MASTER.write_text("{ 깨진 JSON", encoding="utf-8")
        self._put(cs.MIRROR, _sample(4))
        self.assertEqual(len(cs.load()["tasks"]), 4)
        self.assertEqual(len(json.loads(cs.MASTER.read_text(encoding="utf-8"))["tasks"]), 4)

    def test_tasks_배열이_없는_정본은_손상으로_보고_복구한다(self) -> None:
        self._put(cs.MASTER, {"meta": {}})  # tasks 키 자체가 없음
        self._put(cs.MIRROR, _sample(6))
        self.assertEqual(len(cs.load()["tasks"]), 6)

    # ── 거부 경로 (여기서 조용히 빈 목록을 주면 데이터가 날아간다) ──────────

    def test_둘_다_깨졌으면_빈_목록_대신_예외를_던진다(self) -> None:
        cs.MASTER.write_text("{ 깨짐", encoding="utf-8")
        cs.MIRROR.write_text("{ 깨짐", encoding="utf-8")
        with self.assertRaises(cs.ChecklistUnavailable):
            cs.load()

    def test_정본이_깨졌고_미러가_없으면_예외를_던진다(self) -> None:
        cs.MASTER.write_text("{ 깨짐", encoding="utf-8")
        with self.assertRaises(cs.ChecklistUnavailable):
            cs.load()

    def test_tasks가_없는_데이터는_저장을_거부한다(self) -> None:
        with self.assertRaises(ValueError):
            cs.save({"meta": {}})

    # ── 2026-07-11 사고 회귀 가드 ──────────────────────────────────────────

    def test_손상된_정본으로_추가해도_기존_태스크가_사라지지_않는다(self) -> None:
        """봇이 손상된 정본을 만난 뒤 태스크를 추가하는, 사고 당시의 실제 경로."""
        self._put(cs.MIRROR, _sample(75))          # 미러에는 75개가 살아 있다
        cs.MASTER.write_text("", encoding="utf-8")  # 정본은 빈 파일로 손상

        data = cs.load()                            # 예전엔 여기서 빈 목록이 나왔다
        data["tasks"].append(
            {"id": "CL-076", "title": "새 할일", "status": "pending"}
        )
        cs.save(data)

        master = json.loads(cs.MASTER.read_text(encoding="utf-8"))
        mirror = self._mirror()
        self.assertEqual(len(master["tasks"]), 76, "기존 75개가 소실됐다")
        self.assertEqual(master, mirror)
        self.assertEqual(master["tasks"][0]["id"], "CL-001", "ID가 처음부터 재생성됐다")

    # ── 2026-07-14 공개 노출 회귀 가드 ─────────────────────────────────────
    # 미러는 GitHub Pages로 그대로 공개된다. 여기에 평문이 실리면 할 일 제목이
    # 인터넷에 새어나간다. 아래 두 테스트가 그 경로를 막는다.

    def test_미러에는_할일_제목이_평문으로_남지_않는다(self) -> None:
        cs.save(_sample(3))
        raw = cs.MIRROR.read_text(encoding="utf-8")
        self.assertNotIn("할일 1", raw, "미러에 제목이 평문으로 노출됐다")
        self.assertNotIn("CL-001", raw, "미러에 태스크 ID가 평문으로 노출됐다")
        self.assertTrue(json.loads(raw).get("encrypted"), "미러가 암호문이 아니다")

    def test_비밀번호가_없으면_저장하지_않고_멈춘다(self) -> None:
        """암호화할 수 없으면 정본도 건드리지 않는다 — 반쪽 상태를 만들지 않는다."""
        self._put(cs.MASTER, _sample(5))
        os.environ.pop("CHECKLIST_PASSWORD", None)
        orig_key, crypto.KEY_FILE = crypto.KEY_FILE, Path(self._tmp.name) / "없는키"
        try:
            with self.assertRaises(crypto.KeyUnavailable):
                cs.save(_sample(9))
        finally:
            crypto.KEY_FILE = orig_key

        # 정본이 9개짜리로 덮어써지지 않고 원래 5개 그대로여야 한다
        self.assertEqual(len(json.loads(cs.MASTER.read_text(encoding="utf-8"))["tasks"]), 5)
        self.assertFalse(cs.MIRROR.exists(), "미러가 반쪽으로 쓰였다")

    def test_암호문_미러에서도_정본을_복구한다(self) -> None:
        cs.MIRROR.write_text(
            crypto.encrypt_json(_sample(7), PASSWORD), encoding="utf-8"
        )
        self.assertEqual(len(cs.load()["tasks"]), 7)
        self.assertTrue(cs.MASTER.exists(), "정본이 복원되지 않았다")

    def test_비밀번호가_틀리면_빈_목록_대신_예외를_던진다(self) -> None:
        cs.MIRROR.write_text(
            crypto.encrypt_json(_sample(7), "다른-비밀번호"), encoding="utf-8"
        )
        with self.assertRaises(cs.ChecklistUnavailable):
            cs.load()


if __name__ == "__main__":
    unittest.main()
