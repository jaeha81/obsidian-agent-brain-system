---
title: 랜딩과 온보딩 체크리스트
date: 2026-06-06
source: daily-plus/2026-06-06.md (Card 6)
priority: P3
category: knowledge
status: distilled
tags:
- landing
- onboarding
- conversion
- oauth
- subscription
- daily-plus
- knowledge
- source/today_plus
- type/reference
graph_cluster: daily-practice
---

# 랜딩과 온보딩 체크리스트

> ChatGPT Pulse 2026-06-06 Card 6 증류 (P3 · knowledge-candidate)

## 목적

방문자→시험판→OAuth 연결→첫 영상→결제로 변환하는 단일 세션 온보딩. 구글 연동, 음성 선택, 요금제, 첫 영상 생성, 업로드 확인 5단계.

## 5단계 전환 흐름

```
[방문자 도착]
    ↓
Step 1: 랜딩 (가치 제안 + CTA)
    ↓
Step 2: OAuth 연결 (Google/YouTube)
    ↓
Step 3: 설정 (음성 선택 + 요금제)
    ↓
Step 4: 첫 영상 생성 (즉각 가치 경험)
    ↓
Step 5: 업로드 확인 + 결제 전환
```

## 단계별 상세

### Step 1 — 랜딩

**버튼 텍스트**: "무료로 시작하기 →" (7초 이내 가치 전달)

핵심 메시지 (히어로 섹션):
- 헤드라인: "AI가 대신 만드는 유튜브 영상"
- 서브: "스크립트→음성→영상→업로드까지 5분"
- 소셜 증명: "이미 000명이 사용 중"

### Step 2 — OAuth 연결

```python
# Google OAuth 2.0 (YouTube 업로드 권한 포함)
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "openid",
    "email",
    "profile"
]

# 버튼 텍스트: "Google 계정으로 연결"
# 안내 문구: "YouTube 채널에 영상을 자동 업로드하기 위해 필요합니다"
```

### Step 3 — 설정 (음성 + 요금제)

**음성 선택 UI**:
- 3가지 샘플 재생 버튼 (각 5초)
- 선택 후 즉시 미리듣기

**요금제**:
- 무료: 영상 3개/월
- 스타터 ₩29,000/월: 영상 30개/월
- 프로 ₩79,000/월: 무제한 + 우선 처리

### Step 4 — 첫 영상 생성

```
입력: 주제 한 줄 (예: "인테리어 견적 자동화 AI 소개")
    ↓
AI 스크립트 생성 (30초)
    ↓
TTS 음성 합성 (30초)
    ↓
영상 자동 편집 (60초)
    ↓
미리보기 표시
```

**목표 생성 시간**: 총 2분 이내

### Step 5 — 업로드 확인 + 결제

- 업로드 버튼 클릭 시 YouTube에 즉시 게시
- 성공 화면: "첫 영상이 업로드되었습니다!" + 채널 링크
- 결제 CTA: "무료 크레딧 소진 전에 업그레이드"

## 자동 이메일 템플릿

### 웰컴 이메일 (Step 2 완료 후)

```
제목: [ProSuTech] 채널 연결 완료! 첫 영상을 만들어보세요

안녕하세요 {name}님,

YouTube 채널이 성공적으로 연결되었습니다.
지금 바로 첫 AI 영상을 만들어보세요.

[첫 영상 만들기 →]

무료 크레딧 3개가 제공됩니다.
```

### STT 검토 승인 게이트 이메일

```
제목: [검토 필요] 영상 "{title}" 업로드 대기 중

생성된 영상의 자막을 검토하고 승인해주세요.
부정확한 발음이나 오탈자가 있을 수 있습니다.

[검토 및 승인 →]   [수정하기]

24시간 내 미승인 시 자동 취소됩니다.
```

## STT 검토 승인 게이트

음성 합성 후 업로드 전 검수 단계:

- 자동 생성된 자막(SRT) 표시
- 수정 가능한 텍스트 에디터
- "승인 후 업로드" / "다시 생성" 버튼
- 최대 대기 시간: 24시간 (초과 시 자동 취소)

## 관련 컨텍스트

- [[youtube-automation-package]], [[video-distribution-pipeline]]
- [[prosutech-youtube-hooks]]
