---
source: 11_client_projects.md
source_type: unknown
date: 2026-07-22
original_file: "D:\ai프로젝트\obsidian-agent-brain-system\ObsidianVault\01_RAW\memories\11_client_projects.md"
source_conversation_id: 
source_file: "D:\ai프로젝트\obsidian-agent-brain-system\ObsidianVault\01_RAW\memories\11_client_projects.md"
topics: [클라이언트-납품, d2c-플랫폼, eonid, 대시보드, 인프라-분리]
related: ["[[10_business_strategy]]", "[[01_personal_career]]"]
confidence: 0.9
priority: 7.0
category_tags: [category/비즈니스, category/개발]
distilled_at: 2026-07-22 03:30
supersedes: 
valid_until: 
last_verified: 
tags: [ai-distilled, source/unknown, category/비즈니스, category/개발, 클라이언트-납품, d2c-플랫폼, eonid, 대시보드, 인프라-분리]
---

> 클라이언트 납품 프로젝트 2건(일본 타겟 의료미용 D2C 제안서, EONID 멀티브랜드 대시보드)과 운영 원칙 — 모든 클라이언트 작업은 JH 개인 인프라와 완전 분리, 운영 책임은 클라이언트.

## 핵심 인사이트

- **의료미용/여성건강 D2C 구독 플랫폼**: 일본 시장 타겟, 한국 제품의 일본 진출 플랫폼. 정기 배송 기반 구독 모델. 납품 형태 = 기획 제안서(DOCX + PDF). JH 인프라 의존 없는 스탠드얼론 시스템.
- **EONID 브랜드 포트폴리오 대시보드**: 멀티브랜드 포트폴리오 관리, React 멀티탭 7탭 구성(Adidas 관련 / Converse 관련 / Twosome 관련 / SPC 서브브랜드 다수 / 경복대 콘텐츠 / 추가 브랜드 2탭). 디자인 = 다크 올리브/라임 색상 스킴, 다크 테마, 반응형. 납품 = Netlify 배포 패키지.
- **분리 원칙**: 모든 클라이언트 프로젝트는 JH 개인 인프라와 완전 분리 — 독립 배포 환경(클라이언트 도메인), JH 브랜딩 포함 여부는 협의.
- **납품 프로세스 4단계**: 기획/제안서(DOCX/PDF) → 클라이언트 승인 → 구현 → 납품 패키지(Netlify-ready, Docker-ready 등).
- **보안 원칙**: 클라이언트 데이터는 클라이언트 인프라에만 저장, API 키·민감 정보는 클라이언트가 직접 관리하도록 지시. 재하 역할 = 구조 설계 + 구현 제공, 운영은 클라이언트 책임.
- **구분 기준표**: 클라이언트 작업(독립 인프라·클라이언트 브랜드·클라이언트 환경 배포·코드 소유 협의·수익 창출) vs JH 개인 프로젝트(jh-* 레포·JH 브랜드·Vercel/Railway 배포·재하 소유·제품/포트폴리오).

## 연결 개념

- [[10_business_strategy]]
- [[01_personal_career]]

## 지식 그래프 링크 🟡 MEDIUM

- [[2026-07-22-03-사업-철학-의사결정]]
- [[2026-07-22-02-JH-브랜드-생태계]]
- [[2026-07-22-01-personal-career]]

## 실행 가능한 태스크

- [ ] 신규 클라이언트 작업 착수 시 이 노트의 4단계 납품 프로세스·보안 원칙을 체크리스트로 재사용
- [ ] D2C 플랫폼·EONID 대시보드의 현재 납품/운영 상태 확인 (기록 시점 이후 변동 가능)

## 태그

#source/unknown #category/비즈니스 #category/개발 #클라이언트-납품 #d2c-플랫폼 #eonid #대시보드 #인프라-분리

---
*수동 정제: Claude Code 세션 (2026-07-22) — API 크레딧 부족으로 knowledge_distiller.py 재시도 대신 직접 정제. 원본: `11_client_projects.md` — 소스: unknown*
