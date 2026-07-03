#!/usr/bin/env python3
"""
Bucky Landing Page Generator
GitHub 레포 정보 → 프리미엄 랜딩 페이지 자동 생성
"""
import json
import re
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).parent.parent
TEMPLATE_PATH = ROOT / "templates" / "landing_page_template.html"
OUTPUT_DIR = ROOT / "generated" / "landing_pages"

DEFAULT_CONFIG = {
    "REPO_NAME": "MyProduct",
    "LOGO_CHAR": "M",
    "TAGLINE": "당신의 문제를 해결하는 가장 빠른 방법",
    "BADGE_TEXT": "✨ 새로운 기능 출시",
    "HEADLINE_LINE1": "더 스마트하게,",
    "HEADLINE_LINE2": "더 빠르게.",
    "DESCRIPTION": "복잡한 작업을 자동화하고 생산성을 10배 높이세요. 지금 바로 시작할 수 있습니다.",
    "GITHUB_URL": "#",
    "CTA_URL": "#",
    "DEMO_URL": "#",
    "CTA_TEXT": "무료 시작",
    "CTA_PRIMARY": "무료로 시작하기",
    "CTA_SECONDARY": "데모 보기",
    "SOCIAL_PROOF": "이미 1,000명 이상이 사용 중 · 카드 불필요",
    "YEAR": str(datetime.now().year),
    "FEATURES_TITLE": "왜 선택해야 할까요?",
    "FEATURES_SUBTITLE": "단순하고 강력한 기능으로 구성되어 있습니다.",
    "HOWTO_TITLE": "3단계로 시작하세요",
    "PRICING_TITLE": "투명한 가격",
    "PRICING_SUBTITLE": "숨겨진 비용 없이 합리적인 가격으로 시작하세요.",
    "CTA_BOTTOM_TITLE": "지금 바로 시작하세요",
    "CTA_BOTTOM_DESC": "무료 플랜으로 시작하고 언제든지 업그레이드하세요.",
    "STATS": [
        {"STAT_VALUE": "10x", "STAT_LABEL": "생산성 향상"},
        {"STAT_VALUE": "1k+", "STAT_LABEL": "활성 사용자"},
        {"STAT_VALUE": "99%", "STAT_LABEL": "만족도"},
        {"STAT_VALUE": "24/7", "STAT_LABEL": "자동화"},
    ],
    "FEATURES": [
        {"FEATURE_ICON": "⚡", "FEATURE_TITLE": "빠른 속도", "FEATURE_DESC": "밀리초 단위 응답으로 사용자 경험을 극대화합니다."},
        {"FEATURE_ICON": "🤖", "FEATURE_TITLE": "AI 자동화", "FEATURE_DESC": "반복 작업을 AI가 대신 처리합니다."},
        {"FEATURE_ICON": "🔗", "FEATURE_TITLE": "손쉬운 연동", "FEATURE_DESC": "기존 워크플로우에 5분 안에 연결합니다."},
    ],
    "STEPS": [
        {"STEP_NUM": "1", "STEP_TITLE": "설치하기", "STEP_DESC": "npm install 또는 pip install로 30초 안에 시작하세요."},
        {"STEP_NUM": "2", "STEP_TITLE": "설정하기", "STEP_DESC": "API 키 입력 후 바로 사용 가능합니다."},
        {"STEP_NUM": "3", "STEP_TITLE": "즐기기", "STEP_DESC": "자동화된 워크플로우로 생산성을 높이세요."},
    ],
    "PLANS": [
        {
            "PLAN_NAME": "Free", "PLAN_PRICE": "₩0", "PLAN_DESC": "개인 사용자용",
            "PLAN_BG": "bg-gray-900", "PLAN_BORDER": "border-white/8",
            "PLAN_BTN_STYLE": "bg-white/5 hover:bg-white/10 text-white",
            "PLAN_BTN_TEXT": "무료 시작", "PLAN_URL": "#", "IS_FEATURED": False,
            "PLAN_FEATURES": [{"FEATURE": "월 100회 요청"}, {"FEATURE": "기본 기능"}],
        },
        {
            "PLAN_NAME": "Pro", "PLAN_PRICE": "₩29,000", "PLAN_DESC": "팀 및 전문가용",
            "PLAN_BG": "bg-indigo-950", "PLAN_BORDER": "border-indigo-500/30",
            "PLAN_BTN_STYLE": "bg-indigo-600 hover:bg-indigo-500 text-white",
            "PLAN_BTN_TEXT": "Pro 시작하기", "PLAN_URL": "#", "IS_FEATURED": True,
            "PLAN_FEATURES": [{"FEATURE": "무제한 요청"}, {"FEATURE": "모든 기능"}, {"FEATURE": "우선 지원"}],
        },
        {
            "PLAN_NAME": "Enterprise", "PLAN_PRICE": "문의", "PLAN_DESC": "기업용",
            "PLAN_BG": "bg-gray-900", "PLAN_BORDER": "border-white/8",
            "PLAN_BTN_STYLE": "bg-white/5 hover:bg-white/10 text-white",
            "PLAN_BTN_TEXT": "문의하기", "PLAN_URL": "mailto:", "IS_FEATURED": False,
            "PLAN_FEATURES": [{"FEATURE": "전용 인프라"}, {"FEATURE": "SLA 보장"}, {"FEATURE": "온보딩 지원"}],
        },
    ],
}


