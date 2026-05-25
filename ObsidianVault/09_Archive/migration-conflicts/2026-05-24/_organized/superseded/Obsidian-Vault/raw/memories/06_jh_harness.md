# 06 — JH-하네스 (멀티하네스 아키텍처)

> 에이전트 제어 구조의 핵심 설계 원칙. 재하-AI 관계의 구조적 표현.

---

## 📊 개요

| 항목 | 내용 |
|---|---|
| 목적 | 멀티에이전트 제어 하네스 아키텍처 설계 |
| 상태 | 아키텍처 설계 단계 |
| JH-키아누와의 관계 | **별개 프로젝트** — 혼동 금지 |

---

## 🔑 핵심 원칙

### "재하가 통제한다. AI는 그 구조 안에서 실행한다."

이것은 단순한 개발 원칙이 아니라 **JH 브랜드의 철학적 기반**:
- AI 자율성에 의존하지 않음
- 명시적 승인 없이 에이전트 실행 없음
- 제어권은 항상 재하에게

---

## 🚫 이전 설계의 문제점 (비판 세션에서 도출)

### 문제 1: YAML 스키마의 한계
```yaml
# ❌ YAML은 런타임 동작을 강제할 수 없음
agent:
  name: researcher
  max_tokens: 1000
  # → 이 설정이 실제 에이전트 동작을 보장하지 않음
```
- YAML은 선언이지 런타임 강제가 아님
- **해결**: 코드 레벨 구현으로 동작 보장

### 문제 2: 파일 기반 로그
```python
# ❌ 파일 로그는 삭제 가능, 런타임 방지 불가
with open("agent.log", "w") as f:
    f.write(action)
# → 누군가 파일을 지워버리면 감사 불가
```
- **해결**: DB 기반 불변 로그 (Supabase)

### 문제 3: Supervisor 역할 혼재
```
# ❌ 잘못된 설계
Supervisor = 판단 + 실행 (혼재)

# ✅ 올바른 설계
Supervisor = 판단만
Executor = 실행만
```
- Supervisor가 판단과 실행을 함께 하면 통제권 상실
- **해결**: 판단(Supervisor) ↔ 실행(Executor) 명확 분리

---

## 🏗️ 하네스 구조 설계

### 하네스(Harness) 개념
```
재하 (Control Layer)
    │
    ├── Harness A (프로젝트 A 전용)
    │   ├── Agent 1
    │   ├── Agent 2
    │   └── Agent 3
    │
    ├── Harness B (프로젝트 B 전용)
    │   ├── Agent 1
    │   └── Agent 2
    │
    └── Harness C (공통 유틸리티)
        └── Agent 1
```

- 각 하네스는 독립적으로 작동
- 하네스 간 통신은 명시적 인터페이스만
- 재하가 하네스 레벨에서 통제

### Harness 인터페이스 (설계 중)
```python
class JHHarness:
    def __init__(self, name: str, agents: list[JHAgent]):
        self.name = name
        self.agents = agents
        self.approval_required = True  # 항상 승인 필요

    async def execute(self, task: Task, approved: bool = False) -> Result:
        if not approved:
            raise PermissionError("재하의 승인 없이 실행 불가")
        # ...
```

---

## 📋 Scope Tag 개념 (미래 사용 예정)

- **DEV**: 개발 관련 에이전트 (코딩, 테스트, 빌드)
- **OPS**: 운영 관련 에이전트 (배포, 모니터링, 알림)

**현재 적용 보류 이유**: 동시 진행 프로젝트가 5개 미만 → 불필요
5개 이상 동시 프로젝트 시 Scope Tag 도입 검토

---

## 🔗 JH-EstimateAI와의 연결

- EstimateAI 대회 출품 버전에 멀티하네스 아키텍처 적용 승인
- 실제 적용 케이스로 검증 예정
