아래는 legalize-kr/legalize-kr 레포를 너의 Obsidian Agent Brain System에 적용하기 위한 클로드 코드 / 코덱스 공통 명령 프롬프트야.

이 레포는 일반 앱 개발 레포가 아니라, 대한민국 법령을 Markdown 파일과 Git 히스토리로 관리하는 법령 데이터 저장소야. README 기준으로 각 법령은 Markdown 파일이고, 각 개정은 실제 공포일자를 가진 Git commit으로 관리된다고 설명되어 있어.
또한 구조는 kr/{법령명}/{법령구분}.md, 예를 들면 kr/민법/법률.md, kr/민법/시행령.md 같은 형태로 되어 있고, YAML frontmatter에 제목, 법령ID, 소관부처, 공포일자, 시행일자, 상태, 출처 같은 메타데이터가 들어간다.

중요한 건, 이 레포는 양이 크고 Git 히스토리도 많기 때문에 옵시디언 Vault 안에 통째로 넣으면 안 된다는 거야.
대신 외부 법령 데이터 소스로 연결하고, 옵시디언에는 필요한 색인·요약·프로젝트별 법령 Context Pack만 저장하는 방식이 맞아.

legalize-kr 적용용 통합 명령 프롬프트

아래 내용을 그대로 클로드 코드 또는 코덱스에 넣으면 돼.

# UNIVERSAL PROMPT
# legalize-kr 법령 지식베이스를 Obsidian Agent Brain System에 적용하라

너는 지금부터 사용자의 Obsidian Agent Brain System에 `legalize-kr/legalize-kr` 법령 데이터 저장소를 적용하는 개발 에이전트다.

적용 대상 레포:

https://github.com/legalize-kr/legalize-kr.git

이 레포는 일반적인 앱 코드 레포가 아니라 대한민국 법령 데이터를 Git 저장소로 관리하는 데이터 레포다. 각 법령은 Markdown 파일이고, 각 개정 이력은 Git commit으로 관리된다. 따라서 이 레포를 Obsidian 안에 단순 복사하지 말고, 외부 법령 지식베이스로 연결해서 사용해야 한다.

---

## 1. 최종 목표

사용자의 Obsidian Agent Brain System에 다음 기능을 추가한다.

1. `legalize-kr/legalize-kr` 레포를 외부 법령 데이터 소스로 등록한다.
2. Obsidian Agent가 법령 관련 질문, 개발 요청, 사업 아이디어, 문서 작성 요청을 받을 때 필요한 법령 정보를 검색할 수 있게 한다.
3. Claude Code와 Codex는 법령 전체를 직접 컨텍스트로 들고 가지 않는다.
4. 대신 Obsidian Agent가 필요한 법령 정보만 요약해서 `Legal Context Pack`으로 제공한다.
5. 법령 원문, 시행령, 시행규칙, 개정 이력, 특정 날짜 기준 법령 상태를 조회할 수 있는 구조를 만든다.
6. 법령 데이터는 Obsidian Vault 안에 통째로 복사하지 않는다.
7. Obsidian 안에는 법령 색인, 요약, 사용 기록, 프로젝트별 법령 판단 근거만 저장한다.

---

## 2. 핵심 원칙

다음 원칙을 반드시 지켜라.

### A. legalize-kr 레포는 외부 데이터 소스다

`legalize-kr/legalize-kr` 레포 전체를 Obsidian Vault 내부에 넣지 마라.

이 레포는 법령 Markdown 파일이 많고 Git 히스토리도 크기 때문에 Obsidian Vault 안에 그대로 넣으면 다음 문제가 생길 수 있다.

- Obsidian 인덱싱 과부하
- 그래프뷰 과부하
- 검색 속도 저하
- 컨텍스트 초과
- Git 히스토리 관리 혼선
- 불필요한 파일 동기화 증가

따라서 아래 중 하나의 위치에 외부 데이터로 둔다.

권장 위치:

