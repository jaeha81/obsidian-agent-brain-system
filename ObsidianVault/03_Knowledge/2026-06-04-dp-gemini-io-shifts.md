---
type: knowledge-note
date: 2026-06-04
source: daily-plus
category: obsidian-queue
tags:
- '#area/ai_automation'
- '#status/active'
summary: Google I/O 발표 기반 Gemini 소비자 AI 변화 — JH 에이전트 시스템 호환성 추적 포인트
status: applied
applied_at: 2026-06-11
graph_cluster: daily-practice
---

# Gemini I/O Shifts to Watch

## 개요

Google I/O에서 발표된 Gemini 업데이트는 단순 답변 제공을 넘어 **consumer AI capability** 전반을 재편하는 방향으로 진화하고 있다. JH 에이전트 시스템에서 Gemini를 활용하거나 경쟁 포지션을 파악하는 데 필요한 핵심 변화를 정리한다.

## 주요 발표 내용

### 1. Gemini 2.0 Flash 범용화
- 속도/비용 대비 성능에서 GPT-4o Mini급 포지션
- Multimodal 입력 (이미지, 오디오, 비디오) 기본 지원
- **JH 관련**: 저비용 transcription 대안으로 검토 가능

### 2. Project Astra — 실시간 멀티모달 에이전트
- 카메라/화면을 실시간으로 보며 대화하는 에이전트
- 기억 지속성(persistent memory) 탑재
- **JH 관련**: Bucky의 메모리 레이어 설계 참고 포인트

### 3. Deep Research 기능 강화
- 수십 개 소스 자동 탐색 후 장문 보고서 생성
- Google 검색 인텍스 직접 연동
- **JH 관련**: Wishket 프로젝트 리서치 자동화 활용 가능성

### 4. Gemini in Workspace 확장
- Google Docs, Sheets, Gmail 내 에이전트 액션
- 이메일 초안 자동 작성, 미팅 노트 요약
- **JH 관련**: 현재 사용 중인 Google Drive 연동 개선 기회

## JH 에이전트 호환성 체크

| 항목 | 현재 JH 스택 | Gemini 대안 | 우선순위 |
|------|-------------|------------|---------|
| 텍스트 생성 | Claude Sonnet | Gemini 2.0 Flash | 낮음 |
| 음성 인식 | whisper.cpp | Gemini Audio | 검토 |
| 멀티모달 | 미사용 | Gemini 2.0 | 미래 |
| 검색 통합 | 없음 | Grounding API | 중간 |

## 다음 액션

- [ ] Gemini API 무료 티어 한도 확인 (JH 테스트용)
- [ ] Grounding API와 Bucky 검색 기능 연동 가능성 평가
- [ ] Model Routing 노트 업데이트: Gemini 옵션 추가 검토

## 참고

- 관련 노트: `project_model_routing.md`
- Google I/O 2026 발표 자료

## 관련 노트
- [[hubs/JH System]]
