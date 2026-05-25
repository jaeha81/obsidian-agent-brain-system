#!/usr/bin/env python3
"""STT 고도화 모듈 — Typeless 벤치마킹 + 컨텍스트 인식 후처리

Typeless (typeless.com)의 핵심 기능을 분석해 구현:
1. 실시간 스트리밍 STT (Whisper 기반)
2. 컨텍스트 인식 교정 (이전 대화 참조)
3. 명령어 감지 및 포맷팅
4. 자동 구두점 삽입

기존 bucky_voice.py / discord_bot.py와 연동됩니다.
"""

from __future__ import annotations

import os
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

try:
    from nlp_preprocessor import correct_stt, preprocess
    NLP_AVAILABLE = True
except ImportError:
    NLP_AVAILABLE = False


# ── 후처리 규칙 ──────────────────────────────────────────────────────────────

@dataclass
class STTContext:
    """대화 컨텍스트 — 교정 품질 향상에 사용."""
    history: list[str] = field(default_factory=list)
    last_action: Optional[str] = None
    last_component: Optional[str] = None
    topic_keywords: list[str] = field(default_factory=list)
    session_start: float = field(default_factory=time.time)

    def add_utterance(self, text: str) -> None:
        self.history.append(text)
        if len(self.history) > 20:
            self.history.pop(0)

    def update_from_structured(self, structured: dict) -> None:
        if structured.get("action"):
            self.last_action = structured["action"]
        if structured.get("component"):
            self.last_component = structured["component"]


# ── 구두점 자동 삽입 ─────────────────────────────────────────────────────────

SENTENCE_ENDINGS = re.compile(r'(해줘|해줘요|해주세요|했어|했어요|이야|이에요|입니다|습니다|할게|할게요|할까요|할까|주세요|세요|어요|아요)\s*$')
QUESTION_ENDINGS = re.compile(r'(할까요|할까|있어요|있어|인가요|인가|나요|나|죠|지요)\s*$')


def add_punctuation(text: str) -> str:
    """자연스러운 구두점 자동 삽입."""
    text = text.strip()
    if not text:
        return text
    if text.endswith(("?", ".", "!")):
        return text
    if QUESTION_ENDINGS.search(text):
        return text + "?"
    if SENTENCE_ENDINGS.search(text):
        return text + "."
    return text


# ── 반복/필러 제거 ───────────────────────────────────────────────────────────

FILLER_PATTERNS = [
    r'\b(어\s?어|음\s?음|아\s?아|네\s?네|예\s?예)\b',
    r'^(음|어|아|에|그|이제|뭐|저)\s+',
    r'\s+(음|어|아)\s+',
    r'(그러니까|뭐냐면|있잖아요?|있잖아)\s*,?\s*',
]

def remove_fillers(text: str) -> str:
    """음성 필러 및 반복 제거."""
    for pattern in FILLER_PATTERNS:
        text = re.sub(pattern, ' ', text, flags=re.IGNORECASE)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


# ── 명령어 감지 ──────────────────────────────────────────────────────────────

COMMANDS = {
    "!취소": "CANCEL",
    "!중지": "STOP",
    "!다시": "RETRY",
    "!확인": "CONFIRM",
    "취소해줘": "CANCEL",
    "중지해줘": "STOP",
    "다시 해줘": "RETRY",
}

def detect_command(text: str) -> Optional[str]:
    """특수 명령어 감지."""
    for kw, cmd in COMMANDS.items():
        if kw in text:
            return cmd
    return None


# ── 컨텍스트 기반 교정 ───────────────────────────────────────────────────────

def context_aware_correction(text: str, ctx: STTContext) -> str:
    """이전 대화 컨텍스트 기반으로 애매한 표현 교정."""
    corrected = text

    # "이거", "그거" → 이전 컴포넌트로 교체
    if ctx.last_component and re.search(r'\b(이거|그거|이것|그것|거기|여기)\b', corrected):
        corrected = re.sub(
            r'\b(이거|그거|이것|그것)\b',
            ctx.last_component,
            corrected, count=1
        )

    # "이어서", "계속" → CONTINUE 플래그
    if any(kw in corrected for kw in ["이어서", "계속해", "다음 거", "그다음"]):
        if ctx.last_action:
            corrected = f"{corrected} [이전 작업: {ctx.last_action} 이어서]"

    return corrected


# ── 메인 후처리 파이프라인 ───────────────────────────────────────────────────

