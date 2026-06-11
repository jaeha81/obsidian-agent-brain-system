---
type: knowledge-note
date: 2026-06-04
source: daily-plus
category: obsidian-queue
tags:
  - "#area/ai_automation"
  - "#status/active"
summary: Obsidian 키워드 그래프 패턴 — WIP/에버그린 구분, 태그 기반 그래프 색상, MOC 구조 최적화
status: applied
applied_at: 2026-06-11
---

# Obsidian Keyword Graph Patterns

## 개요

JH Agent Brain Vault를 **즉시 파악 가능한 시각적 구조**로 유지하기 위한 저마찰 그래프 조직 패턴. WIP vs 에버그린 노트 구분, 태그 기반 그래프 색상, MOC 구조를 포함한다.

## 핵심 원칙

1. **즉시 파악**: 그래프 보는 순간 무엇이 활성 작업인지 보여야 함
2. **저마찰**: 새 노트 추가 시 태그 1-2개만 달면 자동 분류
3. **Agent Brain 명확성**: 에이전트가 읽을 노트와 아카이브 구분 필수

## 태그 체계

### Status 태그 (그래프 색상 기준)
```
#status/active    → 초록 (현재 작업 중)
#status/staged    → 노랑 (검토/승인 대기)
#status/evergreen → 파랑 (완성된 지식)
#status/archived  → 회색 (비활성)
#status/wip       → 주황 (미완성)
```

### Area 태그 (클러스터 기준)
```
#area/ai_automation   → AI/에이전트 자동화
#area/business        → 수익화/비즈니스
#area/dev             → 개발/코드
#area/ops             → 운영/인프라
#area/research        → 리서치/학습
```

## Obsidian Graph 색상 설정

Obsidian 그래프 뷰에서 Groups 설정:

```json
{
  "groups": [
    {
      "query": "tag:#status/active",
      "color": {"r": 76, "g": 187, "b": 23, "a": 1}
    },
    {
      "query": "tag:#status/staged",
      "color": {"r": 255, "g": 200, "b": 0, "a": 1}
    },
    {
      "query": "tag:#status/evergreen",
      "color": {"r": 66, "g": 135, "b": 245, "a": 1}
    },
    {
      "query": "tag:#status/archived",
      "color": {"r": 150, "g": 150, "b": 150, "a": 1}
    },
    {
      "query": "tag:#area/ai_automation",
      "color": {"r": 180, "g": 100, "b": 255, "a": 1}
    }
  ]
}
```

## MOC (Map of Content) 구조 패턴

### 허브 MOC 배치 전략
```
00_System/
  └── MOC-agent-brain.md     # 에이전트 운영 전체 허브
03_Knowledge/
  └── MOC-ai-automation.md   # AI 자동화 지식 허브
  └── MOC-business.md        # 수익화 지식 허브
03_Projects/
  └── MOC-active-projects.md # 활성 프로젝트 허브
```

### MOC 노트 형식

```markdown
---
type: moc
tags:
  - "#status/active"
  - "#area/ai_automation"
---

# AI Automation MOC

## 현재 활성 노트
- [[2026-06-04-dp-whisper-cpp-transcription-mvp]]
- [[2026-06-04-dp-three-step-shorts-pipeline]]

## 에버그린 지식
- [[2026-05-28-dp-codex-claude-separation-pattern]]
- [[2026-05-30-dp-obsidian-yaml-standard]]

## 대기 중 (staged)
- [[2026-06-04-dp-claude-opus-compatibility]]
- [[2026-06-04-dp-shortform-ai-template-pack]]
```

## WIP vs 에버그린 구분 기준

| 기준 | WIP (#status/wip) | 에버그린 (#status/evergreen) |
|------|------------------|---------------------------|
| 내용 완성도 | 50% 미만 | 80% 이상 |
| 최근 편집 | 1주 이내 | 1개월 이상 안정 |
| 링크 수 | 0-2개 | 3개 이상 |
| 적용 여부 | 미적용 | applied 또는 staged |

## 에이전트 친화적 패턴

### Agent Brain이 읽어야 할 노트 표시
```yaml
# frontmatter에 agent_readable: true 추가
agent_readable: true
priority: high  # low/medium/high
```

### 자동 태그 스크립트 (Python)
```python
def auto_tag_note(note_path: str) -> dict:
    """노트 내용 분석 후 자동 태그 추천"""
    content = Path(note_path).read_text(encoding="utf-8")
    
    # 키워드 기반 area 태그 추천
    keywords = {
        "ai_automation": ["claude", "bucky", "agent", "whisper", "pipeline"],
        "business": ["수익", "매출", "wishket", "고객"],
        "dev": ["python", "git", "api", "코드"],
    }
    
    suggested_tags = []
    for area, words in keywords.items():
        if any(w.lower() in content.lower() for w in words):
            suggested_tags.append(f"#area/{area}")
    
    return {"suggested_tags": suggested_tags}
```

## 참고

- 현재 Graph 설정: 세션 2026-06-07 (3D Galaxy Graph v2.0.1)
- InfraNodus 통합: `project_session_2026-06-09.md`
- 태그 파이프라인: `project_session_2026-06-02.md`
