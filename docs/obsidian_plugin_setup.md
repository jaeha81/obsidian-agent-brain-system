# Obsidian 커뮤니티 플러그인 설치 가이드

## 설치 방법

```bash
python scripts/obsidian_plugin_setup.py
```

스크립트가 `ObsidianVault/.obsidian/community-plugins.json`을 생성하고
각 플러그인 디렉토리를 사전 생성합니다.

그 후 Obsidian을 재시작하면 설치 프롬프트가 나타납니다.

---

## 설치 플러그인 목록 (20개)

| Plugin ID | 용도 |
|-----------|------|
| `calendar` | 달력 + 일간 노트 |
| `claudian` | Claude AI 연동 |
| `dataview` | DB-like 노트 쿼리 |
| `infranodus-graph-view` | 그래프 지식 분석 |
| `jh-local-graph-view` | JH 로컬 그래프 시각화 |
| `obsidian-claude-code-mcp` | Claude Code MCP 연동 |
| `obsidian-excalidraw-plugin` | 손그림/다이어그램 |
| `obsidian-git` | Git 자동 sync |
| `obsidian-icon-folder` | 폴더/파일 아이콘 |
| `obsidian-kanban` | 칸반 보드 |
| `obsidian-local-rest-api` | REST API 서버 |
| `obsidian-shellcommands` | 터미널 명령어 실행 |
| `obsidian-style-settings` | CSS 테마 설정 |
| `obsidian-tasks-plugin` | 태스크 관리 |
| `omnisearch` | 전체 텍스트 검색 |
| `quickadd` | 빠른 노트 생성 |
| `remotely-save` | 원격 백업 (S3/OneDrive/WebDAV) |
| `smart-connections` | AI 유사 노트 추천 |
| `table-editor-obsidian` | 테이블 편집기 |
| `templater-obsidian` | 고급 템플릿 엔진 |

---

## 설치 후 설정 복원 가이드

### obsidian-git
설정 > 커뮤니티 플러그인 > obsidian-git > 설정:
- Auto pull interval: 10분
- Auto push interval: 10분
- Vault backup interval: 30분

### obsidian-local-rest-api
- API Key를 발급하여 `jh-brain-system`의 `.env`에 `OBSIDIAN_API_KEY=` 추가

### remotely-save
- Google Drive 또는 S3 연동 설정 (민감 정보이므로 별도 기록)

### templater-obsidian
- Template folder: `ObsidianVault/08_Templates/`
- Trigger on new file creation: ON

### dataview
- 기본 설정 유지 (Inline queries: ON)

### smart-connections
- OpenAI API Key 또는 로컬 모델 설정 필요

---

## 문제 해결

**플러그인이 표시되지 않는 경우**
1. Obsidian 설정 > 커뮤니티 플러그인 > "안전 모드" 비활성화
2. Obsidian 완전 종료 후 재시작
3. 커뮤니티 플러그인 > "Browse" > 해당 플러그인 검색 후 수동 설치

**`jh-local-graph-view` / `infranodus-graph-view`가 없는 경우**
- 이 플러그인들은 공식 커뮤니티 목록에 없을 수 있음
- 수동 설치: `ObsidianVault/.obsidian/plugins/<id>/` 디렉토리에 직접 빌드 결과 복사
