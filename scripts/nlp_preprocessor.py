#!/usr/bin/env python3
"""NLP 전처리기 — 자연어(음성/텍스트) → AI 최적 구조화 포맷 변환

사용자의 자연어 발화를 Claude Code / Codex가 바로 실행할 수 있는
구조화된 포맷으로 변환합니다.

사용법:
    from nlp_preprocessor import preprocess
    result = preprocess("대시보드 같은 거 만들어줘")
    # → {"action": "BUILD", "component": "dashboard", ...}
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent.parent

# ── 액션 사전 ─────────────────────────────────────────────────────────────────

ACTION_MAP: dict[str, list[str]] = {
    "BUILD":    ["만들어", "만들게", "만들자", "만들어줘", "개발해", "개발해줘", "구축해", "구현해", "생성해", "만들어봐"],
    "FIX":      ["고쳐", "고쳐줘", "수정해", "수정해줘", "버그", "오류", "에러", "안 돼", "안돼", "문제", "픽스"],
    "DEPLOY":   ["배포해", "배포해줘", "배포", "올려", "올려줘", "publish", "deploy"],
    "ANALYZE":  ["분석해", "분석해줘", "확인해", "확인해봐", "살펴봐", "파악해"],
    "SEARCH":   ["찾아", "찾아줘", "검색해", "검색해줘", "어디", "뭐야"],
    "EXPLAIN":  ["설명해", "설명해줘", "알려줘", "알려", "가르쳐", "뭔지"],
    "UPDATE":   ["업데이트", "업데이트해줘", "수정해", "바꿔", "변경해", "고도화"],
    "DELETE":   ["삭제해", "삭제해줘", "지워", "지워줘", "제거해"],
    "LIST":     ["목록", "보여줘", "리스트", "뭐가 있어", "나열해"],
    "SAVE":     ["저장해", "저장해줘", "기록해", "기록해줘", "남겨", "기억해"],
    "CAPTURE":  ["캡처", "캡셔", "캡쳐", "스크린샷", "스냅샷"],
    "CONTINUE": ["이어서", "계속해", "다음", "진행해", "진행해줘"],
}

# ── 컴포넌트 사전 ────────────────────────────────────────────────────────────

COMPONENT_MAP: dict[str, list[str]] = {
    "dashboard":      ["대시보드", "dashboard"],
    "landing_page":   ["랜딩", "랜딩페이지", "landing", "홈페이지"],
    "api":            ["api", "API", "엔드포인트", "endpoint"],
    "bot":            ["봇", "bot", "디스코드 봇"],
    "payment":        ["결제", "payment", "stripe", "toss", "페이먼트"],
    "auth":           ["인증", "로그인", "login", "auth", "회원"],
    "database":       ["db", "database", "데이터베이스", "디비"],
    "ui":             ["ui", "UI", "화면", "인터페이스", "레이아웃"],
    "agent":          ["에이전트", "agent", "bucky", "버키"],
    "knowledge":      ["지식", "노트", "obsidian", "옵시디안", "vault"],
    "voice":          ["음성", "voice", "stt", "tts", "마이크"],
    "graph":          ["그래프", "graph", "그래플", "graphify"],
    "skill":          ["스킬", "skill", "명령어", "커맨드"],
    "pipeline":       ["파이프라인", "pipeline", "자동화", "워크플로우"],
    "template":       ["템플릿", "template", "양식"],
    "report":         ["보고서", "리포트", "report", "일일"],
    "deploy_config":  ["vercel", "배포설정", "github actions", "ci"],
}

# ── 타겟 추론 사전 ───────────────────────────────────────────────────────────

TARGET_MAP: dict[str, list[str]] = {
    "obsidian-agent-brain-system": ["이 시스템", "우리 시스템", "브레인", "버키 시스템"],
    "discord_bot":                 ["디스코드", "discord", "봇"],
    "obsidian_vault":              ["옵시디안", "vault", "볼트", "노트"],
    "scripts":                     ["scripts", "스크립트", "파이썬"],
    "templates":                   ["템플릿", "template"],
}

# ── STT 오류 교정 사전 ───────────────────────────────────────────────────────

STT_CORRECTIONS: dict[str, str] = {
    "타임리스":  "Typeless",
    "드래플루":  "그래프",
    "캡셔":     "캡처",
    "캡셀":     "캡슐",
    "클로드코드": "Claude Code",
    "코덱스":   "Codex",
    "그래플비":  "Graphify",
    "옵시디안":  "Obsidian",
    "OCD":     "Obsidian",
    "OCD 화면": "Obsidian 화면",
    "디스코드":  "Discord",
    "깃허브":   "GitHub",
    "스트라이프": "Stripe",
    "벌키":    "Bucky",
    "버키":    "Bucky",
    "파이프라인": "pipeline",
    "워크플로우": "workflow",
    "에이전트":  "agent",
    "스킬":    "skill",
    "템플릿":   "template",
    "랜딩":    "landing",
    "배포":    "deploy",
    "분석":    "analyze",
    "전처리":   "preprocess",
    "자동화":   "automation",
    "인프라노더스": "InfraNodus",
    "인프라노두스": "InfraNodus",
    "깃":     "Git",
    "깃헙":    "GitHub",
    "AI":    "AI",
    "유튜브":   "YouTube",
    "크레딧":   "credit",
    "API 키":  "API key",
    "URL":   "URL",
    "명명 푸넘포트": "well-formed prompt",
    "퍼넘포트":  "prompt format",
    "포멧":    "format",
    # ── 이번 세션에서 추가된 오류 패턴 ──────────────────────────────────────
    "플레이는": "플랜은",
    "플레이를": "플랜을",
    "플레이": "플랜",
    "음성의식": "음성인식",
    "음성식": "음성인식",
    "인식이": "인식이",
    "패스워드": "password",
    "레포": "레포지토리",
    "레포지": "레포지토리",
    "그래플루": "그래프",
    "그래플": "그래프",
    "드래플": "그래프",
    "웹훅": "webhook",
    "웹 훅": "webhook",
    "스트라이프 결제": "Stripe 결제",
    "도커": "Docker",
    "도커파일": "Dockerfile",
    "쿠버": "Kubernetes",
    "쿠버네티스": "Kubernetes",
    "레일웨이": "Railway",
    "레일웨이배포": "Railway 배포",
    "봇 재시작": "봇 재시작",
    "버클리": "Bucky",
    "버킷": "Bucky",
    "다음 플레이": "다음 플랜",
    "작업 플레이": "작업 플랜",
    "플레이대로": "플랜대로",
    "음성인 식": "음성인식",
}


def correct_stt(text: str) -> str:
    """STT 오류를 사전 기반으로 교정."""
    corrected = text
    for wrong, right in STT_CORRECTIONS.items():
        corrected = corrected.replace(wrong, right)
    return corrected


def detect_action(text: str) -> str:
    """텍스트에서 주요 액션 감지."""
    text_lower = text.lower()
    for action, keywords in ACTION_MAP.items():
        for kw in keywords:
            if kw.lower() in text_lower:
                return action
    return "QUERY"


def detect_component(text: str) -> Optional[str]:
    """텍스트에서 대상 컴포넌트 감지."""
    text_lower = text.lower()
    for component, keywords in COMPONENT_MAP.items():
        for kw in keywords:
            if kw.lower() in text_lower:
                return component
    return None


def detect_target(text: str) -> Optional[str]:
    """텍스트에서 대상 레포/시스템 감지."""
    text_lower = text.lower()
    for target, keywords in TARGET_MAP.items():
        for kw in keywords:
            if kw.lower() in text_lower:
                return target
    return None


def extract_urls(text: str) -> list[str]:
    """텍스트에서 URL 추출."""
    url_pattern = r'https?://[^\s]+'
    return re.findall(url_pattern, text)


def detect_priority(text: str) -> str:
    """우선순위 감지."""
    if any(kw in text for kw in ["급해", "급히", "빨리", "바로", "지금 당장", "P0"]):
        return "P0"
    if any(kw in text for kw in ["중요해", "중요한", "P1"]):
        return "P1"
    return "P2"


def preprocess(raw_text: str, context: Optional[dict] = None) -> dict:
    """자연어 텍스트를 AI 실행 가능한 구조화 포맷으로 변환.

    Args:
        raw_text: 원본 자연어 텍스트 (음성 인식 결과 포함)
        context: 이전 대화 컨텍스트 (선택)

    Returns:
        구조화된 딕셔너리:
        {
            "raw": 원본 텍스트,
            "corrected": STT 교정 텍스트,
            "action": 주요 액션,
            "component": 대상 컴포넌트,
            "target": 대상 시스템/레포,
            "urls": 추출된 URL 목록,
            "priority": 우선순위,
            "context_refs": 컨텍스트 참조,
            "prompt": Claude Code용 최적화 프롬프트
        }
    """
    corrected = correct_stt(raw_text)
    action = detect_action(corrected)
    component = detect_component(corrected)
    target = detect_target(corrected)
    urls = extract_urls(corrected)
    priority = detect_priority(corrected)

    context_refs: list[str] = []
    if context:
        if context.get("last_component"):
            context_refs.append(f"이전 작업: {context['last_component']}")
        if context.get("last_action"):
            context_refs.append(f"이전 액션: {context['last_action']}")

    # Claude Code용 최적화 프롬프트 생성
    prompt_parts = [f"[{action}]"]
    if component:
        prompt_parts.append(f"component={component}")
    if target:
        prompt_parts.append(f"target={target}")
    if urls:
        prompt_parts.append(f"urls={urls}")
    if priority != "P2":
        prompt_parts.append(f"priority={priority}")
    prompt_parts.append(f"instruction={corrected}")

    return {
        "raw": raw_text,
        "corrected": corrected,
        "action": action,
        "component": component,
        "target": target,
        "urls": urls,
        "priority": priority,
        "context_refs": context_refs,
        "prompt": " | ".join(prompt_parts),
    }


def format_for_claude(structured: dict) -> str:
    """구조화 결과를 Claude Code 프롬프트로 포맷."""
    lines = [
        f"# 작업 요청",
        f"**액션**: {structured['action']}",
    ]
    if structured["component"]:
        lines.append(f"**컴포넌트**: {structured['component']}")
    if structured["target"]:
        lines.append(f"**대상**: {structured['target']}")
    if structured["urls"]:
        lines.append(f"**참조 URL**: {', '.join(structured['urls'])}")
    if structured["priority"] != "P2":
        lines.append(f"**우선순위**: {structured['priority']}")
    lines.append(f"\n**원본 지시**: {structured['corrected']}")
    if structured["context_refs"]:
        lines.append(f"\n**컨텍스트**: {'; '.join(structured['context_refs'])}")
    return "\n".join(lines)


# ── Discord 봇 연동용 래퍼 ───────────────────────────────────────────────────

def preprocess_for_discord(text: str, channel_context: Optional[dict] = None) -> tuple[dict, str]:
    """Discord 메시지 전처리 + 포맷된 프롬프트 반환."""
    structured = preprocess(text, context=channel_context)
    formatted = format_for_claude(structured)
    return structured, formatted


if __name__ == "__main__":
    # 테스트
    test_cases = [
        "대시보드 같은 거 만들어줘",
        "OCD 화면 안에 드래플루 뷰를 캡셔해서 보내줘",
        "타임리스 벤치마킹해서 직접 제작해줘",
        "트랙 A와 B를 승인하니까 진행해",
        "이 시스템 배포해줘 빨리",
        "지식 그래플비 캡셀해줘",
    ]

    for test in test_cases:
        result = preprocess(test)
        print(f"\n입력: {test}")
        print(f"  액션: {result['action']}")
        print(f"  교정: {result['corrected']}")
        print(f"  컴포넌트: {result['component']}")
        print(f"  우선순위: {result['priority']}")
        print(f"  프롬프트: {result['prompt']}")
