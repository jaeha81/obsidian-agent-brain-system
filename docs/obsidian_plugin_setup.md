# Obsidian 플러그인 설치하기

> **자동 설치 완료** — 17개 플러그인 파일 다운로드 + 안전모드 OFF 설정 완료.  
> Obsidian 재시작 후 '켜기'만 하면 됩니다.

---

## 지금 해야 할 것

1. **Obsidian 완전 종료 후 재시작**
2. 설정(⚙) → **커뮤니티 플러그인** → 설치된 플러그인 목록에서 원하는 것 **켜기**

> 안전모드는 이미 OFF 처리됨 (`app.json: restrictedMode: false`)

### 수동 설치 필요 (공식 레지스트리 외 커스텀 플러그인 3개)

| 플러그인 | 설치 방법 |
|---------|---------|
| `claudian` | GitHub에서 main.js + manifest.json 다운 → `.obsidian/plugins/claudian/` 에 복사 |
| `jh-local-graph-view` | JH 로컬 빌드 결과물 → `.obsidian/plugins/jh-local-graph-view/` 에 복사 |
| `obsidian-claude-code-mcp` | GitHub에서 직접 다운 → `.obsidian/plugins/obsidian-claude-code-mcp/` 에 복사 |

---

## 설치 플러그인 20개

| 이름 | 용도 |
|------|------|
| calendar | 달력 + 일간 노트 |
| claudian | Claude AI 연동 |
| dataview | 노트 DB 쿼리 |
| infranodus-graph-view | 그래프 지식 분석 |
| jh-local-graph-view | JH 로컬 그래프 |
| obsidian-claude-code-mcp | Claude Code MCP |
| obsidian-excalidraw-plugin | 손그림/다이어그램 |
| obsidian-git | Git 자동 sync |
| obsidian-icon-folder | 폴더 아이콘 |
| obsidian-kanban | 칸반 보드 |
| obsidian-local-rest-api | REST API 서버 |
| obsidian-shellcommands | 터미널 명령 실행 |
| obsidian-style-settings | CSS 테마 조정 |
| obsidian-tasks-plugin | 태스크 관리 |
| omnisearch | 전체 텍스트 검색 |
| quickadd | 빠른 노트 생성 |
| remotely-save | 원격 백업 |
| smart-connections | AI 유사 노트 추천 |
| table-editor-obsidian | 테이블 편집기 |
| templater-obsidian | 고급 템플릿 |

---

## 설치 후 핵심 설정

| 플러그인 | 설정 |
|---------|------|
| **obsidian-git** | Auto pull/push 간격: 10분 |
| **templater-obsidian** | Template folder: `08_Templates/` |
| **obsidian-local-rest-api** | API Key 발급 → `jh-brain-system/.env`에 `OBSIDIAN_API_KEY=` 추가 |
| **dataview** | Inline queries ON (기본값 유지) |

---

## 목록에 없으면

스크립트 재실행:
```bash
python -X utf8 scripts/obsidian_plugin_setup.py
```

`jh-local-graph-view` / `infranodus-graph-view`는 공식 마켓에 없을 수 있음 → `.obsidian/plugins/<id>/` 에 빌드 파일 직접 복사.
