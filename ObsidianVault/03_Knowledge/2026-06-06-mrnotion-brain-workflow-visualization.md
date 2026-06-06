---
title: JH Agent Brain System — Single Page Workflow Visualization
source: https://vt.tiktok.com/ZSQFysUXg/ (@mr.notion)
date: 2026-06-06
tags: [workflow, visualization, brain-system, agent-os, mermaid]
type: knowledge
---

# JH Agent Brain System — Single Page Workflow

> mr.notion의 "entire business laid out on a single page" 컨셉을 JH 에이전트 OS에 적용한 워크플로우 시각화.
> 원본 영상: Sales Blueprint / Customer / Narrative / Framework / Capture / Tech Stack / Asset Library 구조 참고.

---

## 1. 전체 시스템 조감도 (Single Page OS)

```mermaid
flowchart TD
    subgraph CAPTURE["🎯 CAPTURE — 입력 레이어"]
        C1[Discord 명령]
        C2[ChatGPT Daily 수집]
        C3[Wishket 공고 크롤링]
        C4[수동 Vault 입력]
    end

    subgraph BRAIN["🧠 BRAIN — 오케스트레이션"]
        B1[Bucky\n오케스트레이터]
        B2[Context Pack Selector\ncontext_pack_selector.py]
        B3[ROUTING_RULES\n의사결정 트리]
    end

    subgraph AGENTS["⚙️ AGENTS — 실행 레이어"]
        A1[Claude Code\n구현·운영]
        A2[Codex\n독립 검수]
        A3[Pulse Evolution\n자율 진화]
    end

    subgraph PIPELINE["📦 PIPELINE — 처리 레이어"]
        P1[daily_plus_morning_report.py\n아침 보고서]
        P2[wishket_development_request.py\n수익화 파이프라인]
        P3[bucky_chat_server.py\nIPC 8765/8766]
        P4[discord_bot.py\n알림·체크리스트]
    end

    subgraph STORAGE["🗄️ STORAGE — 지식 베이스"]
        S1[ObsidianVault\n03_Knowledge]
        S2[Context Packs\n06_Context_Packs]
        S3[data/channel_tasks.db\n태스크 DB]
        S4[HANDOFF_LOG\n에이전트 핸드오프]
    end

    subgraph OUTPUT["📤 OUTPUT — 출력 레이어"]
        O1[Discord 보고\n채널별 분리]
        O2[Vercel Dashboard\ndocs/index.html]
        O3[Wishket 제안서\n수익 창출]
        O4[Obsidian 노트\n지식 축적]
    end

    subgraph REVENUE["💰 REVENUE — 수익 레이어"]
        R1[Wishket 낙찰\n직접 수익]
        R2[구독 서비스\nAI Usage 대시보드]
        R3[에이전트 서비스\n미래 수익화]
    end

    CAPTURE --> BRAIN
    BRAIN --> B2 --> B3
    B1 --> AGENTS
    B3 --> A1
    B3 --> A2
    AGENTS --> PIPELINE
    PIPELINE --> STORAGE
    PIPELINE --> OUTPUT
    OUTPUT --> REVENUE
    STORAGE --> B2
```

---

## 2. 에이전트 역할 분리 (Department View)

```mermaid
flowchart LR
    subgraph NARRATIVE["THE NARRATIVE\n시스템의 영혼"]
        N1["CLAUDE.md\n전략 원칙"]
        N2["BUCKY_CONTEXT.md\n운영 철학"]
        N3["MASTER_PLAN.md\n큰 그림"]
    end

    subgraph FRAMEWORK["THE FRAMEWORK\n실행 전략"]
        F1["ROUTING_RULES.md\n에이전트 라우팅"]
        F2["context_pack_selector.py\n컨텍스트 선택"]
        F3["BUCKY_OS_RUNBOOK.md\n운영 절차"]
    end

    subgraph SALES["SALES FUNNEL\n수익화 퍼널"]
        SL1["Wishket 크롤링\n공고 발굴"]
        SL2["wishket_development_request.py\n제안서 자동화"]
        SL3["Discord 알림\n진행 상황 추적"]
    end

    subgraph TECH["TECH STACK\n기술 스택"]
        T1["Python 스크립트\n자동화 엔진"]
        T2["Cloudflare Pages\n호스팅"]
        T3["Discord Bot\n인터페이스"]
        T4["Vercel\n대시보드"]
    end

    subgraph ASSET["ASSET LIBRARY\n에셋 라이브러리"]
        AS1["03_Knowledge\n지식 노트"]
        AS2["06_Context_Packs\n작업 패킷"]
        AS3["memory/\n에이전트 메모리"]
    end

    subgraph HOOKS["HOOK SETS\n트리거 시스템"]
        H1["Discord 명령어\n!체크리스트, !보고서"]
        H2["스케줄 크론\n아침 7시 보고"]
        H3["IPC WebSocket\n에이전트 간 통신"]
    end

    NARRATIVE --> FRAMEWORK
    FRAMEWORK --> SALES
    FRAMEWORK --> HOOKS
    TECH --> SALES
    TECH --> HOOKS
    ASSET --> FRAMEWORK
    HOOKS --> SALES
```

