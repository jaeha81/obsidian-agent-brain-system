# Bucky OS Oracle Cloud + Obsidian Second Brain 아키텍처 플랜

> 문서 버전: v1.0  
> 작성일: 2026-07-07  
> 목적: 현재 진행 중인 **Oracle Cloud 기반 Bucky 운영체제**, **Obsidian Second Brain**, **Discord 연동**, **MCP/API 연결**, **다중 PC 운영 전략**을 하나의 실행 가능한 설계 문서와 체크리스트로 정리한다.

---

> ⚠️ **정정 2026-07-08 (재확정) — 이전 "오라클=풀브레인" 갱신 철회. 본 문서 본문이 확정.**
> 07-07에 삽입됐던 "오라클 = 풀 세컨드브레인(ObsidianVault + gbrain + Ollama 전부 오라클 상주)" 갱신은 **07-08 사용자 재번복으로 무효**.
> **현재 확정 = 본 문서 본문의 하이브리드**: 오라클 = 중앙 운영서버(오케스트레이터) + `obsidian-index`만 / 집 PC = Vault 원본·데이터·무거운 실행(gbrain·Ollama·PGLite 로컬) / Google Drive = 백업. → **§3.1·§4.1·§17·§25 유효(현재 진리).**
> 사용자 확정문: "Oracle Cloud가 명령하고, 로컬 PC들이 데이터를 보유하고 실행하는 하이브리드 AI 운영체제." 상세 = `latest-handoff.md` / memory `project_oci_homepc_split_direction`.

## 0. 핵심 결론 요약

현재 구축 방향은 다음 구조로 가는 것이 가장 안정적이다.

```text
[사용자]
   │
   ├─ Discord
   ├─ Claude Code
   ├─ Codex
   ├─ Claude App
   ├─ GPT / 웹 인터페이스
   │
   ▼
[Oracle Cloud: Bucky Core]
   ├─ Main Bucky Agent
   ├─ API Server
   ├─ MCP Server
   ├─ Agent Registry
   ├─ Task Queue
   ├─ Scheduler
   ├─ Workflow Engine
   ├─ Auth / Token 관리
   ├─ Logging / Monitoring
   └─ 중앙 지침 / 중앙 메모리 / 중앙 라우팅
   │
   ├─────────────── 집 PC: Main Workstation
   ├─────────────── 사무실 PC: Office Client
   └─────────────── 노트북: Mobile Client
```

핵심 원칙은 다음과 같다.

- **Oracle Cloud = Bucky 운영체제의 두뇌**
- **집 PC = 메인 작업장 + 원본 데이터 + 무거운 작업 처리**
- **사무실 PC = 업무용 클라이언트**
- **노트북 = 이동형 클라이언트**
- **Google Drive = 백업 / 동기화 / 문서 저장소**
- **Obsidian = Second Brain 지식 베이스**
- **MCP = Claude Code, Codex, 로컬 개발 도구 연결 통로**
- **API = GPT, 웹, Discord, 외부 서비스 연결 통로**
- **Bucky Agent = 모든 지침과 실행 흐름의 중앙 관리자**

---

# 1. 현재 상황 정리

## 1.1 현재 진행 중인 시스템

현재 구축 중인 시스템은 단순 챗봇이 아니라, 장기적으로 다음 역할을 수행하는 **AI 운영체제**에 가깝다.

- 개인 지식 관리
- 업무 자동화
- 인테리어 업무 보조
- 견적 / 문서 / 감리 / 협력사 대응
- 파일 정리
- 개발 자동화
- AI Agent 운영
- Discord 기반 명령 처리
- Oracle Cloud 기반 중앙 제어
- Obsidian 기반 Second Brain 운영
- 여러 PC에서 동일한 Bucky 시스템 사용

## 1.2 현재 고민한 핵심 문제

이번 대화에서 다룬 핵심 질문은 다음과 같다.

1. Obsidian Second Brain을 어디에 둬야 하는가?
2. Oracle Cloud와 로컬 PC의 역할을 어떻게 나눠야 하는가?
3. Claude Code, Codex, Claude App, GPT를 어떻게 Bucky와 연결할 것인가?
4. MCP와 API는 각각 어떤 역할을 해야 하는가?
5. 집 PC, 사무실 PC, 노트북을 동시에 또는 번갈아 쓰려면 어떻게 구성해야 하는가?
6. 상용화용 에이전트와 개인용 Bucky가 충돌하지 않게 하려면 어떻게 해야 하는가?
7. 로컬 상주 에이전트를 각 PC에 둘 경우, 지침과 기능 중복을 어떻게 막을 것인가?
8. Google Drive는 앞으로 어떤 역할로 제한해야 하는가?
9. Obsidian Graph View는 실제 시스템에서 어떤 의미를 가져야 하는가?

---

# 2. 최종 운영 방향

## 2.1 시스템의 큰 방향

최종 방향은 **중앙집중형 두뇌 + 분산형 실행 장비** 구조다.

```text
두뇌: Oracle Cloud의 Bucky Core
실행: 집 PC / 사무실 PC / 노트북
지식: Obsidian Vault
백업: Google Drive
개발 연결: MCP
웹 연결: API
```

즉, 모든 PC가 각각 독립적인 Bucky를 가지는 것이 아니라, **하나의 Bucky Core를 여러 PC가 함께 사용하는 방식**이다.

## 2.2 비유로 이해하기

```text
Oracle Bucky Core = 두뇌
집 PC = 메인 작업실
사무실 PC = 업무용 팔
노트북 = 이동용 팔
Google Drive = 창고
Obsidian = 기억 노트
MCP = 개발자용 전용 통로
API = 외부 서비스용 대문
Discord = 명령 입력 인터페이스
GPT = API를 통한 명령 전달자
Claude Code / Codex = MCP를 통한 개발 실행자
```

---

# 3. Oracle Cloud의 역할

## 3.1 Oracle Cloud는 무엇을 해야 하는가?

Oracle Cloud는 파일 저장소가 아니라 **Bucky OS의 중앙 운영 서버** 역할을 해야 한다.

### Oracle Cloud에 둘 것

- Bucky Main Agent
- API Server
- MCP Server
- Agent Registry
- Task Queue
- Scheduler
- Workflow Engine
- Auth / Token System
- Logging System
- Monitoring System
- 중앙 지침 파일
- 중앙 Agent 설정
- 외부 서비스 연결 설정
- Discord Bot Backend
- GPT / Claude / Codex 요청 라우팅

