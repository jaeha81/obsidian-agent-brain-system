아래 기준으로 정리하면 돼.
Graphify는 옵시디언을 대체하는 브레인이 아니라, 각 프로젝트/레포/문서 묶음을 “지식 그래프”로 바꿔서 Claude Code, Codex, Cursor, Antigravity 같은 개발 도구가 구조적으로 조회하게 만드는 보조 레이어로 적용하는 게 맞다.

공식 설명 기준으로 Graphify는 코드, 문서, 논문, 다이어그램 등을 분석해서 질의 가능한 knowledge graph를 만들고, Tree-sitter 정적 분석과 LLM 기반 의미 추출을 조합해 레포 전체를 그래프화한다. 결과물은 graph.html, GRAPH_REPORT.md, graph.json 형태로 생성된다.

설치 패키지명은 graphifyy이고 CLI 명령은 graphify다. Claude Code, Codex, Cursor, Google Antigravity 등 여러 개발 환경에 설치 명령이 따로 있으며, Codex는 ~/.codex/config.toml에 multi_agent = true 설정이 필요할 수 있다.

Graphify는 /graphify query, /graphify path, /graphify explain 같은 명령으로 그래프를 질의할 수 있고, --wiki, --obsidian, --mcp, --neo4j 같은 export 옵션도 제공한다.
다만 코드 파일은 로컬에서 Tree-sitter로 처리되고, 문서/PDF/이미지 등 의미 추출이 필요한 자료는 사용 중인 AI assistant의 모델 API를 통해 처리될 수 있으므로, 민감한 자료는 .graphifyignore로 제외하는 구조가 필요하다.

최종 적용 방향

네 시스템에서는 이렇게 잡는 게 가장 안정적이야.

Obsidian Agent
= 중앙 브레인 / 지식 관리 / Context Pack 생성

Graphify
= 프로젝트별 코드·문서·다이어그램 지식 그래프 생성기

Claude Code / Codex
= Graphify 그래프를 참고해서 개발 수행

GitHub
= 코드 저장소 / 버전 관리

Discord / Voice / RAW
= 입력 수집 채널

LegalizeKR
= 외부 법령 지식베이스

Graphify Context Pack
= Graphify 질의 결과를 개발 도구에게 넘기는 압축 문맥

즉, 옵시디언 전체를 Graphify로 무식하게 그래프화하는 게 아니라, 프로젝트별로 필요한 범위만 그래프화하고, 옵시디언 에이전트가 그 결과를 받아서 Context Pack으로 정리하는 구조가 맞다.

Graphify 적용용 최종 명령 프롬프트

아래 내용을 그대로 Claude Code 또는 Codex에 넣으면 된다.

# UNIVERSAL PROMPT
# Graphify를 Obsidian Agent Brain System에 적용하라

너는 지금부터 사용자의 Obsidian Agent Brain System에 Graphify를 적용하는 개발 에이전트다.

Graphify 공식 사이트:
https://graphify.net/kr/

Graphify는 코드, 문서, PDF, 이미지, 다이어그램, 연구자료 등을 분석해서 지식 그래프를 만들고, Claude Code, Codex, Cursor, OpenCode, Google Antigravity 같은 AI coding assistant가 해당 그래프를 조회할 수 있게 해주는 오픈소스 도구다.

이 작업의 목표는 Graphify를 단순 설치하는 것이 아니다.
목표는 사용자의 Obsidian Agent Brain System 안에서 Graphify를 “프로젝트 구조 이해용 지식 그래프 레이어”로 적용하는 것이다.

---

## 1. 전체 시스템에서 Graphify의 역할

사용자의 시스템 구조는 다음과 같다.