```txt
사용자작업공간/
  external_data/
    legalize-kr/

또는:

사용자작업공간/
  data_sources/
    legalize-kr/

Obsidian Vault 안에는 다음 정보만 저장한다.

ObsidianVault/
  04_Wiki/
    Legal/
      Index.md
      Law_Search_Guide.md
      LegalizeKR_Source.md
      Frequently_Used_Laws.md

  05_Frameworks/
    LegalizeKR/
      README.md
      legalize_kr_adapter.md
      law_context_pack_rules.md
      law_query_patterns.md
      update_policy.md

  06_Context_Packs/
    Legal/
      generated/

  10_AgentBus/
    context_requests/
      legal/
    context_responses/
      legal/
3. 현재 레포 이해

작업을 시작하기 전에 legalize-kr/legalize-kr 레포의 구조를 이해하라.

기본 구조는 다음과 같다.

legalize-kr/
  kr/
    {법령명}/
      법률.md
      시행령.md
      시행규칙.md
      대통령령.md
      {파일명}({법령구분}).md
  README.md

예시:

kr/민법/법률.md
kr/민법/시행령.md
kr/근로기준법/법률.md
kr/건축법/법률.md
kr/건축법/시행령.md
kr/건축법/시행규칙.md

각 법령 Markdown 파일에는 YAML frontmatter가 있을 수 있다.

예상 메타데이터:

---
제목: 민법
법령MST: 284415
법령ID: "001001"
법령구분: 법률
법령구분코드: A0002
소관부처:
  - 법무부
공포일자: 2024-01-02
공포번호: "19834"
시행일자: 2024-07-03
법령분야: 민사
상태: 시행
출처: https://www.law.go.kr/법령/민법
---

이 메타데이터를 법령 검색과 Context Pack 생성에 활용하라.

4. Clone 전략

두 가지 모드를 지원하라.

Mode A. 현재 법령 조회 중심

현재 시행 중인 법령 원문 검색과 요약이 목적이면 shallow clone을 우선 사용한다.

mkdir -p external_data
cd external_data
git clone --depth 1 https://github.com/legalize-kr/legalize-kr.git

이 방식은 빠르고 가볍다.

사용 목적:

현재 법령 검색
특정 법령 원문 조회
법률 / 시행령 / 시행규칙 비교
Obsidian Wiki 색인 생성
프로젝트별 법령 Context Pack 생성
Mode B. 개정 이력 분석 중심

법령의 과거 개정 이력, 특정 날짜 기준 법령 상태, 공포일자별 변경 분석이 필요하면 full clone을 사용한다.

mkdir -p external_data
cd external_data
git clone https://github.com/legalize-kr/legalize-kr.git

사용 목적:

특정 날짜 기준 법령 상태 조회
과거 개정 이력 분석
법령 변화 추적
Git log 기반 히스토리 분석
프로젝트별 법령 변화 리포트 작성

단, full clone은 무겁기 때문에 처음에는 Mode A를 기본으로 두고, 필요할 때 Mode B로 전환한다.

5. Force-push 대응 규칙

이 레포는 파이프라인 개선 시 전체 법령 히스토리 재구성을 위해 force-push가 발생할 수 있다.

따라서 다음을 지켜라.

특정 commit hash를 영구 기준으로 삼지 않는다.
법령 기준점은 commit hash보다 다음 정보를 우선 사용한다.
법령명
법령ID
법령MST
공포일자
시행일자
출처 URL
Obsidian 기록에는 commit hash를 보조 정보로만 저장한다.
동기화 스크립트에는 강제 재동기화 옵션을 둔다.

동기화 명령 예시:

cd external_data/legalize-kr
git fetch --all
git reset --hard origin/main
6. legalize-cli / MCP 선택적 적용

가능하면 legalize-kr/cli-tools도 검토하라.

legalize-cli는 GitHub REST API로 한국 법령, 판례, 행정규칙, 자치법규를 조회하는 CLI이며, 클론 없이 인증 없이 사용할 수 있고 JSON 출력도 지원한다.

또한 MCP 서버인 legalize-mcp를 통해 Claude Code, Cursor, Gemini CLI 등 MCP 지원 클라이언트에서 법령 조회 도구로 등록할 수 있다.

따라서 두 가지 연결 방식을 모두 설계하라.

방식 1. Git Repository 기반
external_data/legalize-kr를 로컬에 clone
grep, rg, git log, git show로 검색
대량 검색과 로컬 분석에 유리
방식 2. legalize-cli / MCP 기반
legalize-cli 설치
법령 조회를 CLI 또는 MCP로 수행
JSON 결과를 Obsidian Agent가 받아서 Context Pack으로 변환

설치 예시:

pipx install legalize-cli

MCP 서버가 필요한 경우:

pipx install 'legalize-cli[mcp]'
legalize-mcp

또는 설치 없이 실행:

uvx --from legalize-cli[mcp] legalize-mcp

단, MCP는 초기 필수 구현이 아니다.
먼저 로컬 Git 기반 검색 구조를 만들고, 이후 MCP를 확장 옵션으로 둔다.

7. Obsidian 내부 폴더 생성

Obsidian Vault 안에 다음 구조를 생성하라.

04_Wiki/
  Legal/
    Index.md
    LegalizeKR_Source.md
    Law_Search_Guide.md
    Frequently_Used_Laws.md
    Interior_Laws.md
    Business_Laws.md
    AI_Service_Laws.md
    Privacy_Laws.md
    Contract_Laws.md

05_Frameworks/
  LegalizeKR/
    README.md
    legalize_kr_adapter.md
    law_context_pack_rules.md
    law_query_patterns.md
    update_policy.md
    legal_risk_policy.md
    github_sync_policy.md
    cli_mcp_policy.md

06_Context_Packs/
  Legal/
    generated/
    templates/
      legal_context_pack_template.md

10_AgentBus/
  context_requests/
    legal/
  context_responses/
    legal/
  reports/
    LegalizeKR/
8. LegalizeKR Framework Card 작성

다음 파일을 생성하라.

05_Frameworks/LegalizeKR/README.md

내용은 다음 구조로 작성한다.

# LegalizeKR Framework

## 목적
LegalizeKR는 대한민국 법령 데이터를 Obsidian Agent Brain System에서 조회, 요약, 비교, 프로젝트별 법령 Context Pack 생성에 활용하기 위한 외부 법령 지식베이스다.

## 데이터 소스
- Repository: legalize-kr/legalize-kr
- Data Type: Korean laws as Markdown files
- Main Folder: kr/
- Metadata: YAML frontmatter
- History: Git commits based on promulgation dates

## 사용해야 하는 경우
- 사용자가 법령 정보를 요구할 때
- 사업 아이디어가 법적 검토가 필요할 때
- 인테리어, 건축, 계약, 개인정보, AI 서비스, 광고, 전자상거래 관련 판단이 필요할 때
- 개발 중 약관, 개인정보처리방침, 계약서, 고지문, 정책문서가 필요할 때
- 특정 날짜 기준 법령 상태를 확인해야 할 때

## 사용하지 말아야 하는 경우
- 단순 개발 코드 작성만 필요한 경우
- 법령과 무관한 일반 아이디어 정리
- 법적 판단 없이 단순 UI/UX 작업만 하는 경우

## 조회 방식
1. Local Git Repository
2. legalize-cli
3. legalize-mcp
4. law.go.kr 출처 URL 확인

## 주의사항
- 전체 법령을 LLM 컨텍스트로 넣지 않는다.
- 필요한 조문만 추출한다.
- 법령 원문과 요약을 구분한다.
- 날짜 기준을 명확히 한다.
- 개정 이력 분석 시 Git history를 사용한다.
- force-push 가능성을 고려하여 commit hash에만 의존하지 않는다.
9. 법령 검색 규칙 작성

다음 파일을 생성하라.

05_Frameworks/LegalizeKR/law_query_patterns.md

내용은 다음 구조로 작성한다.

# Law Query Patterns

## 1. 법령명으로 현재 법령 찾기

예시:

```bash
find external_data/legalize-kr/kr -type d -name "민법"
cat external_data/legalize-kr/kr/민법/법률.md
2. 특정 키워드 검색