### Oracle Cloud에 넣지 않는 것이 좋은 것

- 모든 Obsidian 원본 데이터 전체
- CAD 원본 파일 전체
- 렌더링 이미지 전체
- 영상 원본 전체
- 대용량 AI 모델 파일
- 불필요한 백업 파일
- 개인 민감 문서 전체

## 3.2 Oracle Cloud의 핵심 기능

### 1) 명령 수신

Discord, API, MCP, CLI 등에서 들어오는 명령을 받는다.

예시:

```text
사용자: 버키야, 오늘 회의 내용 정리해줘.
Discord → Oracle Bucky API → Task Queue → Agent 실행
```

### 2) 명령 분류

Bucky는 명령의 성격을 판단한다.

- 지식 검색인가?
- 파일 정리인가?
- 문서 생성인가?
- 개발 작업인가?
- 사무실 PC에서 해야 하는가?
- 집 PC에서 해야 하는가?
- 클라우드 안에서 처리 가능한가?

### 3) 작업 분배

작업을 적절한 위치로 보낸다.

```text
간단한 문서 생성 → Oracle 내부 처리
Obsidian 검색 → 로컬/동기화 Vault 조회
CAD 변환 → 집 PC Local Agent 요청
업무 문서 생성 → Google Drive 저장
개발 작업 → Claude Code / Codex / MCP 연결
```

### 4) 결과 저장

작업 결과를 다음 위치에 저장한다.

- Obsidian 노트
- Google Drive 문서
- 프로젝트 폴더
- Discord 응답
- 로그 DB
- Task History

---

# 4. 집 PC의 역할

## 4.1 집 PC는 Main Workstation이다

집 PC는 가장 중요한 로컬 작업 장비다.

집 PC에는 다음 항목을 둔다.

- Obsidian Vault 원본 또는 가장 신뢰도 높은 사본
- 대용량 프로젝트 파일
- CAD 파일
- 렌더링 파일
- 영상 파일
- AI 모델 파일
- 개발 프로젝트 원본
- Local Agent
- 자동 백업 스크립트
- 파일 인덱싱 스크립트
- Bucky와 통신하는 로컬 실행기

## 4.2 집 PC가 담당할 작업

집 PC는 다음 작업을 담당한다.

- 대용량 파일 처리
- CAD / 도면 / 이미지 변환
- 로컬 파일 검색
- Obsidian Vault 관리
- 프로젝트 원본 보관
- AI 자동화 결과물 저장
- Google Drive 백업 기준점 역할
- 필요 시 로컬 서버 역할

## 4.3 집 PC 운영 체크리스트

- [ ] 집 PC에 `Bucky Local Agent` 설치
- [ ] 집 PC에 Obsidian Vault 기준 폴더 지정
- [ ] 대용량 파일 저장소 분리
- [ ] Google Drive 동기화 폴더 설정
- [ ] Oracle Bucky API 토큰 등록
- [ ] MCP 접속 설정 확인
- [ ] 자동 백업 스크립트 구성
- [ ] 파일 인덱싱 스크립트 구성
- [ ] 부팅 시 Local Agent 자동 실행 설정
- [ ] 로컬 방화벽 / 포트 정책 정리
- [ ] 민감 정보 파일 접근 권한 제한

---

# 5. 사무실 PC의 역할

## 5.1 사무실 PC는 Office Client이다

사무실 PC는 메인 저장소가 아니라, 업무용 클라이언트로 사용하는 것이 좋다.

사무실 PC의 역할은 다음과 같다.

- 업무 중 Bucky 접속
- Discord 명령 입력
- Claude Code / Codex 사용
- Obsidian 노트 확인 및 가벼운 수정
- 견적 / 감리 / 협력사 문서 작성
- 현장 업무 기록
- Google Drive 문서 확인
- 필요 시 Local Agent로 제한적 파일 처리

## 5.2 사무실 PC에는 최소한만 둔다

사무실 PC에 모든 원본 데이터를 넣으면 관리가 복잡해진다.

따라서 다음 기준으로 운영한다.

```text
필요한 것만 동기화한다.
무거운 것은 집 PC 또는 별도 저장소에 둔다.
사무실 PC는 작업 요청과 문서 작업 중심으로 쓴다.
```

## 5.3 사무실 PC 운영 체크리스트

- [ ] Obsidian 설치
- [ ] Google Drive 동기화 설정
- [ ] Bucky API 토큰 등록
- [ ] MCP 클라이언트 설정
- [ ] Claude Code 연결
- [ ] Codex 연결
- [ ] Discord Bot 명령 테스트
- [ ] 업무용 프로젝트 폴더만 동기화
- [ ] 대용량 원본 파일 동기화 제외
- [ ] Local Agent 설치 여부 결정
- [ ] 보안상 민감 파일 접근 제한

---

# 6. 노트북의 역할

## 6.1 노트북은 Mobile Client이다

노트북은 이동 중 작업과 긴급 수정용이다.

역할은 다음과 같다.

- 외부 미팅
- 발표
- 자료 확인
- 긴급 수정
- Obsidian 확인
- Claude / GPT / Discord 명령 입력
- 간단한 개발 작업
- Bucky 상태 확인

## 6.2 노트북 운영 기준

노트북은 가장 가볍게 유지한다.

```text
노트북에는 원본 데이터를 많이 넣지 않는다.
핵심 문서와 텍스트 노트 중심으로만 동기화한다.
무거운 작업은 집 PC 또는 Oracle Bucky에게 요청한다.
```

## 6.3 노트북 운영 체크리스트

- [ ] Obsidian 설치
- [ ] 최소 Vault 동기화 설정
- [ ] Google Drive 선택 동기화 설정
- [ ] Bucky API 토큰 등록
- [ ] Discord 명령 테스트
- [ ] Claude Code / Codex 필요 여부 결정
- [ ] 외부 네트워크 사용 시 보안 설정
- [ ] 민감 폴더 동기화 제외
- [ ] Local Agent 설치 여부 결정

---

# 7. Google Drive의 역할

## 7.1 Google Drive는 운영체제가 아니다

Google Drive는 Bucky의 두뇌가 아니다.

Google Drive는 다음 역할로 제한하는 것이 좋다.

