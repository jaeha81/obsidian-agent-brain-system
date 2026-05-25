---
type: knowledge
source: gpt-memory
date: 2026-04-27
tags: [gpt, memory, projects, jaya]
summary: "재하(Jaya)의 진행 중인 프로젝트 목록 — 현황, 목표, 도메인"
---

# 진행 중인 프로젝트 목록

최종 업데이트: 2026-04-27

---

## 프로젝트 현황 표

| 프로젝트명 | 현황 | 목표 | 관련 도메인 / URL |
|-----------|------|------|-----------------|
| **JH Connect** | 운영 중 | 인테리어·건축 솔루션 플랫폼 통합 브랜드 | Architecture & Interior Solutions |
| **NeuronGPT** | 구상/개발 중 | 모듈형 멀티에이전트 AI 웹앱 (헤드 교체 구조) | — |
| **스페이스 819 웹** | 운영 중 | 개인 인테리어 브랜드 웹사이트 | 010-6642-8922 |
| **P2P Shop-AI** | 개발 예정 | AI 기반 P2P 쇼핑 플랫폼 | — |
| **드림랜드 / 루루** | 세계관 확장 중 | 동화책 → 굿즈 → AR 게임 전방향 확장 | — |
| **JH Trading System** | 운영 중 | 선물옵션 자동화 매매 시스템 | 비트맥스 거래소 |
| **유튜브 자동화 3채널** | 운영 중 | GPT → Make Webhook → 자동 설명/태그 생성 | dynamic-bavarois-1b3b93.netlify.app |
| **SPACEGPT 앱** | 개발 예정 | 인테리어 특화 AI 앱 | — |
| **인테리어 시공 케어 앱** | 개발 예정 | 시공 관리·감리·케어 자동화 앱 | — |

---

## 프로젝트 상세

### JH Connect
- **정식 명칭**: JH Connect / Architecture & Interior Solutions (또는 Building & Design Network)
- **역할**: 재하의 AI·인테리어 사업 통합 브랜드
- **하위 서비스**: 스페이스 819, 더나은공간, 관련 웹앱들 포괄

### NeuronGPT (멀티에이전트 AI 플랫폼)
- **구조**: 10+ 에이전트봇을 교체 가능한 '팩(머리)'으로 모듈화, 공통 '바디(워크플로우·데이터흐름·로그·보안)' 위에 장착
- **Supervisor 에이전트**: 모니터링·오류감지·피드백·DB관리·에이전트 간 지시 전달
- **프론트엔드**: 모바일/웹 대시보드
- **백엔드**: API 라우팅 + DB (모델 교체 가능, 예: Gemini 등)
- **개발 스택**: Next.js (프론트) + FastAPI (백엔드)

### 유튜브 자동화 (Make.com 완성)
- **배포 주소**: dynamic-bavarois-1b3b93.netlify.app (Netlify PWA)
- **구조**: 영상 제목 입력 → GPT → Make Webhook → 자동 설명/태그 생성 → 응답 반환
- **상태**: 정상 운영 중 (2025-08-04 기준 Make.com 워크플로우 완성 확인)

### JH Trading System
- **거래소**: 비트맥스
- **매매 방식**: 가격 저항 기준 — 시작가 대비 고점/저점 중간점 매매
- **목표**: 7억 채무 상환 + 장기 100억 자산

### 드림랜드 / 루루 (LULU)
- **세계관**: 드림랜드
- **주인공**: 루루(LULU) — 귀여운 캐릭터
- **확장 로드맵**: 동화책 → 굿즈 → AR 게임

---

## 관련 페이지

- [[gpt-memory-profile]] — 사용자 프로필 및 AI 협업 원칙
- [[gpt-memory-tech-stack]] — 기술 스택 및 자동화 시스템
