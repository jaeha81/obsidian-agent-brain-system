---
title: PlanSwift QC 파일럿 테스트 계획
date: 2026-06-06
source: daily-plus/2026-06-06.md (Card 1)
priority: P1
category: knowledge
status: distilled
tags:
  - planswift
  - qc
  - pilot
  - dxf
  - pdf-scan
  - daily-plus
  - knowledge
---

# PlanSwift QC 파일럿 테스트 계획

> ChatGPT Pulse 2026-06-06 Card 1 증류 (P1 · knowledge-candidate)

## 목적

PlanSwift 도면→추출→견적 파이프라인 검증. 벡터 DWG부터 스캔 PDF까지 12가지 샘플 2-4일 내 실행. 합격 기준: 텍스트 추출 90%+, 측정 오차 3%-이하, 신뢰도 0.82+.

## 테스트 매트릭스

12가지 샘플 도면 유형:

| # | 도면 유형 | 파일 형식 | 기대 난이도 |
|---|---------|---------|-----------|
| 1 | 단순 평면도 (아파트) | DWG | 낮음 |
| 2 | 단순 평면도 (아파트) | DXF | 낮음 |
| 3 | 복잡 평면도 (상업공간) | DWG | 중간 |
| 4 | 복잡 평면도 (상업공간) | DXF | 중간 |
| 5 | 설비 도면 | DWG | 높음 |
| 6 | 전기 도면 | DXF | 높음 |
| 7 | 고품질 벡터 PDF | PDF | 중간 |
| 8 | 저품질 스캔 PDF | PDF (스캔) | 높음 |
| 9 | 기울어진 스캔 PDF | PDF (기울어짐) | 매우 높음 |
| 10 | 다국어 텍스트 도면 | DWG | 중간 |
| 11 | 손글씨 주석 포함 | PDF (스캔) | 매우 높음 |
| 12 | BIM 내보내기 | DXF (IFC 변환) | 중간 |

## 합격 기준값

| 지표 | 합격 | 우수 | 불합격 |
|-----|-----|-----|------|
| 텍스트 추출률 | ≥ 90% | ≥ 95% | < 90% |
| 측정 오차 (MAPE) | ≤ 3% | ≤ 1% | > 3% |
| 신뢰도 점수 | ≥ 0.82 | ≥ 0.90 | < 0.82 |
| 처리 시간 (A2 기준) | ≤ 90초 | ≤ 30초 | > 90초 |

## 음성 리뷰 자동 전사 활용

현장 엔지니어가 도면 검토 시 음성으로 피드백을 남기는 경우, 자동 전사로 QC 노트 생성:

```python
# Whisper 기반 음성 전사
import whisper

model = whisper.load_model("base")

def transcribe_review(audio_path: str) -> str:
    result = model.transcribe(audio_path, language="ko")
    return result["text"]

# 전사 결과를 QC 노트에 자동 첨부
def attach_voice_note(drawing_id: str, audio_path: str):
    note = transcribe_review(audio_path)
    qc_db.update(drawing_id, voice_note=note)
```

## QC 실패 대응

| 실패 케이스 | 1차 대응 | 2차 대응 |
|-----------|---------|---------|
| 텍스트 추출 < 90% | OCR 전처리 강화 (deskew, binarize) | Vision model 폴백 |
| 측정 오차 > 3% | 스케일 재보정 | 수동 측정 포인트 지정 |
| 신뢰도 < 0.82 | 낮은 신뢰도 항목 수동 검토 대기열 | 재추출 요청 |
| 처리 시간 초과 | 병렬 처리, 청크 분할 | 클라우드 GPU 사용 |

## 2~4일 실행 계획

| 일차 | 작업 |
|-----|-----|
| Day 1 | 샘플 1~4 (DWG/DXF 벡터) 테스트, 기준치 확인 |
| Day 2 | 샘플 5~8 (설비/전기/PDF 벡터) 테스트 |
| Day 3 | 샘플 9~12 (스캔 PDF/BIM) 테스트, 실패 케이스 분석 |
| Day 4 | 폴백 로직 구현, 파이프라인 최종 정리 |

## 관련 컨텍스트

- [[cad-estimate-4day-test-plan]], [[planswift-invoice-mapping]]
- [[planswift-open-tools-comparison]]
