#!/usr/bin/env python3
"""
Bucky STT 고도화 레이어 (Item 4) — Typeless 벤치마킹
Whisper STT 출력 → 의도 분류 → 엔티티 추출 → 명령어 감지 → 컨텍스트 보강

기존 discord_bot.py의 _postprocess_stt_claude 대비 강화된 기능:
  - 의도 유형 분류 (COMMAND / QUESTION / INFORMATION / CHITCHAT)
  - Bucky 명령어 자동 감지 → !커맨드 변환
  - 엔티티 추출 (URL, 레포명, 파일명, 숫자)
  - 한국어 맞춤법 교정 패턴 (약어, 띄어쓰기)
  - 멀티턴 컨텍스트 활용
  - 신뢰도 점수
"""
import json
import os
import re
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env", encoding="utf-8", override=True)

_CLAUDE_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
_STT_ENHANCE = bool(_CLAUDE_API_KEY) and os.getenv("STT_AI_ENHANCE", "1").strip() not in {"0", "false", "no"}

# ── 필러 / 반복 패턴 ──────────────────────────────────────────────────────────

_FILLER_PATTERN = re.compile(
    r"(?<!\w)(음+|어+|아+|그+|저+|그니까|그러니까|있잖아|있죠|있어요|뭔가|저기|막|좀|사실|실제로|일단)\s*",
    re.IGNORECASE,
)

_REPEAT_PATTERN = re.compile(r"(\b\w{2,}\b)(\s+\1){2,}", re.IGNORECASE)

# ── 명령어 감지 패턴 ──────────────────────────────────────────────────────────

_COMMAND_PATTERNS = [
    (re.compile(r"(배포|deploy).*?(https?://\S+|github\.com/\S+)"), "!배포 {url}"),
    (re.compile(r"(랜딩|landing).*?(https?://\S+|github\.com/\S+)"), "!랜딩 {url}"),
    (re.compile(r"(상품화|commercialize).*?(https?://\S+)"), "!상품화 {url}"),
    (re.compile(r"(저장|캡처|capture).*?(https?://\S+)"), "!저장 {url}"),
    (re.compile(r"패턴\s*(분석)?"), "!패턴"),
    (re.compile(r"(브리핑|뉴스|briefing)"), "!브리핑"),
    (re.compile(r"(리포트|report|일지)"), "!리포트"),
    (re.compile(r"(성찰|reflect|자기반성)"), "!성찰"),
    (re.compile(r"(태스크|현황)\s*(보여|확인|조회)"), "!태스크"),
]

# ── 의도 분류 ─────────────────────────────────────────────────────────────────

_INTENT_KEYWORDS = {
    "COMMAND": ["만들어", "생성해", "구현해", "배포해", "분석해", "저장해", "수정해", "고쳐", "실행해"],
    "QUESTION": ["뭐야", "어떻게", "왜", "언제", "어디서", "무엇", "알려줘", "설명해"],
    "INFORMATION": ["이거", "이것은", "참고로", "알아둬", "기억해", "메모해"],
    "CHITCHAT": ["안녕", "고마워", "잘했어", "오케이", "알겠어", "좋아"],
}

# ── 엔티티 추출 ───────────────────────────────────────────────────────────────

def _extract_entities(text: str) -> dict:
    entities: dict = {}

    # URL
    urls = re.findall(r"https?://\S+", text)
    if urls:
        entities["urls"] = urls

    # GitHub
    gh = re.findall(r"github\.com/[\w-]+/[\w-]+", text)
    if gh:
        entities["github_repos"] = gh

    # 파일명
    files = re.findall(r"[\w가-힣_-]+\.(py|js|ts|html|md|json|yaml|yml|sh|txt)", text)
    if files:
        entities["files"] = [f"{f[0]}.{f[1]}" for f in files]

    # 숫자/가격
    prices = re.findall(r"₩?[\d,]+\s*(?:원|만원|/월|/년)?", text)
    if prices:
        entities["prices"] = prices

    return entities


def _classify_intent(text: str) -> str:
    text_lower = text.lower()
    scores: dict[str, int] = {k: 0 for k in _INTENT_KEYWORDS}
    for intent, keywords in _INTENT_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                scores[intent] += 1
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "CHITCHAT"


