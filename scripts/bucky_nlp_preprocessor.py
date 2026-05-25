#!/usr/bin/env python3
"""
Bucky NLP 전처리기 (Item 1)
자연어 입력(한국어 음성/텍스트) → AI 최적 구조화 포맷 변환

파이프라인:
  사용자 자연어 → 액션 분류 → 타겟 추출 → 파라미터 파싱 → 구조화 프롬프트 생성
"""
import json
import os
import re
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env", encoding="utf-8", override=True)

# STT 오류 교정 사전 (nlp_preprocessor와 공유)
try:
    _scripts = str(ROOT / "scripts")
    if _scripts not in sys.path:
        sys.path.insert(0, _scripts)
    from nlp_preprocessor import correct_stt as _correct_stt  # type: ignore
    _HAS_STT_CORRECTION = True
except Exception:
    _HAS_STT_CORRECTION = False
    def _correct_stt(text: str) -> str:
        return text

_CLAUDE_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
_NLP_ENHANCE_ENABLED = bool(_CLAUDE_API_KEY) and os.getenv("NLP_ENHANCE", "1").strip() not in {"0", "false", "no"}

# ── 액션 매핑 ──────────────────────────────────────────────────────────────────

ACTION_MAP = {
    "BUILD": [
        "만들어", "만들어줘", "생성해", "작성해", "구현해", "개발해", "제작해", "만들자",
        "create", "build", "make", "generate", "implement", "develop",
    ],
    "DEPLOY": [
        "배포해", "올려줘", "퍼블리시", "런치해", "배포해줘", "deploy", "publish", "launch",
    ],
    "ANALYZE": [
        "분석해", "살펴봐", "확인해", "검토해", "파악해", "조사해", "알아봐",
        "analyze", "check", "review", "inspect", "examine",
    ],
    "CAPTURE": [
        "저장해", "기록해", "메모해", "캡처해", "흡수해", "정리해",
        "save", "capture", "record", "store",
    ],
    "SEARCH": [
        "찾아봐", "검색해", "조회해", "가져와", "알려줘",
        "search", "find", "get", "fetch", "lookup",
    ],
    "FIX": [
        "고쳐", "수정해", "고쳐줘", "해결해", "디버그", "버그",
        "fix", "debug", "repair", "solve", "patch",
    ],
    "EXPLAIN": [
        "설명해", "알려줘", "뭐야", "어떻게", "왜",
        "explain", "describe", "what is", "how does", "why",
    ],
    "UPGRADE": [
        "업그레이드", "개선해", "향상해", "발전시켜", "진화시켜",
        "upgrade", "improve", "enhance", "evolve",
    ],
    "LIST": [
        "목록", "나열해", "보여줘", "리스트",
        "list", "show", "display",
    ],
}

# ── 컴포넌트/타겟 키워드 ───────────────────────────────────────────────────────

COMPONENT_KEYWORDS = {
    "dashboard": ["대시보드", "dashboard"],
    "landing_page": ["랜딩", "landing", "랜딩페이지"],
    "api": ["api", "엔드포인트", "endpoint", "서버"],
    "database": ["db", "database", "데이터베이스", "디비"],
    "bot": ["봇", "bot", "디스코드봇"],
    "pipeline": ["파이프라인", "pipeline", "자동화", "워크플로우"],
    "payment": ["결제", "payment", "stripe", "toss", "페이먼트"],
    "auth": ["인증", "auth", "로그인", "login"],
    "knowledge": ["지식", "knowledge", "obsidian", "볼트", "vault"],
    "skill": ["스킬", "skill", "명령어", "command"],
}

STYLE_KEYWORDS = {
    "minimal": ["미니멀", "심플", "simple", "minimal", "깔끔"],
    "dark": ["다크", "dark", "어두운"],
    "saas": ["saas", "SaaS", "서비스", "구독"],
    "modern": ["모던", "modern", "세련된", "트렌디"],
}


# ── 핵심 전처리기 ──────────────────────────────────────────────────────────────

