# Boris Phase 2 — 병렬 세션 오케스트레이션 설계 계획

> 작성일: 2026-05-02  
> 작성자: Claude (노트북 세션)  
> 선행 문서: `00_SYSTEM/boris-phase1-report.md`  
> 상태: **승인 대기**

---

## 목표

대규모 작업(파일 10개+, 독립 영역 분리 가능, 단일 세션 2시간+ 예상)을 여러 Claude Code 세션이 병렬로 처리할 때:

1. **충돌 없이** 각 세션이 담당 영역을 안전하게 작업한다
2. **오케스트레이터 세션**이 전체 진행을 조율하고 통합을 책임진다
3. **검증 게이트**는 Phase 1의 auto-verify.sh를 그대로 재사용한다

---

## 현황 분석

### 이미 존재하는 인프라

| 인프라 | 위치 | 상태 |
|--------|------|------|
| Task Lock 시스템 | `05_TASK_LOCKS/active/`, `done/` | 설계 완료, 운영 중 |
| Task Log 시스템 | `06_TASK_LOGS/YYYY-MM/*.jsonl` | 설계 완료, 운영 중 |
| 세션 간 통신 채널 | `01_AGENT_ROOM/agent-room-messages.jsonl` | 운영 중 |
| PS1 스크립트 | `JH-Agent-Room/scripts/start-task.ps1` 등 | 운영 중 |
| 검증 게이트 | `~/.claude/scripts/auto-verify.sh` v1.2 | 운영 중 |

### 현재 갭

| 갭 | 설명 |
|----|------|
| 진입 판단 부재 | "지금 병렬 세션이 필요한가?" 기준이 CLAUDE.md에 없음 |
| 오케스트레이터 역할 미정의 | Session A가 어떻게 작업을 분해·배정·통합하는지 절차 없음 |
| 워커 세션 온보딩 없음 | 신규 세션이 "나는 어느 영역을 담당한다"를 확인하는 방법 없음 |
| 병합 프로토콜 없음 | 각 세션 완료 후 통합 절차 미정 |

---

## 설계 원칙

1. **기존 인프라 최대 재사용**: 새 스크립트보다 현재 PS1 + JSONL 채널 활용
2. **파일 기반 단순성**: 복잡한 서버 없이 파일 읽기/쓰기로 통신
3. **오케스트레이터 단일 책임**: 통합은 반드시 Session A만 담당
4. **Phase 1 검증 재사용**: 각 세션도 작업 완료 시 auto-verify.sh 실행

---

## 병렬 세션 진입 판단 기준 (3조건 모두 충족 시)

```
조건 1: 수정 예상 파일 10개 이상  
조건 2: 독립적으로 분리 가능한 영역이 2개 이상 식별됨  
       (예: frontend/backend, 기능A/기능B, 데이터/UI)  
조건 3: 단일 세션으로 2시간 이상 예상
```

3조건 미충족 → 단일 세션으로 진행 (Phase 1 검증만 적용)

---

## 시스템 구성

### 역할 정의

```
Session A (오케스트레이터)
  ├── 작업 분해 및 영역 식별
  ├── Task Lock 등록 (05_TASK_LOCKS/)
  ├── 워커 세션 배정 파일 생성
  ├── 진행 모니터링 (06_TASK_LOGS/)
  └── 최종 통합 및 auto-verify.sh 실행

Session B/C/D (워커)
  ├── 배정 파일 확인 → 자기 영역만 작업
  ├── Task Lock 확인 (충돌 시 중단·보고)
  ├── 완료 시 Task Log 기록
  └── auto-verify.sh 실행 (자기 영역)
```

### 통신 파일 구조

```
05_TASK_LOCKS/active/
  TASK-YYYYMMDD-HHMMSS.json    ← 작업 잠금 (기존 형식 유지)

G:\내 드라이브\JH-SHARED\00_SYSTEM\
  parallel-session-YYYYMMDD-HHMMSS.md  ← 오케스트레이터가 생성하는 배정 파일
    - taskId
    - 영역별 담당 세션
    - 각 세션의 작업 파일 목록
    - 의존성 순서
    - 완료 조건
```

---

## 구현 항목

### Phase 2-A: 문서·프로토콜 (이번 세션 구현)

