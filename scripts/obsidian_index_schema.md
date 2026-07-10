# Obsidian Index Schema (obsidian-index) — B1

> 정본 필드 소스: `ObsidianVault/00_System/oabs-library-taxonomy-standard.md` (Required Catalog Fields)
> 생산자: `scripts/obsidian_indexer.py` (집PC) · 소비자: Oracle 인덱스 API (B3, stdlib 전용)
> 설계 근거: `bucky_os_oracle_cloud_second_brain_plan.md` §3.1/§4.1 — Oracle은 원본을 갖지 않고 **경량 인덱스**만 보유.

## 원칙

- **경량 = 메타데이터 + 짧은 스니펫.** 전체 원본은 담지 않는다(원본 조회는 집PC/gbrain).
- **plain JSON만.** Oracle(#2, aarch64)은 stdlib 전용이라 numpy/임베딩 불가 → 키워드·메타데이터 검색(발견/라우팅)만 인덱스가 담당. 의미검색은 집PC gbrain이 담당(공존).
- **증분.** 파일 해시로 변경분만 재인덱싱.

## 산출물 (`OBSIDIAN_INDEX_DIR`, 기본 `data/obsidian-index/`)

| 파일 | 내용 |
|---|---|
| `records.jsonl` | 노트 1개 = 1줄 JSON (아래 레코드 스키마) |
| `manifest.json` | 인덱스 메타(스키마 버전·생성시각·집계·증분 해시맵) |

## 레코드 스키마 (records.jsonl 한 줄)

```json
{
  "slug": "03_knowledge/distilled/2026-07/2026-07-09-foo",  // 안정 ID (경로 기반, sync_vault_to_gbrain.slug_for 규약)
  "path": "03_Knowledge/distilled/2026-07/2026-07-09-foo.md", // Vault 상대경로(posix)
  "folder": "03_Knowledge",          // 최상위 선반(폴더) — Taxonomy Folder Roles
  "title": "제목",                    // 본문 첫 H1, 없으면 파일 stem
  "type": "knowledge-node",           // frontmatter type (Node Types), 없으면 null
  "status": "active",                 // frontmatter status | null
  "domain": "agent_os",               // frontmatter domain | null
  "asset_type": "knowledge",          // frontmatter asset_type | null
  "growth_stage": "system_building",  // frontmatter growth_stage | null
  "source": "user",                   // frontmatter source | null
  "confidence": "verified",           // frontmatter confidence | null
  "keywords": ["second-brain"],       // frontmatter keywords (검색 핸들)
  "tags": ["ai-distilled"],           // frontmatter tags
  "wikilinks": ["related-node"],      // 본문 [[...]] 대상(별칭/앵커 제거)
  "headings": ["개요", "핵심"],        // 본문 H1~H3 (라우팅용)
  "snippet": "제목 + 첫 N줄 요약...",   // 발견용 짧은 스니펫(기본 500자)
  "mtime": 1751990400,                // 파일 수정시각(epoch)
  "size": 1234,                       // 바이트
  "hash": "md5..."                    // 증분 감지용
}
```

- 결측 카탈로그 필드는 `null`(스칼라)/`[]`(리스트). 인덱서는 검증하지 않고 **관측된 그대로** 기록한다(Audit는 별도 도구 책임).
- `keywords`/`tags`/`wikilinks`/`headings`는 항상 리스트.

## manifest.json

```json
{
  "schema_version": 1,
  "generated_at": "2026-07-09T12:00:00",
  "vault": "G:/내 드라이브/obsidian-agent-brain-system/ObsidianVault",
  "count": 4210,
  "folders": {"03_Knowledge": 120, "04_Wiki": 88},
  "types": {"knowledge-node": 95, "context-pack": 40},
  "hashes": {"<slug>": "<md5>"}   // 증분 재인덱싱용
}
```

## 검색 계약 (B3 Oracle API가 구현할 스코어링)

키워드 질의 토큰에 대해 레코드별 가중 매칭 점수(높은 순 top-k):

| 필드 | 가중치 |
|---|---|
| keywords (정확) | 5 |
| title | 4 |
| headings | 3 |
| tags / type / domain | 2 |
| snippet | 1 |

반환: `{slug, path, title, folder, snippet, score}` 리스트. (인덱서 `search` 서브커맨드가 동일 스코어링으로 로컬 검증)

## 제외 폴더

`.obsidian .trash .claude .rag node_modules .git __pycache__ 09_Archive`
(근거: `vault_rag.EXCLUDE_DIRS` + `sync_vault_to_gbrain.SKIP_DIRS` 합집합. 09_Archive=보존 선반이라 인덱싱 제외.)

## 버전

- `schema_version: 1` — 2026-07-09 초판.