- 백업
- 파일 동기화
- 문서 보관
- PDF 보관
- 이미지 보관
- Obsidian Markdown 동기화
- 협업 문서 공유

## 7.2 Google Drive에 적합한 데이터

- `.md` 노트
- PDF 자료
- 회의록
- 문서 초안
- 제안서
- 견적서
- 이미지 참고자료
- 작은 첨부파일
- 프로젝트 요약본

## 7.3 Google Drive에 부적합한 데이터

- 대용량 CAD 원본
- 영상 원본
- 렌더링 대용량 파일
- AI 모델 파일
- 대량 로그 파일
- 실행 중인 데이터베이스
- 실시간 Agent Memory 원본
- 충돌 가능성이 높은 작업 파일

## 7.4 Google Drive 사용 전략

### 권장 구조

```text
Google Drive/
└── BuckyOS/
    ├── 00_ObsidianVault/
    ├── 01_Backup/
    ├── 02_Documents/
    ├── 03_Project_Summary/
    ├── 04_Reference/
    └── 99_Archive/
```

### 사용 원칙

- Obsidian Markdown은 Google Drive로 동기화 가능
- 대용량 파일은 링크만 Obsidian에 기록
- 여러 PC에서 동시에 같은 노트 수정은 피하기
- 중요한 노트는 주기적으로 백업
- Drive는 창고, Oracle은 두뇌, 집 PC는 작업장으로 분리

## 7.5 Google Drive 체크리스트

- [ ] `BuckyOS` 최상위 폴더 생성
- [ ] Obsidian Vault 폴더 분리
- [ ] 문서 폴더 분리
- [ ] 프로젝트 요약 폴더 분리
- [ ] 대용량 파일 동기화 제외
- [ ] 충돌 파일 발생 여부 주기 확인
- [ ] 자동 백업 주기 설정
- [ ] 휴지통 / 중복 파일 정리 루틴 만들기

---

# 8. Obsidian Second Brain 전략

## 8.1 Obsidian의 진짜 역할

Obsidian은 단순 메모장이 아니라, Bucky가 참고할 수 있는 **지식 베이스**다.

Obsidian의 목적은 다음과 같다.

- 생각 저장
- 업무 기록
- 프로젝트 정리
- 지식 연결
- AI Context 제공
- 반복 업무 매뉴얼화
- 개인 운영체제 문서화
- 사업 아이디어 축적
- 상용 Agent 기획 정리

## 8.2 Graph View에 대한 관점

Graph View는 목표가 아니라 결과물이다.

좋은 Second Brain은 그래프가 예쁜 것이 아니라, 필요한 정보를 빠르게 찾고 재사용할 수 있어야 한다.

따라서 Graph View는 다음 용도로만 사용한다.

- 지식 연결 확인
- 주제 간 관계 파악
- 고립된 노트 발견
- 너무 복잡해진 구조 점검
- 핵심 주제 허브 확인

## 8.3 Obsidian에서 중요한 구조

Graph View보다 중요한 것은 다음이다.

- MOC
- 태그
- 폴더 구조
- 프로젝트 노트
- 데일리 노트
- 작업 큐
- 링크 규칙
- 프론트매터
- Agent가 읽기 쉬운 문서 형식

## 8.4 권장 Obsidian Vault 구조

```text
ObsidianVault/
├── 00_Inbox/
├── 01_Daily/
├── 02_Projects/
├── 03_Areas/
├── 04_Resources/
├── 05_MOC/
├── 06_Agent_Memory/
├── 07_Bucky_OS/
├── 08_Business/
├── 09_Interior/
├── 10_AI_Automation/
├── 11_Investment/
├── 12_Template/
└── 99_Archive/
```

## 8.5 각 폴더 역할

### `00_Inbox`

빠르게 저장하는 임시함이다.

- 갑자기 떠오른 아이디어
- 회의 중 메모
- 현장 메모
- 미정리 자료
- 나중에 분류할 내용

### `01_Daily`

하루 단위 기록이다.

- 오늘 한 일
- 오늘 받은 지시
- 오늘의 문제
- 오늘의 아이디어
- 오늘의 업무 기록
- 버키에게 시킬 작업

### `02_Projects`

진행 중인 프로젝트를 관리한다.

예시:

```text
02_Projects/
├── Bucky_OS/
├── Interior_Automation/
├── Estimate_System/
├── Discord_Bot/
├── Oracle_Migration/
└── AI_Monetization/
```

### `03_Areas`

계속 유지해야 하는 책임 영역이다.

예시:

- 회사 업무
- 인테리어 시공
- 협력사 관리
- 견적 상담
- 감리 업무
- AI 사업
- 투자 공부

### `04_Resources`

참고자료 저장소다.

- AI 자료
- 개발 자료
- 인테리어 자료
- 법규 자료
- 마케팅 자료
- 자동화 자료

### `05_MOC`

Map of Content이다.

각 주제별 메인 지도 노트다.

예시:

- `MOC_Bucky_OS.md`
- `MOC_Oracle_Cloud.md`
- `MOC_Obsidian_SecondBrain.md`
- `MOC_AI_Automation.md`
- `MOC_Interior_Business.md`
- `MOC_Monetization.md`

### `06_Agent_Memory`

AI Agent가 읽기 쉬운 기억 저장소다.

- 사용자 선호
- Bucky 지침
- 반복 업무 규칙
- 프로젝트별 컨텍스트
- 금지사항
- 자동화 규칙
- 응답 스타일
- 비즈니스 목표

### `07_Bucky_OS`

Bucky 운영체제 설계 문서다.

- API 구조
- MCP 구조
- Agent 구조
- Discord 구조
- Memory 구조
- Scheduler 구조
- Task Queue 구조
- 보안 정책

### `08_Business`

수익화 / 사업화 관련 자료다.

- AI 자동화 사업
- 광고 수익 모델
- 웹 기반 수익화
- 콘텐츠 자동화
- SaaS 기획
- 고객용 Agent 기획

### `09_Interior`

인테리어 업무 지식 베이스다.

- 견적
- 시공
- 감리
- 현장관리
- 협력사
- 자재
- 공정표
- 클라이언트 대응

### `10_AI_Automation`

Make.com, n8n, API, Agent 자동화 자료를 관리한다.

### `11_Investment`

주식, 가상화폐, 시장 분석 자료를 관리한다.

### `12_Template`