@dataclass
class STTResult:
    """STT 처리 결과."""
    raw: str
    cleaned: str
    corrected: str
    structured: Optional[dict]
    command: Optional[str]
    confidence: float
    processing_time_ms: float


def postprocess(
    raw_text: str,
    ctx: Optional[STTContext] = None,
    apply_nlp: bool = True,
) -> STTResult:
    """STT 결과 전체 후처리 파이프라인.

    단계:
    1. 필러 제거
    2. STT 오류 교정 (NLP 사전)
    3. 컨텍스트 기반 교정
    4. 구두점 삽입
    5. 명령어 감지
    6. 구조화 (NLP 전처리기)
    """
    t_start = time.time()
    if ctx is None:
        ctx = STTContext()

    # 1. 필러 제거
    cleaned = remove_fillers(raw_text)

    # 2. STT 오류 교정
    if NLP_AVAILABLE:
        corrected = correct_stt(cleaned)
    else:
        corrected = cleaned

    # 3. 컨텍스트 기반 교정
    corrected = context_aware_correction(corrected, ctx)

    # 4. 구두점 삽입
    corrected = add_punctuation(corrected)

    # 5. 명령어 감지
    command = detect_command(corrected)

    # 6. 구조화
    structured = None
    if apply_nlp and NLP_AVAILABLE and not command:
        structured = preprocess(corrected, context={
            "last_action": ctx.last_action,
            "last_component": ctx.last_component,
        })
        ctx.update_from_structured(structured)

    ctx.add_utterance(corrected)

    t_end = time.time()

    return STTResult(
        raw=raw_text,
        cleaned=cleaned,
        corrected=corrected,
        structured=structured,
        command=command,
        confidence=_estimate_confidence(raw_text, corrected),
        processing_time_ms=(t_end - t_start) * 1000,
    )


def _estimate_confidence(raw: str, corrected: str) -> float:
    """교정 전후 변화량으로 신뢰도 추정 (0~1)."""
    if not raw:
        return 0.0
    # 변화가 많을수록 STT 신뢰도 낮다고 추정
    changes = sum(1 for a, b in zip(raw, corrected) if a != b)
    ratio = changes / max(len(raw), 1)
    return max(0.0, min(1.0, 1.0 - ratio))


# ── Discord 봇 연동 ──────────────────────────────────────────────────────────

class DiscordSTTSession:
    """Discord 채널별 STT 세션 관리."""

    def __init__(self):
        self._sessions: dict[str, STTContext] = {}

    def get_context(self, channel_id: str) -> STTContext:
        if channel_id not in self._sessions:
            self._sessions[channel_id] = STTContext()
        return self._sessions[channel_id]

    def process(self, channel_id: str, raw_text: str) -> STTResult:
        ctx = self.get_context(channel_id)
        return postprocess(raw_text, ctx=ctx)

    def reset(self, channel_id: str) -> None:
        if channel_id in self._sessions:
            del self._sessions[channel_id]


# 전역 세션 매니저 (discord_bot.py에서 import해서 사용)
discord_stt_session = DiscordSTTSession()


def postprocess_for_discord(text: str) -> str:
    """discord_bot.py 연동용 래퍼 — 교정된 텍스트 문자열만 반환."""
    result = postprocess(text, ctx=None, apply_nlp=True)
    return result.corrected


# ── 독립 실행 테스트 ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    test_cases = [
        "음 그러니까 어 대시보드 같은 거 만들어줘",
        "OCD 화면 안에 드래플루 뷰를 캡셔해서 보내줘",
        "타임리스 벤치마킹해서 직접 제작해줘",
        "이어서 진행해줘",
        "취소해줘",
        "버키 이 레포 배포해줘 빨리",
    ]

    ctx = STTContext()
    print("=" * 60)
    print("STT Enhanced 테스트")
    print("=" * 60)

    for raw in test_cases:
        result = postprocess(raw, ctx=ctx)
        print(f"\n원본:   {result.raw}")
        print(f"정제:   {result.cleaned}")
        print(f"교정:   {result.corrected}")
        if result.command:
            print(f"명령어: {result.command}")
        if result.structured:
            print(f"액션:   {result.structured['action']}")
            if result.structured['component']:
                print(f"컴포:   {result.structured['component']}")
        print(f"신뢰도: {result.confidence:.2f} | {result.processing_time_ms:.1f}ms")