def render_template(template: str, config: dict) -> str:
    result = template

    # 배열 렌더링 ({{#KEY}}...{{/KEY}})
    for key, value in config.items():
        if isinstance(value, list):
            pattern = rf"\{{{{#{key}\}}}}(.*?)\{{{{/{key}\}}}}"
            match = re.search(pattern, result, re.DOTALL)
            if match:
                item_template = match.group(1)
                rendered_items = ""
                for item in value:
                    rendered_item = item_template
                    for k, v in item.items():
                        if k == "IS_FEATURED" and isinstance(v, bool):
                            if not v:
                                rendered_item = re.sub(
                                    r"\{\{#IS_FEATURED\}\}.*?\{\{/IS_FEATURED\}\}",
                                    "",
                                    rendered_item,
                                    flags=re.DOTALL,
                                )
                            else:
                                rendered_item = re.sub(
                                    r"\{\{#IS_FEATURED\}\}|\{\{/IS_FEATURED\}\}",
                                    "",
                                    rendered_item,
                                )
                        elif isinstance(v, list):
                            sub_pattern = rf"\{{{{#{k}\}}}}(.*?)\{{{{/{k}\}}}}"
                            sub_match = re.search(sub_pattern, rendered_item, re.DOTALL)
                            if sub_match:
                                sub_template = sub_match.group(1)
                                sub_items = ""
                                for sub_item in v:
                                    sub_rendered = sub_template
                                    for sk, sv in sub_item.items():
                                        sub_rendered = sub_rendered.replace(f"{{{{{sk}}}}}", str(sv))
                                    sub_items += sub_rendered
                                rendered_item = rendered_item[:sub_match.start()] + sub_items + rendered_item[sub_match.end():]
                        else:
                            rendered_item = rendered_item.replace(f"{{{{{k}}}}}", str(v))
                    rendered_items += rendered_item
                result = result[:match.start()] + rendered_items + result[match.end():]

    # 단순 변수 치환 {{KEY}}
    for key, value in config.items():
        if not isinstance(value, list):
            result = result.replace(f"{{{{{key}}}}}", str(value))

    return result


def generate(config: Optional[dict] = None, output_name: Optional[str] = None) -> Path:
    merged = {**DEFAULT_CONFIG, **(config or {})}
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    html = render_template(template, merged)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    name = output_name or merged.get("REPO_NAME", "landing").lower().replace(" ", "-")
    out_path = OUTPUT_DIR / f"{name}.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"✅ 랜딩 페이지 생성: {out_path}")
    return out_path


def from_github_url(github_url: str, extra: dict = None) -> Path:
    """GitHub URL에서 레포 이름 추출 후 기본 config 생성"""
    parts = github_url.rstrip("/").split("/")
    repo_name = parts[-1] if len(parts) >= 2 else "Product"
    owner = parts[-2] if len(parts) >= 2 else ""
    config = {
        "REPO_NAME": repo_name,
        "LOGO_CHAR": repo_name[0].upper(),
        "GITHUB_URL": github_url,
        **(extra or {}),
    }
    return generate(config, repo_name.lower())


if __name__ == "__main__":
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg.startswith("http"):
            out = from_github_url(arg)
        elif arg.endswith(".json"):
            cfg = json.loads(Path(arg).read_text(encoding="utf-8"))
            out = generate(cfg)
        else:
            print("Usage: python bucky_landing_generator.py <github_url | config.json>")
            sys.exit(1)
    else:
        out = generate()
    print(f"Output: {out}")
