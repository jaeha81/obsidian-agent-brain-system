---
title: "옵시디언과 헤르메스 AI로 슈퍼 UX 디자인 에이전트 만들기"
source: "https://youtu.be/nmlYSLmmRBg?si=NH0fbp-oHZwjIsAy"
source_type: youtube
channel: "유훈식 교수 : AI4UX"
publish_date: "20260609"
date: 2026-06-10
captured_at: 2026-06-10T00:00:00+09:00
tags:
  - youtube
  - knowledge
  - bucky
  - ux
  - hermes-agent
  - obsidian
  - markdown
status: knowledge
has_transcript: true
transcript_source: "YouTube ko automatic captions via timedtext metadata"
verification:
  - "watch extracted 40 frames from 38:47 video"
  - "YouTube caption download initially hit 429; ko json3 caption was recovered from saved metadata URL"
  - "OpenAI Whisper fallback hit insufficient_quota 429 and was not used"
---

# 옵시디언과 헤르메스 AI로 슈퍼 UX 디자인 에이전트 만들기

![thumbnail](https://i.ytimg.com/vi/nmlYSLmmRBg/maxresdefault.jpg)

## Source

- YouTube: https://youtu.be/nmlYSLmmRBg?si=NH0fbp-oHZwjIsAy
- Title: 옵시디언과 헤르메스 AI로 '슈퍼 UX 디자인 에이전트' 만들기
- Channel: 유훈식 교수 : AI4UX
- Duration: 38:47
- Captured: 2026-06-10 KST

## 핵심 요약

이 영상의 핵심은 "AI 에이전트는 도구 설치만으로 강해지는 것이 아니라, 에이전트가 읽고 연결하고 재사용할 수 있는 마크다운 기반 LLM Wiki가 있어야 전문 업무를 지속적으로 수행한다"는 점이다. 발표자는 Hermes Agent, OpenClow, Gemini Spark를 자율형 개인 에이전트 계열로 묶어 설명하고, UX/UI 디자인 업무에서는 Obsidian 기반 지식 구조와 Hermes Agent를 연결해 리서치, 인터뷰 계획, 분석, 페르소나, PRD, 웹페이지 생성, 평가까지 하나의 작업 흐름으로 위임하는 방식을 제시한다.

## Bucky Agent에 전달할 지식

### 1. 에이전트는 "직원", 모델은 "두뇌"로 분리해서 봐야 한다

- Hermes Agent, OpenClow, Gemini Spark는 모두 사용자의 업무를 수행하는 자율형 에이전트 계열로 설명된다.
- 에이전트 자체는 업무 실행 환경이고, 실제 추론 성능은 연결한 LLM 모델에 따라 달라진다.
- Hermes/OpenClow는 로컬 PC 중심으로 동작하고, Gemini Spark는 Google 클라우드/Drive/Gmail/Sheets 생태계와 결합되는 방향으로 설명된다.
- Bucky 관점에서는 "어떤 모델을 쓰는가"보다 "에이전트가 어떤 저장소, 규칙, 기술 파일, 업무 히스토리를 참조하는가"가 장기 성능의 핵심이다.

### 2. Hermes Agent의 차별점은 자기 진화형 업무 히스토리

- 발표자는 Hermes Agent를 OpenClow보다 "자기 진화형 에이전트"에 더 특화된 것으로 설명한다.
- 일반 채팅은 세션이 끝나면 결과만 남고 과정/히스토리가 약하게 남는다.
- Hermes 계열 구조는 업무 과정, 산출물, 기술 파일을 계속 쌓아 에이전트가 점점 더 잘 일하게 만드는 방향에 가깝다.
- Bucky 적용 포인트: 단발성 답변이 아니라 `작업 요청 -> 산출물 저장 -> 평가 -> 다음 작업에 재사용` 루프를 Vault 안에 명시적으로 남겨야 한다.

### 3. AI 시대의 세컨드 브레인은 "사람 기억 저장소"가 아니라 "에이전트 업무 인수인계서"

- 기존 세컨드 브레인은 사람이 기억 부담을 줄이기 위한 저장소 성격이 강했다.
- AI 에이전트 시대에는 세컨드 브레인이 에이전트에게 업무 맥락, 철학, 판단 기준, 기술 절차를 전달하는 인수인계 자산이 된다.
- 단순 데이터 저장보다 중요한 것은 에이전트가 바로 실행 가능한 형태로 정리된 노드, 규칙, 예시, 체크리스트, 평가 기준이다.
- Bucky 적용 포인트: Vault 지식은 "사람이 나중에 읽는 문서"보다 "에이전트가 다음 작업에서 바로 참조할 수 있는 operating memory"로 작성해야 한다.

### 4. 마크다운은 AI 업무 효율을 높이는 기본 포맷

- 발표자는 HTML 등 장식/태그가 많은 문서보다 마크다운이 AI에게 더 효율적이라고 설명한다.
- 마크다운은 구조, 제목, 목록, 링크, 표를 유지하면서 불필요한 스타일 정보를 줄인다.
- Obsidian의 링크/노드 구조는 LLM이 관련 자료를 추적하고 필요한 파일만 참조하는 데 유리하다.
- Bucky 적용 포인트: 기술, 판단 기준, 워크플로우, 예시 산출물은 가능한 한 Markdown으로 저장하고, 제목/태그/상호링크를 유지한다.

### 5. UX 전문 에이전트는 스킬 폴더와 작업 산출물 폴더가 필요하다

발표자는 UX/UI 업무를 위해 다음 유형의 기술 파일을 에이전트에게 제공하는 방식을 보여준다.

- 리서치 방법
- 사용성 평가
- 사용자 인터뷰
- 인터뷰 분석
- 어피니티 맵
- 페르소나 설계
- 사용자 시나리오
- PRD 작성
- 웹페이지/HTML 생성
- 결과물 평가
- UX 심리학 적용 기준

Bucky 적용 포인트: `skills` 또는 `context packs`는 추상 설명만 담으면 약하다. 실제로는 "입력, 절차, 출력 형식, 평가 기준, 예시"가 들어 있어야 에이전트가 반복 가능한 품질로 일한다.

## 영상의 UX 에이전트 워크플로우

1. UX/UI 프로젝트 목표를 한 줄로 지시한다.
2. 에이전트가 기존 스킬/가이드 파일을 읽고 정성적 인터뷰 계획서를 Markdown으로 작성한다.
3. 실제 또는 가상의 사용자 인터뷰 데이터를 Markdown 폴더에 저장한다.
4. 에이전트가 인터뷰 데이터를 코드화하고 분석 보고서를 만든다.
5. 분석 내용을 어피니티 맵으로 정리한다.
6. 분석 데이터에서 페르소나를 생성한다.
7. 페르소나와 사용자 데이터를 바탕으로 PRD를 작성한다.
8. PRD를 기반으로 원페이지 웹사이트/HTML 결과물을 만든다.
9. 생성 결과가 목표/요구사항을 충족했는지 평가한다.
10. 평가 결과를 다시 수정 지시와 다음 작업에 반영한다.

## Bucky OS 적용 액션

- `ObsidianVault/03_Knowledge`의 영상 지식 노트는 단순 요약보다 "Bucky가 재사용할 규칙" 중심으로 작성한다.
- UX/디자인 관련 반복 업무는 `입력 -> 참조 스킬 -> 생성 산출물 -> 평가 기준 -> 다음 액션` 필드를 가진 템플릿으로 고정한다.
- 에이전트가 참조해야 하는 지식 파일은 단일 긴 문서보다 주제별 Markdown 파일과 인덱스로 나눈다.
- Bucky가 Claude/Codex에게 일을 보낼 때는 필요한 Context Pack, 스킬 파일, 출력 형식, 검증 기준을 함께 지정한다.
- AI 산출물은 곧바로 최종물로 보지 말고, 별도 평가 에이전트 또는 검수 루틴을 통해 요구사항 충족 여부를 확인한다.
- 장기적으로는 Daily Plus, AgentBus, Knowledge note, Context Pack을 연결해 "매일 수집한 지식이 다음 자동화/개선 작업으로 이어지는 루프"를 구성한다.

## Bucky에 저장할 패턴

```yaml
pattern: ux_agent_markdown_workflow
goal: UX/UI 전문 에이전트가 리서치부터 산출물 평가까지 반복 수행하게 한다.
input:
  - project_goal
  - user_research_data
  - skill_folder
  - design_requirements
process:
  - read_relevant_skills
  - create_interview_plan
  - analyze_interview_data
  - build_affinity_map
  - create_personas
  - write_prd
  - generate_design_or_html
  - evaluate_against_requirements
output:
  - markdown_reports
  - persona_set
  - prd
  - html_or_design_artifact
  - evaluation_report
verification:
  - source data referenced
  - markdown outputs saved
  - requirements covered
  - evaluation findings reflected in next action
```

## 주의점

- 영상의 Hermes/OpenClow/Gemini Spark 비교는 발표자의 경험 기반 설명이므로, 도구별 현재 기능/가격/보안 상태는 실제 도입 전에 별도 최신 검증이 필요하다.
- YouTube 자동자막 기반 전사라 일부 용어가 부정확할 수 있다. 예: OpenClow/OpenClow 표기, Hermes/Hermes Agent 표기, Gemini Spark 표기.
- 이 노트는 도구 설치 매뉴얼이 아니라 Bucky Agent OS에 적용할 지식/워크플로우 요약이다.

## Related

- [[2026-06-09-yt-쓸수록-똑똑해지는-ai-에이전트-헤르메스-완벽-정리]]
- [[2026-06-09-yt-루프-엔지니어링이-답이다-ai를-자동으로-진화시키는-법]]
- [[2026-06-10-yt-hermes-agentic-os-is-insane-just-watch]]
- [[bucky-evolution-pipeline]]
- [[bucky-evolution-roadmap]]
- [[goalmode-claude-code-handoff]]
