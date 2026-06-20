---
type: system-policy
title: Private Boundary Policy
status: active
owner: Bucky
created: 2026-06-12
related:
  - ObsidianVault/00_System/VAULT_BOUNDARY.md
  - ObsidianVault/00_System/LEGACY_SECRET_REVIEW_POLICY_2026-05-30.md
  - ObsidianVault/06_Context_Packs/bucky-security-runtime-governance.md
tags:
  - status/active
  - area/security
---

# _Private 보안 분리 정책 (PRIVATE_BOUNDARY)

> 이 문서는 `_Private` 네임스페이스의 정의·취급·게이트 규칙을 명문화한다. `VAULT_BOUNDARY.md`(경계), `LEGACY_SECRET_REVIEW_POLICY`(레거시 시크릿 처리), `bucky-security-runtime-governance`(상위 보안 원칙) 위에 운영 레이어를 얹는다.

---

## 1. 적용 대상 (What goes in _Private)

다음 데이터는 반드시 `_Private` 네임스페이스에 둔다.

| 분류 | 예시 |
|---|---|
| 신원/계정 PII | 주민번호, 운전면허, 여권, 실주소, 가족·고객·협력사 개인정보 |
| 인증/자격 정보 | API 키, 비밀번호, OAuth refresh token, 인증서·키페어 |
| 금융 정보 | 계좌·카드 번호, 세금계산서 원본, 매출·매입 원장, 정산서 |
| 계약/법무 원본 | 고객 계약서 원본, NDA, 합의서, 분쟁 자료 |
| 고객 데이터 원본 | Wishket 클라이언트 미공개 정보, 인테리어 고객 도면·견적 원본 |
| 사업 비밀 | 가격 전략, 마진율 원장, 미공개 로드맵, 내부 협상 메모 |
| 개인 회고/일기 | 미공개 멘탈/건강 기록, 개인 감정 일지 |
| 인증 화면 캡처 | 토큰·세션·결제 정보가 비식별 처리되지 않은 스크린샷 |

→ 위 항목은 **공개 가능한 요약/규칙만** 일반 영역에 두고, 원본·원장·식별 가능한 디테일은 `_Private`로 격리한다.

---

## 2. 경로 컨벤션 (Path convention)

- **표준 폴더명**: `_Private/` (언더스코어 prefix → Obsidian 알파벳 정렬 최상단 + 시각적 구분)
- **위치 규칙**:
  - 1순위: `ObsidianVault/_Private/` (Vault 루트 직속, 도메인 무관 민감자료)
  - 2순위: 도메인 하위 격리 — `ObsidianVault/11_Interior_Business/_Private/`, `ObsidianVault/03_Projects/<repo>/_Private/`
  - **금지**: `_private/`, `_PRIVATE/`, `private/`, `.private/` 등 변형 표기. 도구가 인식 못함.
- **하위 구조 예시**:
  ```
  _Private/
    clients/          # 고객별 계약·연락처·결제 원본
    finance/          # 매출·매입·세무 원장
    credentials/      # 절대 평문 금지 — 인덱스/메타만, 실제 값은 secret store
    journal/          # 개인 회고
    archive/          # 만료/종료된 민감자료
  ```

---

## 3. Git 처리 (Git treatment)

`.gitignore` 강제 항목:

```
# Private content — never commit anywhere in vault or repo
_Private/
**/_Private/
.private/
**/.private/
```

추가 규칙:

1. `_Private/` 경로의 파일은 **절대 git add 금지** (커밋 훅으로 차단 권장).
2. Public push 전에 `git status` → `_Private` 경로 변경분이 없어야 함.
3. 실수 커밋 시: 즉시 `git rm --cached` + history rewrite + 노출된 시크릿 **rotate**.
4. `_Private` 내용은 **GitHub·공개 docs·Vercel/Cloudflare 배포 산출물에 포함 금지**.

---

## 4. 에이전트 처리 규칙 (Agent rules)

### 4.1 Bucky (오케스트레이터)
- `_Private` 경로의 파일을 Context Pack·패킷·프롬프트에 **원문 포함 금지**.
- 사용자 요청이 `_Private` 데이터를 필요로 하면 → **사용자가 직접 인용**해야 진행. Bucky가 읽어 옮기지 않음.
- 패킷 발행 시 `secret_handling: "_Private 접근 금지"` 명시.

