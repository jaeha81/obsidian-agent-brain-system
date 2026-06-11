---
type: knowledge-note
date: 2026-06-05
source: daily-plus
category: agent-prompting
tags:
  - "#area/ai_automation"
  - "#status/active"
summary: 오늘의 하이라이트 자동 생성 템플릿 — 원본 링크 보존, Obsidian 카드 템플릿, 이부장 실행 프롬프트
status: staged
applied_at: 2026-06-11
approval_required: true
approval_note: Bucky approval needed before activating as daily automation
---

# 오늘의 하이라이트 자동 생성 템플릿

## 개요

매일 하루치 하이라이트 노트를 자동 생성하는 one-page 생성기. 원본 오디오/텍스트 링크 보존, Obsidian 카드 템플릿, 이부장 one-line 실행 프롬프트, JSON 출력 포맷을 포함한다.

## Obsidian 카드 템플릿

```markdown
---
type: daily-highlight
date: {{date}}
source_links:
  - {{source_1}}
  - {{source_2}}
tags:
  - "#status/active"
  - "#area/ai_automation"
generated_by: ibujang-auto
---

# 오늘의 하이라이트 — {{date}}

## 핵심 인사이트
{{#each insights}}
> {{text}}
— 출처: [[{{source}}]]
{{/each}}

## 오늘 완료한 것
{{#each completed}}
- ✅ {{item}}
{{/each}}

## 내일 우선순위
{{#each priorities}}
- [P{{rank}}] {{item}}
{{/each}}

## 원본 링크
{{#each source_links}}
- [{{title}}]({{url}})
{{/each}}

---
*자동 생성: {{timestamp}} by 이부장*
```

## 이부장 One-Line 실행 프롬프트

```
/ibujang daily-highlight --date today --sources vault,discord --publish obsidian
```

상세 옵션:
```
/ibujang daily-highlight
  --date "{{YYYY-MM-DD}}"
  --sources "vault,discord,notes"
  --template "card"
  --preserve-links true
  --publish "obsidian"
  --idempotency-key "highlight-{{date}}"
```

## 자동화 스크립트

```python
from datetime import date
import json

def generate_daily_highlight(
    vault_path: str,
    discord_messages: list = None,
    voice_notes: list = None
) -> dict:
    """
    하루치 하이라이트 노트 자동 생성
    - vault 변경사항 수집
    - Discord 중요 메시지 수집
    - 음성 노트 전사 내용 수집
    - 통합 카드 생성
    """
    today = date.today()
    
    # 1. 소스별 데이터 수집
    vault_changes = collect_vault_changes(vault_path, today)
    discord_highlights = filter_important_messages(discord_messages or [])
    voice_transcripts = collect_voice_notes(voice_notes or [])
    
    # 2. 핵심 인사이트 추출 (Claude 요약)
    raw_content = {
        "vault": vault_changes,
        "discord": discord_highlights,
        "voice": voice_transcripts
    }
    
    insights = extract_insights_claude(raw_content)
    
    # 3. 우선순위 추출
    priorities = extract_priorities(vault_changes)
    
    # 4. 하이라이트 구조 생성
    highlight = {
        "date": str(today),
        "insights": insights,
        "completed": [c["item"] for c in vault_changes.get("completed", [])],
        "priorities": priorities,
        "source_links": collect_source_links(raw_content),
        "timestamp": datetime.now().isoformat()
    }
    
    return highlight

def render_highlight_card(highlight: dict, template_path: str) -> str:
    """하이라이트 데이터를 Obsidian 카드 마크다운으로 렌더링"""
    # Jinja2 템플릿 렌더링
    from jinja2 import Template
    template = Template(Path(template_path).read_text(encoding="utf-8"))
    return template.render(**highlight)

def save_to_vault(content: str, vault_path: str, date: str):
    """Obsidian Vault에 하이라이트 노트 저장"""
    filename = f"{date}-daily-highlight.md"
    output_path = Path(vault_path) / "01_Daily" / filename
    output_path.write_text(content, encoding="utf-8")
    return str(output_path)
```

## JSON 출력 형식

```json
{
  "date": "2026-06-05",
  "version": "1.0",
  "highlight": {
    "insights": [
      {
        "text": "whisper.cpp small 모델이 한국어 실용 수준 도달",
        "source": "2026-06-04-dp-whisper-cpp-transcription-mvp",
        "confidence": 0.92
      }
    ],
    "completed": [
      "Daily Plus 노트 12개 생성 완료",
      "LibreDWG 파이프라인 설계 완료"
    ],
    "priorities": [
      {"rank": 0, "item": "이부장 게이트 Bucky 승인 요청"},
      {"rank": 1, "item": "whisper.cpp Discord 봇 통합 테스트"}
    ],
    "source_links": [
      {
        "title": "Daily Plus 2026-06-04",
        "url": "obsidian://open?vault=ObsidianVault&file=03_Knowledge/2026-06-04-dp-whisper-cpp-transcription-mvp",
        "type": "vault"
      }
    ]
  },
  "generated_by": "ibujang-auto",
  "idempotency_key": "highlight-2026-06-05"
}
```

## Claude 요약 프롬프트

```python
HIGHLIGHT_SUMMARY_PROMPT = """
다음 오늘의 활동 데이터에서 핵심 인사이트 3-5개를 추출해주세요.

조건:
1. 각 인사이트는 한 문장으로 (20자 이내)
2. 실행 가능한 내용 우선
3. 원본 소스 파일명 반드시 포함
4. 중복 내용 제거

출력 형식: JSON 배열
[{"text": "...", "source": "파일명", "confidence": 0.0~1.0}]

데이터:
{raw_content}
"""
```

## 자동화 스케줄 (승인 후 활성화)

```python
import schedule

# 매일 오후 11시 30분 자동 실행
schedule.every().day.at("23:30").do(
    lambda: run_daily_highlight_pipeline(
        vault_path=VAULT_PATH,
        discord_messages=fetch_todays_discord(),
        voice_notes=scan_voice_notes()
    )
)
```

## 참고

- 관련 정책: `2026-06-04-dp-bucky-ibujang-prompt.md`
- triage 정책: `2026-06-04-dp-todays-plus-triage-policy.md`
- 음성 노트: `2026-05-27-dp-voice-note-safe-template.md`