```txt
사용자
  ↓
Discord / Voice / Obsidian / Claude Code / Codex 입력
  ↓
01_RAW
  ↓
Obsidian Agent
  ↓
Context Pack 생성
  ↓
Claude Code / Codex 개발 실행
  ↓
작업 결과 보고
  ↓
Obsidian Wiki / Project / Devlog / GitHub 반영

Graphify는 이 구조 안에서 다음 역할을 맡는다.

Graphify
= 프로젝트별 코드베이스, 문서, 다이어그램, 레포 구조를 지식 그래프로 변환하는 레이어

Graphify는 중앙 브레인이 아니다.
중앙 브레인은 Obsidian Agent다.

Graphify는 Claude Code와 Codex가 프로젝트를 이해할 때 전체 파일을 무작정 읽지 않도록 도와주는 “구조 지도” 역할을 한다.

2. 핵심 원칙

다음 원칙을 반드시 지켜라.

Obsidian은 중앙 브레인이다.
Graphify는 프로젝트별 지식 그래프 도구다.
Claude Code와 Codex는 개발 실행 도구다.
Graphify 결과는 Obsidian Agent가 읽어서 Context Pack으로 변환한다.
전체 Obsidian Vault를 무조건 Graphify로 스캔하지 않는다.
01_RAW 전체를 무조건 Graphify로 스캔하지 않는다.
external_data/legalize-kr 전체를 무조건 Graphify로 스캔하지 않는다.
프로젝트별 필요한 범위만 그래프화한다.
민감한 파일은 .graphifyignore로 제외한다.
Claude Code와 Codex는 Graphify 결과를 참고하되, 전체 graph.json을 무조건 컨텍스트에 넣지 않는다.
항상 graphify query, graphify path, graphify explain, GRAPH_REPORT.md를 통해 필요한 정보만 가져온다.
3. Graphify를 사용해야 하는 상황

사용자 요청에 다음 의도가 있으면 Graphify를 사용한다.

코드 구조 이해
이 프로젝트 구조를 파악해줘
어떤 파일들이 연결되어 있어?
핵심 모듈이 뭐야?
어디를 수정해야 해?
이 오류가 어디까지 영향이 있어?
이 기능과 DB가 어떻게 연결돼?
API 흐름을 파악해줘
인증 흐름을 파악해줘
리팩토링 범위를 잡아줘
아키텍처 분석
프로젝트 아키텍처 설명
핵심 노드 파악
모듈 간 의존성 분석
God node 확인
숨은 연결 관계 확인
surprising connection 확인
call flow 분석
문서/코드 통합 분석
README와 코드가 맞는지 확인
기술문서와 실제 구현 비교
논문/자료/다이어그램과 코드 연결
기존 Agent Room 자료를 구조적으로 분석
마이그레이션 대상 자료의 연결 관계 확인
개발 도구 지원
Claude Code가 개발 전 구조를 파악해야 할 때
Codex가 구현 전 관련 파일을 찾아야 할 때
기존 코드를 기반으로 새 기능을 붙일 때
GitHub 레포 변경 영향도를 분석할 때
4. Graphify를 사용하지 말아야 하는 상황

다음 상황에서는 Graphify를 우선 사용하지 않는다.

단순 텍스트 정리
단순 아이디어 메모
법령 원문만 검색하는 경우
아주 작은 단일 파일 수정
사용자가 단순 문장 작성만 요구한 경우
Graphify 대상 범위가 너무 넓고 목적이 불명확한 경우
민감한 고객 자료가 포함되어 있는데 제외 규칙이 없는 경우
전체 RAW를 무차별적으로 분석하려는 경우
전체 legalize-kr 법령 저장소를 한 번에 그래프화하려는 경우
5. 설치 전략

작업 시작 전 Python 버전을 확인한다.

python --version
python3 --version

Graphify는 Python 3.10 이상 환경을 기준으로 한다.

가능하면 uv 또는 pipx를 우선 사용한다.

uv tool install graphifyy

또는:

pipx install graphifyy

대안:

pip install graphifyy

설치 후 CLI 확인:

graphify --help

AI assistant 스킬 등록:

graphify install

플랫폼별 설치:

# Claude Code
graphify claude install

# Codex
graphify codex install

# Cursor
graphify cursor install

# Google Antigravity
graphify antigravity install

# VS Code Copilot Chat
graphify vscode install

Codex 사용 시 필요하면 다음 설정을 확인한다.

# ~/.codex/config.toml

[features]
multi_agent = true

Windows PowerShell에서는 /graphify . 대신 다음처럼 사용한다.

graphify .
6. Optional Extras 설치 기준

기본은 가볍게 설치한다.

필요한 경우에만 extras를 추가한다.

# PDF 분석 필요
pip install "graphifyy[pdf]"

# DOCX, XLSX 필요
pip install "graphifyy[office]"

# 영상/음성 전사 필요
pip install "graphifyy[video]"

# MCP 서버 필요
pip install "graphifyy[mcp]"

# OpenAI backend 필요
pip install "graphifyy[openai]"

# Ollama 로컬 모델 필요
pip install "graphifyy[ollama]"

# 전체 기능
pip install "graphifyy[all]"

초기에는 all 설치를 남발하지 않는다.
필요한 기능만 설치한다.

7. Obsidian Vault 내부에 생성할 구조

Obsidian Vault 안에 다음 구조를 만든다.

04_Wiki/
  Graphify/
    Index.md
    Graphify_Source.md
    Graphify_Usage_Guide.md
    Graphify_Query_Guide.md
    Graphify_vs_Obsidian_Graph.md
    Graphify_for_ClaudeCode.md
    Graphify_for_Codex.md
    Graphify_for_Antigravity.md

05_Frameworks/
  Graphify/
    README.md
    graphify_adapter.md
    graphify_context_pack_rules.md
    graphify_query_patterns.md
    graphify_scope_policy.md
    graphify_security_policy.md
    graphify_update_policy.md
    graphify_mcp_policy.md
    graphify_obsidian_policy.md

06_Context_Packs/
  Graphify/
    generated/
    templates/
      graphify_context_pack_template.md

10_AgentBus/
  context_requests/
    graphify/
  context_responses/
    graphify/
  reports/
    Graphify/
8. 프로젝트 레포 내부에 생성할 구조

각 개발 프로젝트 레포에는 다음 구조를 만든다.

project-root/
  graphify-out/
    graph.html
    GRAPH_REPORT.md
    graph.json
    cache/

  .graphifyignore

  scripts/
    graphify_build.sh
    graphify_update.sh
    graphify_query.sh
    graphify_context_pack.py

  docs/
    graphify/
      graphify_usage.md
      graphify_queries.md
      graphify_report_summary.md

graphify-out/은 프로젝트별로 생성한다.
Obsidian Vault 전체 공용 graphify-out 하나로 모든 프로젝트를 섞지 않는다.

9. .graphifyignore 기본값

각 프로젝트 루트에 .graphifyignore를 생성한다.

기본 내용:

# Dependencies
node_modules/
vendor/
.venv/
venv/
__pycache__/

# Build outputs
dist/
build/
out/
.next/
.nuxt/
.cache/
coverage/

# Secrets
.env
.env.*
*.pem
*.key
*.crt
secrets/
credentials/
private/

# Git
.git/

# Large binary files
*.zip
*.tar
*.gz
*.7z
*.rar

# Logs
*.log
logs/

# Local cache
graphify-out/cache/
graphify-out/cost.json
graphify-out/manifest.json

# Obsidian raw overload prevention
01_RAW/Misc/
01_RAW/Screenshots/
01_RAW/Errors/

# LegalizeKR full law repository should not be blindly indexed
external_data/legalize-kr/

단, 특정 프로젝트에서 필요한 문서가 제외되면 예외 규칙을 추가한다.

예시:

!docs/
!docs/**
!src/
!src/**
!README.md
10. Graphify 적용 범위 정책

Graphify는 다음 4가지 범위로 사용한다.

A. Project Graph

각 개발 프로젝트 레포에서 사용한다.

graphify .

또는 assistant 안에서는:

/graphify .

목적:

코드 구조 파악
API 흐름 분석
모듈 관계 분석
리팩토링 범위 파악
Claude Code / Codex 개발 전 구조 확인
B. Obsidian Knowledge Graph Subset

Obsidian Vault 전체가 아니라 선별된 폴더만 대상으로 한다.

대상 후보:

02_Processed/
03_Projects/
04_Wiki/
05_Frameworks/
06_Context_Packs/

실행 예시:

graphify ./03_Projects
graphify ./04_Wiki
graphify ./05_Frameworks

금지:

graphify ./ObsidianVault

전체 Vault를 바로 스캔하지 않는다.

C. Agent Room Legacy Migration Graph

기존 Agent Room 자료 마이그레이션 시 한 번 사용한다.

대상:

01_RAW/AgentRoom_Legacy/

목적:

과거 에이전트룸 자료의 핵심 노드 파악
중복 지침 파악
충돌 지침 파악
기존 기술 스킬 분류
현재 Obsidian Agent 구조로 옮길 지식 선별

실행 예시:

graphify ./01_RAW/AgentRoom_Legacy --no-viz

결과는 마이그레이션 보고서로 정리한다.

D. LegalizeKR Selected Graph

external_data/legalize-kr 전체를 그래프화하지 않는다.

법령은 양이 매우 크기 때문에 다음 방식만 허용한다.

사용자가 요청한 법령만 선별한다.
필요한 법령 파일을 임시 폴더에 복사한다.
해당 임시 폴더를 Graphify로 분석한다.
결과를 Legal Context Pack에 반영한다.

예시:

temp_graphify/legal_context/
  민법_법률.md
  건축법_법률.md
  건축법_시행령.md
  개인정보보호법_법률.md

실행:

graphify ./temp_graphify/legal_context --no-viz
11. Graphify 기본 명령

프로젝트 그래프 생성:

graphify .

특정 폴더 그래프 생성:

graphify ./src
graphify ./docs
graphify ./raw

업데이트:

graphify ./docs --update

클러스터만 재실행:

graphify . --cluster-only

HTML 생략:

graphify . --no-viz

Wiki 생성:

graphify . --wiki

Obsidian vault export:

graphify . --obsidian

MCP 서버:

graphify . --mcp

질의:

graphify query "show the auth flow"
graphify query "what connects user service to database?"
graphify path "UserService" "Database"
graphify explain "AuthController"

assistant slash command 환경에서는 다음을 사용할 수 있다.

/graphify .
/graphify query "show the auth flow"
/graphify path "UserService" "Database"
/graphify explain "AuthController"
12. Graphify Context Pack 템플릿

다음 파일을 생성한다.

06_Context_Packs/Graphify/templates/graphify_context_pack_template.md

내용:

# Graphify Context Pack

## 1. 요청 ID
예: graphify-request-2026-05-21-001

## 2. 사용자 요청
사용자의 원래 요청

## 3. 대상 프로젝트
프로젝트명

## 4. 대상 경로
Graphify를 실행한 경로

## 5. Graphify 출력 위치
```txt
graphify-out/GRAPH_REPORT.md
graphify-out/graph.json
graphify-out/graph.html
6. 기준 시점

