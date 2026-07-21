---
source: 05_jh_estimate_ai.md
source_type: unknown
date: 2026-07-22
original_file: "D:\ai프로젝트\obsidian-agent-brain-system\ObsidianVault\01_RAW\memories\05_jh_estimate_ai.md"
source_conversation_id: 
source_file: "D:\ai프로젝트\obsidian-agent-brain-system\ObsidianVault\01_RAW\memories\05_jh_estimate_ai.md"
topics: [jh-estimate-ai, 견적시스템, 인테리어, 멀티에이전트, 공종분류, 도메인지식]
related: ["[[01_personal_career]]", "[[06_jh_harness]]", "[[02_JH_브랜드_생태계]]"]
confidence: 0.9
priority: 7.5
category_tags: [category/건설-인테리어, category/AI-에이전트]
distilled_at: 2026-07-22 03:30
supersedes: 
valid_until: 
last_verified: 
tags: [ai-distilled, source/unknown, category/건설-인테리어, category/AI-에이전트, jh-estimate-ai, 견적시스템, 인테리어, 멀티에이전트, 공종분류, 도메인지식]
---

> JH 인테리어 견적 AI의 정본 — 선행 JH-견적시스템(Excel 정규화)과 대회 출품 JH-EstimateAI(SCANNER→REPORTER 5-에이전트 파이프라인), 그리고 재하가 정의한 "현장성 있는 견적 시스템" 요구사항(14단계 흐름·데이터 구조·기존 AI 견적의 10대 문제)을 통합 정리.

> 병합 원본: `memories/05_jh_estimate_ai.md` + `memories2/05_인테리어_견적시스템.md` (동일 주제, 개념 70% 이상 겹침 → 1개 노트로 병합)

## 핵심 인사이트

- **JH-EstimateAI** = 인테리어 시공 비용 자동 추정 파이프라인. 2026 전국민 AI 챔피언 대회 출품작(마감 2026-04-24). 차별점: 단순 ChatGPT 연동이 아닌 18년 인테리어 실무 지식을 내재화한 도메인 전문 5-에이전트 end-to-end 자동화.
- **5-에이전트 파이프라인**: SCANNER(도면/사진/텍스트 → 공간 정보·치수·공종 목록) → ESTIMATOR(공종별 물량 m²/m³/개소) → PRICER(지역별·시장 단가 적용) → VALIDATOR(검증·이상값 플래그) → REPORTER(최종 견적서 Excel/PDF). 대회 출품 버전에 멀티하네스 아키텍처 적용 승인 — JH-하네스의 실제 검증 케이스.
- **선행 프로젝트 JH-견적시스템**(구현 완료 버전): FastAPI + Next.js 14 + Supabase, 5개 에이전트(orchestrator / template_manager / normalizer / classifier / bid_formatter). 핵심 과제 = 클라이언트마다 다른 Excel 컬럼 구조 → **정규화가 핵심**. 보안 사고 이력: `.env` 파일이 채팅에 업로드됨 → 키 교체 완료.
- **Paperclip 벤치마크 기반 4대 업그레이드**(우선순위 순): ① Goal Tree View(목표 구조 시각화) ② Per-Agent Token Budget Tracking ③ Cron Trigger Layer(시장가 정기 업데이트·자동 재견적) ④ EstimateAI 템플릿 패키징.
- **내재화된 공종 분류 9종**: 철거 / 목공 / 도장 / 바닥재 / 전기 / 설비(MEP) / 타일 / 창호 / 가구·붙박이. 단가는 지역별 인건비 차이 반영, 평당 기준가 → 실제 물량 기준가 변환, 시장가 주기 업데이트 필요.
- **기존 AI 견적 서비스의 10대 현장성 문제**(재하 판단): 철거비 누락, 욕실/주방 방수 누락, 업계 미사용 단위, 자재비·노무비 미구분, 공정 순서 이해 부족, 별도공사 미반영, 고객 예산 괴리, 상업/주거 단가 차이 무시, 하자 리스크 무시, 현장 조건 변동성 무시. → 인테리어 AI는 이미지 생성 수준으로 끝나면 안 되고 고객 정보·현장 정보·공사 항목 체크리스트(철거/전기 증설/냉난방/제작가구/외부공사/방수)·산출 항목·리스크 요소를 반드시 포함해야 한다.
- **원하는 견적 시스템 14단계 흐름**: 고객 기본 정보 입력 → 공간 유형 → 공사 범위 → 현장 조건 → 사진/도면 업로드 → AI가 누락 항목 질문 → 시장 단가 기반 1차 견적 → 별도공사 분리 → 공정·일정 계획 제안 → 설명형 견적서 제공 → 시공 의뢰 선택 → 관리자 대시보드 기록 → Sheets/DB 저장 → 실제 계약 데이터 비교로 정확도 개선(피드백 루프).
- **견적 요청 데이터 구조 확정**: request_id, customer(name/phone/email), space_type, project_type, location, area_pyeong, budget_range, construction_scope, 6개 공사 여부 플래그(demolition/waterproof/electric/hvac/custom_furniture/external), preferred_schedule, uploaded_files, ai_estimate_summary, estimated_min/max, separate_items, admin_status, memo.

## 연결 개념

- [[01_personal_career]]
- [[06_jh_harness]]
- [[02_JH_브랜드_생태계]]

## 지식 그래프 링크 🟡 MEDIUM

- [[2026-07-22-01-personal-career]]
- [[2026-07-22-02-JH-브랜드-생태계]]
- [[2026-07-22-03-tech-stack]]
- [[2026-07-22-04-jh-keanu]]

## 실행 가능한 태스크

- [ ] (2026-04 시점 기록) 2026 전국민 AI 챔피언 대회(마감 2026-04-24) 출품 결과·이후 진행 상태 확인
- [ ] 14단계 흐름 마지막 단계(실제 계약 데이터 vs 견적 비교 피드백 루프) 구현 여부 점검
- [ ] 시장 단가 데이터 업데이트 주기(Cron Trigger Layer) 실제 적용 여부 확인

## 태그

#source/unknown #category/건설-인테리어 #category/AI-에이전트 #jh-estimate-ai #견적시스템 #인테리어 #멀티에이전트 #공종분류 #도메인지식

---
*수동 정제: Claude Code 세션 (2026-07-22) — API 크레딧 부족으로 knowledge_distiller.py 재시도 대신 직접 정제. 원본: `05_jh_estimate_ai.md` + `05_인테리어_견적시스템.md` — 소스: unknown*