예시:

rg "개인정보" external_data/legalize-kr/kr
rg "건축허가" external_data/legalize-kr/kr
rg "실내건축" external_data/legalize-kr/kr
rg "전자상거래" external_data/legalize-kr/kr
3. 법률 / 시행령 / 시행규칙 비교

예시:

ls external_data/legalize-kr/kr/건축법
cat external_data/legalize-kr/kr/건축법/법률.md
cat external_data/legalize-kr/kr/건축법/시행령.md
cat external_data/legalize-kr/kr/건축법/시행규칙.md
4. 개정 이력 조회

예시:

cd external_data/legalize-kr
git log -- kr/민법/
git log -- kr/건축법/
5. 특정 날짜 기준 법령 확인

예시:

cd external_data/legalize-kr
git log --before="2025-01-01" -1 -- kr/민법/법률.md
git show <commit_hash>:kr/민법/법률.md
6. YAML frontmatter 추출

법령 파일의 상단 YAML frontmatter를 읽어 다음 정보를 추출한다.

제목
법령ID
법령MST
법령구분
소관부처
공포일자
시행일자
상태
출처
7. 검색 결과 처리 원칙

검색 결과는 그대로 LLM에 넣지 않는다.
다음 순서로 압축한다.

관련 법령 후보 목록
관련 조문 후보
핵심 원문 발췌
요약
프로젝트 적용 판단
출처 경로
날짜 기준

