#!/usr/bin/env python3
"""
Bucky Commercialize Pipeline
레포 URL → 랜딩 페이지 생성 → Vercel 배포 → 결제 버튼 삽입 → Discord 보고
"""
import json
import os
import re
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env", encoding="utf-8-sig", override=True)

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK_URL", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")


def _discord(msg: str) -> None:
    if DISCORD_WEBHOOK:
        try:
            requests.post(DISCORD_WEBHOOK, json={"content": msg}, timeout=5)
        except Exception:
            pass


def fetch_github_meta(repo_url: str) -> dict:
    """GitHub API로 레포 메타데이터 가져오기"""
    match = re.search(r"github\.com/([^/]+)/([^/]+)", repo_url)
    if not match:
        return {}
    owner, repo = match.group(1), match.group(2).rstrip(".git")

    headers = {}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"

    try:
        r = requests.get(f"https://api.github.com/repos/{owner}/{repo}", headers=headers, timeout=10)
        if r.ok:
            data = r.json()
            return {
                "name": data.get("name", repo),
                "description": data.get("description", ""),
                "stars": data.get("stargazers_count", 0),
                "language": data.get("language", ""),
                "topics": data.get("topics", []),
                "homepage": data.get("homepage", ""),
                "owner": owner,
            }
    except Exception:
        pass
    return {"name": repo, "owner": owner}


def meta_to_config(meta: dict, extra: dict = None) -> dict:
    name = meta.get("name", "Product")
    desc = meta.get("description") or "강력하고 빠른 솔루션"
    stars = meta.get("stars", 0)
    lang = meta.get("language", "")

    return {
        "REPO_NAME": name,
        "LOGO_CHAR": name[0].upper(),
        "TAGLINE": desc,
        "HEADLINE_LINE1": f"{name}으로",
        "HEADLINE_LINE2": "더 빠르게 시작하세요.",
        "DESCRIPTION": desc,
        "GITHUB_URL": f"https://github.com/{meta.get('owner', '')}/{name}",
        "BADGE_TEXT": f"⭐ GitHub {stars}+ Stars · {lang}",
        "SOCIAL_PROOF": f"GitHub에서 {stars}+ 개발자가 선택했습니다",
        **(extra or {}),
    }


def add_payment_button(html_path: Path, payment_url: str, price: str = "₩29,000/월") -> None:
    """랜딩 페이지에 결제 버튼 삽입"""
    html = html_path.read_text(encoding="utf-8")
    payment_section = f"""
  <!-- PAYMENT -->
  <section class="py-12 px-6 text-center">
    <a href="{payment_url}"
       class="inline-block px-12 py-5 rounded-2xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 font-bold text-xl transition-all shadow-2xl shadow-indigo-500/30">
      💳 지금 구매하기 — {price}
    </a>
    <p class="mt-3 text-sm text-gray-500">Stripe/Toss 결제 · 30일 환불 보장</p>
  </section>
"""
    html = html.replace("<!-- FOOTER -->", payment_section + "\n  <!-- FOOTER -->")
    html_path.write_text(html, encoding="utf-8")
    print(f"💳 결제 버튼 삽입 완료")


def run(
    repo_url: str,
    payment_url: str = "",
    price: str = "₩29,000/월",
    deploy: bool = True,
    extra_config: dict = None,
) -> dict:
    _discord(f"🏭 **상품화 파이프라인 시작**: {repo_url}")

    # 1. GitHub 메타데이터
    print("1️⃣ GitHub 메타데이터 수집...")
    meta = fetch_github_meta(repo_url)
    config = meta_to_config(meta, extra_config)
    print(f"   → {config['REPO_NAME']}: {config['DESCRIPTION'][:50]}")

    # 2. 랜딩 페이지 생성
    print("2️⃣ 랜딩 페이지 생성...")
    from bucky_landing_generator import generate
    landing_path = generate(config, config["REPO_NAME"].lower())
    print(f"   → {landing_path}")

    # 3. 결제 버튼 삽입
    if payment_url:
        print("3️⃣ 결제 버튼 삽입...")
        add_payment_button(landing_path, payment_url, price)

    result = {
        "repo": repo_url,
        "landing_path": str(landing_path),
        "config": config,
        "deployed": False,
        "url": "",
    }

    # 4. Vercel 배포
    if deploy:
        print("4️⃣ Vercel 배포...")
        from bucky_vercel_deploy import deploy_landing_page
        deploy_result = deploy_landing_page(config["REPO_NAME"], landing_path)
        result["deployed"] = deploy_result.get("success", False)
        result["url"] = deploy_result.get("url", "")

    # 5. Discord 보고
    msg_parts = [f"✅ **{config['REPO_NAME']}** 상품화 완료!"]
    msg_parts.append(f"📄 랜딩 페이지: `{landing_path.name}`")
    if result["url"]:
        msg_parts.append(f"🌐 배포 URL: {result['url']}")
    if payment_url:
        msg_parts.append(f"💳 결제: {payment_url}")
    _discord("\n".join(msg_parts))

    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python bucky_commercialize.py <github_url> [payment_url] [price]")
        print("Example: python bucky_commercialize.py https://github.com/user/repo https://buy.stripe.com/xxx '₩29,000/월'")
        sys.exit(1)

    repo = sys.argv[1]
    pay_url = sys.argv[2] if len(sys.argv) > 2 else ""
    price = sys.argv[3] if len(sys.argv) > 3 else "₩29,000/월"
    result = run(repo, pay_url, price)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
