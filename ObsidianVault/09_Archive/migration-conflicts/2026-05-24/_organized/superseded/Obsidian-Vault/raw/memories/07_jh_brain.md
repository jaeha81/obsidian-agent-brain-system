# 07 — JH-브레인시스템

> Obsidian 기반 세컨드 브레인 시스템. AI가 지식을 자동으로 구조화.

---

## 📊 개요

| 항목 | 내용 |
|---|---|
| 목적 | 재하의 지식/정보를 자동으로 Obsidian에 구조화 저장 |
| 핵심 | Obsidian + LangGraph + Google Sheets/Drive |
| 상태 | 활성 코어 프로젝트 |

---

## 🏗️ 아키텍처

### 스택
- **오케스트레이터**: Express.js
- **프론트엔드**: Vanilla JS
- **데이터**: Google Sheets / Google Drive
- **지식 저장**: Obsidian vault
- **에이전트 프레임워크**: LangGraph

### LangGraph StateGraph (8-노드)

```
START
  ↓
INTAKE (입력 수신)
  ↓
CLASSIFY (분류: 어떤 에이전트가 처리할지)
  ↓
RESEARCH (므네메 → 스카우트에 조사 요청)
  ↓
AWAITING ← ─ ─ ─ ─ ─ ─ (단일 human intervention 포인트)
  ↓ "구현해" 승인
BUILD (빌더 구현)
  ↓
RECORD (므네모시네 → Obsidian 기록)
  ↓
END
```

- **단일 승인 포인트**: AWAITING 노드에서만 재하 개입
- **승인 패턴**: "구현해" 키워드 매칭

---

## 🤖 명명된 에이전트

| 에이전트 | 이름 | 역할 |
|---|---|---|
| Orchestrator | **므네메 (Mneme)** | 오케스트레이터, Opus 모델 사용 |
| Recorder | **므네모시네 (Mnemosyne)** | Obsidian 기록 전담 |
| Scout | **스카우트 (Scout)** | 정보 수집, 웹 조사 |
| Builder | **빌더 (Builder)** | 구현 실행 |

> 므네메/므네모시네: 그리스 신화의 기억의 신에서 따옴

---

## 📁 Obsidian 연동

### 기록 구조 (Obsidian vault)
```
OBSIDIAN-SECOND/
├── raw/
│   ├── memories/    ← 이 폴더가 현재 작성 대상
│   └── ...
├── projects/
└── daily/
```

### 자동 기록 항목
- 프로젝트 진행 상황
- 기술 결정 사항
- 문제/해결 패턴
- 재하의 선호도/원칙

---

## 🔄 Google Sheets/Drive 연동

- **Google Sheets**: 구조화 데이터 저장 (프로젝트 상태, 단가 데이터 등)
- **Google Drive**: 문서, 제안서, 설계 파일 관리
- Obsidian ↔ Google Drive 동기화 구조

---

## 🎯 목표

- 모든 대화, 결정, 학습을 자동으로 영구 기록
- "재하가 기억하지 않아도 시스템이 기억한다"
- 지식 검색: Obsidian 검색 + AI 쿼리
- 미래: 세컨드 브레인이 새 프로젝트 컨텍스트 자동 제공

---

## 📌 현재 상태 (2026-04)

- Express.js + Vanilla JS 기반 UI 구현
- LangGraph StateGraph 설계 완료
- 에이전트 명명 완료 (므네메/므네모시네/스카우트/빌더)
- Obsidian 연동 구현 중
