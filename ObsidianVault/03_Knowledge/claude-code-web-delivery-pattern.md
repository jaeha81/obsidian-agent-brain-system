---
graph_cluster: claude-ai
---

# Claude Code 고가치 웹 납품 패턴

## 핵심 워크플로우

1. **클라이언트 브리프 → 구현 스펙 자동 변환**
   - 요구사항 수집 → PRD 생성 → 기술 스펙 분해
   - 수익 역산으로 기능 범위 결정

2. **MCP 기반 원클릭 파이프라인**
   - 디자인 탐색 (Variant/Pencil) → 코드 생성 → 배포 (Vercel)
   - 브라우저 MCP로 실시간 검증

3. **에이전트 체인 자동화**
   - 디자인 → 코드 → 검수 → 배포 4단계
   - 각 단계 완료 증거 필수 (Lighthouse, 스크린샷)

4. **반복 가능 템플릿**
   - 프로젝트 유형별 스캐폴딩 (랜딩페이지, 대시보드, SaaS MVP)
   - CLAUDE.md + Context Pack 사전 구성

5. **납품 품질 기준**
   - Lighthouse 90+, 모바일 반응형, SEO 메타태그
   - 404/빈 상태/에러 상태 처리 완비

## Bucky OS 적용 포인트

- [[06_Context_Packs/web-delivery-pack|웹 납품 Context Pack]] 신설
- `agent_dispatcher.py`에 `wishket_bid` 태스크 타입 추가
- `review_checklist_runner.py`에 납품 체크 항목 확장
- 수익 대시보드에 클라이언트 프로젝트 탭 추가

## 관련 허브

- [[jh-system]] — JH 통합 구축 시스템
- [[vibe-coding-pipeline]] — 배포 파이프라인
- [[webhook-vault-write-pattern]] — Vault 쓰기 패턴
- [[vault-galaxy-graph-bridge]] — 전체 지식 허브
