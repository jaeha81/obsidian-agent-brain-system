# Claude Code in Obsidian — 사용 가이드

> 설정일: 2026-04-20 | 노트북 환경 (user=info)

---

## 설치된 플러그인

| 플러그인 | 역할 |
|---------|------|
| **Terminal** (v3.23.0) | Obsidian 내 터미널 창 — `claude` 인터랙티브 실행 |
| **Shell Commands** (v0.23.0) | 단축키 → shell 명령 실행 |

---

## 시작하는 법

### Obsidian 첫 실행 시
1. Obsidian 열기 → **설정(⚙️)** → **커뮤니티 플러그인**
2. **"안전 모드 끄기"** 클릭 (최초 1회만)
3. Terminal, Shell commands 둘 다 **활성화** 확인

---

## Terminal 플러그인으로 Claude Code 실행

### 터미널 열기
- 리본(왼쪽 사이드바) **터미널 아이콘** 클릭
- 또는 **명령 팔레트** (`Ctrl+P`) → `Terminal: Open terminal`
- 프로필 선택: **"Claude Code"** → 볼트 디렉토리에서 `claude` 자동 실행

### 직접 실행
터미널 열린 후:
```bash
claude              # 인터랙티브 모드
claude --print "질문"   # 단발 질문
```

---

## Shell Commands 단축키 (명령 팔레트에서 실행)

`Ctrl+P` 열고 아래 명령 검색:

| 명령 이름 | 동작 |
|---------|------|
| `Claude Code 실행 (인터랙티브)` | 볼트 디렉토리에서 claude 실행 |
| `Claude: 현재 노트 요약` | 현재 노트를 claude로 요약 |
| `Claude: 아이디어 확장` | 현재 노트 아이디어 3가지 확장 |
| `Claude: Wiki 인덱스 업데이트` | wiki/index.md 자동 갱신 |
| `Git: 노트 동기화` | add → commit → push 자동화 |

> Shell Commands 설정에서 단축키 직접 등록 가능 (설정 → Shell commands → 각 명령 옆 ⌨️)

---

## 권장 워크플로우

```
노트 작성
    ↓
Ctrl+P → "Claude: 아이디어 확장"  (아이디어 브레인스토밍)
    ↓
Terminal에서 claude 실행 → 깊은 대화
    ↓
Ctrl+P → "Claude: Wiki 인덱스 업데이트"  (지식 정리)
    ↓
Ctrl+P → "Git: 노트 동기화"  (GitHub 백업)
```

---

## 볼트 경로
```
C:\ai프로젝트\JA-OBSIDIAN-SECOND\
├── .obsidian/plugins/terminal/        ← Terminal 플러그인
├── .obsidian/plugins/obsidian-shellcommands/  ← Shell Commands
├── wiki/                              ← LLM Wiki
├── raw/                               ← 원본 소스
└── CLAUDE.md                          ← 브레인 운영 스키마
```

---

## 트러블슈팅

| 증상 | 해결 |
|------|------|
| 플러그인이 보이지 않음 | 설정 → 커뮤니티 플러그인 → 안전 모드 끄기 |
| claude 명령 못 찾음 | 터미널에서 `where claude` 확인, PATH 설정 필요 |
| Shell command 실행 안 됨 | Shell Commands 설정에서 기본 셸을 `powershell.exe`로 설정 |

## 관련
- [[INDEX]] — 볼트 전체 구조
- [[wiki/index]] — LLM Wiki 카탈로그
- [[wiki/entity-claude-ai-desktop-setup]] — Claude.ai Desktop 설정
- [[환영합니다!]] — 볼트 빠른 시작