그래프 생성 또는 업데이트 날짜

7. 사용한 명령
graphify .
graphify query "..."
graphify path "A" "B"
graphify explain "Node"
8. 핵심 노드

Graphify가 식별한 god nodes 또는 핵심 개념

9. 주요 커뮤니티

프로젝트의 주요 모듈/기능 그룹

10. 예상 밖 연결

surprising connections

11. 관련 파일

이번 작업과 관련된 파일 목록

12. 관련 함수/클래스/모듈

노드 단위로 정리

13. Graphify 질의 결과 요약

원문 전체를 붙이지 말고 필요한 부분만 요약

14. Claude Code / Codex에게 전달할 작업 지시

개발자가 수행해야 할 구체 작업

15. 주의사항
수정 금지 파일
영향 범위
위험한 의존성
추가 확인 필요 지점
16. 완료 후 보고 위치
10_AgentBus/reports/ClaudeCode/
10_AgentBus/reports/Codex/
10_AgentBus/reports/Graphify/

---

## 13. Graphify Framework Card 생성

다음 파일을 만든다.

```txt
05_Frameworks/Graphify/README.md

내용:

# Graphify Framework

## 목적
Graphify는 프로젝트의 코드, 문서, 다이어그램, 연구자료를 지식 그래프로 변환하여 Claude Code, Codex, Cursor, Antigravity 같은 개발 도구가 구조적으로 프로젝트를 이해하도록 돕는 프레임워크다.

## 시스템 내 역할
- Obsidian Agent의 보조 그래프 레이어
- 프로젝트 구조 지도
- 코드와 문서 관계 분석 도구
- 개발 전 Context Pack 생성 도구
- 리팩토링 영향 범위 분석 도구

## 사용해야 하는 경우
- 프로젝트 구조를 파악해야 할 때
- 파일 간 연결 관계가 필요할 때
- 핵심 모듈을 찾아야 할 때
- 코드와 문서가 함께 있는 프로젝트를 분석할 때
- 기존 Agent Room 자료의 연결 구조를 파악할 때
- Claude Code나 Codex가 작업 전 프로젝트 맥락을 받아야 할 때

## 사용하지 말아야 하는 경우
- 전체 Obsidian Vault를 무작정 분석하려는 경우
- 전체 RAW를 무작정 분석하려는 경우
- 법령 저장소 전체를 분석하려는 경우
- 단순 메모 정리
- 단일 파일 수정
- 민감 자료가 제외되지 않은 상태

## 주요 결과물
- graphify-out/graph.html
- graphify-out/GRAPH_REPORT.md
- graphify-out/graph.json

## 주요 명령
```bash
graphify .
graphify . --update
graphify . --wiki
graphify . --obsidian
graphify query "..."
graphify path "A" "B"
graphify explain "Node"
Obsidian Agent와의 연결

