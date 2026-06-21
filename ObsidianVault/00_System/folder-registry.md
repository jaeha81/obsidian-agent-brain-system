---
type: folder-registry
updated: 2026-06-13
author: claude-code
status: active
---

# Vault Folder Registry

> 중복 번호 폴더 현황 및 마이그레이션 계획 추적 문서.
> 06_Context_Packs는 Bucky 런타임 경로 — 절대 이동 금지.
> 2026-06-13 G1 폴더 축 정리 실행 완료 — [[G1-folder-merge-plan]] (Codex 3회전 PASS) 참조.

---

## 정규(Canonical) 폴더 — G1 이후 최상위 24개 기준

| 폴더 | 용도 | 상태 |
|------|------|------|
| `00_Dashboard/` | 대시보드 노트 | 정규 |
| `00_Inbox/` | 미분류 입력 + Discord 캡처 + daily-plus triage | 정규 (**G1에서 Inbox 흡수**) |
| `00_System/` | 시스템 설정·규칙·운영 문서 | 정규 |
| `00_UPGRADE/` | 업그레이드 계획 | 정규 (용도 확정) |
| `01_RAW/` | 원본 ingest 입력 | 정규 |
| `02_Processed/` | RAW 처리 출력 | 정규 |
| `03_Knowledge/` | 지식 베이스 | 정규 |
| `03_Projects/` | 프로젝트 문서 | 정규 |
| `04_DAILY_REPORTS/` | 데일리 리포트 | 정규 |
| `04_SiteLog/` · `04_Wiki/` | 현장 로그 · Wiki 콘텐츠 | 번호 중복이나 용도 상이 — 검토 대기 |
| `05_Frameworks/` | 프레임워크·방법론 (AgentBus 프로토콜 문서 포함) | 정규 |
| `05_Logs/` | 시스템 로그 | 정규 |
| `06_Context_Packs/` | **FROZEN — Bucky 런타임 경로** | 동결 |
| `07_Reports/` | 분석 리포트 | 정규 |
| `08_Content/` | 콘텐츠 | 정규 |
| `08_Templates/` | 템플릿 | 정규 |
| `09_Archive/` | 아카이브 (레거시 gdrive 사본은 `gdrive-archive/` 하위) | 정규 (**G1에서 99_Archive 흡수**) |
| `09_Knowledge_Capture/` | 패턴·자기성찰 캡처 | 번호 중복이나 용도 상이 — 유지 |
| `10_AgentBus/` | AgentBus 태스크 큐 (라이브 DB) | 정규 |
| `11_Interior_Business/` | 인테리어 사업 | 정규 |
| `12_Client_Consulting/` | 클라이언트 컨설팅 | 정규 |
| `goals/` | Goal Mode 데이터 | 정규 (런타임 경로) |
| `graphify-out/` | 그래프 출력 | 검토 대기 |

---

## G1 정리 완료 기록 (2026-06-13)

| 폴더 | 처리 | 증거 |
|------|------|------|
| `06_Knowledge/` | 빈 껍데기 삭제 (3d996aa 이관 완료 잔존) + 깨진 링크 4건 → 03_Knowledge 재표적 | 삭제 전 0파일 재확인 |
| `06_Projects/` | 빈 껍데기 삭제 + 깨진 링크 4건 → 03_Projects 재표적 | 〃 |
| `06_Resources/` | 빈 껍데기 삭제 + 깨진 링크 1건 → 03_Knowledge 재표적 | 〃 |
| `AgentBus/` (루트) | 빈 스켈레톤 삭제 (코드 경로 참조 0건 실측) | 〃 |
| `Inbox/` | 57파일 → `00_Inbox/` 병합 (DiscordCaptures 포함), 스크립트 5곳+필터 4곳+링크 18건 갱신 | 00_Inbox 8→65파일 |
| `99_Archive/` | 22파일 → `09_Archive/gdrive-archive/` 흡수, migrator·scanner·tagger 갱신 | 22→22 보존 |

- 과거 완료 (3d996aa, 2026-06-02): 06_Knowledge/06_Projects/06_Resources 내용물 이관.
- `02_Project/`, `_templates/`: 2026-06-13 실측에서 이미 부재 — 별도 처리 불요 확인.

---

## Preflight 검증 기록

| 날짜 | 작업 | 결과 |
|------|------|------|
| 2026-06-02 | 06_Knowledge + 06_Projects + 06_Resources 이동 | ✅ 완료 (G1에서 빈 폴더 잔존 확인·제거) |
| 2026-06-13 | G1 전체 (껍데기 4 삭제 + Inbox·99_Archive 병합) | 스냅샷: `00_System/G1-preflight-snapshot.txt` / dirty patch: 레포 루트 `G1-preflight-dirty.patch` |

[[bucky-system-hub]]