---

## 3. 일일 운영 플로우 (Daily Operations)

```mermaid
sequenceDiagram
    participant D as Discord
    participant B as Bucky
    participant C as Claude Code
    participant CX as Codex
    participant V as Vault

    Note over D,V: 🌅 아침 루틴 (07:00)
    D->>B: 아침 보고서 요청
    B->>C: daily_plus_morning_report.py 실행
    C->>V: ChatGPT 세션 + Wishket 공고 수집
    C->>D: 📊 보고서 Discord 전송

    Note over D,V: ⚡ 작업 실행 (상시)
    D->>B: 새 작업 지시
    B->>B: Context Pack 선택
    B->>C: 구현 패킷 전달
    C->>C: 코드 작성 / 파일 수정
    C->>CX: 완료 핸드오프
    CX->>D: 독립 검수 결과 보고
    C->>V: HANDOFF_LOG 기록

    Note over D,V: 🔄 수익화 루틴
    B->>C: Wishket 공고 분석
    C->>C: 제안서 자동 생성
    C->>D: 낙찰 후보 알림
```

---

## 4. 수익화 파이프라인 (Sales Blueprint 대응)

```mermaid
flowchart TD
    subgraph DISCOVER["발굴"]
        D1[Wishket 크롤링\n공고 자동 수집]
        D2[키워드 필터링\n적합 공고 선별]
    end

    subgraph QUALIFY["검증"]
        Q1[예산 / 기간 분석]
        Q2[기술 스택 매칭]
        Q3[경쟁 강도 평가]
    end

    subgraph PROPOSE["제안"]
        P1[제안서 자동 생성\nwishket_development_request.py]
        P2[Discord 검토 알림]
        P3[사용자 승인 후 제출]
    end

    subgraph EXECUTE["실행"]
        E1[프로젝트 착수]
        E2[Claude Code 구현]
        E3[Codex 검수]
        E4[납품 + 수익 확정]
    end

    DISCOVER --> QUALIFY --> PROPOSE --> EXECUTE
    E4 -->|수익 기록| D1
```

---

## 5. mr.notion 구조 ↔ JH Brain System 매핑

| mr.notion 모듈 | JH Brain System 대응 | 파일/스크립트 |
|---|---|---|
| **The Narrative** | 시스템 철학·원칙 | `CLAUDE.md`, `BUCKY_CONTEXT.md` |
| **The Framework** | 라우팅·의사결정 | `ROUTING_RULES.md`, `context_pack_selector.py` |
| **Sales Blueprint** | Wishket 수익화 | `wishket_development_request.py` |
| **Customer Finance** | 예산·수익 추적 | `data/channel_tasks.db`, AI Usage 대시보드 |
| **Sales Funnel** | 공고 → 제안 → 낙찰 | `scripts/wishket_*.py` |
| **Hook Sets** | 트리거·자동화 | Discord 명령어, 크론 스케줄 |
| **Tech Stack** | 운영 인프라 | Python, Cloudflare, Discord Bot, Vercel |
| **Asset Library** | 지식 베이스 | `03_Knowledge/`, `06_Context_Packs/` |
| **Global Sharables** | 공유 보고서 | `docs/`, Discord 채널 보고 |
| **Departments** | 에이전트 역할 | Bucky / Claude / Codex |

---

## 6. 시스템 건강 지표 (KPI Dashboard)

```mermaid
flowchart LR
    subgraph INPUT_KPI["입력 지표"]
        I1["Discord 일일 명령 수\n목표: 5+/일"]
        I2["Wishket 신규 공고\n목표: 10+/주"]
        I3["ChatGPT 세션 수집\n목표: 3+/일"]
    end

    subgraph PROCESS_KPI["처리 지표"]
        P1["Context Pack 매칭 정확도\n목표: 90%+"]
        P2["에이전트 핸드오프 성공률\n목표: 95%+"]
        P3["Codex 검수 통과율\n목표: 85%+"]
    end

    subgraph OUTPUT_KPI["수익 지표"]
        O1["Wishket 월 낙찰 수\n목표: 2+/월"]
        O2["구독 대시보드 활성 유저\n추적 중"]
        O3["에이전트 자율 완료 태스크\n목표: 증가 추세"]
    end

    INPUT_KPI --> PROCESS_KPI --> OUTPUT_KPI
```

---

## 참고

- **원본 영상**: [@mr.notion](https://www.tiktok.com/@mr.notion/video/7635006262492613896) — Business Blueprint (Single Page Business OS)
- **핵심 인사이트**: "한 페이지에 전체 비즈니스" 컨셉 → JH는 `BUCKY_STATUS.md` 한 파일이 시스템 전체 상태를 반영
- **다음 적용 가능 개선**: 
  - [ ] Wishket 수익 추적 대시보드 추가
  - [ ] 에이전트별 KPI 자동 집계 스크립트
  - [ ] "Single Page OS" 스타일 Obsidian Canvas 파일 생성

## 관련 허브

- [[jh-system]] — JH 브레인 시스템 구조
- [[vault-galaxy-graph-bridge]] — Vault 전체 지식 허브
- [[bucky-evolution-pipeline]] — 워크플로우 파이프라인