Graphify 결과를 직접 사용자에게 던지지 않는다.
Obsidian Agent가 Graphify 결과를 읽고 Graphify Context Pack으로 압축해서 Claude Code 또는 Codex에게 전달한다.

주의사항
전체 파일을 LLM 컨텍스트에 넣지 않는다.
graph.json 전체를 그대로 프롬프트에 넣지 않는다.
query/path/explain 결과만 사용한다.
민감 파일은 .graphifyignore로 제외한다.
프로젝트별 graphify-out을 분리한다.

---

## 14. Graphify Query Patterns 생성

다음 파일을 만든다.

```txt
05_Frameworks/Graphify/graphify_query_patterns.md

내용:

# Graphify Query Patterns

## 1. 프로젝트 전체 구조 파악

```bash
graphify .
cat graphify-out/GRAPH_REPORT.md

질문 예시:

graphify query "summarize the main architecture of this project"
2. 인증 흐름 파악
graphify query "show the authentication flow"
3. 데이터베이스 연결 파악
graphify query "what connects the API layer to the database?"
4. 특정 노드 설명
graphify explain "AuthService"
graphify explain "UserRepository"
graphify explain "DatabasePool"
5. 두 노드 사이 경로
graphify path "UserController" "Database"
graphify path "DiscordBot" "ObsidianAgent"
6. 리팩토링 영향 범위
graphify query "what modules would be affected if we refactor the auth layer?"
7. 문서와 코드 연결
graphify query "which documentation explains the implementation of the agent bus?"
8. Agent Room Legacy 분석
graphify query "what are the main agent roles and duplicated instructions in this legacy folder?"
9. Graphify 결과 사용 원칙
먼저 GRAPH_REPORT.md를 읽는다.
세부 질문은 graphify query를 사용한다.
정확한 연결 경로는 graphify path를 사용한다.
특정 노드 설명은 graphify explain을 사용한다.
결과를 그대로 복사하지 말고 Context Pack으로 요약한다.