반복 사용할 템플릿이다.

- 회의록 템플릿
- 프로젝트 노트 템플릿
- 견적 상담 템플릿
- Agent 지침 템플릿
- API 문서 템플릿
- 업무 보고 템플릿

### `99_Archive`

완료되었거나 사용 빈도가 낮은 자료 보관소다.

---

# 9. Obsidian 노트 작성 규칙

## 9.1 모든 노트에 기본 메타데이터 추가

권장 프론트매터 형식:

```yaml
---
type: project
status: active
created: 2026-07-07
updated: 2026-07-07
tags:
  - bucky
  - oracle
  - second-brain
related:
  - MOC_Bucky_OS
  - MOC_Oracle_Cloud
---
```

## 9.2 노트 제목 규칙

권장 형식:

```text
YYYY-MM-DD_주제_상세내용.md
```

예시:

```text
2026-07-07_BuckyOS_OracleCloud_Architecture.md
2026-07-07_Obsidian_SecondBrain_Structure.md
2026-07-07_MCP_API_Strategy.md
```

## 9.3 Agent가 읽기 쉬운 노트 형식

Bucky가 읽기 쉽게 하기 위해 노트는 다음 구조를 권장한다.

```markdown
# 제목

## 목적

## 현재 상태

## 결정사항

## 해야 할 일

## 참고 링크

## 관련 노트
```

## 9.4 태그 규칙

권장 태그:

```text
#bucky
#oracle
#mcp
#api
#obsidian
#second-brain
#discord
#automation
#interior
#business
#agent
#local-agent
#google-drive
#memory
#workflow
```

---

# 10. MCP 전략

## 10.1 MCP의 역할

MCP는 로컬 개발 환경과 Bucky를 연결하는 통로다.

사용 대상:

- Claude Code
- Codex
- Claude App
- 로컬 CLI
- 개발용 Agent
- 파일 시스템 도구
- 코드 편집 도구

## 10.2 MCP 연결 구조

```text
Claude Code / Codex / Claude App
        │
        ▼
      MCP
        │
        ▼
Oracle Bucky MCP Server
        │
        ▼
Bucky Core
```

## 10.3 MCP로 처리하기 좋은 작업

- 로컬 파일 읽기
- 코드 분석
- 프로젝트 구조 파악
- 개발 명령 실행
- Obsidian 노트 검색
- 작업 폴더 접근
- Agent 도구 호출
- Bucky 메모리 검색

## 10.4 MCP 체크리스트

- [ ] Oracle Cloud에 MCP Server 구성
- [ ] MCP Server 인증 토큰 설정
- [ ] Claude Code에 MCP 연결
- [ ] Codex에 MCP 연결
- [ ] Claude App에 MCP 연결 가능 여부 확인
- [ ] 각 PC별 MCP 설정 파일 분리
- [ ] 공통 MCP 설정 템플릿 생성
- [ ] 접근 가능한 폴더 제한
- [ ] 읽기 전용 / 쓰기 가능 권한 구분
- [ ] 작업 로그 저장
- [ ] 실패 시 재시도 로직 구성

---

# 11. API 전략

## 11.1 API의 역할

API는 웹, GPT, Discord, 외부 서비스가 Bucky에게 명령을 보내는 대문이다.

```text
GPT / Web / Discord / Mobile
        │
        ▼
      API
        │
        ▼
Oracle Bucky Core
```

## 11.2 API로 처리하기 좋은 작업

- GPT에서 Bucky에게 명령 전달
- 웹 대시보드에서 작업 요청
- Discord Bot 명령 처리
- Make.com / n8n 자동화 연결
- 외부 서비스 Webhook 수신
- 작업 상태 조회
- 결과물 다운로드
- 문서 생성 요청

## 11.3 API Endpoint 예시

```text
POST /api/v1/tasks
GET  /api/v1/tasks/{task_id}
POST /api/v1/agents/bucky/run
POST /api/v1/memory/search
POST /api/v1/obsidian/search
POST /api/v1/discord/command
POST /api/v1/local-agent/dispatch
GET  /api/v1/system/status
```

## 11.4 API 체크리스트

- [ ] Bucky API Server 구성
- [ ] 인증 토큰 방식 결정
- [ ] GPT 연결용 Endpoint 구성
- [ ] Discord Bot 연결용 Endpoint 구성
- [ ] Make.com / n8n Webhook 연결
- [ ] 작업 요청 스키마 정의
- [ ] 응답 포맷 정의
- [ ] Error Handling 규칙 정의
- [ ] Rate Limit 설정
- [ ] 로그 저장
- [ ] 외부 공개 Endpoint와 내부 Endpoint 분리

---

# 12. GPT 연결 전략

## 12.1 GPT는 MCP에 직접 연결하지 않는다

GPT는 MCP를 직접 사용하는 구조가 아니라, API를 통해 Bucky에게 요청을 보내는 구조가 적합하다.

```text
GPT
 │
 ▼
Bucky API
 │
 ▼
Oracle Bucky Core
 │
 ├─ Obsidian 검색
 ├─ Local Agent 요청
 ├─ Discord 응답
 ├─ 문서 생성
 └─ 작업 큐 등록
```

## 12.2 GPT의 역할

GPT는 다음 역할로 쓰는 것이 좋다.

- 자연어 명령 입력
- Bucky에게 요청 전달
- 결과 해석
- 문서화
- 아이디어 정리
- 전략 수립
- 사용자가 쉽게 명령할 수 있는 대화 인터페이스

## 12.3 GPT가 직접 하면 안 좋은 것

- 로컬 파일 직접 제어
- 민감 데이터 직접 저장
- 모든 메모리 원본 관리
- Agent 전체 실행 책임
- Obsidian 원본 직접 수정

## 12.4 GPT 연결 체크리스트

- [ ] Bucky API에 GPT용 Endpoint 생성
- [ ] 명령 요청 스키마 정의
- [ ] 응답 포맷 정의
- [ ] 민감 정보 필터링 규칙 작성
- [ ] GPT가 실행 가능한 명령 범위 정의
- [ ] GPT가 실행하면 안 되는 명령 범위 정의
- [ ] 승인 필요 작업 구분
- [ ] 결과를 Obsidian에 저장할지 여부 결정

---

# 13. Discord 연동 전략

## 13.1 Discord는 명령 센터로 사용한다

