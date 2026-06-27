"""
SPC 표준 양식(2024) 파서 기본 동작 테스트.
실제 파일 없이 파서 로직과 헬퍼 함수를 단위 검증한다.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# 패키지 루트를 sys.path에 추가
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.estimate_analyzer.parsers.spc_2024 import (
    SPCEstimateParser,
    _safe_float,
    _clean_model_no,
)


# ── _safe_float 테스트 ──────────────────────────────────────────────

class TestSafeFloat:
    def test_int_value(self):
        assert _safe_float(1000) == 1000.0

    def test_float_value(self):
        assert _safe_float(3.14) == pytest.approx(3.14)

    def test_string_with_comma(self):
        assert _safe_float("1,234,567") == pytest.approx(1234567.0)

    def test_empty_string(self):
        assert _safe_float("") == 0.0

    def test_none(self):
        assert _safe_float(None) == 0.0

    def test_non_numeric_string(self):
        assert _safe_float("N/A") == 0.0

    def test_zero_string(self):
        assert _safe_float("0") == 0.0


# ── _clean_model_no 테스트 ─────────────────────────────────────────

class TestCleanModelNo:
    def test_strips_whitespace(self):
        assert _clean_model_no("  F2  ") == "F2"

    def test_none_returns_none(self):
        assert _clean_model_no(None) is None

    def test_empty_string_returns_none(self):
        assert _clean_model_no("") is None

    def test_whitespace_only_returns_none(self):
        assert _clean_model_no("   ") is None

    def test_valid_code(self):
        assert _clean_model_no("WT1") == "WT1"

    def test_numeric_code(self):
        assert _clean_model_no(123) == "123"


# ── SPCEstimateParser.parse 파일 없음 처리 ────────────────────────

class TestSPCEstimateParserFileNotFound:
    def test_raises_file_not_found(self):
        parser = SPCEstimateParser()
        with pytest.raises(FileNotFoundError):
            parser.parse("non_existent_file.xlsx")

    def test_unsupported_extension(self, tmp_path):
        # 임시 파일 생성 (csv는 지원 안 함)
        fake = tmp_path / "test.csv"
        fake.write_text("a,b,c")
        parser = SPCEstimateParser()
        with pytest.raises(ValueError, match="지원하지 않는 파일 형식"):
            parser.parse(str(fake))


# ── 실제 xlsx 파일 기반 통합 테스트 (fixture 없으면 skip) ──────────

FIXTURE_XLSX = (
    Path(__file__).parent / "fixtures" / "mock_spc2024.xlsx"
)


@pytest.mark.skipif(
    not FIXTURE_XLSX.exists(),
    reason="mock fixture 파일 없음 (fixtures/mock_spc2024.xlsx)",
)
class TestSPCParserWithFixture:
    def test_parse_returns_required_keys(self):
        parser = SPCEstimateParser()
        result = parser.parse(str(FIXTURE_XLSX))
        assert "project_name" in result
        assert "rows" in result
        assert "rows_direct" in result
        assert "summary" in result

    def test_summary_values_are_floats(self):
        parser = SPCEstimateParser()
        result = parser.parse(str(FIXTURE_XLSX))
        s = result["summary"]
        assert isinstance(s["total_material"], float)
        assert isinstance(s["total_labor"], float)
        assert isinstance(s["total_sum"], float)

    def test_rows_have_required_fields(self):
        parser = SPCEstimateParser()
        result = parser.parse(str(FIXTURE_XLSX))
        for row in result["rows"]:
            assert "row_index" in row
            assert "trade_category" in row
            assert "quantity" in row
            assert isinstance(row["quantity"], float)
            assert isinstance(row["material_amount"], float)
            assert isinstance(row["labor_amount"], float)
            assert isinstance(row["total"], float)
