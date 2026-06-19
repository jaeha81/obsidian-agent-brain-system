---
title: JH AI SKU Blueprint — 음성 입력 에이전트 패키지 설계
date: 2026-06-11
source: daily-plus/2026-06-10.md (Card 6)
priority: P3
category: knowledge
status: distilled
tags:
- sku
- voice-pipeline
- stt
- obsidian
- agent
- daily-plus
- knowledge
graph_cluster: daily-practice
---

# JH AI SKU Blueprint

> ChatGPT Pulse 2026-06-10 Card 6 증류 (P3 · voice-pipeline)

## 목적

음성 입력 에이전트 시스템을 3단계 SKU(초급/중급/고급)로 패키지화하여 설치와 사용이 즉시 가능한 스타터 키트 설계.

## SKU 구조

각 SKU는 **다운로드 가능한 스타터 키트**로 구성:
- Obsidian 볼트 템플릿
- 원클릭 설치 프로그램
- 샘플 데이터
- manifest.json

### Beginner SKU

| 항목 | 내용 |
|-----|-----|
| STT 엔진 | VOSK (온디바이스, ~50MB) |
| 설치 | pip install vosk |
| 언어 | 한국어 모델 선택 가능 |
| 특징 | 인터넷 없이 작동, 개인정보 보호 |
| 적합 | 현장 음성 메모, 오프라인 환경 |

### Intermediate SKU

| 항목 | 내용 |
|-----|-----|
| STT 엔진 | whisper.cpp + 클라우드 폴백 |
| 로컬 | Whisper small/medium 모델 |
| 클라우드 폴백 | CLOVA Speech API |
| 특징 | 높은 정확도, 다국어 |
| 적합 | 팀 협업, 상시 연결 환경 |

### Advanced SKU

| 항목 | 내용 |
|-----|-----|
| STT 엔진 | 프로덕션 등급 (다중 제공자) |
| 결제 | Toss Payments 샌드박스 연동 |
| 특징 | 여러 결제 게이트웨이, 고가용성 |
| 적합 | 상업 서비스 운영 |

## 공통 manifest.json 구조

```json
{
  "name": "JH AI Voice Kit",
  "version": "1.0.0",
  "sku": "beginner",
  "stt": {"engine": "vosk", "model": "vosk-model-small-ko-0.22"},
  "vault": "ObsidianVault/",
  "output": {"format": "markdown", "folder": "00_Inbox"},
  "fields": {
    "sensitive_mask": true,
    "timestamp": true
  }
}
```

## Obsidian 연동

음성 → STT → 마크다운 변환 → `00_Inbox` 자동 저장

```
[음성 입력]
     ↓
[STT 엔진]
     ↓
[필드 마스킹 (민감 정보)]
     ↓
[Obsidian 노트 생성]
```

## 구현 우선순위

- [ ] Beginner SKU VOSK 파이프라인 (현장 우선)
- [ ] manifest.json 스키마 표준화
- [ ] Obsidian 자동 저장 훅

## 관련 컨텍스트

- [[voice-pipeline-approval-pending]] 기존 설계 연동
- [[typeless-voice-stt-analysis]] 기존 분석 참고