현재 Bucky OS가 Discord와 연동되고 있으므로, Discord는 빠른 명령 입력 채널로 유지하는 것이 좋다.

## 13.2 Discord 명령 예시

```text
/bucky status
/bucky search 옵시디언 MCP 구조
/bucky task add 오늘 회의록 정리
/bucky obsidian save "새로운 아이디어"
/bucky agent run estimate-ai
/bucky local home-pc convert-cad-to-pdf
/bucky plan oracle-migration
```

## 13.3 Discord 역할

- 명령 입력
- 작업 상태 확인
- 알림 수신
- 자동화 결과 확인
- 긴급 명령 실행
- 작업 큐 관리

## 13.4 Discord 체크리스트

- [ ] Discord Bot 명령어 체계 정리
- [ ] Bucky API와 Discord Bot 연결
- [ ] 작업 큐 등록 명령 만들기
- [ ] 상태 조회 명령 만들기
- [ ] Obsidian 저장 명령 만들기
- [ ] Agent 실행 명령 만들기
- [ ] 권한 있는 사용자만 실행 가능하게 설정
- [ ] 위험 명령은 승인 단계 추가
- [ ] 로그 채널 생성
- [ ] 에러 알림 채널 생성

---

# 14. Local Agent 전략

## 14.1 Local Agent의 개념

각 PC에 상주하는 Local Agent는 Bucky의 지시를 받아 자기 PC 안에서 작업을 실행하는 작은 실행기다.

중요한 점:

```text
Local Agent는 두뇌가 아니다.
Local Agent는 실행 도구다.
두뇌와 지침은 Oracle Bucky Core에 있다.
```

## 14.2 Local Agent 역할

- 로컬 파일 접근
- 폴더 검색
- 프로그램 실행
- 파일 변환
- Obsidian Vault 접근
- 특정 PC에서만 가능한 작업 실행
- 결과를 Oracle Bucky에게 반환

## 14.3 Local Agent가 가지면 안 되는 것

- 독립적인 Bucky 지침
- 별도 장기 메모리
- 별도 의사결정 체계
- 상용 Agent 핵심 로직
- 민감 정보 전체 복사본

## 14.4 Local Agent 구조

```text
Oracle Bucky Core
    │
    ├── home-pc-agent
    ├── office-pc-agent
    └── laptop-agent
```

각 Agent는 다음처럼 등록한다.

```yaml
agent_id: home-pc-agent
role: main-workstation
allowed_paths:
  - D:/BuckyOS
  - D:/ObsidianVault
  - D:/Projects
capabilities:
  - file_search
  - file_write
  - cad_convert
  - image_process
  - backup
status: active
```

## 14.5 Local Agent 체크리스트

- [ ] 각 PC별 Agent ID 지정
- [ ] 각 PC별 허용 폴더 지정
- [ ] 각 PC별 실행 가능 명령 지정
- [ ] Oracle Bucky와 통신 방식 결정
- [ ] 인증 토큰 설정
- [ ] 부팅 시 자동 실행 설정
- [ ] 작업 로그 저장
- [ ] 실패 시 재시도 방식 구성
- [ ] 위험 명령 승인 절차 추가
- [ ] 각 PC Agent 상태 확인 명령 만들기

---

# 15. 중앙 지침 관리 전략

## 15.1 지침은 한 곳에만 둔다

각 PC에 별도의 Bucky 지침을 만들면 관리가 복잡해진다.

따라서 원칙은 다음과 같다.

```text
Bucky의 핵심 지침은 Oracle Cloud에만 둔다.
각 PC는 필요할 때 중앙 지침을 불러와 실행한다.
```

## 15.2 중앙 지침 구조

```text
BuckyCore/
└── instructions/
    ├── main_system_prompt.md
    ├── user_profile.md
    ├── response_rules.md
    ├── business_rules.md
    ├── safety_rules.md
    ├── local_agent_rules.md
    ├── obsidian_rules.md
    ├── discord_rules.md
    └── commercial_agent_rules.md
```

## 15.3 중앙 지침 체크리스트

- [ ] Main System Prompt 작성
- [ ] 사용자 프로필 정리
- [ ] 응답 스타일 규칙 작성
- [ ] 업무 처리 규칙 작성
- [ ] Local Agent 행동 규칙 작성
- [ ] Obsidian 작성 규칙 작성
- [ ] Discord 명령 규칙 작성
- [ ] 상용 Agent 분리 규칙 작성
- [ ] 위험 작업 승인 규칙 작성
- [ ] 버전 관리 방식 결정

---

# 16. 상용 Agent 분리 전략

## 16.1 개인 Bucky와 상용 Agent를 섞지 않는다

상용화를 고려한다면 가장 중요한 원칙은 분리다.

```text
Bucky = 개인 운영체제 / 플랫폼 코어
Commercial Agent = 별도 상품 / 별도 프로젝트 / 별도 배포 단위
```

## 16.2 권장 폴더 구조

```text
BuckySystem/
├── core/
│   └── bucky/
│
├── agents/
│   ├── personal/
│   │   └── bucky-main/
│   │
│   └── commercial/
│       ├── interior-estimate-ai/
│       ├── site-supervision-ai/
│       ├── document-agent/
│       ├── marketing-agent/
│       └── client-support-agent/
│
├── shared/
│   ├── llm-client/
│   ├── auth/
│   ├── file-utils/
│   ├── prompt-utils/
│   └── api-utils/
│
└── projects/
    ├── bucky-os/
    ├── interior-ai/
    └── monetization-system/
```

## 16.3 상용 Agent 분리 기준

상용 Agent는 다음을 분리해야 한다.

- 지침
- 메모리
- API Key
- 고객 데이터
- 로그
- 작업 큐
- 권한
- 배포 환경
- 수익 모델

## 16.4 상용 Agent 체크리스트

- [ ] 개인 Bucky와 상용 Agent 폴더 분리
- [ ] 상용 Agent별 독립 지침 작성
- [ ] 상용 Agent별 데이터 저장소 분리
- [ ] 고객 데이터와 개인 데이터 완전 분리
- [ ] 공통 모듈만 shared로 분리
- [ ] 상용 Agent별 API Endpoint 분리
- [ ] 상용 Agent별 로그 분리
- [ ] 상용 Agent별 권한 분리
- [ ] 테스트 환경과 운영 환경 분리
- [ ] 배포 전 보안 점검 체크리스트 작성

