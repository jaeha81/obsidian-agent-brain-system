---
type: knowledge
source: gpt-memory
date: 2026-04-27
tags: [gpt, memory, tech-stack, automation, agent, make, fastapi, nextjs]
  - #status/archive
summary: "재하(Jaya)의 현재 기술 스택, Make.com 자동화 완성 워크플로우, 멀티에이전트 아키텍처"
---

# 기술 스택 및 시스템 구성

최종 업데이트: 2026-04-27

---

## 현재 사용 기술 스택

| 레이어 | 기술 / 도구 |
|--------|------------|
| **프론트엔드** | Next.js, PWA (Netlify 배포) |
| **백엔드** | FastAPI (Python) |
| **자동화** | Make.com (Webhook, HTTP, JSON, Google Sheets) |
| **AI API** | OpenRouter (GPT-4o), Claude, Gemini (교체 가능) |
| **배포** | Netlify (PWA), 추후 확장 예정 |
| **데이터** | Google Sheets (자동 기록), DB (API 라우팅 연동) |
| **개발 도구** | VS Code + Claude Code (확장), Cursor AI, OpenClaw, GPT |
| **버전 관리** | GitHub |

### AI 도구 활용 현황
- Claude Code (VS Code 확장) — 주 개발 실행 환경
- ChatGPT (AIMY) — 전체 계획 수립 + 실행 오케스트레이션
- Cursor AI — 보조 코드 편집
- OpenRouter — API 라우팅 (GPT-4o 등 모델 연결)

---

## Make.com 완성 자동화 워크플로우

> 2025-08-04 기준 정상 작동 확인

| 단계 | 모듈 | 기능 |
|------|------|------|
| 1 | Webhook | 트리거 수신 |
| 2 | Router | 경로 분기 |
| 3 | RSS (×5+) | 다중 RSS 피드 수집 |
| 4 | Array Aggregator | 피드 통합 |
| 5 | Iterator | 개별 뉴스 반복 처리 |
| 6 | HTTP 모듈 | OpenRouter (GPT-4o) 호출 → 트렌드 분석 |
| 7 | JSON Parse | 분석 결과 파싱 |
| 8 | Google Sheets | 결과 자동 기록 |

**유튜브 자동화 구조**
```
영상 제목 입력 → GPT → Make Webhook → 자동 설명/태그 생성 → 응답 반환
배포: Netlify PWA (dynamic-bavarois-1b3b93.netlify.app)
```

---

## 멀티에이전트 AI 아키텍처 구상 (NeuronGPT)

### 모듈형 에이전트 구조

```
[바디 (공통 인프라)]
├── 워크플로우 엔진
├── 데이터 흐름 관리
├── 로그 시스템
└── 보안 레이어

[팩 (교체 가능한 에이전트 헤드, 10개+)]
├── 각 에이전트: 역할/철학/말투 지침서로 정의
└── 웹앱에서 선택·전환 가능

[Supervisor 에이전트]
├── 전체 에이전트 모니터링
├── 오류 감지 및 피드백
├── DB 관리
└── 에이전트 간 지시 전달
```

### 역할 분리 원칙
- **재하**: 전체 계획 수립 + 실행 오케스트레이션 (단계 설계, 지시 프롬프트 생성, 검증 체크리스트)
- **에이전트**: 실제 코딩·구현 위임
- **모델 교체 가능**: GPT-4o, Claude, Gemini 등 API 단위로 교체

---

## 4대 핵심 운영 시스템

모든 개발·자동화·에이전트 운영의 기본 규칙:

| 시스템 | 역할 |
|--------|------|
| **자동 매뉴얼 시스템** | DB 관리 지침, 개발 매뉴얼을 모든 프로젝트에 일관 반영. 외주 개발에도 동일 기준 적용. |
| **작업 기억 시스템** | 세션 간 컨텍스트 유지. 이전 결정·상태를 다음 세션에서 복원. |
| **자동 품질 검사** | 구현 완료 후 자동 검증, 타입 체크, 오류 탐지 실행. |
| **전문 에이전트 체계** | 역할별 에이전트 분리 (Planner / Builder / Reviewer / Archivist). Supervisor가 전체 관리. |

---

## 웹앱 개발 기본 지침

- 모든 웹앱 개발 시 프론트엔드 + 백엔드 동시 고려
- 프로젝트 종류에 따라 최적 스택 자동 제안
- 그래픽 퀄리티: AI 기반 그래픽 개선 라이브러리 적극 활용
- 바이브 코딩: 웹앱 카테고리별 필요 엔진·라이브러리·보안 도구 자동 제안 (시장 변화 반영 업데이트)

---

## 관련 페이지

- [[gpt-memory-profile]] — 사용자 프로필 및 AI 협업 원칙
- [[gpt-memory-projects]] — 진행 중인 프로젝트 목록
