---
type: knowledge-note
date: 2026-06-09
source: daily-plus
category: verification
tags:
- area/ai_automation
- status/active
summary: 숏폼 훅 5개 + Trigger.dev 콘텐츠 자동화 파이프라인 패턴
status: applied
applied_at: 2026-06-11
graph_cluster: daily-practice
---

# 숏폼 훅 5개 + Trigger.dev 콘텐츠 자동화

한국 플랫폼(인스타/유튜브 쇼츠/틱톡) 대상 AI 자동화 콘텐츠 훅 템플릿과
Trigger.dev를 활용한 백그라운드 콘텐츠 파이프라인 패턴.

---

## 숏폼 훅 템플릿 5개

### Hook 1 — 충격 통계형
```
"회의록 쓰는 데 하루 2시간?
AI한테 맡겼더니 3분 됐습니다.
방법 알려드림."
```
**용도**: 시간 절약 소구, 사무직/1인기업 타겟

---

### Hook 2 — Before/After 대비형
```
"전: 음성 메모 → 직접 타이핑 → 메일 작성 (45분)
후: 음성 메모 → AI 자동 처리 → 슬랙 발송 (90초)
이게 가능한 이유 설명합니다."
```
**용도**: 구체적 수치, 신뢰도 높음

---

### Hook 3 — 공감+문제 제기형
```
"아직도 카카오톡으로 업무 지시 받아서
수동으로 정리하고 계세요?
2025년엔 이렇게 합니다."
```
**용도**: 중소기업 관리자/팀장 타겟

---

### Hook 4 — 비밀 공개형
```
"제가 혼자서 월 매출 300 올리는 시스템
공짜로 다 풀어드립니다.
진짜 비개발자도 됩니다."
```
**용도**: 수익화 소구, 프리랜서/1인기업

---

### Hook 5 — 반전형
```
"AI 쓴다고 하면 다들 '어렵지 않아?'
네. 저도 그랬습니다.
그래서 버튼 하나로 만들었습니다."
```
**용도**: 진입 장벽 해소, 비개발자 공략

---

## Trigger.dev 콘텐츠 파이프라인

### 개요

Trigger.dev는 TypeScript 기반 백그라운드 잡 오케스트레이터.
Node.js 환경에서 웹훅, 스케줄, 이벤트 기반 잡을 서버 없이 실행.

### 기본 패턴 — 음성 메모 → 멀티 콘텐츠 생성

```typescript
// trigger.dev v3
import { task, schedules } from "@trigger.dev/sdk/v3";

export const voiceToContent = task({
  id: "voice-to-content",
  run: async (payload: { audioUrl: string; userId: string }) => {
    // 1. STT 변환
    const transcript = await transcribeAudio(payload.audioUrl);

    // 2. 병렬 콘텐츠 생성
    const [shortform, blog, sns] = await Promise.all([
      generateShortform(transcript),
      generateBlogDraft(transcript),
      generateSNSPost(transcript),
    ]);

    // 3. Obsidian Vault 저장
    await saveToVault({ shortform, blog, sns, userId: payload.userId });

    // 4. Discord 알림
    await notifyDiscord(`콘텐츠 생성 완료: ${shortform.title}`);

    return { shortform, blog, sns };
  },
});
```

### 스케줄 잡 패턴 — 매일 오전 6시 Daily Digest

```typescript
export const dailyDigest = schedules.task({
  id: "daily-digest",
  cron: "0 6 * * *", // 매일 오전 6시 KST
  run: async () => {
    const yesterday = await getYesterdayNotes();
    const digest = await summarizeNotes(yesterday);
    await postToDiscord("#daily-digest", digest);
  },
});
```

### 웹훅 트리거 패턴 — Discord 명령 → 잡 실행

```typescript
export const discordCommandHandler = task({
  id: "discord-command-handler",
  run: async (payload: { command: string; args: string[] }) => {
    if (payload.command === "generate") {
      await voiceToContent.trigger({ audioUrl: payload.args[0], userId: "jh" });
    }
  },
});
```

### 재시도/에러 처리

```typescript
export const robustTask = task({
  id: "robust-content-gen",
  retry: { maxAttempts: 3, factor: 2, minTimeoutInMs: 1000 },
  run: async (payload) => {
    // 실패 시 자동 재시도, 지수 백오프
  },
});
```

---

## 플랫폼별 콘텐츠 배포 전략

| 플랫폼 | 길이 | 훅 위치 | 최적 업로드 시간 |
|---|---|---|---|
| 인스타 릴스 | 15-30초 | 0-3초 | 오전 7-9시, 오후 7-9시 |
| 유튜브 쇼츠 | 30-60초 | 0-5초 | 오후 12-2시 |
| 틱톡 | 15-60초 | 0-2초 | 오후 6-10시 |

## 다음 액션

- [ ] Trigger.dev 프로젝트 생성 + 첫 잡 배포
- [ ] 훅 5개 중 1개 선택 → 오늘 영상 촬영
- [ ] `voiceToContent` 잡을 현재 Discord 봇과 연결

## 관련 노트
- [[hubs/JH System]]