---

# 17. 데이터 저장 위치 결정표

| 데이터 종류 | 권장 저장 위치 | 이유 |
|---|---|---|
| Bucky Core 코드 | Oracle Cloud + Git | 운영 중심 |
| API 서버 | Oracle Cloud | 외부 연결 필요 |
| MCP 서버 | Oracle Cloud 또는 PC별 로컬 | 개발 도구 연결 |
| Obsidian Vault | 집 PC + Google Drive 동기화 | 빠른 접근 + 백업 |
| 대용량 CAD | 집 PC | 용량 / 속도 |
| 영상 원본 | 집 PC / 외장 저장소 | 대용량 |
| 문서 PDF | Google Drive | 백업 / 공유 |
| Agent 지침 | Oracle Cloud | 단일 원천 유지 |
| Local Agent 설정 | 각 PC + Oracle Registry | PC별 제어 |
| 작업 로그 | Oracle Cloud | 중앙 기록 |
| 상용 고객 데이터 | 별도 저장소 | 보안 / 분리 |
| 투자 자료 | Obsidian + Drive | 지식화 |
| 사업 아이디어 | Obsidian | 장기 축적 |

---

# 18. 충돌 방지 전략

## 18.1 Obsidian 충돌 방지

Google Drive에 Obsidian Vault를 두면 여러 PC에서 접근할 수 있지만, 동시에 같은 파일을 수정하면 충돌이 생길 수 있다.

### 방지 원칙

- 한 번에 한 PC에서 주로 편집한다.
- 다른 PC에서는 읽기 중심으로 사용한다.
- Daily Note는 PC별 임시 노트로 분리할 수 있다.
- 충돌 파일은 주기적으로 점검한다.
- 중요한 노트는 Bucky가 자동 백업한다.

## 18.2 Agent 충돌 방지

- 같은 작업을 여러 Agent가 동시에 실행하지 않게 Task Lock 사용
- 작업 ID 부여
- PC별 Agent ID 분리
- 파일 작업 전 Lock 생성
- 작업 완료 후 Lock 해제
- 실패 시 Lock 자동 해제 시간 설정

## 18.3 프로젝트 충돌 방지

- 개인 Bucky와 상용 Agent 분리
- 프로젝트별 환경변수 분리
- 프로젝트별 폴더 분리
- 프로젝트별 로그 분리
- 프로젝트별 API Endpoint 분리

## 18.4 충돌 방지 체크리스트

- [ ] Obsidian 동시 편집 규칙 작성
- [ ] 파일 Lock 시스템 구현
- [ ] Task ID 발급 방식 구현
- [ ] Agent별 작업 범위 제한
- [ ] 프로젝트별 환경변수 분리
- [ ] 로그 파일 분리
- [ ] 백업 주기 설정
- [ ] 충돌 파일 탐지 스크립트 작성

---

# 19. 권한과 보안 전략

## 19.1 기본 원칙

Bucky OS는 여러 PC와 클라우드를 연결하므로 보안을 처음부터 설계해야 한다.

핵심 원칙:

```text
모든 Agent는 필요한 권한만 가진다.
모든 외부 요청은 인증을 거친다.
위험 작업은 승인 절차를 거친다.
개인 데이터와 상용 데이터는 분리한다.
```

## 19.2 권한 등급

### Level 0: 읽기 전용

- 노트 검색
- 문서 조회
- 상태 확인

### Level 1: 일반 작업

- 노트 생성
- 문서 초안 생성
- 요약 생성
- 작업 큐 등록

### Level 2: 로컬 파일 작업

- 파일 이동
- 파일 복사
- 폴더 생성
- 변환 작업

### Level 3: 위험 작업

- 파일 삭제
- 대량 수정
- 배포
- 고객 데이터 접근
- 외부 전송

### Level 4: 관리자 작업

- Agent 설정 변경
- API Key 변경
- 서버 설정 변경
- 권한 변경

## 19.3 보안 체크리스트

- [ ] API 인증 토큰 설정
- [ ] MCP 인증 설정
- [ ] Local Agent별 토큰 분리
- [ ] PC별 권한 분리
- [ ] 외부 공개 API 최소화
- [ ] 위험 명령 승인 절차 추가
- [ ] 로그에 민감 정보 저장 금지
- [ ] API Key 환경변수 관리
- [ ] Google Drive 공유 권한 점검
- [ ] Obsidian 민감 노트 별도 관리

---

# 20. Bucky Task Queue 설계

## 20.1 Task Queue가 필요한 이유

여러 PC와 여러 Agent가 동시에 작업할 수 있기 때문에 작업 큐가 필요하다.

작업 큐는 다음을 관리한다.

- 어떤 작업이 들어왔는가?
- 어떤 Agent가 처리해야 하는가?
- 현재 작업 상태는 무엇인가?
- 실패했는가?
- 재시도해야 하는가?
- 결과는 어디에 저장되었는가?

## 20.2 Task 상태값

```text
pending      = 대기 중
assigned     = Agent 배정 완료
running      = 실행 중
waiting      = 사용자 승인 대기
completed    = 완료
failed       = 실패
cancelled    = 취소됨
```

## 20.3 Task 예시

```json
{
  "task_id": "task_20260707_001",
  "source": "discord",
  "requested_by": "jaeha",
  "target_agent": "home-pc-agent",
  "task_type": "obsidian_save",
  "priority": "normal",
  "status": "pending",
  "payload": {
    "title": "Oracle Cloud Bucky OS 구조 정리",
    "content": "오늘 대화 내용을 정리해서 Obsidian에 저장"
  }
}
```

## 20.4 Task Queue 체크리스트

- [ ] Task ID 생성 규칙 정의
- [ ] 작업 상태값 정의
- [ ] 우선순위 정의
- [ ] Agent 배정 규칙 정의
- [ ] 실패 재시도 규칙 정의
- [ ] 작업 완료 후 결과 저장 위치 정의
- [ ] 사용자 승인 필요한 작업 구분
- [ ] Discord에서 작업 상태 확인 명령 만들기

---

# 21. Bucky Agent Registry 설계

## 21.1 Agent Registry란?

Agent Registry는 현재 사용 가능한 Agent 목록과 능력을 관리하는 시스템이다.

## 21.2 등록할 Agent 예시

