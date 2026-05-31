---
type: reference
source: claude
project: jh-estimate-system
system: JH-Obsidian-Vault
status: done
date: 2026-04-27
tags: [견적시스템, 사용가이드, PDF, Excel, Supabase, SQLite]
  - #status/archive
  - #status/completed
summary: JH 견적시스템 전체 사용 가이드 — 설치, 실행, 파일 업로드, 공정 분류, 결과 다운로드
---

# JH 견적시스템 사용 가이드

> 인테리어/건설 견적 Excel·PDF → AI 공정 분류 자동화 시스템  
> GitHub: https://github.com/jaeha81/jh-estimate-system

---

## 빠른 시작

### 로컬 실행

1. `d:/ai프로젝트/jh-estimate-system/start-local.bat` 더블클릭
2. 브라우저에서 `http://localhost:3000` 접속

```
백엔드 API : http://localhost:8000
프론트엔드 : http://localhost:3000
API 문서   : http://localhost:8000/docs
```

### 배포 환경

프론트엔드: `https://frontend-six-bice-h5ixxwa1ij.vercel.app`

---

## 전체 사용 흐름

```
[파일 업로드] → [AI 자동 분류] → [검토 항목 확인] → [결과 다운로드]
     ↓                ↓                 ↓                   ↓
  /upload         PROCESSING        /confirm/{id}       /results/{id}
```

---

## 1단계 — 파일 업로드 (`/upload`)

**지원 형식:** `.xlsx`, `.xls`, `.pdf` (최대 50MB)

**AI 모드:**
- `api` — Claude AI 분류 (실운영, 정확)
- `mock` — 키워드 분류 (테스트, 빠름)

---

## 2단계 — AI 자동 분류

파이프라인: 파일 수신 → 항목 추출 → 공정 분류 → 신뢰도 검사 → 저장

| 결과 | 이동 |
|------|------|
| 전체 신뢰도 충족 (`DONE`) | 결과 페이지 자동 이동 |
| 검토 필요 항목 존재 (`CONFIRM_WAIT`) | 검토 페이지 이동 |

---

## 3단계 — 검토 확인 (`/confirm/{sessionId}`)

- 신뢰도 낮은 항목만 카드 표시
- 대공정 / 소공정 / 표준품명 직접 지정
- 확정 데이터 → 키워드 사전 누적 (다음 분류 정확도 향상)

---

## 4단계 — 결과 다운로드 (`/results/{sessionId}`)

| 입력 | 출력 |
|------|------|
| Excel | 원본 시트 유지 + 공정분류결과 시트 추가 |
| PDF | 새 Excel 파일 생성 |

---

## DB 모드 전환

`d:/ai프로젝트/jh-estimate-system/backend/.env`

```env
DB_TYPE=supabase   # 실운영
DB_TYPE=sqlite     # 로컬 테스트 (인터넷 불필요)
```

**Supabase 프로젝트:** `yxkgdnbqplolhuogrzmd.supabase.co`  
**테이블:** `estimate_sessions`, `estimate_line_items`, `brand_profiles`, `keyword_dict`  
**Storage 버킷:** `estimate-files`

---

## 브랜드 프로필 등록

```json
POST /api/v1/brand-profiles
{
  "brand_name": "업체명",
  "sheet_mapping": { "세부내역": "세부내역서" },
  "column_mapping": {
    "item_name": "B", "qty": "E", "unit_price": "F", "data_start_row": 5
  }
}
```

---

## API 엔드포인트 요약

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `POST` | `/api/v1/sessions` | 파일 업로드 + 세션 생성 |
| `GET` | `/api/v1/sessions/{id}` | 세션 상태 조회 |
| `GET` | `/api/v1/sessions/{id}/items` | 항목 목록 조회 |
| `PATCH` | `/api/v1/items/{id}/confirm` | 항목 공정 확정 |
| `POST` | `/api/v1/sessions/{id}/export` | 결과 Excel 생성 |
| `GET/POST` | `/api/v1/brand-profiles` | 브랜드 목록/등록 |

---

## 관련 노트

- [[jh-estimate-system-architecture]] (아키텍처)
- [[2026-04-27]] (세션 기록)
