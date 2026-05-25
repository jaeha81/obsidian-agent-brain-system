---
type: reference
system: JH-Brain
date: 2026-04-21
---

# JH Obsidian Vault — 개발 기억 저장소

> jh-brain-system 연결 | 개발 자산 전용

## 폴더 구조

| 폴더 | 용도 | 주요 내용 |
|------|------|----------|
| 00_Inbox/ | 미분류 임시 수신함 | 새로 들어온 미분류 파일 |
| 01_Projects/ | 개발 프로젝트 기록 | agents/, brain/, jh-brain-system/, knowledge/ |
| 02_Architecture/ | 아키텍처 설계 문서 | 시스템 설계, 구조도 |
| 03_Prompts/ | 재사용 프롬프트 | templates/ (에이전트·세션 템플릿) |
| 04_Issues/ | 버그·이슈 기록 | 문제 추적, 해결 이력 |
| 05_Logs/ | 운영 로그 | daily/ (일별 회고), decisions/ (결정 기록) |
| 06_Deploy/ | 배포 기록 | 배포 이력, CI/CD 기록 |
| 07_Archive/ | 완료 아카이브 | 종료된 작업, 구버전 문서 |

## 서브폴더 상세

### 01_Projects/
| 서브폴더 | 내용 |
|---------|------|
| agents/ | 에이전트 철학·진화·순위 체계 문서 (COMMON-PHILOSOPHY.md 등) |
| brain/ | 브레인 설정, 대시보드, user-brain.md |
| jh-brain-system/ | jh-brain-system 프로젝트 기록 |
| knowledge/ | errors/, patterns/, references/, skills/ |

### 03_Prompts/
| 서브폴더 | 내용 |
|---------|------|
| templates/ | agent-skill.md, decision-log.md, jh-daily-retrospective.md, jh-metadata-template.md, session-summary.md |

### 05_Logs/
| 서브폴더 | 내용 |
|---------|------|
| daily/ | 일별 회고 (2026-03-22 ~ 현재) |
| decisions/ | 결정 기록 (현재 비어있음) |

## 조회 가이드

| 질문 | 찾아볼 위치 |
|------|-----------|
| 코드 구조 / 아키텍처 | `02_Architecture/` |
| 버그·이슈 | `04_Issues/` |
| 배포 기록 | `06_Deploy/` |
| 에이전트 설정·철학 | `01_Projects/agents/` |
| 일일 회고 | `05_Logs/daily/` |
| 결정 이력 | `05_Logs/decisions/` |
| 브레인 설정 | `01_Projects/brain/` |
| 프롬프트·템플릿 | `03_Prompts/templates/` |
| 지식·패턴·오류 | `01_Projects/knowledge/` |
| 신규 미분류 파일 | `00_Inbox/` |

## 핵심 허브 노트

### 브레인 설정
- [[01_Projects/brain/dashboard]] — JH Brain 대시보드
- [[01_Projects/brain/user-brain]] — 재하님 뇌 복제 파일
- [[01_Projects/brain/config]] — 브레인 시스템 설정

### 에이전트 체계
- [[01_Projects/agents/mneme]] — 마스터 에이전트 므네메
- [[01_Projects/agents/sub-agents]] — 서브 에이전트 지침서
- [[01_Projects/agents/COMMON-PHILOSOPHY]] — 에이전트 공통 철학
- [[01_Projects/agents/rank-system]] — 에이전트 계급 시스템
- [[01_Projects/agents/evolution]] — 므네메 진화 로그

### 프롬프트 템플릿
- [[03_Prompts/templates/agent-skill]] — 에이전트 스킬 템플릿
- [[03_Prompts/templates/session-summary]] — 세션 요약 템플릿
- [[03_Prompts/templates/decision-log]] — 결정 기록 템플릿
- [[03_Prompts/templates/jh-daily-retrospective]] — 일일 회고 템플릿
- [[03_Prompts/templates/jh-metadata-template]] — 메타데이터 템플릿

### 운영 로그
- [[05_Logs/daily/2026-04-23-retrospective]] — 최근 일일 회고
- [[05_Logs/daily/2026-04-22-retrospective]] — 2026-04-22 회고
- [[05_Logs/daily/2026-04-21-retrospective]] — 2026-04-21 회고

### 수신함
- [[00_Inbox/2026-04-23-claude-code]] — 최근 세션 캡처

## LLM Wiki (복리 지식 베이스)

> LLM이 작성·유지하는 개발 지식 위키. 세션이 쌓일수록 더 강해진다.
> 운영 스키마: `CLAUDE.md`

| 파일 | 역할 |
|------|------|
| [[wiki/index]] | 위키 마스터 카탈로그 (세션 시작 시 읽기) |
| [[wiki/log]] | 시간순 활동 로그 |
| [[wiki/overview]] | 전체 합성 개요 |
| [[wiki/entity-mneme]] | 마스터 에이전트 므네메 |
| [[wiki/entity-jh-brain-system]] | JH Brain System 아키텍처 |
| [[wiki/entity-agent-ecosystem]] | 에이전트 생태계 전체 맵 |
| [[wiki/concept-agent-philosophy]] | 에이전트 공통 철학 5원칙 |
| [[wiki/concept-dev-workflow]] | JH 개발 워크플로우 0~8단계 |

### 슬래시 명령어
| 명령어 | 동작 |
|--------|------|
| `/ingest [경로]` | 볼트 파일 → 위키 통합 |
| `/query [질문]` | 위키 기반 답변 |
| `/lint` | 위키 건강 검진 |
| `/status` | 위키 통계 |

---

## 관련 시스템

- [[OBSIDIAN-SECOND/INDEX]] — 지식 기반 볼트 (LLM Wiki 별도 운영)
- GitHub: jaeha81/jh-brain-system