---

## 10. Legal Context Pack 템플릿 생성

다음 파일을 생성하라.

```txt
06_Context_Packs/Legal/templates/legal_context_pack_template.md

내용:

# Legal Context Pack

## 1. 요청 ID
예: legal-request-2026-05-20-001

## 2. 사용자 요청
사용자의 원래 질문 또는 개발 요청

## 3. 법령 조회 목적
- 현재 법령 확인
- 특정 조문 확인
- 법률/시행령/시행규칙 비교
- 특정 날짜 기준 확인
- 개정 이력 분석
- 사업/개발 적용 검토

## 4. 기준일
예: 2026-05-20

## 5. 조회한 데이터 소스
- Repository: legalize-kr/legalize-kr
- Local path:
- 법령 파일 경로:
- Git commit:
- 출처 URL:

## 6. 관련 법령 후보
| 법령명 | 파일 경로 | 법령구분 | 시행일자 | 상태 |
|---|---|---|---|---|

## 7. 관련 조문 원문
필요한 조문만 발췌한다.
전체 법령을 붙여넣지 않는다.

## 8. 핵심 요약
법령 원문을 사용자 목적에 맞게 요약한다.

## 9. 프로젝트 적용 판단
이 법령이 현재 프로젝트에 어떤 영향을 주는지 정리한다.

## 10. 개발 작업 반영 사항
Claude Code 또는 Codex가 반영해야 할 사항.

예:
- 약관 문구 필요
- 개인정보 수집 동의 필요
- 건축/인테리어 관련 고지 필요
- 계약서 조항 필요
- 사용자 데이터 저장 방식 수정 필요
- 광고 문구 제한 필요

## 11. 주의사항
- 날짜 기준
- 원문 확인 필요 지점
- 법령 해석상 불확실한 부분
- 추가로 확인해야 할 법령

## 12. 다음 액션
- Obsidian Wiki 반영
- 프로젝트 문서 반영
- Claude Code 작업 요청
- Codex 구현 요청
11. Obsidian Agent 라우팅 규칙에 추가

기존 파일이 있으면 수정하고, 없으면 생성하라.

00_System/ROUTING_RULES.md

다음 내용을 추가하라.

# LegalizeKR Routing Rules

## LegalizeKR를 사용해야 하는 요청

사용자 요청에 다음 키워드나 의도가 포함되면 LegalizeKR Framework를 사용한다.

### 법령 직접 질문
- 법
- 법률
- 시행령
- 시행규칙
- 조문
- 법령
- 개정
- 공포일자
- 시행일자
- 판례
- 행정규칙
- 자치법규

### 사업 관련
- 계약서
- 약관
- 개인정보처리방침
- 전자상거래
- 광고 문구
- 고지 의무
- 수수료
- 플랫폼 운영
- AI 서비스 운영
- 데이터 수집
- 회원가입
- 결제
- 환불
- 구독

### 인테리어 / 건축 관련
- 건축법
- 실내건축
- 인테리어 공사
- 감리
- 하자
- 계약
- 시공
- 안전관리
- 소방
- 전기
- 주택
- 상가
- 용도변경
- 허가
- 신고

## 처리 순서

1. 사용자 요청에서 법령 관련 의도를 감지한다.
2. 관련 키워드를 추출한다.
3. LegalizeKR 데이터 소스에서 관련 법령 후보를 검색한다.
4. 필요한 조문만 추출한다.
5. Legal Context Pack을 생성한다.
6. 개발 작업이면 Claude Code 또는 Codex에게 Context Pack만 전달한다.
7. Obsidian Wiki에 법령 요약과 사용 기록을 저장한다.

## 금지 사항

- 전체 법령 파일을 통째로 Claude Code나 Codex에 전달하지 않는다.
- 전체 `kr/` 폴더를 Obsidian Vault에 넣지 않는다.
- 법령 요약과 원문을 혼동하지 않는다.
- 기준일 없이 법령 판단을 하지 않는다.
- commit hash만으로 법령 기준점을 삼지 않는다.
12. 법령 검색 어댑터 설계

다음 파일을 생성하라.

05_Frameworks/LegalizeKR/legalize_kr_adapter.md

내용:

# LegalizeKR Adapter Design

## 목적
Obsidian Agent가 legalize-kr 법령 데이터를 조회하고, 필요한 결과만 Context Pack으로 변환하기 위한 어댑터 설계다.

## 입력
- 사용자 질문
- 프로젝트명
- 기준일
- 법령명
- 키워드
- 필요한 결과 유형

## 출력
- 관련 법령 후보
- 관련 조문
- YAML metadata
- 법령 원문 일부
- 요약
- 프로젝트 적용 판단
- Context Pack

## Adapter Modes

### 1. Local Git Mode
로컬에 clone된 `external_data/legalize-kr`를 사용한다.

장점:
- 빠른 검색
- Git history 분석 가능
- 오프라인 활용 가능

단점:
- 저장 공간 필요
- 업데이트 관리 필요

### 2. legalize-cli Mode
`legalize-cli`를 사용해 조회한다.

장점:
- 클론 없이 사용 가능
- JSON 출력 가능
- 에이전트 소비에 적합

단점:
- GitHub API rate limit 영향
- 토큰 설정 필요 가능

### 3. MCP Mode
`legalize-mcp`를 Claude Code, Cursor, Codex 등 MCP 지원 도구에 연결한다.

장점:
- AI Agent가 직접 도구 호출 가능
- 법령 조회 자동화 가능

단점:
- MCP 설정 필요
- 초기 구조에서는 선택 사항

## 기본 전략
초기에는 Local Git Mode를 기본으로 한다.
이후 legalize-cli와 MCP Mode를 확장한다.
13. 스크립트 생성 요청

가능하다면 다음 스크립트를 생성하라.

scripts/legalize_sync.sh
scripts/legalize_search.sh
scripts/legalize_context_pack.py
scripts/legalize_sync.sh

역할:

external_data/legalize-kr가 없으면 clone
있으면 fetch/reset
shallow mode / full mode 선택 가능

예상 기능:

./scripts/legalize_sync.sh shallow
./scripts/legalize_sync.sh full
./scripts/legalize_sync.sh update
scripts/legalize_search.sh

역할:

키워드 기반 법령 검색
법령명 기반 파일 찾기
ripgrep 사용 가능

예상 기능:

./scripts/legalize_search.sh "개인정보"
./scripts/legalize_search.sh "건축허가"
./scripts/legalize_search.sh "실내건축"
scripts/legalize_context_pack.py

역할:

법령 파일 경로와 사용자 요청을 입력받음
YAML frontmatter 추출
관련 조문 일부 추출
Legal Context Pack Markdown 생성
결과를 06_Context_Packs/Legal/generated/에 저장

예상 사용:

python scripts/legalize_context_pack.py \
  --query "인테리어 계약서 작성 시 필요한 법령 검토" \
  --law "건축법" \
  --date "2026-05-20"
14. 프로젝트별 적용 방식

사용자가 특정 프로젝트에서 법령 검토를 요청하면 다음 순서로 처리한다.

예시 프로젝트:

03_Projects/
  AI_Automation_Business/
  Interior_Contract_System/
  Discord_Agent_System/
  Obsidian_Agent_Brain/

처리 방식:

프로젝트 폴더의 project.md를 읽는다.
요청 내용에서 법령 관련 키워드를 추출한다.
LegalizeKR Framework를 호출한다.
관련 법령을 검색한다.
Legal Context Pack을 생성한다.
프로젝트 폴더에 결과를 저장한다.

저장 위치 예시:

03_Projects/Interior_Contract_System/legal_context.md
03_Projects/Interior_Contract_System/legal_decisions.md
03_Projects/Interior_Contract_System/legal_risks.md
15. 인테리어 / 건축 업무용 기본 법령 후보

사용자는 인테리어 디자이너 및 시공·관리·감리 업무를 한다.

따라서 다음 법령 후보를 우선 색인 대상으로 검토하라.

건축법
건축법 시행령
건축법 시행규칙
건설산업기본법
하도급거래 공정화에 관한 법률
주택법
소방시설 관련 법령
전기사업법 또는 전기공사 관련 법령
산업안전보건법
개인정보 보호법
전자상거래 등에서의 소비자보호에 관한 법률
표시ㆍ광고의 공정화에 관한 법률
약관의 규제에 관한 법률
민법
상법

단, 이 목록은 초기 후보일 뿐이다.
실제 파일 존재 여부는 legalize-kr 레포에서 검색해서 확인하라.
추측으로 확정하지 마라.

16. AI 자동화 사업용 기본 법령 후보

사용자의 AI 자동화 사업, 웹 수익화, 디스코드 봇, 자동화 서비스, 데이터 수집 시스템과 관련해서 다음 법령 후보를 검토하라.

개인정보 보호법
정보통신망 이용촉진 및 정보보호 등에 관한 법률
전자상거래 등에서의 소비자보호에 관한 법률
약관의 규제에 관한 법률
표시ㆍ광고의 공정화에 관한 법률
콘텐츠산업 진흥법
저작권법
부가가치세법
소득세법
전기통신사업법

실제 적용 여부는 프로젝트 목적에 따라 판단한다.

17. Context Pack 생성 예시

사용자 요청:

인테리어 계약 자동화 시스템을 만들려고 한다.
계약서 작성, 하자, 공사대금, 개인정보 수집, 전자서명 관련해서 필요한 법령을 검토해줘.

Obsidian Agent는 다음을 수행한다.

요청을 법령 검토 요청으로 분류
관련 키워드 추출:
인테리어
계약
하자
공사대금
개인정보
전자서명
LegalizeKR에서 후보 법령 검색:
민법
건축법
건설산업기본법
개인정보 보호법
전자문서 및 전자거래 관련 법령
관련 조문 후보를 추출
Legal Context Pack 생성
Claude Code 또는 Codex에게는 전체 법령이 아니라 Context Pack만 전달
개발 결과는 프로젝트 문서와 Wiki에 저장
18. Claude Code / Codex 작업 분담

이 프롬프트를 Claude Code와 Codex 둘 다 받을 수 있다.

최초 실행자

00_System/AGENT_STATE.md가 없으면 현재 에이전트가 Coordinator다.

해야 할 일:

구조 설계
폴더 생성
LegalizeKR Framework 문서 생성
Routing Rule 작성
Context Pack 템플릿 생성
스크립트 설계
초기 보고서 작성
두 번째 실행자

00_System/AGENT_STATE.md가 이미 있으면 현재 에이전트는 Reviewer / Implementer / Verifier다.

해야 할 일:

기존 Coordinator 계획 검토
누락된 파일 확인
스크립트 구현
검색 테스트
Context Pack 샘플 생성
보고서 작성
19. 충돌 방지

작업 시작 전 다음 파일을 확인하라.

00_System/AGENT_STATE.md
00_System/TASKS.md
00_System/HANDOFF_LOG.md
00_System/LOCKS/

LegalizeKR 작업을 시작하면 다음 lock을 생성하라.

00_System/LOCKS/task-legalizekr-integration.lock

작업 완료 후 다음 보고서를 작성하라.

10_AgentBus/reports/LegalizeKR/legalizekr_initial_integration_report.md

보고서에는 다음을 포함한다.

# LegalizeKR Integration Report

## 1. 작업자
Claude Code 또는 Codex

## 2. 작업 목적
legalize-kr 법령 데이터 저장소를 Obsidian Agent Brain System에 연결

## 3. 생성한 폴더
목록

## 4. 생성한 파일
목록

## 5. 외부 데이터 위치
external_data/legalize-kr

## 6. 적용 방식
Local Git / legalize-cli / MCP 중 무엇을 적용했는지

## 7. 테스트 결과
검색 테스트 결과

## 8. 샘플 Context Pack
생성 여부

## 9. 남은 작업
다음 작업

## 10. 위험 요소
컨텍스트 초과, 저장소 크기, force-push, GitHub rate limit 등
20. 테스트 작업

초기 구축 후 다음 테스트를 수행하라.

테스트 1. 민법 검색
rg "손해배상" external_data/legalize-kr/kr/민법

또는:

cat external_data/legalize-kr/kr/민법/법률.md
테스트 2. 개인정보 보호법 검색
rg "개인정보" external_data/legalize-kr/kr
테스트 3. 건축법 검색
rg "건축허가" external_data/legalize-kr/kr
테스트 4. 시행령 비교
ls external_data/legalize-kr/kr/건축법
테스트 5. Git 이력 조회

full clone일 경우:

cd external_data/legalize-kr
git log -- kr/민법/
21. 최종 산출물

작업 완료 후 다음 산출물을 제공하라.

LegalizeKR Framework 문서
법령 검색 규칙 문서
Legal Context Pack 템플릿
Obsidian Routing Rule 추가
외부 데이터 clone 위치
검색 스크립트
동기화 스크립트
샘플 Context Pack
초기 통합 보고서
다음 작업 목록
22. 금지 사항

다음은 절대 하지 마라.

legalize-kr 전체 레포를 Obsidian Vault 내부에 복사하지 마라.
전체 법령 원문을 LLM 프롬프트에 한 번에 넣지 마라.
Claude Code와 Codex 각각에 별도 법령 위키를 중복 장착하지 마라.
commit hash를 영구 기준으로 삼지 마라.
기준일 없이 법령 내용을 단정하지 마라.
법령 원문과 요약을 섞지 마라.
기존 Obsidian Agent 구조를 덮어쓰지 마라.
lock이 걸린 파일을 수정하지 마라.
법령 해석을 확정적 결론처럼 작성하지 마라.
외부 데이터 업데이트 없이 오래된 법령을 최신처럼 사용하지 마라.
23. 지금 바로 수행할 첫 작업

이 프롬프트를 받으면 다음 순서로 작업하라.

현재 작업 디렉토리를 확인한다.
Obsidian Vault 위치를 찾는다.
없으면 ObsidianVault_Scaffold를 기준으로 임시 구조를 만든다.
00_System/AGENT_STATE.md를 확인한다.
LegalizeKR 작업 lock을 생성한다.
Obsidian 내부 LegalizeKR 폴더 구조를 만든다.
05_Frameworks/LegalizeKR/README.md를 생성한다.
law_query_patterns.md를 생성한다.
legal_context_pack_template.md를 생성한다.
ROUTING_RULES.md에 LegalizeKR 라우팅 규칙을 추가한다.
external_data/legalize-kr 위치에 shallow clone을 준비한다.
검색 테스트를 1개 이상 수행한다.
초기 통합 보고서를 작성한다.
24. 응답 형식

작업 완료 후 다음 형식으로 보고하라.

# LegalizeKR 적용 작업 보고

## 1. 내 역할
Coordinator / Reviewer / Implementer / Verifier

## 2. 적용 대상
legalize-kr/legalize-kr

## 3. 적용 목적
Obsidian Agent Brain System의 외부 법령 지식베이스로 연결

## 4. 생성한 폴더
목록

## 5. 생성한 파일
목록

## 6. 외부 데이터 위치
external_data/legalize-kr

## 7. 검색 테스트
실행한 명령과 결과 요약

## 8. Obsidian Agent 연동 방식
RAW, Context Pack, Routing Rule, Legal Wiki 연결 방식

## 9. Claude Code / Codex 사용 방식
개발 도구가 법령 정보를 어떻게 요청하고 받는지

## 10. 남은 작업
다음 단계

## 11. 주의사항
컨텍스트 초과, force-push, GitHub rate limit, 법령 기준일 문제

## 12. 완료 여부
완료 / 부분 완료 / 보류

이제 위 지침에 따라 legalize-kr 법령 지식베이스를 Obsidian Agent Brain System에 적용하라.


---

# 추가로 넣으면 좋은 짧은 지시문

첫 번째로 실행할 도구에게는 이걸 붙이면 돼.

```md
너는 최초 실행자다. LegalizeKR 적용 작업의 Coordinator / Architect 역할을 맡아라. 먼저 구조를 만들고, Obsidian Vault 안에 전체 법령 레포를 복사하지 말고, 외부 데이터 소스로 연결하는 방식으로 설계하라.