class NLPPreprocessor:
    """자연어 → AI 에이전트 최적화 구조화 포맷 변환기."""

    def __init__(self, use_api: bool = True):
        self.use_api = use_api and _NLP_ENHANCE_ENABLED

    # ── 규칙 기반 분류 ─────────────────────────────────────────────────────────

    def _classify_action(self, text: str) -> tuple[str, float]:
        text_lower = text.lower()
        scores: dict[str, int] = {}
        for action, keywords in ACTION_MAP.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score:
                scores[action] = score
        if not scores:
            return "EXPLAIN", 0.4
        best = max(scores, key=scores.get)
        confidence = min(scores[best] / 3.0, 1.0)
        return best, confidence

    def _extract_target(self, text: str) -> str:
        # URL 추출
        url_m = re.search(r"https?://\S+", text)
        if url_m:
            return url_m.group(0)

        # GitHub 레포 패턴
        gh_m = re.search(r"github\.com/[\w-]+/[\w-]+", text)
        if gh_m:
            return gh_m.group(0)

        # 파일명 패턴
        file_m = re.search(r"[\w가-힣_-]+\.(py|js|ts|html|md|json|yaml|yml|sh)", text)
        if file_m:
            return file_m.group(0)

        # 시스템 컴포넌트 매핑
        for comp, keywords in COMPONENT_KEYWORDS.items():
            if any(kw in text.lower() for kw in keywords):
                return comp

        return "system"

    def _extract_component(self, text: str) -> Optional[str]:
        text_lower = text.lower()
        for comp, keywords in COMPONENT_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                return comp
        return None

    def _extract_style(self, text: str) -> Optional[str]:
        text_lower = text.lower()
        for style, keywords in STYLE_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                return style
        return None

    def _detect_agent_router(self, action: str, target: str) -> str:
        if action in ("BUILD", "FIX", "UPGRADE") and target not in ("system", "knowledge"):
            return "claude_code"
        if action == "ANALYZE":
            return "codex"
        if action == "CAPTURE":
            return "bucky_knowledge"
        if action == "DEPLOY":
            return "bucky_vercel"
        return "bucky"

    # ── 구조화 프롬프트 생성 ──────────────────────────────────────────────────

    def _build_structured_prompt(self, parsed: dict) -> str:
        action = parsed["action"]
        target = parsed["target"]
        component = parsed.get("component", "")
        style = parsed.get("style", "")
        raw = parsed["raw"]

        parts = [f"[{action}]"]
        if target and target != "system":
            parts.append(f"대상: {target}")
        if component:
            parts.append(f"컴포넌트: {component}")
        if style:
            parts.append(f"스타일: {style}")
        parts.append(f"\n원문: {raw}")

        return " | ".join(parts[:3]) + parts[-1]

    # ── Claude API 강화 처리 (선택적) ─────────────────────────────────────────

    def _enhance_with_claude(self, text: str, base_result: dict) -> dict:
        if not self.use_api or len(text) < 5:
            return base_result

        prompt = f"""다음 한국어 자연어 입력을 분석해 JSON으로 반환하세요.

입력: {text}

반환 형식 (JSON만, 설명 없이):
{{
  "action": "BUILD|DEPLOY|ANALYZE|CAPTURE|SEARCH|FIX|EXPLAIN|UPGRADE|LIST 중 하나",
  "target": "대상 (레포명, URL, 파일명, 시스템 컴포넌트)",
  "component": "컴포넌트 (dashboard, landing_page, api, bot 등, 없으면 null)",
  "style": "스타일 힌트 (minimal, dark, saas 등, 없으면 null)",
  "intent_summary": "한 줄 의도 요약",
  "agent_router": "claude_code|codex|bucky_knowledge|bucky_vercel|bucky 중 가장 적합한 에이전트"
}}"""

        try:
            import urllib.request
            body = json.dumps({
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 300,
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
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                raw_text = data["content"][0]["text"].strip()
                # JSON 블록 추출
                json_m = re.search(r"\{.*\}", raw_text, re.DOTALL)
                if json_m:
                    enhanced = json.loads(json_m.group(0))
                    base_result.update({k: v for k, v in enhanced.items() if v is not None})
                    base_result["enhanced"] = True
        except Exception as e:
            print(f"[NLP] Claude API 강화 실패: {e}", flush=True)

        return base_result

    # ── 메인 처리 ─────────────────────────────────────────────────────────────

    def process(self, text: str, context: Optional[list] = None) -> dict:
        """
        자연어 텍스트를 구조화 포맷으로 변환.

        Returns:
            {
                action, target, component, style,
                agent_router, intent_summary,
                structured_prompt, confidence, enhanced, raw
            }
        """
        text = text.strip()
        if not text:
            return {"action": "EXPLAIN", "target": "system", "raw": text, "confidence": 0.0}

        action, confidence = self._classify_action(text)
        target = self._extract_target(text)
        component = self._extract_component(text)
        style = self._extract_style(text)
        agent_router = self._detect_agent_router(action, target)

        result = {
            "action": action,
            "target": target,
            "component": component,
            "style": style,
            "agent_router": agent_router,
            "intent_summary": f"{action} → {target or '대상 불명'}",
            "confidence": confidence,
            "enhanced": False,
            "raw": text,
            "context_count": len(context) if context else 0,
        }

        if self.use_api and confidence < 0.7:
            result = self._enhance_with_claude(text, result)

        result["structured_prompt"] = self._build_structured_prompt(result)
        return result


# ── 싱글톤 인스턴스 ────────────────────────────────────────────────────────────

_preprocessor: Optional[NLPPreprocessor] = None


def get_preprocessor() -> NLPPreprocessor:
    global _preprocessor
    if _preprocessor is None:
        _preprocessor = NLPPreprocessor()
    return _preprocessor


def preprocess(text: str, context: Optional[list] = None) -> dict:
    """간편 인터페이스 — discord_bot.py 등에서 임포트해 바로 사용."""
    corrected = _correct_stt(text)
    return get_preprocessor().process(corrected, context)


def format_for_discord(result: dict) -> str:
    """처리 결과를 Discord 메시지 형식으로 포맷."""
    icon = {
        "BUILD": "🔨", "DEPLOY": "🚀", "ANALYZE": "🔍", "CAPTURE": "📥",
        "SEARCH": "🔎", "FIX": "🔧", "EXPLAIN": "💬", "UPGRADE": "⬆️", "LIST": "📋",
    }.get(result.get("action", ""), "📋")

    agent = {
        "claude_code": "🤖 Claude Code",
        "codex": "🔍 Codex",
        "bucky_knowledge": "📚 Knowledge",
        "bucky_vercel": "🚀 Vercel",
        "bucky": "🎯 Bucky",
    }.get(result.get("agent_router", "bucky"), "🎯 Bucky")

    lines = [
        f"{icon} **[{result.get('action', '?')}]** → {agent}",
        f"대상: `{result.get('target', 'system')}`",
    ]
    if result.get("component"):
        lines.append(f"컴포넌트: `{result['component']}`")
    if result.get("style"):
        lines.append(f"스타일: `{result['style']}`")
    conf = result.get("confidence", 0.0)
    lines.append(f"신뢰도: `{conf:.0%}` {'✅' if conf >= 0.7 else '⚠️'}")
    return "\n".join(lines)


# ── CLI 테스트 ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys as _sys
    test_inputs = _sys.argv[1:] or [
        "대시보드 같은 거 만들어줘",
        "이 레포 배포해줘 https://github.com/user/bucky",
        "지식베이스에 저장해",
        "패턴 분석해줘",
    ]
    pp = NLPPreprocessor(use_api=False)
    for text in test_inputs:
        r = pp.process(text)
        print(f"\n입력: {text}")
        print(f"결과: {json.dumps(r, ensure_ascii=False, indent=2)}")
