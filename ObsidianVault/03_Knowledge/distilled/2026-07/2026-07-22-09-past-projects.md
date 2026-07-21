---
source: 09_past_projects.md
source_type: unknown
date: 2026-07-22
original_file: "D:\ai프로젝트\obsidian-agent-brain-system\ObsidianVault\01_RAW\memories\09_past_projects.md"
source_conversation_id: 
source_file: "D:\ai프로젝트\obsidian-agent-brain-system\ObsidianVault\01_RAW\memories\09_past_projects.md"
topics: [과거-프로젝트, 아카이브, vision-ai, precon-ai, agent-exchange, 클라이언트-작업]
related: ["[[03_tech_stack]]", "[[04_jh_keanu]]", "[[10_business_strategy]]"]
confidence: 0.9
priority: 7.0
category_tags: [category/AI-에이전트, category/건설-인테리어]
distilled_at: 2026-07-22 03:30
supersedes: 
valid_until: 
last_verified: 
tags: [ai-distilled, source/unknown, category/AI-에이전트, category/건설-인테리어, 과거-프로젝트, 아카이브, vision-ai, precon-ai, agent-exchange, 클라이언트-작업]
---

> 재하의 과거 완료/보류 프로젝트 아카이브 정본 — JH-견적시스템·Vision AI·PreCon AI 등 자체 프로젝트, EONID·메디컬뷰티 등 클라이언트 작업, Agent Exchange 피벗과 보안 인시던트 교훈까지 (2026-04 시점).

> 병합 원본: `memories/09_past_projects.md` + `memories2/09_완료_프로젝트_아카이브.md` (동일 프로젝트 8개 이상 겹침, 개념 70% 이상 → 1개 노트로 병합)

## 핵심 인사이트

- **JH-견적시스템** (인테리어 견적 정규화): FastAPI + Next.js 14 + Supabase, 5개 에이전트(orchestrator, template_manager, normalizer, classifier, bid_formatter). 핵심 문제 = 클라이언트 브랜드마다 다른 Excel 컬럼 구조 → normalizer가 표준 스키마로 변환. **보안 인시던트**: `.env` 파일을 채팅에 실수 업로드 → API 키 로테이션 + 전체 팀 보안 프로세스 강화.
- **Vision AI System**: 6단계 빌드. FastAPI 39개 엔드포인트 + Flutter 앱 + YOLOv8 객체 탐지 + MJPEG 스트리밍 + 인테리어 도메인 어노테이션 + ReportLab PDF 리포트 + SLAM/3D 실험 모듈. 범용 재패키징 = Generic Vision AI Foundation Kit (65개 파일, pytest 16/16 통과).
- **PreCon AI**: 착공 전 AI 시뮬레이션 플랫폼. 10개 에이전트, 84개 파일, 통합 테스트 6/6 통과. 공정 시뮬레이션 + 리스크 사전 탐지.
- **완료 프로젝트**: SketchFlow(손그림 스케치 → 시공 워크플로우 자동 생성), ARKISTORE(물류/무역 — 발주·재고·납품 자동화), BitMEX 트레이딩 봇(마틴게일/DCA), JH Agent Factory(에이전트 생성/관리 팩토리 — 생태계 기반 인프라).
- **JH Agent Exchange** (컨셉 연구 → 피벗): A2A 에이전트 마켓플레이스 개념 → 건설/인테리어 버티컬 비치헤드 전략으로 전환(글로벌 동급 플랫폼 없음). 기술 로드맵: CrewAI MVP → LangGraph 프로덕션. 결제 로드맵: 카드 우선 → USDC(미국 GENIUS Act 이후) → 크립토(한국 입법 이후). 실행은 Claude Code로 전환하며 보류.
- **jh-playwright-agents**: 27개 파일, 13개 에이전트, 3트랙(DEV 검사 / 비즈니스 자동화 / 배포 전 체크). 자율 연속 실행 vs 승인 기반 워크플로우 원칙 충돌로 전역 JH 가이드라인과 **별개** 독립 가이드라인으로 운영.
- **클라이언트 작업 — JH 개인 인프라와 완전 분리**: ① EONID 대시보드(7탭 React 브랜드 포트폴리오 — Adidas, Converse, Twosome, SPC 서브브랜드, 경복대 등. 다크 올리브/라임 컬러, Netlify 배포 패키지 납품). ② 메디컬뷰티 일본 플랫폼(일본 타겟, 메디컬뷰티/여성건강, D2C 구독 모델, DOCX/PDF 제안서 납품 완료).
- **드림랜드**: 루루(LULU) 중심 캐릭터·세계관 프로젝트. 확장 방향: 동화책(PDF/ePub), 굿즈, AR 게임 프로토타입, 애니메이션, 스토리보드, 브랜드화.
- **JH-keanu(캐릭터)**: YouTube/인테리어 앱용 브랜드 캐릭터 이미지(YouTube 프로필, 개발자형 아바타, 하네스 대표 이미지, JH Connect 상징). ⚠️ jh-keanu **개발 레포지토리**와 동일 이름·다른 개념 — 혼동 금지.
- **Hermes Agent**: 벤치마크 완료 후 **도입 보류** — 현재 규모에 과도(스킬 자동 추출, 컨텍스트 압축, 세션 검색). 동시 프로젝트 5개 이상 시 재검토.

## 연결 개념

- [[03_tech_stack]]
- [[04_jh_keanu]]
- [[10_business_strategy]]

## 지식 그래프 링크 🟡 MEDIUM

- [[2026-07-22-04-jh-keanu]]
- [[2026-07-22-03-tech-stack]]
- [[2026-07-22-02-JH-브랜드-생태계]]
- [[2026-07-22-01-personal-career]]

## 실행 가능한 태스크

- [ ] Hermes Agent 재검토 조건(동시 프로젝트 5개 이상) 도달 여부 주기 점검 — 2026-04 보류 결정 기준

## 태그

#source/unknown #category/AI-에이전트 #category/건설-인테리어 #과거-프로젝트 #아카이브 #vision-ai #precon-ai #agent-exchange #클라이언트-작업

---
*수동 정제: Claude Code 세션 (2026-07-22) — API 크레딧 부족으로 knowledge_distiller.py 재시도 대신 직접 정제. 원본: `09_past_projects.md` + `09_완료_프로젝트_아카이브.md` — 소스: unknown*