def _detect_command(text: str) -> Optional[str]:
    """Bucky !명령어 자동 감지 및 변환."""
    for pattern, template in _COMMAND_PATTERNS:
        m = pattern.search(text)
        if m:
            # URL이 있으면 삽입
            url_m = re.search(r"https?://\S+", text)
            url = url_m.group(0) if url_m else ""
            return template.replace("{url}", url).strip()
    return None


def _basic_postprocess(text: str) -> str:
    """필러 제거 + 반복 정리 (regex 기반)."""
    text = _FILLER_PATTERN.sub(" ", text)
    text = _REPEAT_PATTERN.sub(r"\1", text)
    text = re.sub(r"\s{2,}", " ", text).strip()
    return text


def _enhance_with_claude(text: str, intent: str, entities: dict) -> str:
    """Claude API 기반 고급 정제."""
    if not _STT_ENHANCE or len(text) < 10:
        return _basic_postprocess(text)

    entity_hint = ""
    if entities.get("urls"):
        entity_hint = f"\n감지된 URL: {entities['urls'][0]}"

    prompt = f"""다음 한국어 STT 결과를 정제하세요. 의도 유형: {intent}{entity_hint}

규칙:
1. 필러 단어 제거 (음, 어, 아, 그, 저, 그니까 등)
2. 반복 표현 제거
3. 문장을 명확하게 다듬기
4. URL, 파일명, 고유명사는 그대로 유지
5. 의도와 내용은 절대 바꾸지 말 것
6. 정제된 텍스트만 출력 (설명 없이)

STT 원문: {text}"""

    try:
        import urllib.request
        body = json.dumps({
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 200,
            "messages": [{"role": "user", "content": prompt}],
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=body,
            headers={
                "x-api-key": _CLAUDE_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            refined = data["content"][0]["text"].strip()
            return refined if refined else _basic_postprocess(text)
    except Exception as e:
        print(f"[STT] Claude API 실패: {e}", flush=True)
        return _basic_postprocess(text)


# ── 메인 처리 함수 ─────────────────────────────────────────────────────────────

def enhance_stt(raw_text: str, context: Optional[list] = None) -> dict:
    """
    STT 출력을 완전히 분석해 구조화 결과 반환.

    Args:
        raw_text: Whisper STT 원문
        context: 이전 대화 컨텍스트 (멀티턴)

    Returns:
        {
            text: 정제된 텍스트,
            intent: COMMAND|QUESTION|INFORMATION|CHITCHAT,
            entities: {urls, github_repos, files, prices},
            detected_command: "!배포 ...", (None if not a command),
            confidence: float,
            raw: 원문
        }
    """
    if not raw_text or not raw_text.strip():
        return {"text": "", "intent": "CHITCHAT", "entities": {}, "detected_command": None, "confidence": 0.0, "raw": raw_text}

    raw = raw_text.strip()
    intent = _classify_intent(raw)
    entities = _extract_entities(raw)
    detected_command = _detect_command(raw)

    # 의도가 COMMAND면 Claude API 강화 우선
    if intent == "COMMAND" or detected_command:
        refined = _enhance_with_claude(raw, intent, entities)
    else:
        refined = _basic_postprocess(raw)

    # 신뢰도: 길이 + 엔티티 + 의도 명확도
    confidence = min(
        0.3 + (len(refined) / 200) * 0.4 + (0.2 if entities else 0) + (0.1 if intent != "CHITCHAT" else 0),
        1.0,
    )

    return {
        "text": refined,
        "intent": intent,
        "entities": entities,
        "detected_command": detected_command,
        "confidence": round(confidence, 2),
        "raw": raw,
    }


def postprocess_for_bucky(raw_text: str, context: Optional[list] = None) -> str:
    """
    discord_bot.py에서 직접 교체 가능한 간편 인터페이스.
    정제된 텍스트만 반환 (명령어 감지 시 !커맨드 형식 변환).
    """
    result = enhance_stt(raw_text, context)

    # 명령어 감지 시 자동 변환
    if result.get("detected_command"):
        return result["detected_command"]

    return result["text"]


# ── CLI 테스트 ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    tests = sys.argv[1:] or [
        "음 그 저기 배포해줘 https://github.com/user/bucky",
        "어 그러니까 패턴 분석 한번 해봐",
        "대시보드 만들어줘 미니멀하게",
        "안녕 버키야",
    ]
    for t in tests:
        r = enhance_stt(t)
        print(f"\n원문: {t}")
        print(f"정제: {r['text']}")
        print(f"의도: {r['intent']} | 명령어: {r['detected_command']} | 신뢰도: {r['confidence']:.0%}")