---

## 15. Obsidian Routing Rules에 추가

기존 파일이 있으면 수정하고, 없으면 생성한다.

```txt
00_System/ROUTING_RULES.md

다음 내용을 추가한다.

# Graphify Routing Rules

## Graphify를 호출해야 하는 요청

사용자 요청에 다음 의도가 포함되면 Graphify Framework를 사용한다.

### 구조 분석
- 프로젝트 구조
- 아키텍처
- 파일 관계
- 모듈 관계
- 핵심 노드
- 연결 관계
- 의존성
- 코드 흐름
- call flow
- graph
- knowledge graph

### 개발 전 분석
- 어디를 수정해야 하는지
- 어떤 파일을 봐야 하는지
- 오류 영향 범위
- 리팩토링 범위
- DB와 API 연결
- 인증 흐름
- Discord Bot과 Obsidian Agent 연결
- Claude Code와 Codex 작업 범위

### 기존 자료 마이그레이션
- Agent Room Legacy 분석
- 중복 지침 찾기
- 과거 자료 구조화
- RAW 자료 연결 관계 파악

## 처리 순서

1. 사용자 요청에서 프로젝트명 또는 대상 경로를 찾는다.
2. 대상 프로젝트의 graphify-out 존재 여부를 확인한다.
3. 없으면 Graphify 생성 작업을 요청한다.
4. 있으면 GRAPH_REPORT.md를 먼저 확인한다.
5. 질문이 구체적이면 graphify query/path/explain을 사용한다.
6. 결과를 Graphify Context Pack으로 압축한다.
7. Claude Code 또는 Codex에게 Context Pack만 전달한다.
8. 작업 결과는 Obsidian Project / Wiki / Devlog에 반영한다.

## 금지 사항

- 전체 Obsidian Vault를 무조건 Graphify로 분석하지 않는다.
- 전체 RAW를 무조건 Graphify로 분석하지 않는다.
- 전체 legalize-kr 법령 저장소를 무조건 Graphify로 분석하지 않는다.
- graph.json 전체를 LLM 프롬프트에 넣지 않는다.
- 민감 파일을 제외하지 않고 분석하지 않는다.
- Graphify 결과를 최종 판단으로만 사용하지 않는다.
- 코드 수정 전 실제 파일 내용을 확인하지 않고 Graphify 요약만 믿고 수정하지 않는다.
16. Graphify Adapter 설계

다음 파일을 만든다.

05_Frameworks/Graphify/graphify_adapter.md

내용:

# Graphify Adapter Design

## 목적
Obsidian Agent가 Graphify 결과를 읽고, Claude Code와 Codex에게 전달할 Graphify Context Pack을 생성하기 위한 어댑터 설계다.

## 입력
- 사용자 요청
- 프로젝트명
- 대상 경로
- graphify-out/GRAPH_REPORT.md
- graphify-out/graph.json
- graphify query 결과
- graphify path 결과
- graphify explain 결과

## 출력
- 핵심 노드 요약
- 관련 커뮤니티 요약
- 관련 파일 목록
- 관련 함수/클래스/모듈
- 수정 영향 범위
- Claude Code 또는 Codex 작업 지시
- Graphify Context Pack

## 처리 흐름

1. 요청 분석
2. 프로젝트 경로 확인
3. graphify-out 존재 여부 확인
4. 그래프 없으면 생성 요청
5. GRAPH_REPORT.md 읽기
6. 필요한 경우 graphify query/path/explain 실행
7. 결과 요약
8. Graphify Context Pack 생성
9. AgentBus로 작업 전달
10. 작업 결과를 Obsidian에 반영

## Graphify 결과 신뢰도 처리

Graphify 결과는 프로젝트 구조 이해를 돕는 보조 자료다.
코드 수정 전에는 실제 소스 파일을 확인해야 한다.

## Context 절약 원칙

전체 graph.json을 넣지 않는다.
필요한 query 결과만 넣는다.
긴 결과는 요약한다.
관련 파일 경로는 명확히 제공한다.
17. 스크립트 생성 요청

가능하면 다음 스크립트를 생성한다.

scripts/graphify_build.sh
scripts/graphify_update.sh
scripts/graphify_query.sh
scripts/graphify_context_pack.py
scripts/graphify_build.sh

역할:

현재 프로젝트에 Graphify 그래프 생성
.graphifyignore 존재 여부 확인
graphify-out 생성 확인
결과 보고

예상 사용:

./scripts/graphify_build.sh .
./scripts/graphify_build.sh ./src
./scripts/graphify_build.sh ./docs
scripts/graphify_update.sh

역할:

변경된 파일만 업데이트
graphify-out 존재 여부 확인
없으면 build 안내

예상 사용:

./scripts/graphify_update.sh .
scripts/graphify_query.sh

역할:

graphify query/path/explain을 편하게 호출

예상 사용:

./scripts/graphify_query.sh query "show the auth flow"
./scripts/graphify_query.sh path "UserService" "Database"
./scripts/graphify_query.sh explain "AuthService"
scripts/graphify_context_pack.py

역할:

GRAPH_REPORT.md 읽기
graphify query 결과 입력받기
Graphify Context Pack Markdown 생성
결과를 Obsidian의 06_Context_Packs/Graphify/generated/에 저장

예상 사용:

python scripts/graphify_context_pack.py \
  --project "Obsidian_Agent_Brain" \
  --query "show the agent bus flow" \
  --graph-report "graphify-out/GRAPH_REPORT.md" \
  --output "../ObsidianVault/06_Context_Packs/Graphify/generated/"
18. Graphify와 Claude Code / Codex 작업 흐름

Claude Code와 Codex는 다음 방식으로 Graphify를 사용한다.

작업 전
프로젝트의 graphify-out/GRAPH_REPORT.md를 확인한다.
사용자의 요청에 맞는 Graphify query를 실행한다.
필요한 경우 path/explain을 실행한다.
Graphify Context Pack을 생성한다.
실제 코드 수정 전 관련 파일을 직접 확인한다.
작업 중
Graphify 결과로 관련 파일 후보를 좁힌다.
실제 파일 내용을 확인한다.
수정 범위를 최소화한다.
영향 범위를 기록한다.
작업 후
개발 보고서를 작성한다.
변경 파일을 기록한다.
Graphify 업데이트가 필요한지 판단한다.
필요하면 graphify . --update를 실행한다.
Obsidian Agent에게 결과를 보고한다.

보고 위치:

10_AgentBus/reports/ClaudeCode/
10_AgentBus/reports/Codex/
10_AgentBus/reports/Graphify/
19. GitHub와 Graphify 연결

GitHub는 코드 버전 관리 시스템이다.
Graphify는 프로젝트 구조 그래프다.

권장 방식:

프로젝트별로 graphify-out/을 생성한다.
팀 또는 장기 프로젝트에서는 GRAPH_REPORT.md와 graph.json을 Git에 포함할지 검토한다.
manifest.json, cost.json, cache/는 상황에 따라 제외한다.
commit 후 그래프 업데이트가 필요하면 hook을 설치한다.
graphify hook install

브랜치 전환과 커밋 이후 그래프 최신화가 필요하면 hook 상태를 확인한다.

graphify hook status
20. Graphify와 MCP 연결

초기에는 MCP를 필수로 구현하지 않는다.
먼저 파일 기반 Graphify 사용을 안정화한다.

추후 MCP가 필요하면 다음 구조를 검토한다.

pip install "graphifyy[mcp]"
python -m graphify.serve graphify-out/graph.json

MCP는 다음 기능을 제공하는 구조로 설계한다.

query_graph
get_node
get_neighbors
shortest_path
list_prs
get_pr_impact
triage_prs

단, 초기 적용 단계에서는 다음 순서를 지킨다.

Graphify CLI
Graphify Report
Graphify Context Pack
AgentBus 연동
MCP 확장
21. Graphify와 Obsidian Graph의 차이

Obsidian Graph는 노트 간 링크 중심이다.
Graphify Graph는 코드, 문서, 함수, 클래스, 개념, 다이어그램, 설계 의도 간 연결 중심이다.

따라서 둘을 혼동하지 않는다.

Obsidian Graph
= 사용자의 지식 노트 연결

Graphify Graph
= 프로젝트 코드/문서/구조 연결

Obsidian Agent는 두 그래프를 함께 사용한다.

개인 지식/사업/프로젝트 맥락: Obsidian Graph
코드베이스/문서/아키텍처 맥락: Graphify Graph
22. Agent Room Legacy 마이그레이션에 Graphify 적용

기존 Agent Room 자료는 너무 복잡하므로 Graphify로 구조를 파악할 수 있다.

처리 흐름:

기존 Agent Room 자료를 01_RAW/AgentRoom_Legacy/에 모은다.
민감 자료와 불필요 자료를 제외한다.
Graphify를 실행한다.
graphify ./01_RAW/AgentRoom_Legacy --no-viz
GRAPH_REPORT.md를 읽는다.
핵심 노드, 중복 지침, 충돌 지침, 주요 프레임워크를 추출한다.
마이그레이션 보고서를 만든다.
유효한 지식은 04_Wiki, 05_Frameworks, 03_Projects로 옮긴다.
오래된 지침은 09_Archive로 보낸다.

보고서 위치:

07_Reports/Agent_Reports/agentroom_graphify_migration_report.md
23. LegalizeKR와 Graphify 연결 정책

legalize-kr/legalize-kr 전체 저장소는 Graphify로 무조건 돌리지 않는다.

이유:

법령 파일이 많다.
전체 법령 그래프는 너무 무겁다.
사용자 요청과 무관한 법령까지 그래프화하면 컨텍스트가 낭비된다.

대신 다음 방식으로 처리한다.

LegalizeKR에서 필요한 법령 후보만 검색한다.
필요한 법령 파일만 임시 폴더에 모은다.
해당 임시 폴더만 Graphify로 분석한다.
Legal Context Pack과 Graphify Context Pack을 결합한다.

예시:

temp_graphify/legal_selected/
  민법_법률.md
  건축법_법률.md
  건축법_시행령.md
  개인정보보호법_법률.md

실행:

graphify ./temp_graphify/legal_selected --no-viz
24. 보안 및 개인정보 원칙

다음 파일은 Graphify 대상에서 제외한다.

.env
API key
고객 개인정보
계약서 원본
계정 정보
인증서
비밀키
결제 정보
민감한 고객 상담 내용
내부 견적 원본
법적 분쟁 자료

필요한 경우 민감 정보를 제거한 요약본만 Graphify에 넣는다.

Graphify는 코드 구조 분석에 강하지만, 모든 자료를 무조건 넣는 도구가 아니다.
항상 목적에 맞는 범위만 분석한다.

25. 충돌 방지

작업 시작 전 다음 파일을 확인한다.

00_System/AGENT_STATE.md
00_System/TASKS.md
00_System/HANDOFF_LOG.md
00_System/LOCKS/

Graphify 작업을 시작하면 다음 lock을 생성한다.

00_System/LOCKS/task-graphify-integration.lock

이미 lock이 있으면 해당 작업을 덮어쓰지 않는다.
대신 검토, 테스트, 보완 문서 작성만 수행한다.

작업 완료 후 보고서를 작성한다.

10_AgentBus/reports/Graphify/graphify_initial_integration_report.md
26. 초기 테스트

초기 구축 후 다음 테스트를 수행한다.

테스트 1. 설치 확인
graphify --help
테스트 2. 작은 프로젝트 그래프 생성
graphify . --no-viz
테스트 3. GRAPH_REPORT 확인
cat graphify-out/GRAPH_REPORT.md
테스트 4. 질의 테스트
graphify query "summarize the main architecture"
테스트 5. 특정 노드 설명
graphify explain "AgentBus"
테스트 6. 경로 분석
graphify path "DiscordBot" "ObsidianAgent"
테스트 7. 업데이트
graphify . --update
27. 생성해야 할 최종 산출물

작업 완료 후 다음 산출물을 만든다.

05_Frameworks/Graphify/README.md
05_Frameworks/Graphify/graphify_adapter.md
05_Frameworks/Graphify/graphify_query_patterns.md
05_Frameworks/Graphify/graphify_context_pack_rules.md
05_Frameworks/Graphify/graphify_scope_policy.md
05_Frameworks/Graphify/graphify_security_policy.md
05_Frameworks/Graphify/graphify_update_policy.md
06_Context_Packs/Graphify/templates/graphify_context_pack_template.md
04_Wiki/Graphify/Index.md
04_Wiki/Graphify/Graphify_Usage_Guide.md
00_System/ROUTING_RULES.md에 Graphify 라우팅 규칙 추가
프로젝트별 .graphifyignore
프로젝트별 scripts/graphify_build.sh
프로젝트별 scripts/graphify_update.sh
프로젝트별 scripts/graphify_query.sh
가능하면 scripts/graphify_context_pack.py
초기 테스트 결과
Graphify 초기 통합 보고서
28. 금지 사항

다음은 절대 하지 않는다.

전체 Obsidian Vault를 바로 Graphify로 돌리지 않는다.
전체 01_RAW를 바로 Graphify로 돌리지 않는다.
전체 external_data/legalize-kr를 바로 Graphify로 돌리지 않는다.
.env, API key, 고객 개인정보를 Graphify 대상에 포함하지 않는다.
graph.json 전체를 Claude Code나 Codex 프롬프트에 붙여넣지 않는다.
Graphify 결과만 보고 코드를 수정하지 않는다.
실제 파일 확인 없이 리팩토링하지 않는다.
기존 Obsidian Agent 구조를 덮어쓰지 않는다.
lock이 걸린 파일을 수정하지 않는다.
API/MCP부터 무리하게 구현하지 않는다.
Graphify를 Obsidian의 중앙 브레인으로 오해하지 않는다.
29. 지금 바로 수행할 첫 작업

이 프롬프트를 받으면 다음 순서로 작업하라.

현재 작업 디렉토리를 확인한다.
Obsidian Vault 위치를 찾는다.
00_System/AGENT_STATE.md를 확인한다.
Graphify 작업 lock을 생성한다.
Graphify 설치 여부를 확인한다.
설치되어 있지 않으면 설치 계획을 제시하고 가능한 경우 설치한다.
Obsidian Vault 안에 Graphify Framework 구조를 생성한다.
05_Frameworks/Graphify/README.md를 작성한다.
graphify_query_patterns.md를 작성한다.
graphify_context_pack_template.md를 작성한다.
ROUTING_RULES.md에 Graphify 규칙을 추가한다.
현재 프로젝트에 .graphifyignore를 만든다.
작은 범위로 Graphify 테스트를 수행한다.
graphify-out/GRAPH_REPORT.md가 생성되었는지 확인한다.
테스트 질의를 1개 이상 수행한다.
초기 통합 보고서를 작성한다.
30. 응답 형식

작업 완료 후 다음 형식으로 보고하라.

# Graphify 적용 작업 보고

## 1. 내 역할
Coordinator / Reviewer / Implementer / Verifier

## 2. 적용 대상
Graphify

## 3. 적용 목적
Obsidian Agent Brain System의 프로젝트 지식 그래프 레이어로 연결

## 4. 확인한 현재 상태
- Obsidian Vault 위치
- 현재 프로젝트 위치
- Python 버전
- Graphify 설치 여부
- Claude Code / Codex / Cursor / Antigravity 설정 여부

## 5. 생성한 폴더
목록

## 6. 생성한 파일
목록

## 7. Graphify 설치/설정
실행한 명령과 결과

## 8. 테스트 결과
- graphify --help
- graphify 실행 결과
- GRAPH_REPORT.md 생성 여부
- graphify query 결과 요약

## 9. Obsidian Agent 연동 방식
RAW, Project, Wiki, Context Pack, AgentBus 연결 방식

## 10. Claude Code / Codex 사용 방식
개발 도구가 Graphify 결과를 어떻게 요청하고 받는지

## 11. 남은 작업
다음 단계

## 12. 주의사항
컨텍스트 초과, 민감 자료, 전체 Vault 스캔 금지, legalize-kr 전체 스캔 금지

## 13. 완료 여부
완료 / 부분 완료 / 보류

이제 위 지침에 따라 Graphify를 Obsidian Agent Brain System에 적용하라.


---

# 첫 번째 도구에게 붙일 짧은 지시문

Claude Code나 Codex 중 **처음 실행하는 쪽**에는 아래 문구를 추가로 붙이면 좋아.

```md
너는 Graphify 적용 작업의 최초 실행자다. Coordinator / Architect 역할을 맡아라. 먼저 Graphify를 Obsidian Agent Brain System의 중앙 브레인이 아니라 프로젝트별 지식 그래프 레이어로 설계하라. 전체 Obsidian Vault, 전체 RAW, 전체 legalize-kr 저장소를 무차별적으로 스캔하지 말고, 범위 제한 정책과 .graphifyignore를 우선 작성하라.
두 번째 도구에게 붙일 짧은 지시문

