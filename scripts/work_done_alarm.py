#!/usr/bin/env python3
"""Play a short local completion alarm for Codex/Bucky work."""

from __future__ import annotations

import argparse
import os
import platform
import sys
import time
from typing import TextIO


FALSE_VALUES = {"0", "false", "no", "off", "disabled"}


def alarm_enabled(env: dict[str, str] | None = None) -> bool:
    source = env if env is not None else os.environ
    value = source.get("WORK_DONE_ALARM_ENABLED", "1").strip().lower()
    return value not in FALSE_VALUES


def _clamp_int(value: int, *, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))


def play_terminal_bell(*, count: int, gap_ms: int, stream: TextIO | None = None) -> None:
    output = stream or sys.stdout
    for index in range(max(1, count)):
        output.write("\a")
        output.flush()
        if index < count - 1:
            time.sleep(max(0, gap_ms) / 1000)


def play_windows_beep(*, frequency: int, duration_ms: int, count: int, gap_ms: int) -> None:
    import winsound

    safe_frequency = _clamp_int(frequency, minimum=37, maximum=32767)
    safe_duration = _clamp_int(duration_ms, minimum=1, maximum=5000)
    for index in range(max(1, count)):
        winsound.Beep(safe_frequency, safe_duration)
        if index < count - 1:
            time.sleep(max(0, gap_ms) / 1000)


def play_alarm(*, frequency: int = 880, duration_ms: int = 180, count: int = 2, gap_ms: int = 80) -> str:
    if platform.system().lower() == "windows":
        try:
            play_windows_beep(
                frequency=frequency,
                duration_ms=duration_ms,
                count=count,
                gap_ms=gap_ms,
            )
            return "windows-beep"
        except Exception:
            play_terminal_bell(count=count, gap_ms=gap_ms)
            return "terminal-bell-fallback"

    play_terminal_bell(count=count, gap_ms=gap_ms)
    return "terminal-bell"


def main() -> int:
    parser = argparse.ArgumentParser(description="Play a short work-completion alarm.")
    parser.add_argument("--message", default="Work complete.", help="Completion message to print.")
    parser.add_argument("--frequency", type=int, default=880, help="Windows beep frequency in Hz.")
    parser.add_argument("--duration", type=int, default=180, help="Single beep duration in milliseconds.")
    parser.add_argument("--count", type=int, default=2, help="Number of beeps.")
    parser.add_argument("--gap", type=int, default=80, help="Gap between beeps in milliseconds.")
    parser.add_argument("--no-sound", action="store_true", help="Print only; do not play sound.")
    args = parser.parse_args()

    print(f"[WorkDone] {args.message}", flush=True)

    if args.no_sound:
        print("[WorkDone] Alarm skipped by --no-sound.", flush=True)
        return 0

    if not alarm_enabled():
        print("[WorkDone] Alarm disabled by WORK_DONE_ALARM_ENABLED.", flush=True)
        return 0

    mode = play_alarm(
        frequency=args.frequency,
        duration_ms=args.duration,
        count=args.count,
        gap_ms=args.gap,
    )
    print(f"[WorkDone] Alarm sent: {mode}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
