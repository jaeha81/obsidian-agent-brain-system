---
updated: 2026-04-19
type: entity
tags: [setup, claude-ai, desktop, projects]
---

# Claude.ai Desktop — Projects 설정 가이드

> Claude.ai Desktop은 CLAUDE.md를 로드하지 않으므로 Projects 기능으로 wiki를 연결한다.

---

## 설정 방법

1. Claude.ai → 좌측 **Projects** → **New Project** 생성
2. Project 이름: `JH Wiki Agent`
3. **Project Instructions**에 아래 내용 붙여넣기:

```
당신은 JH LLM Wiki 에이전트입니다.
Primary Wiki: C:\Users\user1\Documents\OBSIDIAN-SECOND\
스키마: C:\Users\user1\Documents\OBSIDIAN-SECOND\CLAUDE.md

세션 시작 시:
1. 아래 첨부된 wiki/index.md로 현재 지식 상태 파악
2. 상태 브리핑 1줄 후 대기

슬래시 명령어:
/ingest [내용] - 새 소스를 wiki에 추가
/query [질문] - wiki 기반 답변
/lint - 건강 검진 제안
/status - 현재 통계

규칙:
- wiki 파일은 LLM이 작성, 사용자는 읽기만
- 모든 ingest/query는 log.md에 기록
- 교차 참조 항상 포함
```

4. **Add Content** → `C:\Users\user1\Documents\OBSIDIAN-SECOND\wiki\index.md` 내용 업로드
5. (선택) 주요 개념 페이지 추가 업로드

---

## 동기화 한계 및 해결

| 한계 | 해결 |
|------|------|
| 파일 자동 동기화 없음 | wiki 업데이트 후 index.md를 Projects에 수동 재업로드 |
| 파일 직접 쓰기 불가 | Claude.ai가 생성한 내용을 복사해서 직접 파일에 저장 |
| 실시간 반영 안됨 | 중요 ingest는 터미널 Claude Code에서 진행 권장 |

---

## 권장 사용 패턴

- **Claude.ai Desktop**: 아이디어 탐색, 빠른 질의, 모바일/외출 시
- **VS Code + Claude Code**: 개발 중 wiki 기여, ingest 실행
- **터미널 `cd C:\Users\user1\Documents\OBSIDIAN-SECOND && claude`**: 집중적 wiki 작업

---

**관련 페이지**: [[index]], [[concept-llm-wiki]]

## 연결 노트
- [[index]] — 위키 전체 카탈로그
- [[overview]] — 위키 전체 합성
- [[concept-llm-wiki]] — LLM Wiki 패턴 개념
- [[concept-obsidian-plugins]] — 플러그인 구성 및 Shell Commands 상세
- [[log]] — 위키 활동 로그
