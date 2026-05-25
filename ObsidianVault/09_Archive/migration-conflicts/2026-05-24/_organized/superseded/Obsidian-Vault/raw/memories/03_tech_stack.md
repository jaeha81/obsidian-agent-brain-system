# 03 — 기술 스택 / 코딩 원칙 / 아키텍처

---

## 🏗️ 표준 스택

| 레이어 | 기술 | 버전/비고 |
|---|---|---|
| **Backend** | FastAPI | Python, 비동기 |
| **Frontend** | Next.js | 14 (App Router) |
| **Database** | Supabase | PostgreSQL + Realtime + Auth |
| **AI** | Claude API | claude-opus-4 / claude-sonnet-4 |
| **Agent Framework** | 자체 구현 | LangGraph 참고, 직접 설계 |
| **인프라** | Vercel (FE) / Railway or VPS (BE) | |

---

## 📐 코딩 원칙

### 필수 규칙
1. **named export만** — `export default` 금지
2. **`any`, `unknown` 타입 금지** — 명확한 타입 정의
3. **단일 책임** — 파일당 하나의 명확한 역할
4. **중복 엔드포인트 금지** — API 설계 시 중복 경로 사전 확인
5. **자동결제 사용자 확인 필수** — 결제 로직엔 항상 확인 단계

### TypeScript 원칙
```typescript
// ❌ 금지
export default function MyComponent() {}
const data: any = fetchData()

// ✅ 허용
export function MyComponent() {}
const data: UserData = fetchData()
```

---

## 🤖 에이전트 아키텍처 원칙

### 설계 철학
- **재하가 통제, AI가 실행** — 에이전트도 동일
- Supervisor 역할: 판단과 실행 분리
- 파일 기반 로그 금지 (삭제 가능, 런타임 강제 불가)
- YAML 스키마로 런타임 동작 강제 불가 → 코드로 구현

### 에이전트 분업 패턴
```
Orchestrator (판단/라우팅)
├── Research Agent (정보 수집)
├── Plan Agent (설계)
├── Implementation Agent (구현)
└── QA Agent (검증)
```

### 상태 관리
- LangGraph StateGraph 참고
- 단일 human intervention point
- 승인 패턴: "구현해" 키워드 매칭

---

## 🔌 Claude API 사용 패턴

### 모델 선택
- **Orchestrator / 복잡한 판단**: claude-opus-4
- **일반 에이전트**: claude-sonnet-4
- **빠른 분류 / IntentGate**: claude-haiku-4-5 (비용 최적화)

### 비동기 처리 (중요)
```python
# ❌ 버그 패턴 (JH-키아누에서 발견)
async def process():
    client = Anthropic()  # sync client
    response = client.messages.create(...)  # FastAPI event loop 블로킹

# ✅ 올바른 패턴
async def process():
    client = AsyncAnthropic()
    response = await client.messages.create(...)
```

### 멀티턴 관리
- 상태를 요청마다 완전히 포함
- 컨텍스트 압축 없음 (현재 규모에서 불필요)

---

## 🗄️ Supabase 활용 패턴

- **PostgreSQL**: 주 데이터 저장
- **Realtime**: 에이전트 상태 실시간 구독
- **Row Level Security**: 프로젝트별 데이터 격리
- **Auth**: Supabase Auth (JWT)

---

## 🎨 Frontend 패턴

### Next.js 14 App Router
- Server Components 우선
- Client Components는 인터랙션 필요 시만
- `"use client"` 최소화

### UI 라이브러리
- Tailwind CSS (주력)
- shadcn/ui (컴포넌트)
- Three.js (3D 시각화, Agent Hub 등)

---

## 📦 패키지 관리

- **Python**: `pip install --break-system-packages` (컨테이너 환경)
- **Node**: npm (글로벌 패키지: `~/.npm-global`)
- 가상환경: 복잡한 Python 프로젝트에서 사용

---

## 🔄 테스트 전략

- pytest (Backend)
- 통합 테스트 우선 (유닛 테스트 후순위)
- 사례: PreCon AI — 6/6 통합 테스트 통과 기준
- JH-견적 — 실제 Excel 데이터로 정규화 검증