두 번째 실행자에게는 아래 문구를 붙이면 충돌이 줄어든다.

너는 Graphify 적용 작업의 두 번째 실행자다. 먼저 AGENT_STATE.md, TASKS.md, HANDOFF_LOG.md, Graphify 관련 문서를 읽어라. 기존 Coordinator의 구조를 덮어쓰지 말고 Reviewer / Implementer / Verifier 역할로 누락된 스크립트, 테스트, Context Pack 생성기, .graphifyignore 정책을 보완하라.
최종 판단

Graphify는 네 시스템에서 “개발 프로젝트용 구조 지도” 역할로 쓰는 게 가장 좋다.

옵시디언은 계속 메인 브레인이고, Graphify는 각 프로젝트나 문서 묶음을 그래프로 만들어서 Claude Code와 Codex가 컨텍스트를 덜 쓰고도 구조를 이해하게 해주는 도구다.

가장 중요한 운영 원칙은 이거야.

전체를 읽게 하지 말고,
Graphify로 구조를 만든 뒤,
필요한 질문만 query/path/explain으로 뽑고,
그 결과를 Obsidian Agent가 Context Pack으로 압축해서
Claude Code와 Codex에게 전달한다.

이렇게 하면 네가 처음에 말한 개발자가 보여준 구조, 즉 Antigravity 왼쪽에 지식 그래프가 있고 아래에서 Claude Code/Codex가 대화하며 작업하는 구조를 네 시스템에서는 Obsidian Agent + Graphify + Claude Code/Codex 조합으로 재현할 수 있다.