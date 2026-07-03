from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent.parent
VOICE_LOG_DIR = ROOT / "ObsidianVault" / "10_AgentBus" / "voice-logs"

_FRONTMATTER = """\
---
type: voice-log
date: {date}
---

"""

_SEPARATOR = "---\n"


class ObsidianVoiceLogger:

    def get_today_log_path(self) -> Path:
        date_str = datetime.now().strftime("%Y-%m-%d")
        return VOICE_LOG_DIR / f"{date_str}.md"

    def _ensure_file(self, path: Path) -> None:
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            date_str = path.stem
            path.write_text(_FRONTMATTER.format(date=date_str), encoding="utf-8")

    def _append(self, path: Path, block: str) -> None:
        self._ensure_file(path)
        with path.open("a", encoding="utf-8") as f:
            f.write(block)

    @staticmethod
    def _now_hms() -> str:
        return datetime.now().strftime("%H:%M:%S")

    def log_final(self, event: dict, agent: str, result: dict) -> None:
        path = self.get_today_log_path()
        ts = self._now_hms()
        source = event.get("source", "local")
        text = event.get("text", "")
        confidence = event.get("confidence", 0.0)
        latency_ms = event.get("latency_ms", 0)
        status = result.get("status", "unknown")
        marker = "success" if status == "ok" else status
        icon = "✅" if status == "ok" else "❌"

        block = (
            f"## {ts} — [source: {source}]\n"
            f"**Text:** {text}\n"
            f"**Confidence:** {confidence} | **Latency:** {latency_ms}ms | **Agent:** {agent}\n"
            f"**Result:** {icon} {marker}\n"
            f"{_SEPARATOR}"
        )
        self._append(path, block)

    def log_failover(self, reason: str) -> None:
        path = self.get_today_log_path()
        ts = self._now_hms()
        block = (
            f"## {ts} — ⚠️ FAILOVER\n"
            f"**Reason:** {reason}\n"
            f"{_SEPARATOR}"
        )
        self._append(path, block)

    def log_error(self, event: dict, agent: str, error: str) -> None:
        path = self.get_today_log_path()
        ts = self._now_hms()
        source = event.get("source", "local")
        text = event.get("text", "")

        block = (
            f"## {ts} — [source: {source}]\n"
            f"**Text:** {text}\n"
            f"**Agent:** {agent}\n"
            f"**Result:** ❌ ERROR — {error}\n"
            f"{_SEPARATOR}"
        )
        self._append(path, block)


logger = ObsidianVoiceLogger()
