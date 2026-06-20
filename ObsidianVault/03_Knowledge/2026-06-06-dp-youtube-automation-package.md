---
title: YouTube 자동화 패키지 매니페스트
date: 2026-06-06
source: daily-plus/2026-06-06.md (Card 5)
priority: P3
category: knowledge
status: distilled
tags:
- youtube
- automation
- tts
- zapier
- content
- daily-plus
- knowledge
- source/today_plus
- type/reference
- source/youtube
graph_cluster: daily-practice
---

# YouTube 자동화 패키지 매니페스트

> ChatGPT Pulse 2026-06-06 Card 5 증류 (P3 · knowledge-candidate)

## 목적

5개 스크립트 템플릿, 한국어 TTS 음성 3개, 숏폼 샘플 10개, 썸네일 5개, 자막 SRT 포함 패키지. Zapier/n8n 자동화 레시피와 원클릭 설치.

## 패키지 구성 목록

```
youtube-automation-package/
├── scripts/
│   ├── 01_intro_hook.md          ← 훅 스크립트 템플릿
│   ├── 02_problem_agitate.md     ← 문제 공감 템플릿
│   ├── 03_solution_reveal.md     ← 해결책 공개 템플릿
│   ├── 04_proof_demo.md          ← 증거/시연 템플릿
│   └── 05_cta_close.md           ← CTA 마무리 템플릿
├── voice/
│   ├── voice_01_professional.mp3 ← 전문적 남성 음성
│   ├── voice_02_friendly.mp3     ← 친근한 여성 음성
│   └── voice_03_energetic.mp3    ← 활기찬 중성 음성
├── shorts/
│   └── sample_01~10/             ← 숏폼 샘플 10개
├── thumbnails/
│   └── thumb_01~05.psd           ← 썸네일 템플릿 5개
├── subtitles/
│   └── template.srt              ← 자막 SRT 템플릿
├── automation/
│   ├── zapier_recipe.json        ← Zapier 자동화 레시피
│   └── n8n_workflow.json         ← n8n 워크플로우
└── install.sh                    ← 원클릭 설치 스크립트
```

## 설치 방법

```bash
# 원클릭 설치
curl -sSL https://example.com/youtube-pkg/install.sh | bash

# 또는 수동 설치
git clone https://github.com/jh/youtube-automation-package
cd youtube-automation-package
pip install -r requirements.txt
python setup.py --channel ProSuTech
```

## Zapier/n8n 자동화 레시피

### Zapier 워크플로우

```
트리거: Google Sheets 새 행 추가 (영상 아이디어)
    ↓
Step 1: Claude API로 스크립트 생성 (템플릿 기반)
    ↓
Step 2: TTS API로 음성 생성 (한국어)
    ↓
Step 3: 영상 편집 API (자막 합성)
    ↓
Step 4: YouTube API로 업로드 예약
    ↓
Step 5: Discord 알림 발송
```

### n8n 워크플로우 노드 구성

- `HTTP Request` → Claude API (스크립트)
- `HTTP Request` → ElevenLabs/Clova (TTS)
- `HTTP Request` → Creatomate (영상 합성)
- `HTTP Request` → YouTube Data API (업로드)
- `Discord` → 완료 알림

## 저작권 체크리스트

영상 게시 전 확인 필수:

- [ ] BGM: Creative Commons 또는 YouTube Audio Library
- [ ] 이미지/영상: Pexels, Pixabay, 또는 직접 촬영
- [ ] 폰트: 상업적 무료 폰트 (Noto Sans, Pretendard)
- [ ] TTS 음성: 상업적 이용 허가 확인
- [ ] 인용/클립: 저작권법 제28조 인용 요건 충족

## 수익화 위험 방지

- 경쟁사 로고/브랜드 직접 비교 자제
- 타 채널 영상 무단 클립 사용 금지
- 오해 소지 있는 제목/썸네일(낚시성) 금지
- 수익 예측 과장 주의 (FTC 가이드라인)

## 관련 컨텍스트

- [[prosutech-youtube-hooks]], [[video-distribution-pipeline]]
- [[landing-onboarding-checklist]]