```yaml
agents:
  - id: bucky-main
    type: core
    location: oracle
    role: central-brain
    status: active

  - id: home-pc-agent
    type: local
    location: home-pc
    role: main-workstation
    status: active

  - id: office-pc-agent
    type: local
    location: office-pc
    role: office-client
    status: standby

  - id: laptop-agent
    type: local
    location: laptop
    role: mobile-client
    status: standby

  - id: interior-estimate-ai
    type: commercial
    location: oracle
    role: estimate-generator
    status: development
```

## 21.3 Agent Registry 체크리스트

- [ ] Agent ID 규칙 정의
- [ ] Agent Type 정의
- [ ] Agent Location 정의
- [ ] Agent Capability 정의
- [ ] Agent Status 정의
- [ ] Agent별 권한 정의
- [ ] Agent별 접근 가능한 데이터 정의
- [ ] Agent 상태 확인 API 만들기
- [ ] Discord에서 Agent 상태 확인 명령 만들기

---

# 22. 실행 단계별 플랜

## Phase 1. 구조 확정

목표: 시스템의 역할 분리를 완료한다.

- [ ] Oracle Cloud 역할 확정
- [ ] 집 PC 역할 확정
- [ ] 사무실 PC 역할 확정
- [ ] 노트북 역할 확정
- [ ] Google Drive 역할 확정
- [ ] Obsidian Vault 위치 결정
- [ ] MCP / API 역할 분리 확정

완료 기준:

```text
각 구성 요소가 무엇을 담당하는지 문서로 정리되어 있다.
```

---

## Phase 2. Obsidian Second Brain 정리

목표: Bucky가 읽기 쉬운 Obsidian 구조를 만든다.

- [ ] Vault 폴더 구조 생성
- [ ] MOC 노트 생성
- [ ] Daily Note 템플릿 생성
- [ ] Project Note 템플릿 생성
- [ ] Agent Memory 폴더 생성
- [ ] Bucky OS 설계 폴더 생성
- [ ] 태그 규칙 정의
- [ ] 노트 제목 규칙 정의

완료 기준:

```text
Obsidian이 단순 메모장이 아니라 Bucky의 지식 베이스로 동작할 준비가 되어 있다.
```

---

## Phase 3. Oracle Bucky Core 구성

목표: Oracle Cloud 안에 Bucky 중앙 시스템을 구성한다.

- [ ] API Server 실행
- [ ] MCP Server 실행
- [ ] Discord Bot Backend 연결
- [ ] Agent Registry 구성
- [ ] Task Queue 구성
- [ ] Scheduler 구성
- [ ] Logging 구성
- [ ] Auth Token 구성

완료 기준:

```text
Discord 또는 API를 통해 Bucky에게 명령을 보낼 수 있다.
```

---

## Phase 4. Local Agent 구성

목표: 각 PC를 Bucky의 실행 장비로 연결한다.

- [ ] 집 PC Agent 설치
- [ ] 사무실 PC Agent 설치 여부 결정
- [ ] 노트북 Agent 설치 여부 결정
- [ ] 각 Agent ID 등록
- [ ] 허용 폴더 설정
- [ ] 실행 가능 명령 설정
- [ ] Oracle Bucky와 연결 테스트
- [ ] 상태 확인 명령 구현

완료 기준:

```text
Oracle Bucky가 특정 PC에게 작업을 지시할 수 있다.
```

---

## Phase 5. MCP 연결

목표: Claude Code, Codex 등 개발 도구가 Bucky를 사용할 수 있게 만든다.

- [ ] Claude Code MCP 연결
- [ ] Codex MCP 연결
- [ ] Claude App MCP 연결 가능 여부 확인
- [ ] MCP Tool 목록 정리
- [ ] Obsidian 검색 Tool 구성
- [ ] 파일 시스템 Tool 구성
- [ ] Agent 실행 Tool 구성
- [ ] 권한 제한 설정

완료 기준:

```text
Claude Code 또는 Codex에서 Bucky MCP를 통해 지식 검색과 작업 요청이 가능하다.
```

---

## Phase 6. API 연결

목표: GPT, 웹, Make.com, n8n이 Bucky와 연결되도록 한다.

- [ ] GPT 요청용 API 설계
- [ ] Webhook Endpoint 구성
- [ ] Make.com 연결
- [ ] n8n 연결 가능성 검토
- [ ] Discord API 연결 안정화
- [ ] 작업 결과 조회 API 구성
- [ ] API 로그 저장

완료 기준:

```text
웹 또는 GPT를 통해 Bucky에게 명령을 전달할 수 있다.
```

---

## Phase 7. 상용 Agent 분리

목표: 개인 Bucky와 상용 Agent를 충돌 없이 분리한다.

- [ ] 상용 Agent 폴더 생성
- [ ] 공통 모듈 shared 분리
- [ ] Agent별 지침 분리
- [ ] Agent별 메모리 분리
- [ ] Agent별 API 분리
- [ ] 고객 데이터 저장소 분리
- [ ] 테스트 환경 구성
- [ ] 배포 환경 구성

완료 기준:

```text
개인 Bucky를 건드리지 않고 상용 Agent를 개발할 수 있다.
```

---

# 23. 추천 최종 폴더 구조

## 23.1 Oracle Cloud 폴더 구조

```text
/opt/bucky-os/
├── core/
│   ├── api-server/
│   ├── mcp-server/
│   ├── agent-router/
│   ├── task-queue/
│   ├── scheduler/
│   └── auth/
│
├── agents/
│   ├── bucky-main/
│   ├── local-agent-controller/
│   └── commercial/
│       ├── interior-estimate-ai/
│       ├── document-agent/
│       └── marketing-agent/
│
├── memory/
│   ├── main/
│   ├── obsidian-index/
│   ├── project-context/
│   └── user-profile/
│
├── instructions/
│   ├── main_system_prompt.md
│   ├── user_profile.md
│   ├── local_agent_rules.md
│   ├── obsidian_rules.md
│   └── commercial_agent_rules.md
│
├── config/
│   ├── agents.yaml
│   ├── permissions.yaml
│   ├── routes.yaml
│   └── environment.example
│
├── logs/
│   ├── api/
│   ├── mcp/
│   ├── discord/
│   └── agents/
│
└── scripts/
    ├── backup.sh
    ├── restart.sh
    └── healthcheck.sh
```

## 23.2 집 PC 폴더 구조

