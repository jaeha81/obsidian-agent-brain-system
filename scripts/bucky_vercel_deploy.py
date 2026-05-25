#!/usr/bin/env python3
"""
Bucky Vercel Auto-Deploy
프로젝트 경로 → Vercel 배포 → Discord 알림
"""
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env", encoding="utf-8", override=True)

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK_URL", "")


def _discord(msg: str) -> None:
    if DISCORD_WEBHOOK:
        try:
            requests.post(DISCORD_WEBHOOK, json={"content": msg}, timeout=5)
        except Exception:
            pass


def _run(cmd: list[str], cwd: Path) -> tuple[int, str, str]:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def ensure_vercel_json(project_dir: Path, project_name: str) -> None:
    config_path = project_dir / "vercel.json"
    if not config_path.exists():
        config = {"name": project_name.lower().replace(" ", "-"), "version": 2}
        config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"📄 vercel.json 생성: {config_path}")


def deploy(project_dir: str | Path, project_name: str = "", prod: bool = True) -> dict:
    project_dir = Path(project_dir)
    if not project_dir.exists():
        return {"success": False, "error": f"경로 없음: {project_dir}"}

    name = project_name or project_dir.name
    ensure_vercel_json(project_dir, name)

    _discord(f"🚀 **{name}** Vercel 배포 시작...")

    cmd = ["vercel", "--yes"]
    if prod:
        cmd.append("--prod")

    code, stdout, stderr = _run(cmd, project_dir)

    if code != 0:
        msg = f"❌ **{name}** 배포 실패\n```{stderr[:500]}```"
        _discord(msg)
        return {"success": False, "error": stderr, "project": name}

    # Vercel 출력에서 URL 추출
    url = ""
    for line in stdout.splitlines():
        if line.startswith("https://"):
            url = line.strip()
            break

    result = {
        "success": True,
        "project": name,
        "url": url,
        "deployed_at": datetime.now().isoformat(),
        "prod": prod,
    }

    msg = f"✅ **{name}** 배포 완료!\n🌐 {url}\n⏱️ {datetime.now().strftime('%H:%M:%S')}"
    _discord(msg)
    print(f"✅ 배포 완료: {url}")
    return result


def deploy_landing_page(repo_name: str, landing_html_path: Path, prod: bool = True) -> dict:
    """생성된 랜딩 페이지를 Vercel에 배포"""
    from bucky_landing_generator import generate, DEFAULT_CONFIG

    project_dir = ROOT / "generated" / "deployments" / repo_name.lower()
    project_dir.mkdir(parents=True, exist_ok=True)

    # HTML을 index.html로 복사
    import shutil
    shutil.copy(landing_html_path, project_dir / "index.html")

    # vercel.json 기본 설정
    vercel_cfg = {
        "name": repo_name.lower(),
        "version": 2,
        "routes": [{"src": "/(.*)", "dest": "/index.html"}],
    }
    (project_dir / "vercel.json").write_text(
        json.dumps(vercel_cfg, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    return deploy(project_dir, repo_name, prod)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python bucky_vercel_deploy.py <project_dir> [project_name]")
        sys.exit(1)
    result = deploy(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "")
    print(json.dumps(result, ensure_ascii=False, indent=2))
