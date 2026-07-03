#!/usr/bin/env python3
"""Send a restart signal for the home-PC Bucky bot supervisor."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import socket
import sys


ROOT = Path(__file__).parent.parent
SIGNAL_DIR = ROOT / "ObsidianVault" / "10_AgentBus" / "signals"
SIGNAL_FILE = SIGNAL_DIR / "bot_restart.signal"


def send_restart_signal(reason: str = "manual") -> None:
    SIGNAL_DIR.mkdir(parents=True, exist_ok=True)
    SIGNAL_FILE.write_text(
        f"ts={datetime.now().isoformat(timespec='seconds')}\n"
        f"reason={reason}\n"
        f"from={socket.gethostname()}\n",
        encoding="utf-8",
    )
    print(f"[Signal] Restart signal written: {SIGNAL_FILE}")
    print("[Signal] The home-PC supervisor will restart the bot when it sees this file.")
    print("[Signal] Canonical supervisor must be running: start_discord_bot.bat or scripts/start_discord_bot.ps1.")


if __name__ == "__main__":
    reason = sys.argv[1] if len(sys.argv) > 1 else "manual"
    send_restart_signal(reason)