### 4.2 Claude Code (구현자)
- `_Private/` 경로 자동 탐색·`Read`·`Grep` 금지. 사용자가 명시적으로 절대 경로를 지정한 경우에만 허용.
- 명시적 접근 시에도 **요약·인용을 채팅이나 로그에 남기지 않는다**. 작업 결과는 일반 영역의 비식별 요약으로만 보고.
- `_Private` 파일을 다른 위치로 복사·이동 금지 (단방향).
- `_Private` 데이터를 참조하는 스크립트는 환경변수·로컬 secret store에서 로딩하도록 설계.

### 4.3 Codex (독립 검수자)
- `_Private` 경로 리뷰 금지. 검수 범위는 일반 영역의 파생물(요약·규칙·코드)에 한정.
- 실수로 `_Private` 데이터가 일반 영역에 노출된 것을 발견하면 **사용자에게 직보** + Bucky에 차단 요청.

### 4.4 공통
- 모든 에이전트는 `_Private` 경로를 본 즉시 작업 중단 → 사용자 승인 절차로 전환.

---

## 5. 링크/트랜스클루전 규칙 (Linking rules)

| 방향 | 허용 여부 | 비고 |
|---|---|---|
| 공개 → `_Private` (`[[_Private/...]]`) | ⚠️ 제한적 허용 | 링크 텍스트가 식별 정보를 노출하지 않아야 함. Public 공유 시 dead link로 변환. |
| `_Private` → 공개 | ✅ 허용 | 단방향 참조는 안전 |
| `_Private` 트랜스클루전(`![[...]]`)을 공개 노트에 삽입 | ❌ 금지 | 렌더링 시 원문이 노출됨 |
| Graph view 노출 | 사용자 선택 | Obsidian Graph 필터에서 `path:_Private` 제외 권장 |
| Daily report·Bucky 대시보드 노출 | ❌ 금지 | `docs/`, `bucky-agent-os.html` 등 공개 산출물에서 차단 |

---

## 6. 백업·동기화 (Backup & sync)

- **Google Drive 동기화**: Vault 자체가 G 드라이브에 있으므로 자동 동기화됨. 추가 외부 백업(다른 클라우드·외장 SSD) 시 `_Private`만 별도 암호화 컨테이너(VeraCrypt 등)에 담을 것.
- **그래피파이/RAG 인덱싱 제외**: `_Private/`은 `.graphifyignore`·RAG 인덱서·임베딩 파이프라인에서 제외.
- **로그·캐시 격리**: `_Private` 처리 중 생성된 임시 파일·캐시는 같은 `_Private/` 또는 `runtime/_Private/` 아래에만 두고, 작업 후 즉시 삭제.

---

## 7. 감사·노출 사고 대응 (Audit & breach response)

### 7.1 일상 감사
- 월 1회: `git log --all -- '_Private/**' '**/_Private/**'` → 결과 없어야 정상.
- 월 1회: `grep -r` 또는 RAG 인덱스에서 `_Private` 경로 누출 여부 점검.

### 7.2 노출 사고 발생 시 (escalation)
1. **즉시 격리**: 노출된 파일·커밋·게시물 차단/삭제.
2. **자격 회전**: API 키·토큰·비밀번호 즉시 rotate.
3. **영향 범위 기록**: `ObsidianVault/_Private/incidents/YYYY-MM-DD-<slug>.md` (자체도 _Private).
4. **사용자 통지**: 고객 PII 노출 시 관련 법규(개인정보보호법) 통지 의무 확인.
5. **재발 방지**: 정책·gitignore·훅 보강 후 commit.

---

## 8. 예외/승인 (Exceptions)

`_Private` 데이터를 일반 영역으로 옮기거나 외부 공유해야 할 경우:

1. 사용자가 **명시적으로 비식별화·요약 범위를 지정**.
2. 처리 후 결과를 사용자가 직접 검토.
3. 처리 기록을 `00_System/private-exception-log.md`에 남김 (날짜·대상·범위·승인자).

자동 처리 금지. Bucky/Claude/Codex가 임의로 결정하지 않는다.

---

## 9. 점검 체크리스트

신규 노트·커밋·배포 전 셀프 체크:

- [ ] 이 파일에 PII·시크릿·고객 원본·금융 원장이 있나? → 있으면 `_Private`로 이동
- [ ] `git status`에 `_Private` 경로가 있나? → 있으면 unstage + .gitignore 확인
- [ ] 공개 docs/HTML/PWA 빌드 결과에 `_Private` 내용이 들어갔나?
- [ ] 에이전트 패킷·Context Pack에 `_Private` 원문이 인용됐나?
- [ ] 백업·동기화 대상에 `_Private`만 별도 암호화되어 있나?

---

## 10. 변경 이력

| 날짜 | 내용 | 변경자 |
|---|---|---|
| 2026-06-12 | 초안 작성 (정책 명문화 P0) | Claude Code |
