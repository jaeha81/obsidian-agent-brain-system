---
title: 평면도 조도 산출 구현서
date: 2026-05-29
source: daily-plus/2026-05-29.md (Card 10)
priority: P1
category: knowledge
status: distilled
tags:
- lighting
- floor-plan
- lux
- dxf
- interior
- calculation
- daily-plus
- knowledge
graph_cluster: daily-practice
---

# 평면도 조도 산출 구현서

> ChatGPT Pulse 2026-05-29 Card 10 증류 (P1 · knowledge)

## 목적
평면도(2D)에서 방/장애물/설치 후보점을 추출→광도분포(IES/Eulumdat)로 조도 계산→등기구 배치/지표 요약(JSON 출력)하는 구현서. 인테리어 및 건설 프로젝트의 조도 계획을 자동화해 견적 및 설계 품질을 향상.

## 핵심 내용
- **DXF 입력 처리**:
  ```python
  import ezdxf
  doc = ezdxf.readfile("floor_plan.dxf")
  msp = doc.modelspace()
  # 방 경계: LWPOLYLINE 레이어에서 추출
  rooms = [entity for entity in msp.query('LWPOLYLINE') 
           if entity.dxf.layer == 'ROOMS']
  ```
- **조도 계산식**:
  ```
  조도(Lux) = 루멘(lm) × CU × LLF / 면적(m²)
  
  CU (Coefficient of Utilization): 등기구 배광 + 반사율 기반 (0.4~0.8)
  LLF (Light Loss Factor): 기준값 0.8 (감광, 먼지 등 손실)
  
  예: 100m² 사무실, 3000lm 등기구 10개, CU=0.6, LLF=0.8
  조도 = (3000 × 10 × 0.6 × 0.8) / 100 = 144 Lux
  ```
- **JSON 출력 스키마**:
  ```json
  {
    "room_id": "LR-001",
    "area_m2": 100.0,
    "target_lux": 300,
    "calculated_lux": 144,
    "fixtures": [
      {"id": "F001", "x": 2.5, "y": 3.0, "lumens": 3000, "model": "LED-PL-001"}
    ],
    "status": "insufficient",
    "required_fixtures": 21
  }
  ```
- **IES/Eulumdat 광도 분포**: 등기구 제조사 제공 파일로 정확한 배광 시뮬레이션 가능

## 구현 체크리스트
- [ ] ezdxf 라이브러리 설치 및 DXF 파싱 테스트
- [ ] 방 경계 추출 함수 구현 (레이어명 규칙 정의)
- [ ] 조도 계산 함수 구현 (CU, LLF 파라미터화)
- [ ] JSON 출력 스키마 검증
- [ ] 샘플 평면도로 전체 파이프라인 테스트

## 관련 컨텍스트
- JH 건설/인테리어 견적 스킬: `jh-estimate` skill
- 파주권 번들 10일 파일럿: `2026-05-29-dp-paju-bundle-10day-pilot.md`
- CAD to estimate PoC: `2026-06-11-dp-cad-to-estimate-poc.md` (연관 신규 작업)