두 번째 도구에게는 이걸 붙이면 돼.

너는 두 번째 실행자다. 먼저 AGENT_STATE.md, TASKS.md, HANDOFF_LOG.md, LegalizeKR 관련 문서를 읽어라. 기존 구조를 덮어쓰지 말고 Reviewer / Implementer / Verifier 역할로 누락된 스크립트, 테스트, 샘플 Context Pack을 보완하라.
이 레포를 적용할 때 핵심 판단

legalize-kr/legalize-kr는 법령 원문 데이터 저장소로 쓰고, legalize-kr/cli-tools는 에이전트가 법령을 쉽게 조회하는 도구로 쓰면 좋아. cli-tools README에서는 legalize-cli가 클론 없이 GitHub REST API로 한국 법령·판례·행정규칙·자치법규를 조회할 수 있고, JSON 출력과 MCP 서버도 지원한다고 설명한다.

그래서 최종 구조는 이렇게 잡으면 된다.

legalize-kr/legalize-kr
= 법령 원문 데이터 소스

legalize-cli / legalize-mcp
= 법령 조회 도구

Obsidian Agent
= 법령 검색 요청을 판단하고 Context Pack 생성

Claude Code / Codex
= 법령 Context Pack을 받아 개발 작업에 반영

Obsidian Wiki
= 자주 쓰는 법령 요약, 프로젝트별 법령 판단 근거 저장

즉, 이 레포는 네 시스템에서 “대한민국 법령 위키 소스” 역할을 하게 된다.
옵시디언은 법령 전체를 품는 게 아니라, 법령을 호출하고 정리하는 브레인 역할을 맡는 게 가장 안정적이야.