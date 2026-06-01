---
type: folder-registry
updated: 2026-06-02
author: claude-code
status: active
---

# Vault Folder Registry

> 중복 번호 폴더 현황 및 마이그레이션 계획 추적 문서.
> 06_Context_Packs는 Bucky 런타임 경로 — 절대 이동 금지.

---

## 정규(Canonical) 폴더

| 폴더 | 용도 | 상태 |
|------|------|------|
| `00_Dashboard/` | 대시보드 노트 | 정규 |
| `00_System/` | 시스템 설정·규칙·운영 문서 | 정규 |
| `01_RAW/` | 원본 ingest 입력 | 정규 |
| `02_Processed/` | RAW 처리 출력 | 정규 |
| `03_Knowledge/` | 지식 베이스 (기본 Knowledge 폴더) | 정규 |
| `03_Projects/` | 프로젝트 문서 | 정규 |
| `04_DAILY_REPORTS/` | 데일리 리포트 | 정규 |
| `05_Frameworks/` | 프레임워크·방법론 | 정규 |
| `05_Logs/` | 시스템 로그 | 정규 |
| `06_Context_Packs/` | **FROZEN — Bucky 런타임 경로** | 동결 |
| `07_Reports/` | 분석 리포트 | 정규 |
| `08_Templates/` | 템플릿 | 정규 |
| `09_Archive/` | 아카이브 | 정규 |
| `10_AgentBus/` | AgentBus 태스크 큐 | 정규 |
| `11_Interior_Business/` | 인테리어 사업 | 정규 |
| `12_Client_Consulting/` | 클라이언트 컨설팅 | 정규 |
| `99_Archive/` | 레거시 아카이브 | 정규 |
| `Inbox/` | 미분류 입력 | 정규 |

---

## 중복 번호 폴더 — 마이그레이션 추적

### 번호 02 중복

| 폴더 | 파일 수 | 마이그레이션 대상 | 상태 |
|------|---------|-----------------|------|
| `02_Processed/` | 2 | 정규 유지 | ✅ 정규 |
| `02_Project/` | 2 | → `03_Projects/` | 🔲 대기 중 |

**비고**: `02_Project/sniper-buying-dashboard/`는 `03_Projects/sniper-buying-dashboard.md`와 중복 검토 필요.

### 번호 04 중복

| 폴더 | 파일 수 | 마이그레이션 대상 | 상태 |
|------|---------|-----------------|------|
| `04_DAILY_REPORTS/` | - | 정규 유지 | ✅ 정규 |
| `04_Wiki/` | 5개 하위폴더 | 용도 별도 (Wiki 콘텐츠) | 🔲 검토 대기 |

### 번호 06 중복

| 폴더 | 파일 수 | wikilink 참조 | 마이그레이션 대상 | 상태 |
|------|---------|-------------|-----------------|------|
| `06_Context_Packs/` | - | 다수 | **FROZEN** | ⛔ 동결 |
| `06_Knowledge/` | 2 | 0 | → `03_Knowledge/` | ✅ 완료·검증 (커밋 3d996aa) |
| `06_Projects/` | 1개 하위폴더 | 0 | → `03_Projects/` | ✅ 완료·검증 (커밋 3d996aa) |
| `06_Resources/` | 1 | 0 | → `03_Knowledge/` | ✅ 완료·검증 (커밋 3d996aa) |

### 번호 09 중복

| 폴더 | 파일 수 | 마이그레이션 대상 | 상태 |
|------|---------|-----------------|------|
| `09_Archive/` | - | 정규 유지 | ✅ 정규 |
| `09_Knowledge_Capture/` | 2개 하위폴더 | 용도 별도 (패턴·자기성찰) | 🔲 검토 대기 |

---

## 기타 비표준 폴더

| 폴더 | 내용 | 처리 방향 |
|------|------|----------|
| `00_UPGRADE/` | 업그레이드 계획 | 검토 대기 |
| `AgentBus/` | 레거시 AgentBus (→ `10_AgentBus/`) | 검토 대기 |
| `_templates/` | 템플릿 (→ `08_Templates/`) | 검토 대기 |
| `graphify-out/` | 그래프 출력 | 검토 대기 |

---

## Preflight 검증 기록

| 날짜 | 작업 | 결과 |
|------|------|------|
| 2026-06-02 | 06_Knowledge + 06_Projects + 06_Resources 이동 | 확인 중 |
