---
type: knowledge-note
date: 2026-06-04
source: daily-plus
category: agent-prompting
tags:
- '#area/ai_automation'
- '#status/active'
summary: 비개발자 AI 크리에이터용 숏폼 영상 8종 템플릿 팩 — Hook+Body+CTA 구조, 한국어 플랫폼 최적화
status: staged
applied_at: 2026-06-11
approval_required: true
approval_note: Bucky approval needed before adding to active content pipeline
graph_cluster: daily-practice
---

# Short-Form AI Template Pack

## 개요

비개발자 AI 크리에이터가 즉시 사용 가능한 **숏폼 영상 8종 템플릿**. Hook → Body → CTA 구조로 설계되었으며 YouTube Shorts, TikTok, Instagram Reels에 최적화된 한국어 템플릿이다.

## 템플릿 구조 원칙

```
[HOOK]   — 첫 1-3초: 호기심/문제 제기 (스크롤 멈춤 유발)
[BODY]   — 4-50초: 핵심 정보/시연 (가치 전달)
[CTA]    — 마지막 5초: 행동 유도 (팔로우/저장/댓글)
```

---

## 템플릿 1: "나도 몰랐던 AI 사용법"

```
[HOOK]
"ChatGPT를 이렇게 쓰는 사람은 1%도 안 돼요"

[BODY]
• 일반 사용: [기본 방식 시연]
• 고급 사용: [숨겨진 방법 시연]
• 실제 결과 비교 화면 캡처

[CTA]
"저장해두고 나중에 써보세요 👇"
```

---

## 템플릿 2: "AI로 [시간] 단축하기"

```
[HOOK]
"3시간 걸리던 [작업]을 AI로 5분에 끝냈어요"

[BODY]
• Before: 기존 방식 (숫자로 표현)
• After: AI 사용 방식 단계별 시연
• 실제 결과물 공개

[CTA]
"어떤 작업에 써봤는지 댓글로 알려주세요"
```

---

## 템플릿 3: "AI 초보자 실수 TOP 3"

```
[HOOK]
"AI 쓰다가 이 실수 하면 시간 낭비예요"

[BODY]
실수 1: [구체적 실수] → 올바른 방법
실수 2: [구체적 실수] → 올바른 방법
실수 3: [구체적 실수] → 올바른 방법

[CTA]
"몇 번 실수 공감가면 팔로우 눌러주세요"
```

---

## 템플릿 4: "프롬프트 전/후 비교"

```
[HOOK]
"같은 질문인데 결과가 이렇게 달라요"

[BODY]
• 나쁜 프롬프트: [예시] → 실망스러운 결과
• 좋은 프롬프트: [예시] → 놀라운 결과
• 핵심 차이: [한 줄 설명]

[CTA]
"이 프롬프트 저장해두면 바로 써먹어요"
```

---

## 템플릿 5: "AI로 부업하는 방법"

```
[HOOK]
"AI로 월 [N]만원 버는 사람들의 공통점"

[BODY]
• 방법 1: [구체적 방법 + 실제 수익 증거]
• 방법 2: [구체적 방법]
• 시작 비용: [0원/최소 비용]

[CTA]
"관심 있으면 팔로우하세요, 다음 편 올려드려요"
```

---

## 템플릿 6: "오늘 배운 AI 꿀팁"

```
[HOOK]
"오늘 발견한 AI 기능 진짜 미쳤어요"

[BODY]
• 기능 소개: [이름 + 한 줄 설명]
• 사용 방법: 화면 캡처 + 음성 설명
• 활용 예시: 실생활 사용 사례 1-2개

[CTA]
"저장해두고 오늘 바로 써보세요"
```

---

## 템플릿 7: "AI 툴 랭킹"

```
[HOOK]
"제가 직접 써본 AI 툴 [N]개 솔직 평가"

[BODY]
• [순위별 툴 소개, 각 5-10초]
• 장점/단점 한 줄씩
• 최종 추천: 상황별 픽

[CTA]
"어떤 거 더 자세히 알고 싶어요? 댓글 달아요"
```

---

## 템플릿 8: "AI 챌린지 결과"

```
[HOOK]
"AI한테 [어려운 과제] 시켜봤어요"

[BODY]
• 과제 공개
• AI 응답 과정 (화면 녹화)
• 결과 평가: [기대 vs 실제]

[CTA]
"다음엔 뭐 시켜볼까요? 댓글 달아주세요"
```

---

## Bucky 자동화 연동 (승인 후)

```
/bucky create-short
  --template 4
  --topic "Claude 프롬프트 최적화"
  --platform youtube_shorts
  --language ko
```

## 참고

- 관련 파이프라인: `2026-06-04-dp-three-step-shorts-pipeline.md`
- TikTok 워크플로우: `project_session_2026-06-06b.md`

## 관련 노트
- [[hubs/JH System]]