```text
D:/BuckyOS/
├── ObsidianVault/
├── Projects/
│   ├── BuckyOS/
│   ├── InteriorAI/
│   ├── EstimateAI/
│   └── Automation/
│
├── LargeFiles/
│   ├── CAD/
│   ├── Rendering/
│   ├── Video/
│   └── AI_Models/
│
├── LocalAgent/
│   ├── config/
│   ├── logs/
│   └── scripts/
│
├── Backups/
└── Sync/
    └── GoogleDrive/
```

## 23.3 Google Drive 폴더 구조

```text
Google Drive/BuckyOS/
├── 00_ObsidianVault/
├── 01_Backup/
├── 02_Documents/
├── 03_Project_Summary/
├── 04_Reference/
├── 05_Export/
└── 99_Archive/
```

---

# 24. 우선순위 체크리스트

## 가장 먼저 해야 할 것

- [ ] Obsidian Vault 최종 위치 결정
- [ ] Google Drive 동기화 범위 결정
- [ ] Oracle Cloud Bucky Core 폴더 구조 생성
- [ ] Bucky 중앙 지침 파일 생성
- [ ] Discord 명령 체계 정리
- [ ] API와 MCP 역할 분리 문서화

## 그다음 해야 할 것

- [ ] 집 PC Local Agent 구성
- [ ] Claude Code MCP 연결
- [ ] Codex MCP 연결
- [ ] GPT API 연결 방식 정리
- [ ] Task Queue 구현
- [ ] Agent Registry 구현

## 이후 해야 할 것

- [ ] 상용 Agent 폴더 분리
- [ ] 인테리어 견적 Agent 기획
- [ ] 문서 자동화 Agent 기획
- [ ] Make.com / n8n 연결
- [ ] 웹 대시보드 기획
- [ ] 수익화용 서비스 분리

---

# 25. 오늘 대화에서 확정된 결정사항

## 결정 1. Oracle Cloud는 저장소보다 운영체제 역할로 쓴다

Oracle Cloud에는 Bucky Core, API, MCP, Agent 관리 기능을 둔다.

## 결정 2. Obsidian은 로컬 중심 + Google Drive 동기화 전략이 적합하다

모든 데이터를 Oracle에 올리지 않고, Obsidian Vault는 집 PC와 Google Drive 중심으로 운영한다.

## 결정 3. 집 PC를 Main PC로 사용한다

집 PC가 원본 데이터와 무거운 작업을 담당한다.

## 결정 4. 사무실 PC와 노트북은 하이브리드 클라이언트로 사용한다

사무실 PC와 노트북은 Bucky 접속과 가벼운 작업 중심으로 쓴다.

## 결정 5. MCP와 API는 역할이 다르다

```text
MCP = Claude Code / Codex / 로컬 개발 도구 연결
API = GPT / 웹 / Discord / 자동화 서비스 연결
```

## 결정 6. GPT는 API로 Bucky에게 명령을 전달한다

GPT가 MCP를 직접 쓰는 것이 아니라, Bucky API를 통해 명령 전달자 역할을 한다.

## 결정 7. Local Agent는 실행기이고, 두뇌는 아니다

각 PC에 Local Agent를 둘 수 있지만, 지침과 기억은 Oracle Bucky Core에서 관리한다.

## 결정 8. 상용 Agent는 개인 Bucky와 분리한다

상용화할 Agent는 별도 폴더, 별도 지침, 별도 메모리, 별도 API로 분리해야 한다.

---

# 26. 최종 목표 이미지

최종적으로 만들고 있는 것은 단순한 자동화 봇이 아니다.

```text
Bucky OS = 개인 AI 운영체제
Obsidian = 장기 기억
Oracle Cloud = 중앙 두뇌
집 PC = 메인 작업장
사무실 PC = 업무 터미널
노트북 = 이동 터미널
Discord = 명령 센터
Claude Code / Codex = 개발 실행 도구
GPT = 전략 / 문서화 / API 명령 인터페이스
Google Drive = 백업 창고
상용 Agent = Bucky 플랫폼 위에서 분리 운영되는 상품
```

---

# 27. 다음 액션

바로 다음 단계는 아래 순서가 좋다.

## Step 1. Obsidian Vault 구조 생성

- [ ] 위 폴더 구조대로 Vault 생성
- [ ] `MOC_Bucky_OS.md` 생성
- [ ] `MOC_Oracle_Cloud.md` 생성
- [ ] `MOC_Obsidian_SecondBrain.md` 생성
- [ ] `MOC_MCP_API_Strategy.md` 생성

## Step 2. Bucky 중앙 지침 문서 생성

- [ ] `main_system_prompt.md`
- [ ] `local_agent_rules.md`
- [ ] `obsidian_rules.md`
- [ ] `discord_rules.md`
- [ ] `commercial_agent_rules.md`

## Step 3. Oracle Cloud 폴더 구조 정리

- [ ] `/opt/bucky-os/` 기준으로 구조 생성
- [ ] API / MCP / Agent 폴더 분리
- [ ] config / logs / instructions 분리

## Step 4. 집 PC Local Agent 설계

- [ ] 집 PC Agent ID 정하기
- [ ] 접근 가능 폴더 정하기
- [ ] 실행 가능 명령 정하기
- [ ] Oracle Bucky와 연결 방식 정하기

## Step 5. Discord 명령 체계 정리

- [ ] `/bucky status`
- [ ] `/bucky task add`
- [ ] `/bucky search`
- [ ] `/bucky obsidian save`
- [ ] `/bucky agent run`
- [ ] `/bucky local home-pc`

---

# 28. 최종 운영 원칙

이 시스템은 다음 원칙을 지켜야 한다.

```text
하나의 Bucky Core
하나의 중앙 지침
하나의 Second Brain
여러 개의 실행 장비
여러 개의 AI 인터페이스
프로젝트별 완전 분리
개인 데이터와 상용 데이터 분리
Google Drive는 창고
Oracle Cloud는 두뇌
집 PC는 작업장
MCP는 개발 통로
API는 외부 연결 통로
```

---

# 29. 한 줄 정의

> Bucky OS는 Oracle Cloud를 중심 두뇌로 두고, Obsidian Second Brain과 여러 로컬 PC를 연결하여 개인 업무, 개발, 자동화, 상용 Agent 사업까지 확장하기 위한 중앙집중형 AI 운영체제다.

