#!/usr/bin/env python3
"""
Docker 3-PC 환경 동기화 설정
자동으로 현재 PC를 감지하고 docker/.env를 설정한다.

PC 감지 기준:
  집 PC   → D:/ai프로젝트 존재
  노트북  → whoami 결과에 'info' 포함
  사무실  → whoami 결과에 '설계4' 포함

사용법:
  python scripts/docker_sync.py --setup         # 환경 감지 후 .env 생성
  python scripts/docker_sync.py --start         # setup + docker compose up -d
  python scripts/docker_sync.py --start --full  # 모든 profile 포함
  python scripts/docker_sync.py --status        # 컨테이너 상태 확인
  python scripts/docker_sync.py --stop          # 컨테이너 중지
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# ─────────────────────────────────────────────
# 경로 설정
# ─────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
DOCKER_DIR = REPO_ROOT / "docker"
COMPOSE_FILE = DOCKER_DIR / "docker-compose.yml"
ENV_FILE = DOCKER_DIR / ".env"
BACKUP_DIR = REPO_ROOT / ".agent" / "backup"

# ─────────────────────────────────────────────
# PC별 설정 정의
# ─────────────────────────────────────────────
PC_CONFIGS: dict[str, dict[str, str]] = {
    "home": {
        "PC_ENV": "home",
        "VAULT_BASE_PATH": "G:/내 드라이브/obsidian-agent-brain-system/ObsidianVault",
        "LOCAL_AI_PATH": "D:/ai프로젝트",
        "GDRIVE_PATH": "G:/내 드라이브",
    },
    "laptop": {
        "PC_ENV": "laptop",
        "VAULT_BASE_PATH": "G:/내 드라이브/obsidian-agent-brain-system/ObsidianVault",
        "LOCAL_AI_PATH": "C:/ai프로젝트",
        "GDRIVE_PATH": "G:/내 드라이브",
    },
    "office": {
        "PC_ENV": "office",
        "VAULT_BASE_PATH": "G:/내 드라이브/obsidian-agent-brain-system/ObsidianVault",
        "LOCAL_AI_PATH": "C:/ai프로젝트",
        "GDRIVE_PATH": "G:/내 드라이브",
    },
}

PC_LABELS: dict[str, str] = {
    "home":   "🏠 집 PC",
    "laptop": "💻 노트북",
    "office": "🏢 사무실 PC",
}

# 사용자가 보존해야 할 키 (API 키 등)
USER_PRESERVED_KEYS = {
    "ANTHROPIC_API_KEY",
    "CLAUDE_API_KEY",
    "OPENAI_API_KEY",
    "GITHUB_TOKEN",
    "GITHUB_USERNAME",
    "DISCORD_BOT_TOKEN",
    "DISCORD_WEBHOOK_URL",
    "DISCORD_CHANNEL_ID",
    "REDIS_URL",
    "LOG_LEVEL",
    "DISTILLER_BATCH_SIZE",
    "DISTILLER_RETRY_MAX",
    "DISTILLER_INTERVAL_HOURS",
}


# ─────────────────────────────────────────────
# PC 감지
# ─────────────────────────────────────────────

def detect_pc() -> tuple[str, str]:
    """
    현재 PC 환경을 감지한다.
    반환: (pc_type, reason)  pc_type ∈ {'home', 'laptop', 'office'}
    """
    # 1. 집 PC: D:/ai프로젝트 존재 여부
    home_marker = Path("D:/ai프로젝트")
    if home_marker.exists():
        return "home", "D:/ai프로젝트 존재 감지"

    # 2. whoami로 노트북/사무실 구분
    try:
        result = subprocess.run(
            ["whoami"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
        )
        whoami_output = (result.stdout or "").strip() + (result.stderr or "").strip()
    except Exception as e:
        whoami_output = ""
        print(f"[WARN] whoami 실행 실패: {e}", file=sys.stderr)

    if "설계4" in whoami_output:
        return "office", f"whoami에 '설계4' 포함: {whoami_output!r}"

    if "info" in whoami_output.lower():
        return "laptop", f"whoami에 'info' 포함: {whoami_output!r}"

    # 3. 환경변수 fallback
    env_val = os.environ.get("PC_ENV", "").lower()
    if env_val in PC_CONFIGS:
        return env_val, f"PC_ENV 환경변수 사용: {env_val}"

    # 4. fallback → laptop
    print(f"[WARN] PC 감지 실패 (whoami: {whoami_output!r}), laptop으로 fallback", file=sys.stderr)
    return "laptop", f"감지 실패 — laptop fallback"


# ─────────────────────────────────────────────
# .env 파싱 / 생성
# ─────────────────────────────────────────────

def parse_env_file(path: Path) -> dict[str, str]:
    """기존 .env 파일을 파싱하여 key-value dict 반환."""
    result: dict[str, str] = {}
    if not path.exists():
        return result
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$", line)
        if match:
            key, val = match.group(1), match.group(2)
            # 따옴표 제거
            if (val.startswith('"') and val.endswith('"')) or (
                val.startswith("'") and val.endswith("'")
            ):
                val = val[1:-1]
            result[key] = val
    return result


def build_env_content(pc_type: str, existing: dict[str, str]) -> str:
    """
    pc_type 설정을 기반으로 .env 내용 생성.
    기존 파일에서 USER_PRESERVED_KEYS 값은 그대로 보존.
    """
    config = PC_CONFIGS[pc_type]
    label = PC_LABELS[pc_type]
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines: list[str] = [
        f"# docker/.env — {label}",
        f"# 생성: {now_str} by docker_sync.py",
        f"# 직접 수정 가능하지만 --setup 재실행 시 'PC 환경' 섹션은 덮어씁니다.",
        f"# API 키 등 '사용자 설정' 섹션은 자동으로 보존됩니다.",
        "",
        "# ── PC 환경 (자동 감지·덮어씌워짐) ─────────────",
    ]
    for key, val in config.items():
        lines.append(f"{key}={val}")

    lines += [
        "",
        "# ── 사용자 설정 (보존됨) ────────────────────────",
    ]
    for key in sorted(USER_PRESERVED_KEYS - set(config.keys())):
        val = existing.get(key, "")
        lines.append(f"{key}={val}")

    # 기존 .env에만 있는 추가 키 보존 (PC_CONFIGS 키, USER_PRESERVED_KEYS 제외)
    extra_keys = {
        k: v
        for k, v in existing.items()
        if k not in config and k not in USER_PRESERVED_KEYS
    }
    if extra_keys:
        lines += ["", "# ── 기타 보존 설정 ──────────────────────────────"]
        for key in sorted(extra_keys.keys()):
            lines.append(f"{key}={extra_keys[key]}")

    lines.append("")
    return "\n".join(lines)


def backup_env(env_path: Path) -> Path | None:
    """기존 .env 파일을 타임스탬프 백업 폴더에 복사. 백업 경로 반환."""
    if not env_path.exists():
        return None
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = BACKUP_DIR / ts / ".env"
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(env_path, backup_path)
    return backup_path


# ─────────────────────────────────────────────
# 명령 구현
# ─────────────────────────────────────────────

def cmd_setup() -> str:
    """PC 감지 후 docker/.env 생성/업데이트. 현재 pc_type 반환."""
    pc_type, reason = detect_pc()
    label = PC_LABELS[pc_type]
    print(f"[INFO] PC 감지: {label} — {reason}")

    # 기존 .env 파싱 (보존 키 추출)
    existing = parse_env_file(ENV_FILE)

    # 백업
    backup_path = backup_env(ENV_FILE)
    if backup_path:
        print(f"[INFO] 기존 .env 백업: {backup_path}")

    # 새 .env 작성
    DOCKER_DIR.mkdir(parents=True, exist_ok=True)
    content = build_env_content(pc_type, existing)
    ENV_FILE.write_text(content, encoding="utf-8")

    cfg = PC_CONFIGS[pc_type]
    print(f"[OK] docker/.env 생성 완료 ({pc_type})")
    print(f"     VAULT_BASE_PATH = {cfg['VAULT_BASE_PATH']}")
    print(f"     LOCAL_AI_PATH   = {cfg['LOCAL_AI_PATH']}")
    print(f"     GDRIVE_PATH     = {cfg['GDRIVE_PATH']}")

    return pc_type


def _assert_docker() -> None:
    if not shutil.which("docker"):
        print("[ERROR] docker 명령을 찾을 수 없습니다. Docker Desktop이 실행 중인지 확인하세요.", file=sys.stderr)
        sys.exit(1)


def _assert_env_exists() -> None:
    if not ENV_FILE.exists():
        print(f"[ERROR] {ENV_FILE} 파일이 없습니다. 먼저 --setup을 실행하세요.", file=sys.stderr)
        sys.exit(1)


def run_compose(compose_args: list[str]) -> int:
    """docker compose 명령 실행 (cwd=docker/). 종료 코드 반환."""
    cmd = ["docker", "compose"] + compose_args
    print(f"[RUN] {' '.join(cmd)}  (cwd={DOCKER_DIR})")
    result = subprocess.run(cmd, cwd=str(DOCKER_DIR))
    return result.returncode


def cmd_start(full: bool = False) -> None:
    """setup 후 docker compose up -d 실행."""
    _assert_docker()
    cmd_setup()
    _assert_env_exists()

    compose_args = ["up", "-d", "--build"]
    if full:
        compose_args = ["--profile", "full"] + compose_args

    rc = run_compose(compose_args)
    if rc == 0:
        print("[OK] 컨테이너 시작 완료")
        print("     상태 확인: python scripts/docker_sync.py --status")
    else:
        print(f"[ERROR] docker compose up 실패 (exit code {rc})", file=sys.stderr)
        sys.exit(rc)


def cmd_status() -> None:
    """docker compose ps 실행."""
    _assert_docker()
    _assert_env_exists()
    rc = run_compose(["ps"])
    sys.exit(rc)


def cmd_stop() -> None:
    """docker compose down 실행."""
    _assert_docker()
    _assert_env_exists()
    rc = run_compose(["down"])
    if rc == 0:
        print("[OK] 컨테이너 중지 완료")
    else:
        print(f"[ERROR] docker compose down 실패 (exit code {rc})", file=sys.stderr)
        sys.exit(rc)


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="docker_sync.py",
        description="Docker 3-PC 환경 동기화 설정",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python scripts/docker_sync.py --setup         # 환경 감지 후 .env 생성
  python scripts/docker_sync.py --start         # setup + docker compose up -d
  python scripts/docker_sync.py --start --full  # 모든 profile 포함
  python scripts/docker_sync.py --status        # 컨테이너 상태 확인
  python scripts/docker_sync.py --stop          # 컨테이너 중지
        """,
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--setup",  action="store_true", help="PC 감지 후 docker/.env 생성")
    group.add_argument("--start",  action="store_true", help="setup + docker compose up -d")
    group.add_argument("--status", action="store_true", help="컨테이너 상태 확인 (docker compose ps)")
    group.add_argument("--stop",   action="store_true", help="컨테이너 중지 (docker compose down)")

    parser.add_argument(
        "--full",
        action="store_true",
        help="--start 시 모든 profile 포함 (--profile full)",
    )

    args = parser.parse_args()

    if args.status:
        cmd_status()
    elif args.stop:
        cmd_stop()
    elif args.start:
        cmd_start(full=args.full)
    elif args.setup:
        cmd_setup()


if __name__ == "__main__":
    main()
