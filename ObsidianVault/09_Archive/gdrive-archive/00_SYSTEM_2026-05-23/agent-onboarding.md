# JH 에이전트 온보딩 — 다른 PC 시작 시 최소 확인

> 위치: `G:\내 드라이브\JH-SHARED\00_SYSTEM\agent-onboarding.md`  
> 대상: Claude · Codex  
> 목적: 다른 PC에서 시작할 때 JH 통합 구축 전제를 빠르게 숙지하고, 과도한 전역 지침 로딩을 막는다.

## 먼저 기억할 역할

- 사용자: 방향 · 지시 · 승인
- Claude: 구현 · 운영 총괄
- Codex: 독립 검수 · 사용자 직접 보고
- Agent Room: 사용자/Claude/Codex 커뮤니티방 및 동기화 스냅샷 기록 도구

## 저장소 역할

- GitHub: 코드 기준 저장소
- Google Drive: 자료·공유 문서·JH-SHARED
- Obsidian Vault: 지식·설계 결정·개발 기록
- 로컬 PC: 실행 환경, node_modules, 빌드 산출물

## 동기화 요청 시 우선 읽을 파일

아래 4개만 먼저 읽는다.

1. `G:\내 드라이브\JH-SHARED\00_SYSTEM\agent-onboarding.md`
2. `G:\내 드라이브\JH-SHARED\00_SYSTEM\sync-protocol.md`
3. `G:\내 드라이브\JH-SHARED\00_SYSTEM\jh-system.md`
4. `G:\내 드라이브\JH-SHARED\00_SYSTEM\paths.md`

## 필요한 경우에만 추가로 읽을 파일

- 현재 프로젝트의 `AGENTS.md` 또는 `CLAUDE.md`
- 프로젝트별 handoff
- Obsidian Vault `wiki/index.md`, `wiki/log.md`
- 전역 Claude/Codex 지침의 관련 섹션

## 금지

- 동기화 요청만으로 전역 `~/.claude/CLAUDE.md` 전체를 먼저 읽지 않는다.
- 제품 저장소에 JH 운영 도구를 섞지 않는다.
- Google Drive 폴더를 Git 저장소처럼 직접 운영하지 않는다.
- 사용자 승인 없이 여러 프로젝트를 자동 수정하지 않는다.

## 확인 문구

다른 PC에서 이 문서를 읽은 Claude/Codex는 다음처럼 보고한다.

```text
JH 전제 확인 완료: 역할 분담, 저장소 분리, 동기화 최소 컨텍스트 규칙을 확인했습니다.
현재 PC 스냅샷은 Agent Room의 동기화/업데이트 요청으로 기록하겠습니다.
```
## Agent Room 사전 검수 필수 규칙

Claude가 Agent Room을 통해 작업 결과, 구현 보고, 사용자 전달용 답변을 남길 때는 사용자에게 최종 전달하기 전에 Codex 검수를 항상 거친다.

운영 순서:

1. 사용자 지시
2. Claude 구현 또는 작업 보고 초안 작성
3. Codex 독립 검수
4. Codex 검수 결과를 Agent Room에 기록
5. 사용자에게 최종 보고

금지:

- Claude가 Codex 검수 없이 사용자에게 구현 완료를 최종 보고하지 않는다.
- Codex 검수 결과를 Claude가 자동으로 처리하거나 묵살하지 않는다.
- 수정이 필요하면 사용자가 Claude에게 지시한다.
