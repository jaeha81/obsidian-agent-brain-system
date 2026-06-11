---
title: 탭 울트라 현장 STT 점검
date: 2026-06-01
source: daily-plus/2026-06-01.md (Card 8)
priority: P1
category: knowledge
status: distilled
tags:
  - stt
  - samsung-tablet
  - field
  - smoke-test
  - asr
  - daily-plus
  - knowledge
---

# 탭 울트라 현장 STT 점검

> Daily Plus Pulse 2026-06-01 Card 8 증류 (P1 · knowledge-candidate)

## 목적

에이전트 워크플로우에서 STT 신뢰도를 빠르게 점검하는 Galaxy Tab Ultra 전용 6단계 스모크 테스트. 1-2회 세션 안에 합격/불합격 판단.

## 사전 준비

| 항목 | 설정값 |
|------|-------|
| 기기 | Samsung Galaxy Tab S Ultra |
| Android | 14 이상 |
| STT 엔진 | Google STT 또는 삼성 Voice Input |
| 테스트 환경 | 실내 (배경 소음 40-60dB) / 실외 (60-75dB) |
| 마이크 거리 | 30-50cm |
| 녹음 포맷 | PCM 16kHz mono |

## 6단계 테스트 절차

### Step 1 — 기본 인식 확인

```
발화: "안녕하세요, 이 현장의 공사 진행상황을 보고합니다."
기대: 정확한 텍스트 변환
확인: WER ≤ 10%
```

### Step 2 — 건설 전문 용어 인식

```
발화: "목공, 전기배선, 설비배관, 도장 공정 완료."
기대: 공종명 정확 인식
확인: 공종명 4개 중 3개 이상 정확 (75%)
```

### Step 3 — 숫자/단위 인식

```
발화: "면적 85제곱미터, 단가 15만원, 수량 3개."
기대: 숫자·단위 정확 변환 (㎡, 원, 개)
확인: 숫자 오류 0건
```

### Step 4 — 배경 소음 내성

```
조건: 공구 소리 재생 (약 70dB)
발화: "현장 점검 결과 이상 없습니다."
기대: 소음 환경에서도 WER ≤ 20%
```

### Step 5 — 연속 발화

```
발화: 30초 이상 연속 현장 보고 (200자 이상)
기대: 중간 끊김 없이 연속 인식
확인: 누락 단어 ≤ 5%
```

### Step 6 — 재시작 내성

```
절차: 앱 강제 종료 → 재시작 → STT 즉시 사용
기대: 재시작 후 5초 이내 인식 준비 완료
확인: 첫 발화 WER ≤ 15%
```

## 합격 기준값

| 지표 | 합격 | 조건부 합격 | 불합격 |
|------|-----|-----------|------|
| 평균 WER | ≤ 10% | 10-20% | > 20% |
| 공종명 인식률 | ≥ 90% | 75-90% | < 75% |
| 숫자 오류 | 0건 | 1-2건 | ≥ 3건 |
| 소음 WER | ≤ 20% | 20-35% | > 35% |
| 연속 누락률 | ≤ 5% | 5-10% | > 10% |
| 재시작 준비 | ≤ 5초 | 5-15초 | > 15초 |

**종합 판단**: 6개 항목 중 5개 이상 합격 → PASS

## 실패 시 대응

| 실패 패턴 | 원인 추정 | 대응 |
|---------|---------|------|
| 전문 용어 오인식 | STT 모델 미학습 | 커스텀 단어 사전 등록 |
| 소음 WER 급등 | 마이크 지향성 부족 | 외장 마이크 연결 |
| 연속 발화 끊김 | 타임아웃 설정 | VAD 감도 조정 |
| 재시작 후 느림 | 캐시 미워밍 | 백그라운드 서비스 등록 |
| 숫자 오류 | 언어 모델 | Whisper API 폴백 적용 |

## WER 계산 방법

```python
def calculate_wer(reference: str, hypothesis: str) -> float:
    """Word Error Rate = (S + D + I) / N"""
    ref = reference.split()
    hyp = hypothesis.split()
    # 동적 프로그래밍으로 편집 거리 계산
    d = [[0] * (len(hyp) + 1) for _ in range(len(ref) + 1)]
    for i in range(len(ref) + 1): d[i][0] = i
    for j in range(len(hyp) + 1): d[0][j] = j
    for i in range(1, len(ref) + 1):
        for j in range(1, len(hyp) + 1):
            cost = 0 if ref[i-1] == hyp[j-1] else 1
            d[i][j] = min(d[i-1][j]+1, d[i][j-1]+1, d[i-1][j-1]+cost)
    return d[len(ref)][len(hyp)] / len(ref)
```

## 구현 우선순위

- [ ] 테스트 발화 스크립트 한국어 버전 준비
- [ ] WER 계산 스크립트 Galaxy Tab 설치
- [ ] 6단계 테스트 실행 (1-2세션)
- [ ] 결과 기록 및 합격 판단
- [ ] 불합격 항목 대응 조치

## 관련 컨텍스트

- 현장 음성 수집 에이전트 워크플로우 기반
- [[태블릿-배치-업로드-매니페스트]], [[현장-음성-프라이버시-체크리스트]]
