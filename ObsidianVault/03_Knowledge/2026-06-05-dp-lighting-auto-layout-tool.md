---
title: 조도 계산 자동배치 도구 구상
date: 2026-06-05
source: daily-plus/2026-06-05.md (Card 9)
priority: P2
category: knowledge
status: distilled
tags:
- lighting
- lux
- floor-plan
- ies
- interior-design
- daily-plus
- knowledge
graph_cluster: daily-practice
---

# 조도 계산 자동배치 도구 구상

> ChatGPT Pulse 2026-06-05 Card 9 증류 (P2 · knowledge-candidate)

## 목적

평면도 업로드 한 번으로 방 폴리곤 자동 추출→등기구 적용→격자 조도 계산→권장 수량·간격·배치안 산출하는 미니 앱 구상.

## UX 플로우

```
1. 평면도 업로드 (DXF / SVG / PNG)
        ↓
2. 방 폴리곤 자동 추출
   (ezdxf 레이어 분석 또는 컴퓨터 비전)
        ↓
3. 등기구 선택
   (IES 파일 라이브러리 또는 직접 입력)
        ↓
4. 격자 조도 계산 (룩스 맵 생성)
        ↓
5. 권장 배치안 산출
   (등기구 수량, 간격, 위치 좌표)
        ↓
6. 결과 출력 (PDF / JSON / CSV)
```

## 계산 엔진 설계

### 조도 계산 기본 공식

```python
# 룩스 계산 (역제곱 법칙 + IES 배광 데이터)
def calculate_lux(
    luminous_flux: float,   # 광속 (루멘)
    height: float,          # 등기구 높이 (m)
    cu: float = 0.6,        # 이용률 (Coefficient of Utilization)
    mf: float = 0.8,        # 보수율 (Maintenance Factor)
    area: float = 1.0       # 계산 면적 (m²)
) -> float:
    return (luminous_flux * cu * mf) / area

# 필요 등기구 수 계산
def required_fixtures(
    target_lux: int,    # 목표 조도 (룩스)
    room_area: float,   # 방 면적 (m²)
    lumens_per_fixture: int,
    cu: float = 0.6,
    mf: float = 0.8
) -> int:
    return math.ceil((target_lux * room_area) / (lumens_per_fixture * cu * mf))
```

### 공간별 권장 조도 기준 (KS A 3011)

| 공간 | 최소 조도 | 표준 조도 | 고급 조도 |
|-----|---------|---------|---------|
| 거실 | 150 lux | 300 lux | 600 lux |
| 주방 | 200 lux | 400 lux | 750 lux |
| 침실 | 50 lux | 150 lux | 300 lux |
| 사무실 | 300 lux | 500 lux | 750 lux |
| 복도 | 50 lux | 100 lux | 200 lux |

## IES 파일 처리

IES(Illuminating Engineering Society) 파일은 등기구의 3D 배광 데이터를 담고 있다.

```python
# IES 파일 파싱 (python-ies 라이브러리)
import ies

def load_fixture(ies_path: str) -> dict:
    data = ies.parse(ies_path)
    return {
        "total_lumens": data.total_lumens,
        "candela_distribution": data.candela,
        "beam_angle": data.beam_angle,
        "filename": ies_path
    }
```

**무료 IES 라이브러리**:
- IES Library (ies.lrc.rpi.edu)
- 삼성 LED, 오스람, 필립스 공개 IES

## 출력 포맷

### PDF 보고서
- 평면도 위 배치도 (등기구 위치 표시)
- 조도 등고선 맵 (히트맵)
- 자재 목록 (등기구 × 수량 × 단가)

### JSON (견적 연동용)
```json
{
  "room": "거실",
  "area_m2": 25.5,
  "target_lux": 300,
  "fixtures": [
    {"sku": "LED-DOWN-12W", "qty": 8, "x": 1.5, "y": 2.0}
  ],
  "estimated_cost": 240000
}
```

### CSV (표준 견적 연동)
- 견적 CSV 표준 형식 호환 (→ [[estimator-csv-standardization-kit]])

## 관련 컨텍스트

- 인테리어 견적 자동화 파이프라인 연계 가능
- [[ai-material-matching-prototype]], [[cad-estimate-4day-test-plan]]
