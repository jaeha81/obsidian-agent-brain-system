# 병렬 세션 배정 파일 템플릿

> **이 파일은 템플릿이다. 실제 배정은 복사본을 만들어 사용한다.**  
> 복사 후 파일명: `parallel-session-YYYYMMDD-HHMMSS.md`  
> 작성자: Session A (오케스트레이터)

---

## 기본 정보

| 필드 | 값 |
|------|-----|
| taskId | `TASK-YYYYMMDD-HHMMSS` |
| 작업명 | [작업 설명] |
| 오케스트레이터 | Session A |
| 생성 시각 | YYYY-MM-DD HH:MM KST |
| 상태 | `active` / `done` |

---

## 진입 판단 근거

- 수정 예상 파일 수: N개 (10개 이상 ✅)
- 독립 영역 수: N개 (2개 이상 ✅)
- 예상 소요 시간: N시간 (2시간 이상 ✅)

---

## 영역별 배정

### Session B — [영역명 예: frontend]

**담당 파일 목록 (이 목록 외 수정 불가):**
```
src/components/Login.tsx
src/components/AuthContext.tsx
src/hooks/useAuth.ts
```

**작업 내용:**
- [ ] [구체적 작업 1]
- [ ] [구체적 작업 2]

**완료 조건:** [검증 기준]

**의존성:** 없음 / Session C 완료 후 시작

---

### Session C — [영역명 예: backend]

**담당 파일 목록 (이 목록 외 수정 불가):**
```
api/auth.ts
middleware/jwt.ts
routes/auth.ts
```

**작업 내용:**
- [ ] [구체적 작업 1]
- [ ] [구체적 작업 2]

**완료 조건:** [검증 기준]

**의존성:** 없음 / Session B 완료 후 시작

---

### Session D — [영역명 예: test]

**담당 파일 목록 (이 목록 외 수정 불가):**
```
__tests__/auth/login.test.ts
__tests__/auth/jwt.test.ts
__tests__/auth/routes.test.ts
```

**작업 내용:**
- [ ] [구체적 작업 1]
- [ ] [구체적 작업 2]

**완료 조건:** 모든 테스트 통과

**의존성:** Session B, Session C 완료 후 시작

---

### Session A — 공유 파일 + 통합

**직접 처리 파일 (워커 배정 금지):**
```
src/types/auth.ts
src/constants/auth.ts
```

---

## 진행 상태

| 세션 | 영역 | 상태 | 완료 시각 |
|------|------|------|---------|
| Session B | frontend | `pending` / `in-progress` / `done` / `blocked` | — |
| Session C | backend | `pending` | — |
| Session D | test | `pending` | — |
| Session A | 공유+통합 | `in-progress` | — |

---

## 워커 온보딩 지시

새 Claude Code 세션을 열고 다음을 전달:

```
이 파일을 읽어: G:\내 드라이브\JH-SHARED\00_SYSTEM\parallel-session-YYYYMMDD-HHMMSS.md
너는 Session B야. parallel-worker.md 가이드를 따라 진행해.
```

워커 가이드 위치: `~/.claude/guides/parallel-worker.md`

---

## 완료 신호 형식 (Agent Room append)

```json
{"taskId":"TASK-YYYYMMDD-HHMMSS","session":"B","status":"done","area":"frontend","timestamp":"ISO8601","verifyPassed":true}
```

---

## 메모 / 이슈

<!-- 오케스트레이터가 진행 중 발견한 이슈, 결정 사항을 여기에 기록 -->
