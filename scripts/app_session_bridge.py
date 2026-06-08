"""App Session Bridge — request/status file handler for Claude Code / Codex sessions.

Reads request files from data/app_session_requests/*.json (written by discord_bot intake consumer).
Writes status files to data/app_session_requests/<request_id>.status.json.

PC control (app launch, UI automation) is NOT performed here.
All actions require user approval. Manual action instructions are provided in status files.

Request format (written by discord_bot._process_intake_payload):
  type: "app_session_request"
  request_id: str
  target_app: "claude_code" | "codex"
  target_channel: str (Discord channel id)
  workspace_path: str
  repo_name: str
  handoff_path: str
  start_prompt: str
  action: "start" | "resume" | "stop" | "status"
  requires_user_approval: true
  execution_mode: "user_approved_pc_control"
  status: "pending_approval" | "approved" | "rejected"
  enqueued_at: float

Status format (written by this bridge after user approval):
  type: "app_session_status"
  request_id: str
  target_app: str
  status: "pending_approval" | "approved" | "running" | "done" | "blocked" | "rejected"
  opened_workspace: bool
  handoff_loaded: bool
  prompt_delivered: bool
  manual_action_required: bool
  blocker: str
  next_action: str
  updated_at: float
"""

import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REQUEST_DIR = ROOT / "data" / "app_session_requests"


def list_pending_requests() -> list[dict]:
    """Return all requests with status='pending_approval' sorted by enqueued_at."""
    REQUEST_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    for f in sorted(REQUEST_DIR.glob("*.json")):
        if f.stem.endswith(".status"):
            continue
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if data.get("type") == "app_session_request" and data.get("status") in ("pending_approval", "approved"):
            results.append(data)
    results.sort(key=lambda x: x.get("enqueued_at", 0))
    return results


def read_request(request_id: str) -> dict | None:
    """Read a single request file by request_id."""
    REQUEST_DIR.mkdir(parents=True, exist_ok=True)
    path = REQUEST_DIR / f"{request_id}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def write_status(request_id: str, status: str, *, opened_workspace: bool = False,
                 handoff_loaded: bool = False, prompt_delivered: bool = False,
                 manual_action_required: bool = True, blocker: str = "",
                 next_action: str = "") -> Path:
    """Write a status file for the given request_id."""
    REQUEST_DIR.mkdir(parents=True, exist_ok=True)
    path = REQUEST_DIR / f"{request_id}.status.json"
    payload = {
        "type": "app_session_status",
        "request_id": request_id,
        "status": status,
        "opened_workspace": opened_workspace,
        "handoff_loaded": handoff_loaded,
        "prompt_delivered": prompt_delivered,
        "manual_action_required": manual_action_required,
        "blocker": blocker,
        "next_action": next_action,
        "updated_at": time.time(),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def read_status(request_id: str) -> dict | None:
    """Read the status file for the given request_id."""
    path = REQUEST_DIR / f"{request_id}.status.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def approve_request(request_id: str, *, next_action: str = "") -> dict:
    """Mark a request as approved and generate manual instructions.

    Does NOT launch the app or perform PC control.
    Returns the status payload written.
    """
    req = read_request(request_id)
    if req is None:
        raise FileNotFoundError(f"Request not found: {request_id}")

    target_app = req.get("target_app", "claude_code")
    workspace = req.get("workspace_path", "")
    handoff = req.get("handoff_path", "")
    start_prompt = req.get("start_prompt", "")
    action = req.get("action", "start")

    if target_app == "claude_code":
        app_name = "Claude Code"
        open_cmd = f'claude "{workspace}"' if workspace else "claude ."
    else:
        app_name = "Codex"
        open_cmd = f'codex app "{workspace}"' if workspace else "codex app ."

    instructions = []
    if action in ("start", "resume"):
        if workspace:
            instructions.append(f"1. 터미널에서 실행: {open_cmd}")
        if handoff:
            instructions.append(f"2. 핸드오프 파일 읽기: {handoff}")
        if start_prompt:
            instructions.append(f"3. {app_name}에 아래 프롬프트 붙여넣기:\n   {start_prompt[:300]}")
    elif action == "stop":
        instructions.append(f"1. {app_name} 앱에서 현재 세션 저장 후 종료")
    elif action == "status":
        instructions.append(f"1. {app_name} 앱에서 현재 상태 확인")

    next_action_text = next_action or " → ".join(instructions) if instructions else f"{app_name} 앱에서 수동 실행 필요"

    req["status"] = "approved"
    req_path = REQUEST_DIR / f"{request_id}.json"
    req_path.write_text(json.dumps(req, ensure_ascii=False, indent=2), encoding="utf-8")

    return write_status(
        request_id,
        status="approved",
        manual_action_required=True,
        next_action=next_action_text,
    )


if __name__ == "__main__":
    pending = list_pending_requests()
    if not pending:
        print("대기 중인 앱 세션 요청 없음.")
    else:
        print(f"대기 중인 요청 {len(pending)}개:")
        for r in pending:
            app = "Claude Code" if r.get("target_app") == "claude_code" else "Codex"
            print(f"  [{r['request_id'][:8]}] {app} / {r.get('repo_name','?')} / action={r.get('action','?')}")
