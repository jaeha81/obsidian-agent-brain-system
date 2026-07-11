"""scripts/core/registry.py Stage 16 테스트 — 분류 축 로드·검증·조회.

작업 정본은 오라클 큐 — 레지스트리는 분류 축만 (P0-3).
로드는 crash 금지: 파일 없음·파싱 실패 → 빈 레지스트리.
"""

import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from core.registry import (  # noqa: E402
    PROJECTS_PATH,
    STATUSES,
    get_project,
    load_projects,
    validate_registry,
)


def _write(tmp: str, name: str, text: str, bom: bool = False) -> Path:
    p = Path(tmp) / name
    p.write_bytes(text.encode("utf-8-sig" if bom else "utf-8"))
    return p


VALID = (
    "projects:\n"
    "  - {id: a, title: T1, status: active, parent_goal: g1}\n"
    "  - {id: b, title: T2, status: done, parent_goal: ''}\n"
)


class LoadProjectsTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = self._tmp.name

    def test_load_valid(self):
        p = _write(self.tmp, "projects.yaml", VALID)
        projects = load_projects(p)
        self.assertEqual(set(projects), {"a", "b"})
        self.assertEqual(projects["a"]["title"], "T1")

    def test_missing_file_returns_empty(self):
        self.assertEqual(load_projects(Path(self.tmp) / "none.yaml"), {})

    def test_malformed_yaml_returns_empty(self):
        p = _write(self.tmp, "broken.yaml", "projects: [unclosed\n  - {")
        self.assertEqual(load_projects(p), {})

    def test_non_list_projects_returns_empty(self):
        p = _write(self.tmp, "scalar.yaml", "projects: not-a-list\n")
        self.assertEqual(load_projects(p), {})

    def test_bom_file_loads(self):
        p = _write(self.tmp, "bom.yaml", VALID, bom=True)
        self.assertEqual(set(load_projects(p)), {"a", "b"})

    def test_duplicate_id_keeps_first(self):
        p = _write(
            self.tmp,
            "dup.yaml",
            "projects:\n  - {id: a, title: First, status: active}\n  - {id: a, title: Second, status: active}\n",
        )
        self.assertEqual(load_projects(p)["a"]["title"], "First")


class GetProjectTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = _write(self._tmp.name, "projects.yaml", VALID)

    def test_known_id(self):
        self.assertEqual(get_project("a", self.path)["title"], "T1")

    def test_unknown_id_returns_none(self):
        self.assertIsNone(get_project("nope", self.path))

    def test_none_and_empty_id_return_none(self):
        self.assertIsNone(get_project("", self.path))
        self.assertIsNone(get_project(None, self.path))  # type: ignore[arg-type]


class ValidateRegistryTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = self._tmp.name

    def test_valid_registry_no_errors(self):
        p = _write(self.tmp, "ok.yaml", VALID)
        self.assertEqual(validate_registry(p), [])

    def test_missing_file_reports_error(self):
        self.assertTrue(validate_registry(Path(self.tmp) / "none.yaml"))

    def test_duplicate_id_detected(self):
        p = _write(
            self.tmp,
            "dup.yaml",
            "projects:\n  - {id: a, title: T, status: active}\n  - {id: a, title: T, status: active}\n",
        )
        self.assertTrue(any("중복" in e for e in validate_registry(p)))

    def test_missing_id_and_title_detected(self):
        p = _write(self.tmp, "miss.yaml", "projects:\n  - {status: active}\n")
        errors = validate_registry(p)
        self.assertTrue(any("id 필수" in e for e in errors))
        self.assertTrue(any("title 필수" in e for e in errors))

    def test_bad_status_detected(self):
        p = _write(self.tmp, "bad.yaml", "projects:\n  - {id: a, title: T, status: nope}\n")
        self.assertTrue(any("status" in e for e in validate_registry(p)))

    def test_non_dict_item_detected(self):
        p = _write(self.tmp, "item.yaml", "projects:\n  - just-a-string\n")
        self.assertTrue(any("객체가 아님" in e for e in validate_registry(p)))

    def test_non_string_parent_goal_detected(self):
        p = _write(self.tmp, "pg.yaml", "projects:\n  - {id: a, title: T, status: active, parent_goal: [x]}\n")
        self.assertTrue(any("parent_goal" in e for e in validate_registry(p)))


class ShippedRegistryTests(unittest.TestCase):
    """저장소에 커밋된 실등록부는 항상 유효해야 한다 (사람 편집 파일 회귀 가드)."""

    def test_shipped_file_exists(self):
        self.assertTrue(PROJECTS_PATH.is_file(), PROJECTS_PATH)

    def test_shipped_file_valid(self):
        self.assertEqual(validate_registry(), [])

    def test_shipped_statuses_are_known(self):
        for pid, p in load_projects().items():
            self.assertIn(p.get("status"), STATUSES, pid)


if __name__ == "__main__":
    unittest.main()
