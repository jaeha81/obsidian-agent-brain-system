r"""Multi-PC identity guard for the Obsidian Agent Brain System.

Home PC, office PC, and laptop can run the system at the same time.

Rules:
- Only the registered home primary PC may write directly to the canonical Vault.
- Secondary PCs write to local staging first, then sync through Git.
- Generated files can be tagged with pc_origin, pc_role, and hostname.

Configuration in .env:
  PC_ROLE=primary      # primary | secondary
  PC_NAME=home         # home | office | laptop
  LOCAL_STAGING_PATH=C:/ai-projects/staging/obsidian-agent-brain-system
"""

from __future__ import annotations

import os
import socket
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional runtime dependency
    load_dotenv = None


_ROOT = Path(__file__).parent.parent
if load_dotenv:
    load_dotenv(_ROOT / ".env", encoding="utf-8", override=True)

_KNOWN_PC_ROLES = {"primary", "secondary"}
_KNOWN_PC_NAMES = {"home", "office", "laptop"}


def _normalize_pc_role(value: str | None) -> str:
    role = (value or "").strip().lower()
    return role if role in _KNOWN_PC_ROLES else "secondary"


def _normalize_pc_name(value: str | None) -> str:
    name = (value or "").strip().lower()
    return name if name in _KNOWN_PC_NAMES else "unknown"


PC_ROLE: str = _normalize_pc_role(os.getenv("PC_ROLE"))
PC_NAME: str = _normalize_pc_name(os.getenv("PC_NAME"))
_HOSTNAME: str = socket.gethostname()

_STAGING_BASE = Path(
    os.getenv("LOCAL_STAGING_PATH", "C:/ai-projects/staging/obsidian-agent-brain-system")
)
_VAULT_PATH = Path(os.getenv("VAULT_PATH", str(_ROOT / "ObsidianVault")))


def is_primary() -> bool:
    """Return True only for the registered canonical writer."""
    return PC_ROLE == "primary" and PC_NAME == "home"


def can_write_vault() -> bool:
    """Return whether this PC may write directly to the canonical Vault."""
    return is_primary()


def get_write_path(relative: str) -> Path:
    """Return the direct Vault path for primary, otherwise the staging path."""
    if is_primary():
        return _VAULT_PATH / relative
    return _STAGING_BASE / relative


def tag_yaml(extra: dict | None = None) -> dict:
    """Return origin metadata for Obsidian note frontmatter."""
    tags = {"pc_origin": PC_NAME, "pc_role": PC_ROLE, "hostname": _HOSTNAME}
    if extra:
        tags.update(extra)
    return tags


def write_vault_file(relative_path: str, content: str, encoding: str = "utf-8") -> Path:
    """Write safely to the Vault on primary PCs or to staging on secondary PCs."""
    target = get_write_path(relative_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding=encoding)

    if not is_primary():
        print(
            f"[PCGuard] WARNING SECONDARY PC({PC_NAME}) - saved to staging: {target}\n"
            f"  sync: git add . && git commit -m 'staging: {relative_path}' && git push",
            flush=True,
        )
    return target


def staging_summary() -> str:
    """Return a short summary of staged files for secondary PCs."""
    if is_primary() or not _STAGING_BASE.exists():
        return ""
    files = [path for path in _STAGING_BASE.rglob("*") if path.is_file()]
    if not files:
        return "staging is empty."

    lines = [f"staging has {len(files)} file(s) pending sync:"]
    for path in files[:10]:
        lines.append(f"  - {path.relative_to(_STAGING_BASE)}")
    if len(files) > 10:
        lines.append(f"  - ... {len(files) - 10} more")
    return "\n".join(lines)


def print_identity() -> None:
    """Print PC identity at bot startup."""
    label = {"home": "HOME", "office": "OFFICE", "laptop": "LAPTOP"}.get(PC_NAME, "UNKNOWN")
    role_label = "PRIMARY" if is_primary() else "SECONDARY"
    print(
        f"[PCIdentity] {label} ({_HOSTNAME}) "
        f"| {role_label} "
        f"| Vault direct write: {'allowed' if is_primary() else 'blocked -> staging'}",
        flush=True,
    )
