"""
조도 계산 모듈 — KS C 3011 기준
"""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Tuple

# KS C 3011 권장 조도 기준값 (lux)
KS_LUX: dict[str, int] = {
    "거실":   200,
    "침실":   150,
    "주방":   300,
    "욕실":   200,
    "복도":   100,
    "사무실": 500,
    "서재":   400,
}

ROOM_TYPES = list(KS_LUX.keys())


@dataclass
class RoomSpec:
    """방 사양"""
    name: str           # 방 이름 (사용자 지정)
    room_type: str      # 방 용도 (KS_LUX 키)
    width_m: float      # 가로 (m)
    height_m: float     # 세로 (m)
    ceiling_h: float    # 천장고 (m), 기본 2.4
    lumen: float        # 등기구 광속 (lm)
    uf: float = 0.6     # 조명률 (Utilization Factor)
    mf: float = 0.8     # 보수율 (Maintenance Factor)
    fixture_name: str = "LED 다운라이트"

    # 이미지 좌표 (픽셀) — 방 bbox
    px_x: int = 0
    px_y: int = 0
    px_w: int = 0
    px_h: int = 0

    @property
    def area(self) -> float:
        return self.width_m * self.height_m

    @property
    def target_lux(self) -> int:
        return KS_LUX.get(self.room_type, 200)

    @property
    def work_height(self) -> float:
        """작업면 높이: 천장고 - 작업면(0.85m)"""
        return max(self.ceiling_h - 0.85, 0.5)

    @property
    def max_spacing(self) -> float:
        """최대 등기구 간격: 1.5 × 작업면 높이"""
        return 1.5 * self.work_height


@dataclass
class LightingResult:
    """조도 계산 결과"""
    spec: RoomSpec
    n_fixtures: int           # 필요 등수
    grid_rows: int            # 배치 행 수
    grid_cols: int            # 배치 열 수
    spacing_x: float          # 실제 x 간격 (m)
    spacing_y: float          # 실제 y 간격 (m)
    achieved_lux: float       # 달성 조도 (lux)
    fixture_positions: list[Tuple[float, float]] = field(default_factory=list)
    # (m 단위 방 내부 좌표)

    @property
    def spacing_ok(self) -> bool:
        """간격 기준 만족 여부"""
        return (
            self.spacing_x <= self.spec.max_spacing
            and self.spacing_y <= self.spec.max_spacing
        )


def calculate_fixtures(spec: RoomSpec) -> LightingResult:
    """
    KS C 3011 기준 등기구 수량 및 배치 계산.

    N = (E × A) / (F × UF × MF)
    """
    e = spec.target_lux
    a = spec.area
    f = spec.lumen
    uf = spec.uf
    mf = spec.mf

    n_raw = (e * a) / (f * uf * mf)
    n_fixtures = max(1, math.ceil(n_raw))

    # 균등 격자 배치 — 가로세로 비율에 맞게 행/열 결정
    aspect = spec.width_m / max(spec.height_m, 0.01)
    cols_f = math.sqrt(n_fixtures * aspect)
    cols = max(1, round(cols_f))
    rows = max(1, math.ceil(n_fixtures / cols))

    # 실제 개수 보정 (rows × cols >= n_fixtures)
    while rows * cols < n_fixtures:
        cols += 1

    # 간격 계산 (벽에서 간격/2 떨어진 위치부터 배치)
    spacing_x = spec.width_m / cols
    spacing_y = spec.height_m / rows

    # 등기구 위치 생성 (m, 방 좌상단 기준)
    positions: list[Tuple[float, float]] = []
    for r in range(rows):
        for c in range(cols):
            if len(positions) >= n_fixtures:
                break
            x = spacing_x * (c + 0.5)
            y = spacing_y * (r + 0.5)
            positions.append((x, y))
        if len(positions) >= n_fixtures:
            break

    # 달성 조도 재계산 (실제 배치 수 기준)
    actual_n = len(positions)
    achieved_lux = (actual_n * f * uf * mf) / a if a > 0 else 0

    return LightingResult(
        spec=spec,
        n_fixtures=n_fixtures,
        grid_rows=rows,
        grid_cols=cols,
        spacing_x=spacing_x,
        spacing_y=spacing_y,
        achieved_lux=round(achieved_lux, 1),
        fixture_positions=positions,
    )


def build_summary_row(result: LightingResult) -> dict:
    """결과 테이블 행 생성"""
    spec = result.spec
    return {
        "방 이름":       spec.name,
        "용도":          spec.room_type,
        "면적 (m²)":     round(spec.area, 2),
        "목표 조도 (lux)": spec.target_lux,
        "달성 조도 (lux)": result.achieved_lux,
        "필요 등수":      result.n_fixtures,
        "배치 (행×열)":   f"{result.grid_rows}×{result.grid_cols}",
        "x 간격 (m)":    round(result.spacing_x, 2),
        "y 간격 (m)":    round(result.spacing_y, 2),
        "간격 기준":      "✔ 적합" if result.spacing_ok else "⚠ 초과",
        "등기구":         spec.fixture_name,
        "광속 (lm)":      spec.lumen,
    }
