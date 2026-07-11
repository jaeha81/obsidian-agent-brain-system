# ADR-0005: 지식 정본 = 하나의 볼트 — 파생 저장소는 전부 캐시 (소급 기록)

- 상태: 승인됨 (사용자 확정, 2026-07-11) — 본 문서는 소급 기록 (작성 2026-07-11, Stage 14)
- 주: 플랜의 ADR 목록(0001~4) 외 추가분 — 사용자 확정 결정의 기록 의무(스펙 §0.2 "주요 선택은 ADR로")에 따름
- 관련: `docs/bucky/current_state_audit.md` §2 · `docs/bucky/assumptions.md` A1 · `ObsidianVault/00_System/LIBRARIAN_RULES.md`

## 맥락

기억이 다원 저장되어 있다: 볼트 3층(01_RAW → 03_Knowledge) + bucky_memory SQLite + gbrain DB + vault_rag 임베딩 + oracle obsidian_index. 어느 것이 정본인지 코드·문서 어디에도 선언되어 있지 않았고, gbrain DB 손상(06-28) 때 "무엇으로부터 복구하는가"가 관행으로만 존재했다. 사용자가 07-11 확정: "일원화하여 하나의 볼트를 봐야 합니다."

## 결정

1. **지식의 정본은 ObsidianVault 하나이며, 그 안의 SoT는 `03_Knowledge/`다** (3층 구조·볼트 내 규율은 LIBRARIAN_RULES.md가 정본).
2. 파생 저장소(gbrain DB, oracle obsidian_index, bucky_memory SQLite, vault_rag 임베딩)는 전부 **캐시로 강등**한다: 유실 시 볼트에서 재구축 가능해야 하고, 정본과 불일치 시 볼트가 이긴다.
3. 신규 기능(Stage 15~21 포함)은 파생 저장소에만 존재하는 지식을 만들지 않는다. 이벤트 로그(`05_Logs/` — 볼트 내)와 usage 원장은 지식이 아니라 운영 기록으로, 각자가 자기 도메인의 정본이다.
4. 구 볼트(`G:\내 드라이브\Obsidian Vault\`)는 archive-only 유지 — 통합 범위·시점은 별도 결정.

## 결과

- (+) 복구 시나리오 단순화: 캐시는 버리고 재구축하면 된다 (gbrain 재구축 구조와 정합).
- (+) 로컬 이전(D:\ai프로젝트 컷오버) 시 동기화 대상이 볼트 하나로 수렴.
- (−) 파생 저장소 재구축 경로가 실제로 전부 작동하는지는 미검증 — P1-4(인덱스 경로 불일치)가 첫 검증 지점.
- 제약: 파생 저장소를 정본으로 승격하는 변경은 사용자 승인 + 본 ADR 개정 없이 금지.
