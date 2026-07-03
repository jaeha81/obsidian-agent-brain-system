#!/usr/bin/env python3
"""Start the local docs preview used by the Codex in-app browser."""

from __future__ import annotations

import argparse
import http.client
import os
import socket
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT / "docs"
HOST = "127.0.0.1"
DEFAULT_PORT = 4173
STARTUP_TIMEOUT_SECONDS = 5.0


def is_port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) == 0


def can_fetch_index(host: str, port: int) -> bool:
    try:
        conn = http.client.HTTPConnection(host, port, timeout=1.0)
        conn.request("GET", "/index.html")
        response = conn.getresponse()
        response.read(256)
        return response.status < 500
    except OSError:
        return False
    finally:
        try:
            conn.close()
        except UnboundLocalError:
            pass


def start_server(host: str, port: int) -> subprocess.Popen[bytes]:
    cmd = [
        sys.executable,
        "-m",
        "http.server",
        str(port),
        "--bind",
        host,
        "--directory",
        str(DOCS_DIR),
    ]
    creationflags = 0
    if os.name == "nt":
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return subprocess.Popen(
        cmd,
        cwd=str(ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags,
    )


def wait_for_index(host: str, port: int) -> bool:
    deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if can_fetch_index(host, port):
            return True
        time.sleep(0.2)
    return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Start the local dashboard preview for Codex in-app browser verification."
    )
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()

    if not DOCS_DIR.exists():
        print(f"ERROR: docs directory not found: {DOCS_DIR}", file=sys.stderr)
        return 1

    started = False
    if not is_port_open(args.host, args.port):
        start_server(args.host, args.port)
        started = True

    ready = wait_for_index(args.host, args.port)
    url = f"http://{args.host}:{args.port}/index.html"

    if not ready:
        print(
            f"WARNING: port {args.port} is open, but /index.html did not respond cleanly.",
            file=sys.stderr,
        )

    state = "started" if started else "already_running"
    print(f"CODEX_PREVIEW_STATE={state}")
    print(f"CODEX_PREVIEW_URL={url}")
    print("CODEX_PREVIEW_BROWSER=Codex in-app browser")
    print("CODEX_PREVIEW_LOGIN_COOKIE=bucky_auth=preview")
    return 0 if ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
