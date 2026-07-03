"""
pc_identity.py — 멀티PC 환경 충돌 방지 모듈

집 PC / 사무실 PC / 노트북이 동시에 실행될 때:
- PRIMARY PC(집 PC)만 G:\내 드라이브\ Vault에 직접 쓴다.
- SECONDARY PC는 로컬 스테이징에 먼저 쓰고 git push로 동기화.
- 모든 생성 파일에 pc_origin 태그를 삽입해 충돌 추적 가능.

설정 (.env):
  PC_ROLE=primary     # primary | secondary
  PC_NAME=home        # home | office | laptop
"""

import os
import socket
from pathlib import Path
from dotenv import load_dotenv

_ROOT = Path(__file__).parent.parent
load_dotenv(_ROOT / ".env", encoding="utf-8-sig", override=True)

PC_ROLE: str = os.getenv("PC_ROLE", "primary").strip().lower()   # primary | secondary
PC_NAME: str = os.getenv("PC_NAME", "home").strip().lower()      # home | office | laptop
_HOSTNAME: str = socket.gethostname()

# Secondary PC의 로컬 스테이징 경로
_STAGING_BASE = Path(os.getenv("LOCAL_STAGING_PATH", "C:/ai프로젝트/staging"))

# G:\내 드라이브\ Vault 경로 (primary 전용 쓰기 대상)
_VAULT_PATH = Path(os.getenv("VAULT_PATH", str(_ROOT / "ObsidianVault")))


def is_primary() -> bool:
    """이 PC가 Vault 직접 쓰기 권한을 가진 primary인가."""
    return PC_ROLE == "primary"


def can_write_vault() -> bool:
    """Vault에 직접 쓸 수 있는지 확인. secondary면 False."""
    return is_primary()


def get_write_path(relative: str) -> Path:
    """
    파일 저장 경로를 반환.
    - primary: Vault 내 실제 경로
    - secondary: 로컬 스테이징 경로 (git push로 동기화 필요)
    """
    if is_primary():
        return _VAULT_PATH / relative
    return _STAGING_BASE / relative


def tag_yaml(extra: dict | None = None) -> dict:
    """Obsidian 노트 YAML에 삽입할 PC 식별 태그."""
    tags = {"pc_origin": PC_NAME, "pc_role": PC_ROLE, "hostname": _HOSTNAME}
    if extra:
        tags.update(extra)
    return tags


def write_vault_file(relative_path: str, content: str, encoding: str = "utf-8") -> Path:
    """
    Vault 파일 안전 쓰기.
    - primary: 직접 쓰기
    - secondary: 로컬 스테이징에 쓰고 경고 출력
    반환: 실제로 쓴 Path
    """
    target = get_write_path(relative_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding=encoding)

    if not is_primary():
        print(
            f"[PCGuard] ⚠️ SECONDARY PC({PC_NAME}) — "
            f"스테이징에 저장됨: {target}\n"
            f"  동기화: git add . && git commit -m 'staging: {relative_path}' && git push",
            flush=True,
        )
    return target


def staging_summary() -> str:
    """스테이징에 쌓인 파일 목록 요약 (secondary PC 전용)."""
    if is_primary() or not _STAGING_BASE.exists():
        return ""
    files = list(_STAGING_BASE.rglob("*"))
    files = [f for f in files if f.is_file()]
    if not files:
        return "스테이징 비어있음."
    lines = [f"📂 스테이징 ({len(files)}개 — git push 필요):"]
    for f in files[:10]:
        lines.append(f"  • {f.relative_to(_STAGING_BASE)}")
    if len(files) > 10:
        lines.append(f"  … 외 {len(files)-10}개")
    return "\n".join(lines)


def print_identity() -> None:
    """봇 시작 시 PC 식별 정보 출력."""
    icon = {"home": "🏠", "office": "🏢", "laptop": "💻"}.get(PC_NAME, "🖥️")
    role_icon = "👑" if is_primary() else "🔒"
    print(
        f"[PCIdentity] {icon} {PC_NAME.upper()} ({_HOSTNAME}) "
        f"| {role_icon} {PC_ROLE.upper()} "
        f"| Vault 직접쓰기: {'허용' if is_primary() else '차단 → 스테이징'}",
        flush=True,
    )
