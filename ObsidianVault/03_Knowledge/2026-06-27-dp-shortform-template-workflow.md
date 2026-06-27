---
title: 숏폼 템플릿 3종 편집 흐름 (YouTube Shorts 2026 기준)
date: 2026-06-27
source: daily-plus/2026-06-27.md (Card 5)
priority: P3
category: knowledge
status: distilled
tags:
- shorts
- youtube
- ffmpeg
- shotstack
- automation
- video-editing
- daily-plus
- knowledge
- source/today_plus
- type/reference
graph_cluster: content-ops
---

# 숏폼 템플릿 3종 편집 흐름

> ChatGPT Pulse 2026-06-27 Card 5 증류 (P3)

## 핵심 포맷 기준

- 해상도: 9:16 수직, 1080×1920 (모바일 최적화)
- 후크: 최초 1~3초 내 가치 명확히 제시
- 자막: 음소거 상태에서도 메시지 전달 (온스크린 텍스트 필수)
- 구조: 후크 → 핵심 내용 → 결과/CTA

## 템플릿 3종

### A: 제품 데모
```
[0~2초] 문제 제시 후크
[3~50초] 제품 사용 데모 (단계별 컷)
[51~59초] 결과 + CTA
```

### B: 전후 비교 (Before/After)
```
[0~2초] Before 상태 시각 제시
[3~30초] 변환 과정 가속 편집
[31~59초] After 결과 + CTA
```

### C: 기능 3개 요약
```
[0~2초] "딱 3가지만" 후크
[3~50초] 기능 1→2→3 컷 전환 (각 15초)
[51~59초] 핀 댓글/링크 CTA
```

## FFmpeg 자동화 스크립트

```bash
# 16:9 → 9:16 변환 + 크롭
ffmpeg -i input.mp4 \
  -vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920" \
  output_9x16.mp4

# 텍스트 오버레이
ffmpeg -i input.mp4 \
  -vf "drawtext=text='후크 텍스트':fontsize=60:x=(w-text_w)/2:y=100:fontcolor=white" \
  output_with_text.mp4
```

## Shotstack API 대량 렌더링

```json
{
  "timeline": {
    "tracks": [{
      "clips": [
        { "asset": { "type": "video", "src": "{{input_url}}" }, "start": 0, "length": 59 },
        { "asset": { "type": "title", "text": "{{hook_text}}", "style": "minimal" }, "start": 0, "length": 3 }
      ]
    }]
  },
  "output": { "format": "mp4", "size": { "width": 1080, "height": 1920 } }
}
```

## A/B 테스트 후크 유형

| 유형 | 설명 |
|------|------|
| 즉각적 보상 | "지금 바로 얻을 수 있는 것" |
| 궁금증 생성 | "왜 이게 될까?" |
| 반전형 | "이건 틀렸습니다" |

## 연결 노트

- [[2026-06-25-dp-api-cost-spike-alert-rules]]
- [[bucky-ai-api-routing-policy]]
