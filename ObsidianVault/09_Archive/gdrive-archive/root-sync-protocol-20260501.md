# 동기화 프로토콜 — Claude · Codex 공통 규약

> 최종 업데이트: 2026-04-29 20:16 KST  
> 발동 조건: 사용자가 "동기화" 또는 "동기화해줘" 입력 시  
> 적용 대상: Claude · Codex 양쪽 동일

---

## 트리거 단어

다음 단어/문장 모두 동기화 프로토콜 발동:
- `동기화`
- `동기화해줘`
- `sync`
- `동기화 시작`
- `오늘 작업 정리해줘`
- `이 PC 최신화`

---

## 발동 시 자동 수행 절차 (양쪽 공통)

### 1단계: 환경 감지 및 보고
```
- PC 감지 (집 PC / 사무실 PC / 노트북)
- 현재 시각 (KST)
- 현재 작업 디렉터리
- git 현재 브랜치
```
→ 사용자에게 1줄 보고

### 2단계: 매니페스트 로드 및 상태 점검
```
- sync-manifest.md 로드 (G:\내 드라이브\JH-SHARED\)
- Tier 1 → Tier 2 → Tier 3 순회
- 각 local_path에서 git status / git log --oneline -5
- 미push 커밋 존재 여부 확인
- ~/.claude 또는 ~/.codex 변경 유무
```

### 3단계: 처리 목록 사전 보고
```
다음 항목을 동기화합니다:
1. [프로젝트A] 미커밋 N개 → 커밋·push 필요
2. [프로젝트B] 미push 1개 → push 필요
3. ~/.claude 변경 N개 → push.sh 실행
4. Obsidian 기록 대상: [요약 항목]
```
→ 사용자 승인 대기 (자동 실행 금지)

### 4단계: 사용자 승인 후 실행
- Claude: git add → commit → push, ~/.claude push.sh
- Codex: 변경된 파일 검수 후 보고만 (push는 Claude 담당)

### 5단계: Obsidian 반영 안내
- Daily Note 형식 초안 생성
- 사용자 붙여넣기용 텍스트 제공
- 자동 저장 시도 금지 (Obsidian 앱 외부 쓰기 충돌 우려)

### 6단계: 완료 보고 + 로그 기록
```
✅ 동기화 완료
- GitHub push: N개 레포
- ~/.claude 갱신: 완료/스킵
- Obsidian 초안: 제공됨
- 다음 PC 시작 시: git pull + ~/.claude/scripts/pull.sh
```

→ `G:\내 드라이브\JH-SHARED\sync-log.md` 상단에 결과 항목 추가

---

## 역할 분담 (동기화 시)

| 작업 | Claude | Codex |
|------|--------|-------|
| 환경 감지 보고 | ✅ | ✅ |
| git status 점검 | ✅ | ✅ |
| commit/push 실행 | ✅ | ❌ (검수만) |
| 변경 파일 품질 검수 | ❌ | ✅ |
| Obsidian 초안 생성 | ✅ | ❌ |
| ~/.claude push.sh 실행 | ✅ | ❌ |
| 사용자 승인 대기 | ✅ | ✅ |

**Codex 동기화 시 행동:**
- 검수자 정체성 유지하면서 동기화 절차 협조
- commit 직전 변경 파일 검수 1회 수행
- 보고 형식: 기존 `[Codex 검수 결과]` 양식 유지

---

## 안전 규칙

- **자동 실행 금지**: 모든 단계는 사용자 승인 후
- **파괴적 명령 금지**: `git reset --hard`, `git push --force`, `rm -rf` 자동 실행 차단
- **충돌 발생 시**: 자동 해결 시도 금지 → 사용자에게 보고
- **시크릿 감지 시**: commit 차단 후 사용자 고지

---

## PC별 경로 (참조)

| PC | 프로젝트 루트 |
|----|-------------|
| 집 PC (user1) | `D:\ai프로젝트\` |
| 사무실 PC (설계4) | `C:\ai프로젝트\` |
| 노트북 (info) | `C:\ai프로젝트\` |

| 자원 | 경로 |
|------|------|
| Claude 지침 GitHub | https://github.com/jaeha81/claude-projects-jh |
| 이 프로토콜 파일 | `G:\내 드라이브\JH-SHARED\sync-protocol.md` |
| 시스템 브리핑 | `G:\내 드라이브\JH-SHARED\jh-system.md` |
| Obsidian Vault | `C:\Users\user1\Documents\Obsidian Vault\` |

---

## 갱신 규칙

- 프로토콜 변경 시 이 파일 업데이트
- Google Drive 자동 버전 히스토리로 이력 관리
- Claude · Codex 모두 세션 시작 시 이 파일 우선 참조
