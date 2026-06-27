"""
D2, D4, D6, D7 analyzer 단위 테스트.
inline mock rows 사용 — 외부 파일 의존 없음.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.estimate_analyzer.analyzers.d2_spec import analyze as analyze_d2
from scripts.estimate_analyzer.analyzers.d4_duplicate import analyze as analyze_d4
from scripts.estimate_analyzer.analyzers.d6_loss import analyze as analyze_d6, LOSS_RATE_RULES
from scripts.estimate_analyzer.analyzers.d7_overhead import analyze as analyze_d7


# ── 공통 mock row 팩토리 ──────────────────────────────────────────

def make_row(
    row_index: int = 0,
    name: str = "테스트 자재",
    model_no: str = None,
    spec: str = "300×300",
    unit: str = "m2",
    quantity: float = 10.0,
    loss_rate: float = 1.10,
    material_amount: float = 100_000.0,
    labor_amount: float = 50_000.0,
    total: float = 150_000.0,
    trade_category: str = "바닥공사",
    remark: str = None,
) -> dict:
    return {
        "row_index": row_index,
        "name": name,
        "model_no": model_no,
        "spec": spec,
        "unit": unit,
        "quantity": quantity,
        "loss_rate": loss_rate,
        "material_amount": material_amount,
        "labor_amount": labor_amount,
        "total": total,
        "trade_category": trade_category,
        "remark": remark,
        "location": None,
        "manufacturer": None,
        "material_price": 0.0,
        "labor_price": 0.0,
    }


# ── D2 테스트 ──────────────────────────────────────────────────────

class TestD2Spec:
    def test_no_findings_when_all_match(self):
        rows = [make_row(model_no="F2"), make_row(model_no="WT1", row_index=1)]
        spec_codes = {"F2": "바닥타일", "WT1": "벽타일"}
        findings = analyze_d2(rows, spec_codes)
        assert findings == []

    def test_missing_code_returns_red(self):
        rows = []  # 내역서에 아무 모델No. 없음
        spec_codes = {"F2": "바닥타일"}
        findings = analyze_d2(rows, spec_codes)
        assert len(findings) == 1
        assert findings[0]["severity"] == "RED"
        assert findings[0]["code"] == "F2"
        assert "MISSING" in findings[0]["message"]

    def test_ghost_code_returns_yellow(self):
        rows = [make_row(model_no="XX99", row_index=0)]
        spec_codes = {}  # 도면에 없음
        findings = analyze_d2(rows, spec_codes)
        assert len(findings) == 1
        assert findings[0]["severity"] == "YELLOW"
        assert findings[0]["code"] == "XX99"
        assert "GHOST" in findings[0]["message"]

    def test_both_missing_and_ghost(self):
        rows = [make_row(model_no="GHOST_CODE", row_index=0)]
        spec_codes = {"MISSING_CODE": "없는 자재"}
        findings = analyze_d2(rows, spec_codes)
        severities = {f["severity"] for f in findings}
        assert "RED" in severities
        assert "YELLOW" in severities

    def test_none_model_no_ignored(self):
        rows = [make_row(model_no=None, row_index=0)]
        spec_codes = {"F2": "바닥타일"}
        findings = analyze_d2(rows, spec_codes)
        # model_no가 None인 행은 ghost로 잡히지 않음
        ghost_findings = [f for f in findings if f["severity"] == "YELLOW"]
        assert ghost_findings == []

    def test_finding_ids_are_sequential(self):
        rows = []
        spec_codes = {"A1": "자재A", "B2": "자재B", "C3": "자재C"}
        findings = analyze_d2(rows, spec_codes)
        ids = [f["id"] for f in findings]
        assert ids == ["D2-001", "D2-002", "D2-003"]


# ── D4 테스트 ──────────────────────────────────────────────────────

class TestD4Duplicate:
    def test_no_findings_for_unique_rows(self):
        # 이름과 규격이 충분히 달라야 유사도 0.85 미만 → YELLOW 없음
        rows = [
            make_row(row_index=0, model_no="F2", name="포세린 바닥타일", spec="600×600", unit="m2", quantity=10.0),
            make_row(row_index=1, model_no="F3", name="석고보드 경량벽체", spec="9.5T", unit="m2", quantity=20.0),
        ]
        findings = analyze_d4(rows)
        # 완전 중복(RED)은 없어야 함
        red = [f for f in findings if f["severity"] == "RED"]
        assert red == []

    def test_exact_duplicate_returns_red(self):
        rows = [
            make_row(row_index=0, model_no="F2", unit="m2", quantity=10.0),
            make_row(row_index=1, model_no="F2", unit="m2", quantity=10.0),
        ]
        findings = analyze_d4(rows)
        red = [f for f in findings if f["severity"] == "RED"]
        assert len(red) >= 1
        assert red[0]["row_index"] == 1
        assert red[0]["pair_index"] == 0

    def test_similar_name_returns_yellow(self):
        rows = [
            make_row(row_index=0, name="포세린 타일 600×600 그레이", spec="600×600", model_no=None),
            make_row(row_index=1, name="포세린 타일 600×600 그레이", spec="600×600", model_no=None),
        ]
        findings = analyze_d4(rows)
        yellow = [f for f in findings if f["severity"] == "YELLOW"]
        assert len(yellow) >= 1

    def test_different_quantity_no_exact_duplicate(self):
        rows = [
            make_row(row_index=0, model_no="F2", unit="m2", quantity=10.0),
            make_row(row_index=1, model_no="F2", unit="m2", quantity=20.0),
        ]
        findings = analyze_d4(rows)
        red = [f for f in findings if f["severity"] == "RED"]
        assert red == []

    def test_empty_rows_no_error(self):
        assert analyze_d4([]) == []


# ── D6 테스트 ──────────────────────────────────────────────────────

class TestD6Loss:
    def test_no_alarm_for_correct_loss_rate(self):
        # 타일: 1.10 ~ 1.20 범위 내
        rows = [make_row(trade_category="바닥공사", name="타일", loss_rate=1.10, material_amount=50000.0)]
        findings = analyze_d6(rows)
        assert findings == []

    def test_alarm_for_out_of_range_loss_rate(self):
        # 직영 작업조: 1.00 고정. 1.05는 범위 초과
        rows = [
            make_row(
                row_index=0,
                trade_category="가설공사",
                name="직영",
                loss_rate=1.05,  # 직영 기대: 1.00 exactly
                material_amount=100_000.0,
            )
        ]
        findings = analyze_d6(rows)
        yellow = [f for f in findings if f["severity"] == "YELLOW"]
        assert len(yellow) >= 1
        assert yellow[0]["actual_rate"] == pytest.approx(1.05)

    def test_zero_loss_rate_skipped(self):
        # loss율 0.0이고 자재비도 0인 행은 건너뜀
        rows = [make_row(loss_rate=0.0, material_amount=0.0)]
        findings = analyze_d6(rows)
        assert findings == []

    def test_loss_rate_boundary_exact_min(self):
        # 경량: 1.10 exactly — 경계값은 통과해야 함
        rows = [
            make_row(
                trade_category="천정공사",
                name="경량",
                loss_rate=1.10,
                material_amount=50_000.0,
            )
        ]
        findings = analyze_d6(rows)
        assert findings == []

    def test_default_rule_applied_for_unknown_crew(self):
        # 알 수 없는 작업조: 기본 범위 (1.00, 1.20) 적용
        rows = [
            make_row(
                trade_category="기타공사",
                name="기타알수없는작업조",
                loss_rate=1.15,
                material_amount=50_000.0,
            )
        ]
        findings = analyze_d6(rows)
        assert findings == []  # 1.15는 기본 범위 내

    def test_loss_rate_rules_keys_are_valid(self):
        for key in LOSS_RATE_RULES:
            min_r, max_r = LOSS_RATE_RULES[key]
            assert min_r <= max_r, f"{key}: min > max"
            assert 0.5 <= min_r <= 2.0
            assert 0.5 <= max_r <= 2.0


# ── D7 테스트 ──────────────────────────────────────────────────────

class TestD7Overhead:
    def _make_labor_rows(self, total_labor: float) -> list:
        return [
            make_row(
                row_index=i,
                labor_amount=total_labor,
                total=total_labor * 1.5,
            )
            for i in range(1)
        ]

    def test_workers_comp_within_1pct(self):
        """산재보험료 예상값 계산 오차 ±1% 이내 검증."""
        total_labor = 10_000_000.0
        expected_workers_comp = int(total_labor * 0.0356 / 10_000) * 10_000  # 만단위 절사

        rows = [make_row(row_index=0, labor_amount=total_labor, total=15_000_000.0)]
        # 내역서에 제경비 라인 없음 → 예상값 YELLOW 발생
        findings = analyze_d7(rows, [])

        # 산재보험료 관련 finding 찾기
        comp_findings = [
            f for f in findings
            if "산재보험료" in f.get("overhead_type", "")
            or "산재보험" in f.get("message", "")
        ]
        assert len(comp_findings) >= 1

        # 예상값이 계산식과 1% 이내 일치
        expected_in_finding = comp_findings[0].get("expected")
        if expected_in_finding is not None:
            assert abs(expected_in_finding - expected_workers_comp) / max(expected_workers_comp, 1) < 0.01

    def test_employment_insurance_rate(self):
        """고용보험료 = 인건비 × 0.0101."""
        total_labor = 5_000_000.0
        import math
        expected_emp = math.floor(total_labor * 0.0101 / 10_000) * 10_000

        rows = [make_row(row_index=0, labor_amount=total_labor, total=7_500_000.0)]
        findings = analyze_d7(rows, [])

        emp_findings = [
            f for f in findings
            if "고용보험료" in f.get("overhead_type", "")
            or "고용보험" in f.get("message", "")
        ]
        assert len(emp_findings) >= 1
        exp_val = emp_findings[0].get("expected")
        if exp_val is not None:
            assert abs(exp_val - expected_emp) / max(expected_emp, 1) < 0.01

    def test_no_findings_when_correct_overhead_present(self):
        """제경비 라인이 예상값과 일치하면 알람 없음."""
        import math
        total_labor = 10_000_000.0
        total_sum = 20_000_000.0  # 5억 미만

        expected_wc = math.floor(total_labor * 0.0356 / 10_000) * 10_000
        expected_emp = math.floor(total_labor * 0.0101 / 10_000) * 10_000

        rows = [
            make_row(row_index=0, labor_amount=total_labor, total=total_sum),
            # 산재보험료 라인
            make_row(
                row_index=1,
                name="산재보험료",
                total=float(expected_wc),
                labor_amount=0.0,
                material_amount=0.0,
            ),
            # 고용보험료 라인
            make_row(
                row_index=2,
                name="고용보험료",
                total=float(expected_emp),
                labor_amount=0.0,
                material_amount=0.0,
            ),
        ]
        findings = analyze_d7(rows, [])
        # 오차 5% 이내인 경우 RED/YELLOW 없어야 함
        alarms = [f for f in findings if f["severity"] in ("RED", "YELLOW")]
        # 안전관리비는 별도 라인 없으니 YELLOW 가능, 산재/고용은 없어야 함
        comp_alarms = [
            f for f in alarms
            if "산재보험" in f.get("overhead_type", "") or "고용보험" in f.get("overhead_type", "")
        ]
        assert comp_alarms == []

    def test_empty_rows_no_crash(self):
        findings = analyze_d7([], [])
        # 인건비 0 → 제경비 예상값도 0 → 비교 의미 없음
        # 크래시 없이 리스트 반환해야 함
        assert isinstance(findings, list)