| # | 항목 | 위치 | 우선순위 |
|---|------|------|---------|
| 1 | 오케스트레이터 가이드 | `~/.claude/guides/parallel-orchestrator.md` | P1 |
| 2 | 워커 세션 온보딩 가이드 | `~/.claude/guides/parallel-worker.md` | P1 |
| 3 | 배정 파일 템플릿 | `00_SYSTEM/parallel-session-template.md` | P1 |
| 4 | CLAUDE.md 진입 판단 기준 추가 | `~/.claude/CLAUDE.md` | P1 |

### Phase 2-B: 스크립트 (추후 구현, 사용자 승인 후)

| # | 항목 | 위치 | 우선순위 |
|---|------|------|---------|
| 5 | 배정 파일 생성 스크립트 | `JH-Agent-Room/scripts/create-parallel-session.ps1` | P2 |
| 6 | 워커 완료 알림 스크립트 | `JH-Agent-Room/scripts/notify-worker-done.ps1` | P2 |
| 7 | 충돌 감지 훅 | `~/.claude/hooks/parallel-conflict-check.sh` | P3 |

**이번 세션: Phase 2-A (문서·프로토콜)만 구현. Phase 2-B는 별도 승인.**

---

## 워크플로우 상세 (Phase 2-A 기준)

### Step 1: 오케스트레이터 세션 (Session A) — 진입 판단

```
1. 작업 요청 수신
2. 3조건 체크 → 조건 미충족 시 단일 세션 진행
3. 조건 충족 시 → 영역 분해
   예) "auth 리팩토링": frontend(컴포넌트 5개) / backend(API 3개) / test(4개)
4. parallel-session-YYYYMMDD-HHMMSS.md 생성
5. Task Lock 등록 (start-task.ps1)
6. 사용자에게 배정 계획 고지 → 승인 후 진행
```

### Step 2: 워커 세션 온보딩

```
1. 사용자가 새 Claude Code 세션 오픈
2. 배정 파일 경로 전달: "00_SYSTEM/parallel-session-YYYYMMDD.md 읽어"
3. 워커 가이드 (parallel-worker.md) 로드
4. 자기 영역 Task Lock 확인 → 충돌 없으면 작업 시작
5. 작업 완료 → Task Log 기록 → auto-verify.sh 실행
6. 완료 신호: Agent Room 메시지 append
```

### Step 3: 통합 (Session A)

```
1. 모든 워커 완료 신호 확인 (Agent Room 폴링)
2. 각 워커 작업 결과 검토
3. 통합 병합 (git merge or 파일 결합)
4. auto-verify.sh 전체 실행
5. Task Lock done으로 이동
6. session-state.md 갱신
```

---

## 검증 기준 (Phase 2-A 완료 조건)

- [ ] `parallel-orchestrator.md` 작성 완료 (가이드 충분히 구체적)
- [ ] `parallel-worker.md` 작성 완료
- [ ] `parallel-session-template.md` 작성 완료
- [ ] CLAUDE.md 3조건 진입 판단 섹션 추가
- [ ] boris-phase2-report.md 작성 완료
- [ ] session-state.md 갱신

---

## 리스크 및 반론

| 리스크 | 완화 방안 |
|--------|----------|
| 세션 간 파일 충돌 | Task Lock 필수 + 충돌 시 즉시 중단 원칙 |
| 오케스트레이터 세션 컨텍스트 소진 | 배정 파일에 모든 상태 기록 → 재시작 가능 |
| 워커가 배정 외 파일 수정 | 배정 파일의 담당 파일 목록 = 계약. 이탈 시 Task Lock 오류 |
| Phase 2-B 스크립트 불필요 가능성 | Phase 2-A 문서만으로 수동 운영 → 반복 3회 이상 시 자동화 |

**반론:** Phase 2-B 스크립트 없이 Phase 2-A 문서만으로 충분히 운영 가능. 스크립트는 수동 운영 경험 후 필요한 것만 선별 구현 권장.

---

## 승인 후 진행 순서

1. 이 plan.md 승인 → Phase 2-A 구현 시작
2. `guides/parallel-orchestrator.md` 작성
3. `guides/parallel-worker.md` 작성
4. `00_SYSTEM/parallel-session-template.md` 작성
5. CLAUDE.md 업데이트
6. boris-phase2-report.md 작성 + session-state.md 갱신
7. claude-projects-jh push
