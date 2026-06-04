"""Generate the public Daily Plus operations dashboard.

The dashboard is intentionally static so it can be served by GitHub Pages and
opened directly from the local workspace. It reads the latest ChatGPT Pulse
capture, the Pulse Evolution report, and Bucky's AgentBus result.
"""

from __future__ import annotations

import argparse
import html
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VAULT = ROOT / "ObsidianVault"
DOCS = ROOT / "docs"
SESSION_LOG_PATH = VAULT / "00_UPGRADE" / "daily-plus-session-log.md"


@dataclass
class Candidate:
    card: int
    priority: str
    title: str
    category: str
    owner: str
    target_area: str
    action: str
    evidence: str
    status: str = "staged"


@dataclass
class DailySnapshot:
    date: str
    cards: int
    candidates: int
    queued: int
    approvals: int
    applied: int
    avg_efficiency: int
    avg_compatibility: int


CATEGORY_PROFILES: dict[str, dict[str, object]] = {
    "verification": {
        "label": "검증 자동화",
        "efficiency": 88,
        "compatibility": 90,
        "risk": "low",
        "next": "반복 검수 체크리스트나 리뷰 프로토콜로 정리하면 바로 효율이 난다.",
    },
    "obsidian-queue": {
        "label": "Obsidian 큐",
        "efficiency": 84,
        "compatibility": 86,
        "risk": "low",
        "next": "AgentBus 템플릿 또는 inbox 규칙으로 큐에 올린 뒤 중복 방지를 확인한다.",
    },
    "voice-pipeline": {
        "label": "음성 파이프라인",
        "efficiency": 82,
        "compatibility": 64,
        "risk": "high",
        "next": "실시간 음성/ASR/비용 경계가 있어 사용자 승인 후 별도 검증 계획이 필요하다.",
    },
    "agent-prompting": {
        "label": "에이전트 프롬프트",
        "efficiency": 78,
        "compatibility": 62,
        "risk": "medium",
        "next": "Bucky/Claude/Codex 역할 경계를 건드리므로 review request로 먼저 검토한다.",
    },
    "experiment": {
        "label": "실험 후보",
        "efficiency": 58,
        "compatibility": 76,
        "risk": "medium",
        "next": "사업 실험 후보로 보관하고, 구현 전 기대효과와 측정 지표를 정한다.",
    },
    "command-payload": {
        "label": "명령 페이로드",
        "efficiency": 86,
        "compatibility": 70,
        "risk": "medium",
        "next": "명령 구조, idempotency, 재시도 규칙을 먼저 문서화한다.",
    },
    "knowledge-candidate": {
        "label": "지식 후보",
        "efficiency": 65,
        "compatibility": 82,
        "risk": "low",
        "next": "지식 노트로 보존하고 추후 우선순위가 생기면 큐로 승격한다.",
    },
}


STATUS_LABELS = {
    "applied": "구현됨",
    "queued": "큐 대기",
    "needs-user-approval": "승인 필요",
    "rejected": "보류/거절",
    "staged": "스테이징",
    "done": "처리 완료",
}


DASHBOARD_INTERACTION_CSS = """
  .command-actions { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; }
  .command-btn { border: 1px solid var(--line); border-radius: 8px; min-height: 42px; padding: 8px 10px; background: #fff; color: var(--ink); font-weight: 700; font-size: 13px; cursor: pointer; }
  .command-btn:hover, .command-btn:focus { outline: none; border-color: var(--blue); box-shadow: 0 0 0 3px rgba(37,99,235,.12); }
  .command-btn.approve { color: var(--amber); background: #fff7ed; border-color: #fed7aa; }
  .command-btn.implement { color: var(--green); background: #f0fdf4; border-color: #bbf7d0; }
  .command-btn.queue { color: var(--teal); background: #f0fdfa; border-color: #99f6e4; }
  .command-tray { position: fixed; left: clamp(12px, 3vw, 28px); right: clamp(12px, 3vw, 28px); bottom: 14px; z-index: 50; background: #0f172a; color: #e5e7eb; border: 1px solid #334155; border-radius: 10px; box-shadow: 0 18px 48px rgba(15,23,42,.35); padding: 14px; display: grid; gap: 10px; transform: translateY(calc(100% + 32px)); opacity: 0; pointer-events: none; transition: transform .18s ease, opacity .18s ease; }
  .command-tray.show { transform: translateY(0); opacity: 1; pointer-events: auto; }
  .command-tray strong { color: #fff; }
  .command-tray textarea { width: 100%; min-height: 126px; resize: vertical; border: 1px solid #475569; border-radius: 8px; background: #020617; color: #e5e7eb; padding: 10px; font: 12px/1.5 Consolas, "Segoe UI Mono", monospace; }
  .tray-actions { display: flex; gap: 8px; flex-wrap: wrap; justify-content: flex-end; }
  .tray-actions button { border: 1px solid #475569; border-radius: 8px; background: #1e293b; color: #e5e7eb; min-height: 38px; padding: 8px 12px; cursor: pointer; font-weight: 700; }
  .tray-actions button:hover, .tray-actions button:focus { outline: none; border-color: #93c5fd; }
  .message-box { display: grid; gap: 10px; }
  .message-box textarea, .message-box input { width: 100%; border: 1px solid var(--line); border-radius: 8px; background: #fff; color: var(--ink); padding: 11px 12px; font: 14px/1.5 "Segoe UI", system-ui, sans-serif; }
  .message-box textarea { min-height: 104px; resize: vertical; }
  .message-box textarea:focus, .message-box input:focus { outline: none; border-color: var(--blue); box-shadow: 0 0 0 3px rgba(37,99,235,.12); }
  .message-actions { display: flex; gap: 8px; flex-wrap: wrap; justify-content: flex-end; }
  .message-actions button { border: 1px solid var(--line); border-radius: 8px; min-height: 40px; padding: 8px 13px; cursor: pointer; font-weight: 800; background: #fff; color: var(--ink); }
  .message-actions .send { background: #eff6ff; color: var(--blue); border-color: #bfdbfe; }
  .message-actions .copy { background: #f8fafc; color: #475569; }
  .knowledge-intake { display: grid; gap: 10px; }
  .knowledge-intake .intake-grid { display: grid; grid-template-columns: minmax(150px, 220px) 1fr; gap: 10px; }
  .knowledge-intake textarea, .knowledge-intake input, .knowledge-intake select { width: 100%; border: 1px solid var(--line); border-radius: 8px; background: #fff; color: var(--ink); padding: 11px 12px; font: 14px/1.5 "Segoe UI", system-ui, sans-serif; }
  .knowledge-intake textarea { min-height: 132px; resize: vertical; }
  .knowledge-intake textarea:focus, .knowledge-intake input:focus, .knowledge-intake select:focus { outline: none; border-color: var(--teal); box-shadow: 0 0 0 3px rgba(15,118,110,.12); }
  .knowledge-intake .file-row { display: grid; grid-template-columns: minmax(140px, 220px) 1fr; gap: 10px; }
  .intake-actions { display: flex; gap: 8px; flex-wrap: wrap; justify-content: flex-end; }
  .intake-actions button { border: 1px solid var(--line); border-radius: 8px; min-height: 40px; padding: 8px 13px; cursor: pointer; font-weight: 800; background: #fff; color: var(--ink); }
  .intake-actions .send-discord { background: #f0fdfa; color: var(--teal); border-color: #99f6e4; }
  .intake-actions .copy { background: #f8fafc; color: #475569; }
  .toast { position: fixed; left: 50%; bottom: 12px; transform: translateX(-50%); z-index: 60; background: #0f172a; color: #fff; border-radius: 999px; padding: 10px 14px; font-size: 13px; box-shadow: 0 10px 30px rgba(15,23,42,.28); opacity: 0; pointer-events: none; transition: opacity .16s ease; }
  .toast.show { opacity: 1; }
"""


DASHBOARD_INTERACTION_JS = """
<script>
(function () {
  var DEFAULT_BUCKY_ENDPOINT = "http://localhost:8765";
  var ENDPOINT_KEY = "dailyPlusBuckyOsIntakeUrl";
  var DISCORD_WEBHOOK_KEY = "bucky-webhook";
  var DISCORD_WEBHOOK_NAME_KEY = "bucky-wh-name";
  var DAILY_PLUS_SESSION_KEY = "dailyPlusBuckySessionId";
  var ACTIVE_COMMAND = null;

  function showToast(message) {
    var toast = document.querySelector(".toast");
    if (!toast) {
      toast = document.createElement("div");
      toast.className = "toast";
      document.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.classList.add("show");
    window.clearTimeout(showToast._timer);
    showToast._timer = window.setTimeout(function () {
      toast.classList.remove("show");
    }, 1800);
  }

  function endpointValue() {
    var input = document.getElementById("buckyEndpoint");
    var value = input && input.value ? input.value.trim() : "";
    if (!value) value = localStorage.getItem(ENDPOINT_KEY) || DEFAULT_BUCKY_ENDPOINT;
    if (input) input.value = value;
    localStorage.setItem(ENDPOINT_KEY, value);
    return value;
  }

  function dailyPlusSessionId() {
    var current = localStorage.getItem(DAILY_PLUS_SESSION_KEY) || "";
    if (!current) {
      current = "daily-plus-intake-" + new Date().toISOString().slice(0, 10).replace(/-/g, "") + "-" + Math.random().toString(36).slice(2, 8);
      localStorage.setItem(DAILY_PLUS_SESSION_KEY, current);
    }
    return current;
  }

  function setMessageStatus(message, isError) {
    var el = document.getElementById("messageStatus");
    if (!el) return;
    el.textContent = message;
    el.style.color = isError ? "var(--red)" : "var(--muted)";
  }

  function copyPayload(payload) {
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(payload).then(function () {
        showToast("복사 완료");
      });
    }
    var textarea = document.getElementById("commandPayload") || document.getElementById("buckyMessage");
    if (textarea) {
      textarea.focus();
      textarea.select();
      document.execCommand("copy");
      showToast("복사 완료");
      return Promise.resolve();
    }
    return Promise.reject(new Error("복사할 텍스트 영역이 없습니다."));
  }

  function payloadForBuckyOS(body, action) {
    return {
      type: "daily_plus_user_command",
      source: "daily-plus-dashboard",
      target: "Bucky",
      session_id: dailyPlusSessionId(),
      channel_role: "daily-plus-intake",
      follow_up_state: "awaiting_user_instruction",
      action: action || "message",
      createdAt: new Date().toISOString(),
      body: body
    };
  }

  async function postToBucky(body, action) {
    var endpoint = endpointValue();
    if (!endpoint) throw new Error("Bucky OS 수신 URL이 필요합니다.");

    var payload = payloadForBuckyOS(body, action || "message");
    var json = JSON.stringify(payload);

    try {
      var response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: json
      });
      var data = {};
      try { data = await response.json(); } catch (_) {}
      if (!response.ok) throw new Error(data.error || ("HTTP " + response.status));
      return { method: "fetch" };
    } catch (error) {
      if (navigator.sendBeacon) {
        var blob = new Blob([json], { type: "text/plain;charset=UTF-8" });
        if (navigator.sendBeacon(endpoint, blob)) {
          return { method: "beacon" };
        }
      }
      throw error;
    }
  }

  async function postDiscordWebhookWithFiles(content, files) {
    var url = localStorage.getItem(DISCORD_WEBHOOK_KEY) || "";
    var username = localStorage.getItem(DISCORD_WEBHOOK_NAME_KEY) || "JH Daily Plus";
    if (!url) throw new Error("Discord webhook URL is not configured.");

    var safeFiles = Array.prototype.slice.call(files || [], 0, 10);
    if (!safeFiles.length) {
      var response = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: content, username: username })
      });
      if (!response.ok) throw new Error("Discord HTTP " + response.status);
      return { files: 0 };
    }

    var form = new FormData();
    form.append("payload_json", JSON.stringify({ content: content, username: username }));
    safeFiles.forEach(function (file, index) {
      form.append("files[" + index + "]", file, file.name);
    });
    var uploadResponse = await fetch(url, { method: "POST", body: form });
    if (!uploadResponse.ok) throw new Error("Discord upload HTTP " + uploadResponse.status);
    return { files: safeFiles.length };
  }

  function buildKnowledgeIntakePayload() {
    var typeEl = document.getElementById("dailyPlusIntakeType");
    var titleEl = document.getElementById("dailyPlusIntakeTitle");
    var bodyEl = document.getElementById("dailyPlusIntakeBody");
    var tagsEl = document.getElementById("dailyPlusIntakeTags");
    var filesEl = document.getElementById("dailyPlusIntakeFiles");
    var type = typeEl ? typeEl.value : "auto";
    var title = titleEl ? titleEl.value.trim() : "";
    var body = bodyEl ? bodyEl.value.trim() : "";
    var tags = tagsEl ? tagsEl.value.trim() : "";
    var files = filesEl ? Array.prototype.slice.call(filesEl.files || [], 0, 10) : [];
    var fileLines = files.map(function (file) {
      return "- " + file.name + " (" + Math.ceil(file.size / 1024) + " KB)";
    });
    var isSingleUrl = /^https?:\\/\\/\\S+$/i.test(body);
    var command = isSingleUrl ? "!capture " + body : "!capture " + (title || body || "[Daily Plus dashboard file intake]");

    return [
      command,
      "",
      "[Daily Plus Knowledge Intake]",
      "type: " + type,
      "title: " + (title || "(untitled)"),
      "tags: " + (tags || "(none)"),
      "source: daily-plus-dashboard",
      "session_id: " + dailyPlusSessionId(),
      "channel_role: daily-plus-intake",
      "follow_up_state: awaiting_user_instruction",
      "requested_response: analyze_and_brief_then_wait",
      fileLines.length ? "files:\\n" + fileLines.join("\\n") : "files: (none)",
      "",
      body && !isSingleUrl ? body : ""
    ].join("\\n").trim();
  }

  function commandText(action, card) {
    var title = (card.querySelector("h3") || {}).textContent || "Daily Plus 후보";
    var meta = (card.querySelector(".meta") || {}).textContent || "";
    var next = (card.querySelector(".next") || {}).textContent || "";
    var actionLine = {
      approve: "이 후보를 사용자 승인 완료로 처리하고 다음 실행 큐에 등록해.",
      implement: "이 후보를 구현 착수 대상으로 등록하고 필요한 작업을 분해해.",
      queue: "이 후보를 보류 후보로 유지하고 다음 검토 큐에 정리해."
    }[action] || "이 후보를 검토해.";

    return [
      "[Bucky Daily Plus]",
      "action: " + action,
      "source: daily-plus-dashboard",
      "target: Bucky",
      "card: " + title.trim(),
      "meta: " + meta.trim(),
      "request: " + actionLine,
      "next: " + next.trim()
    ].join("\\n");
  }

  function ensureTray() {
    var tray = document.querySelector(".command-tray");
    if (tray) return tray;
    tray = document.createElement("div");
    tray.className = "command-tray";
    tray.innerHTML = [
      "<strong id=\\"commandTrayTitle\\">지시문 준비됨</strong>",
      "<textarea id=\\"commandPayload\\" readonly></textarea>",
      "<div class=\\"tray-actions\\">",
      "<button type=\\"button\\" data-tray=\\"send\\">Bucky 전송</button>",
      "<button type=\\"button\\" data-tray=\\"copy\\">복사</button>",
      "<button type=\\"button\\" data-tray=\\"close\\">닫기</button>",
      "</div>"
    ].join("");
    document.body.appendChild(tray);
    tray.addEventListener("click", async function (event) {
      var action = event.target && event.target.getAttribute("data-tray");
      if (!action) return;
      var payloadEl = document.getElementById("commandPayload");
      var payload = payloadEl ? payloadEl.value : "";
      if (action === "close") {
        tray.classList.remove("show");
        return;
      }
      if (action === "copy") {
        await copyPayload(payload);
        return;
      }
      if (action === "send") {
        var sendBtn = tray.querySelector("[data-tray='send']");
        if (sendBtn) { sendBtn.disabled = true; sendBtn.textContent = "전송 중..."; }
        try {
          await postToBucky(payload, ACTIVE_COMMAND || "message");
          showToast("Bucky 전송 완료");
          setMessageStatus("Bucky 전송 완료");
          tray.classList.remove("show");
        } catch (error) {
          showToast("전송 실패: " + error.message);
          setMessageStatus("Bucky 전송 실패: " + error.message, true);
        } finally {
          if (sendBtn) { sendBtn.disabled = false; sendBtn.textContent = "Bucky 전송"; }
        }
      }
    });
    return tray;
  }

  function openCommand(action, card) {
    ACTIVE_COMMAND = action;
    var tray = ensureTray();
    var title = document.getElementById("commandTrayTitle");
    var payload = document.getElementById("commandPayload");
    if (title) title.textContent = "Bucky 지시문: " + action;
    if (payload) payload.value = commandText(action, card);
    tray.classList.add("show");
  }

  document.querySelectorAll(".candidate").forEach(function (card) {
    var existing = card.querySelector(".command-actions");
    if (existing) {
      existing.addEventListener("click", function (event) {
        var action = event.target && event.target.getAttribute("data-action");
        if (action) openCommand(action, card);
      });
      return;
    }
    var actions = document.createElement("div");
    actions.className = "command-actions";
    actions.innerHTML = [
      "<button type=\\"button\\" class=\\"command-btn approve\\" data-action=\\"approve\\">승인</button>",
      "<button type=\\"button\\" class=\\"command-btn implement\\" data-action=\\"implement\\">구현</button>",
      "<button type=\\"button\\" class=\\"command-btn queue\\" data-action=\\"queue\\">후보</button>"
    ].join("");
    var details = card.querySelector("details");
    card.insertBefore(actions, details || null);
    actions.addEventListener("click", function (event) {
      var action = event.target && event.target.getAttribute("data-action");
      if (action) openCommand(action, card);
    });
  });

  var endpointInput = document.getElementById("buckyEndpoint");
  if (endpointInput) endpointInput.value = localStorage.getItem(ENDPOINT_KEY) || DEFAULT_BUCKY_ENDPOINT;

  var sendButton = document.getElementById("sendBuckyMessage");
  if (sendButton) {
    sendButton.addEventListener("click", async function () {
      var input = document.getElementById("buckyMessage");
      var message = input ? input.value.trim() : "";
      if (!message) {
        setMessageStatus("보낼 메시지를 입력하세요.", true);
        return;
      }
      var body = "[Bucky 사용자 메시지]\\nsource: daily-plus-dashboard\\ntarget: Bucky\\n\\n" + message;
      try {
        await postToBucky(body, "message");
        setMessageStatus("Bucky 전송 완료");
        showToast("Bucky 전송 완료");
        input.value = "";
      } catch (error) {
        setMessageStatus("Bucky 전송 실패: " + error.message, true);
        showToast("전송 실패");
      }
    });
  }

  var copyButton = document.getElementById("copyBuckyMessage");
  if (copyButton) {
    copyButton.addEventListener("click", async function () {
      var input = document.getElementById("buckyMessage");
      await copyPayload(input ? input.value : "");
    });
  }

  var intakeCopyButton = document.getElementById("copyDailyPlusIntake");
  if (intakeCopyButton) {
    intakeCopyButton.addEventListener("click", async function () {
      await copyPayload(buildKnowledgeIntakePayload());
    });
  }

  var intakeSendButton = document.getElementById("sendDailyPlusIntake");
  if (intakeSendButton) {
    intakeSendButton.addEventListener("click", async function () {
      var filesEl = document.getElementById("dailyPlusIntakeFiles");
      var payload = buildKnowledgeIntakePayload();
      if (!payload && (!filesEl || !filesEl.files || !filesEl.files.length)) {
        setMessageStatus("링크, 글, 자료 또는 파일을 먼저 넣어 주세요.", true);
        return;
      }
      intakeSendButton.disabled = true;
      intakeSendButton.textContent = "Discord 전송 중...";
      try {
        var result = await postDiscordWebhookWithFiles(payload, filesEl ? filesEl.files : []);
        setMessageStatus("Discord를 통해 Bucky Intake 전송 완료" + (result.files ? " (" + result.files + " files)" : ""));
        showToast("Bucky Intake 전송 완료");
        ["dailyPlusIntakeTitle", "dailyPlusIntakeBody", "dailyPlusIntakeTags", "dailyPlusIntakeFiles"].forEach(function (id) {
          var el = document.getElementById(id);
          if (el) el.value = "";
        });
      } catch (error) {
        setMessageStatus("Discord Intake 전송 실패: " + error.message, true);
        showToast("Discord Intake 전송 실패");
      } finally {
        intakeSendButton.disabled = false;
        intakeSendButton.textContent = "Discord로 Bucky Intake 전송";
      }
    });
  }
})();
</script>
"""


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---"):
        return {}
    match = re.match(r"---\s*\n(.*?)\n---", text, re.S)
    if not match:
        return {}
    data: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip('"')
    return data


def latest_report(date: str | None) -> Path:
    report_dir = VAULT / "00_UPGRADE" / "pulse-evolution"
    if date:
        path = report_dir / f"{date}.md"
        if not path.exists():
            raise FileNotFoundError(f"Pulse Evolution report not found: {path}")
        return path
    reports = sorted(report_dir.glob("20??-??-??.md"))
    if not reports:
        raise FileNotFoundError(f"No Pulse Evolution reports found in {report_dir}")
    return reports[-1]


def parse_candidates(text: str) -> list[Candidate]:
    pattern = re.compile(
        r"^###\s+(P\d)\s+.+?\s+Card\s+(\d+):\s+(.+?)\n"
        r"(.*?)(?=^###\s+P\d\s+.+?\s+Card\s+\d+:|\Z)",
        re.M | re.S,
    )
    candidates: list[Candidate] = []
    for match in pattern.finditer(text):
        priority, card, title, block = match.groups()
        fields = {
            key.lower().replace(" ", "_"): value.strip()
            for key, value in re.findall(r"^- ([^:]+):\s*(.*)$", block, re.M)
        }
        candidates.append(
            Candidate(
                card=int(card),
                priority=priority,
                title=title.strip(),
                category=fields.get("category", "").strip("`") or "knowledge-candidate",
                owner=fields.get("owner", "").strip("`") or "collector",
                target_area=fields.get("target_area", ""),
                action=fields.get("action", ""),
                evidence=fields.get("evidence", ""),
            )
        )
    return candidates


def parse_bucky_statuses(date: str) -> dict[int, str]:
    compact = date.replace("-", "")
    outbox = VAULT / "10_AgentBus" / "outbox" / "Bucky"
    candidates = sorted(outbox.glob(f"{compact}_*pulse_evolution*_bucky.md"))
    if not candidates:
        return {}
    text = read_text(candidates[-1])
    statuses: dict[int, str] = {}
    for line in text.splitlines():
        parts = [part.strip() for part in line.split("|")]
        if len(parts) < 7 or not parts[1].isdigit():
            continue
        status = parts[6].replace("*", "").strip()
        statuses[int(parts[1])] = status
    return statuses


def attach_statuses(date: str, candidates: list[Candidate]) -> None:
    statuses = parse_bucky_statuses(date)
    for candidate in candidates:
        candidate.status = statuses.get(candidate.card, candidate.status)


def candidate_scores(candidates: list[Candidate]) -> tuple[int, int]:
    if not candidates:
        return 0, 0
    avg_efficiency = round(
        sum(int(CATEGORY_PROFILES.get(c.category, CATEGORY_PROFILES["knowledge-candidate"])["efficiency"]) for c in candidates)
        / len(candidates)
    )
    avg_compatibility = round(
        sum(int(CATEGORY_PROFILES.get(c.category, CATEGORY_PROFILES["knowledge-candidate"])["compatibility"]) for c in candidates)
        / len(candidates)
    )
    return avg_efficiency, avg_compatibility


def load_history() -> list[DailySnapshot]:
    snapshots: list[DailySnapshot] = []
    report_dir = VAULT / "00_UPGRADE" / "pulse-evolution"
    for report in sorted(report_dir.glob("20??-??-??.md")):
        text = read_text(report)
        meta = parse_frontmatter(text)
        date = meta.get("date") or report.stem
        candidates = parse_candidates(text)
        attach_statuses(date, candidates)
        statuses = Counter(item.status for item in candidates)
        efficiency, compatibility = candidate_scores(candidates)
        snapshots.append(
            DailySnapshot(
                date=date,
                cards=int(meta.get("card_count", len(candidates)) or len(candidates)),
                candidates=int(meta.get("candidate_count", len(candidates)) or len(candidates)),
                queued=statuses.get("queued", 0) + statuses.get("staged", 0),
                approvals=statuses.get("needs-user-approval", 0),
                applied=statuses.get("applied", 0),
                avg_efficiency=efficiency,
                avg_compatibility=compatibility,
            )
        )
    return snapshots


def score_class(score: int) -> str:
    if score >= 80:
        return "good"
    if score >= 65:
        return "mid"
    return "low"


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def short_text(value: str, limit: int = 180) -> str:
    clean = re.sub(r"\s+", " ", value).strip()
    if len(clean) <= limit:
        return clean
    return clean[: limit - 1].rstrip() + "…"


def render_cards(candidates: list[Candidate]) -> str:
    rendered: list[str] = []
    for item in candidates:
        profile = CATEGORY_PROFILES.get(item.category, CATEGORY_PROFILES["knowledge-candidate"])
        efficiency = int(profile["efficiency"])
        compatibility = int(profile["compatibility"])
        status_label = STATUS_LABELS.get(item.status, item.status)
        risk = str(profile["risk"])
        rendered.append(
            f"""
      <article class="candidate" data-card="{item.card}" data-status="{esc(item.status)}" data-priority="{esc(item.priority)}" data-category="{esc(item.category)}">
        <div class="candidate-top">
          <span class="badge priority">{esc(item.priority)}</span>
          <span class="badge status {esc(item.status)}">{esc(status_label)}</span>
          <span class="badge risk risk-{esc(risk)}">{esc(risk)}</span>
        </div>
        <h3>Card {item.card}. {esc(short_text(item.title, 90))}</h3>
        <p class="meta">{esc(profile["label"])} · owner: {esc(item.owner)} · target: {esc(item.target_area or "not specified")}</p>
        <p class="action">{esc(item.action or profile["next"])}</p>
        <div class="bars">
          <div>
            <div class="bar-label"><span>효율성</span><strong>{efficiency}</strong></div>
            <div class="bar"><span class="{score_class(efficiency)}" style="width:{efficiency}%"></span></div>
          </div>
          <div>
            <div class="bar-label"><span>호환성</span><strong>{compatibility}</strong></div>
            <div class="bar"><span class="{score_class(compatibility)}" style="width:{compatibility}%"></span></div>
          </div>
        </div>
        <p class="next">{esc(profile["next"])}</p>
        <div class="command-actions" role="group" aria-label="Bucky 지시">
          <button type="button" class="command-btn approve" data-action="approve">승인</button>
          <button type="button" class="command-btn implement" data-action="implement">구현</button>
          <button type="button" class="command-btn queue" data-action="queue">후보</button>
        </div>
        <details>
          <summary>근거 보기</summary>
          <p>{esc(short_text(item.evidence, 520))}</p>
        </details>
      </article>"""
        )
    return "\n".join(rendered)


def render_trend(history: list[DailySnapshot]) -> str:
    if not history:
        return ""
    max_candidates = max(max(item.candidates for item in history), 1)
    rows = []
    for item in history:
        candidate_width = round(item.candidates / max_candidates * 100)
        approval_width = round(item.approvals / max_candidates * 100)
        applied_width = round(item.applied / max_candidates * 100)
        rows.append(
            f"""
        <div class="trend-row">
          <div class="trend-date">{esc(item.date)}</div>
          <div class="trend-bars">
            <span class="trend candidate" style="width:{candidate_width}%"></span>
            <span class="trend approval" style="width:{approval_width}%"></span>
            <span class="trend applied" style="width:{applied_width}%"></span>
          </div>
          <div class="trend-num">{item.candidates} 후보 · {item.approvals} 승인 · {item.applied} 구현</div>
        </div>"""
        )
    return "\n".join(rows)


def parse_session_log(path: Path) -> dict[str, list[list[str]]]:
    """Read daily-plus-session-log.md and return table data by section heading."""
    if not path.exists():
        return {}
    text = read_text(path)
    text = re.sub(r"^---.*?---\s*", "", text, flags=re.S)
    sections: dict[str, list[list[str]]] = {}
    current_heading = ""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            current_heading = stripped[3:].strip()
            sections.setdefault(current_heading, [])
        elif stripped.startswith("|") and current_heading:
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if any("---" in c for c in cells):
                continue
            sections[current_heading].append(cells)
    return sections


def render_session_section(session: dict[str, list[list[str]]]) -> str:
    if not session:
        return ""
    parts: list[str] = []
    for heading, rows in session.items():
        if not rows or len(rows) < 2:
            continue
        headers = rows[0]
        data_rows = rows[1:]
        header_html = "".join(f"<th>{esc(h)}</th>" for h in headers)
        rows_html = "\n".join(
            "<tr>" + "".join(f"<td>{esc(c)}</td>" for c in row) + "</tr>"
            for row in data_rows
        )
        parts.append(f"""
      <h3 style="margin:20px 0 10px;font-size:16px">{esc(heading)}</h3>
      <div style="overflow-x:auto">
        <table class="session-table">
          <thead><tr>{header_html}</tr></thead>
          <tbody>{rows_html}</tbody>
        </table>
      </div>""")
    if not parts:
        return ""
    return "\n".join(parts)


def render_history_table(history: list[DailySnapshot]) -> str:
    if not history:
        return ""
    first = history[0]
    latest = history[-1]
    cumulative = sum(item.candidates for item in history)
    delta_candidates = latest.candidates - first.candidates
    delta_efficiency = latest.avg_efficiency - first.avg_efficiency
    delta_compatibility = latest.avg_compatibility - first.avg_compatibility
    return f"""
      <div class="compare-grid">
        <div class="compare-card"><span>기준일</span><strong>{esc(first.date)}</strong><p>{first.candidates} 후보 · 효율 {first.avg_efficiency} · 호환 {first.avg_compatibility}</p></div>
        <div class="compare-card"><span>오늘</span><strong>{esc(latest.date)}</strong><p>{latest.candidates} 후보 · 효율 {latest.avg_efficiency} · 호환 {latest.avg_compatibility}</p></div>
        <div class="compare-card"><span>진화 폭</span><strong>{delta_candidates:+d}</strong><p>후보 수 변화 · 효율 {delta_efficiency:+d} · 호환 {delta_compatibility:+d}</p></div>
        <div class="compare-card"><span>누적</span><strong>{cumulative}</strong><p>{len(history)}일 동안 수집된 업그레이드 후보</p></div>
      </div>
"""


def render_dashboard(
    date: str,
    capture_meta: dict[str, str],
    report_meta: dict[str, str],
    candidates: list[Candidate],
    history: list[DailySnapshot],
    report_path: Path,
    capture_path: Path,
    session_html: str = "",
) -> str:
    status_counts = Counter(item.status for item in candidates)
    category_counts = Counter(item.category for item in candidates)
    priority_counts = Counter(item.priority for item in candidates)
    implemented_count = status_counts.get("applied", 0)
    queued_count = status_counts.get("queued", 0)
    approval_count = status_counts.get("needs-user-approval", 0)
    staged_count = status_counts.get("staged", 0)
    kst = timezone(timedelta(hours=9))
    generated_at = datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S KST")

    avg_efficiency, avg_compatibility = candidate_scores(candidates)
    first_date = history[0].date if history else date

    top_next = [
        item
        for item in candidates
        if item.status == "needs-user-approval" or item.priority == "P1"
    ][:5]
    if not top_next:
        top_next = candidates[:5]

    next_rows = "\n".join(
        f"<li><strong>{esc(item.priority)} Card {item.card}</strong><span>{esc(short_text(item.title, 72))}</span><em>{esc(STATUS_LABELS.get(item.status, item.status))}</em></li>"
        for item in top_next
    )
    category_rows = "\n".join(
        f"<div class=\"mini\"><strong>{esc(CATEGORY_PROFILES.get(category, CATEGORY_PROFILES['knowledge-candidate'])['label'])}</strong><span>{count}</span></div>"
        for category, count in category_counts.most_common()
    )

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>오늘의 플러스 운영 리포트</title>
<style>
  :root {{
    --bg: #f6f8fb;
    --surface: #ffffff;
    --surface-2: #eef3f8;
    --text: #17202a;
    --muted: #667085;
    --line: #d8e0ea;
    --blue: #2563eb;
    --green: #15803d;
    --amber: #b45309;
    --red: #b91c1c;
    --teal: #0f766e;
    --ink: #0f172a;
  }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; font-family: "Segoe UI", system-ui, -apple-system, sans-serif; background: var(--bg); color: var(--text); }}
  header {{ background: #0f172a; color: #fff; padding: 28px clamp(18px, 4vw, 48px) 22px; }}
  nav {{ display: flex; gap: 10px; flex-wrap: wrap; align-items: center; margin-bottom: 18px; }}
  nav a {{ color: #cbd5e1; text-decoration: none; border: 1px solid #334155; border-radius: 999px; padding: 7px 12px; font-size: 13px; }}
  nav a.active, nav a:hover {{ color: #fff; border-color: #60a5fa; }}
  nav .auth-start {{ margin-left: auto; }}
  h1 {{ margin: 0; font-size: clamp(28px, 4vw, 44px); letter-spacing: 0; }}
  header p {{ color: #cbd5e1; max-width: 920px; line-height: 1.65; margin: 12px 0 0; }}
  main {{ padding: 24px clamp(14px, 3vw, 42px) 48px; }}
  .hero-grid {{ display: grid; grid-template-columns: 1.35fr .65fr; gap: 16px; align-items: stretch; }}
  .panel, .stat, .candidate {{ background: var(--surface); border: 1px solid var(--line); border-radius: 8px; box-shadow: 0 8px 28px rgba(15,23,42,.05); }}
  .panel {{ padding: 20px; }}
  .status-line {{ display: flex; gap: 10px; flex-wrap: wrap; margin-top: 16px; }}
  .pill {{ display: inline-flex; align-items: center; gap: 7px; border-radius: 999px; padding: 7px 11px; background: var(--surface-2); color: var(--ink); font-size: 13px; border: 1px solid var(--line); }}
  .summary {{ display: grid; grid-template-columns: repeat(4, minmax(120px, 1fr)); gap: 12px; margin: 16px 0; }}
  .stat {{ padding: 18px; min-height: 108px; }}
  .stat strong {{ display: block; font-size: 34px; line-height: 1; }}
  .stat span {{ color: var(--muted); font-size: 13px; display: block; margin-top: 8px; line-height: 1.35; }}
  .stat.blue strong {{ color: var(--blue); }}
  .stat.green strong {{ color: var(--green); }}
  .stat.amber strong {{ color: var(--amber); }}
  .stat.red strong {{ color: var(--red); }}
  .section-title {{ margin: 28px 0 12px; display: flex; align-items: end; justify-content: space-between; gap: 12px; }}
  h2 {{ margin: 0; font-size: 20px; }}
  .muted {{ color: var(--muted); font-size: 13px; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(310px, 1fr)); gap: 14px; }}
  .candidate {{ padding: 16px; min-height: 318px; display: flex; flex-direction: column; gap: 10px; }}
  .candidate-top {{ display: flex; gap: 7px; flex-wrap: wrap; }}
  .badge {{ font-size: 12px; border-radius: 999px; padding: 4px 8px; border: 1px solid var(--line); background: var(--surface-2); color: var(--muted); }}
  .priority {{ color: var(--blue); border-color: #bfdbfe; background: #eff6ff; }}
  .status.queued {{ color: var(--teal); border-color: #99f6e4; background: #f0fdfa; }}
  .status.needs-user-approval {{ color: var(--amber); border-color: #fed7aa; background: #fff7ed; }}
  .status.applied {{ color: var(--green); border-color: #bbf7d0; background: #f0fdf4; }}
  .risk-low {{ color: var(--green); background: #f0fdf4; border-color: #bbf7d0; }}
  .risk-medium {{ color: var(--amber); background: #fff7ed; border-color: #fed7aa; }}
  .risk-high {{ color: var(--red); background: #fef2f2; border-color: #fecaca; }}
  .candidate h3 {{ margin: 0; font-size: 17px; line-height: 1.35; }}
  .meta, .action, .next, details {{ color: var(--muted); font-size: 13px; line-height: 1.55; margin: 0; }}
  .action {{ color: var(--ink); }}
  .bars {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: auto; }}
  .bar-label {{ display: flex; justify-content: space-between; color: var(--muted); font-size: 12px; margin-bottom: 4px; }}
  .bar {{ height: 8px; background: #e5e7eb; border-radius: 999px; overflow: hidden; }}
  .bar span {{ display: block; height: 100%; border-radius: inherit; }}
  .bar .good {{ background: var(--green); }}
  .bar .mid {{ background: var(--amber); }}
  .bar .low {{ background: var(--red); }}
  details {{ border-top: 1px solid var(--line); padding-top: 9px; }}
  summary {{ cursor: pointer; color: var(--blue); }}
  .next-list {{ list-style: none; padding: 0; margin: 12px 0 0; display: grid; gap: 9px; }}
  .next-list li {{ display: grid; grid-template-columns: 120px 1fr auto; gap: 10px; align-items: center; padding: 10px 0; border-bottom: 1px solid var(--line); }}
  .next-list em {{ color: var(--muted); font-style: normal; font-size: 12px; }}
  .mini-grid {{ display: grid; gap: 9px; margin-top: 12px; }}
  .mini {{ display: flex; justify-content: space-between; gap: 12px; padding: 10px 0; border-bottom: 1px solid var(--line); }}
  .source {{ display: grid; gap: 8px; font-size: 13px; color: var(--muted); }}
  .source code {{ color: var(--ink); background: var(--surface-2); border-radius: 4px; padding: 2px 5px; word-break: break-all; }}
  .compare-grid {{ display: grid; grid-template-columns: repeat(4, minmax(150px, 1fr)); gap: 12px; }}
  .compare-card {{ border: 1px solid var(--line); border-radius: 8px; padding: 14px; background: #fbfdff; }}
  .compare-card span {{ color: var(--muted); font-size: 12px; }}
  .compare-card strong {{ display: block; margin-top: 6px; font-size: 28px; }}
  .compare-card p {{ color: var(--muted); margin: 6px 0 0; line-height: 1.45; font-size: 13px; }}
  .trend-wrap {{ display: grid; gap: 12px; margin-top: 12px; }}
  .trend-row {{ display: grid; grid-template-columns: 110px 1fr 190px; gap: 12px; align-items: center; }}
  .trend-date, .trend-num {{ color: var(--muted); font-size: 13px; }}
  .trend-bars {{ position: relative; height: 22px; background: #e5e7eb; border-radius: 999px; overflow: hidden; }}
  .trend {{ position: absolute; left: 0; top: 0; height: 100%; border-radius: 999px; min-width: 2px; }}
  .trend.candidate {{ background: #bfdbfe; }}
  .trend.approval {{ background: #fdba74; height: 66%; top: 17%; }}
  .trend.applied {{ background: #86efac; height: 34%; top: 33%; }}
  .legend {{ display: flex; gap: 12px; flex-wrap: wrap; color: var(--muted); font-size: 12px; margin-top: 10px; }}
  .legend span::before {{ content: ""; display: inline-block; width: 10px; height: 10px; border-radius: 99px; margin-right: 5px; vertical-align: -1px; }}
  .legend .candidate::before {{ background: #bfdbfe; }}
  .legend .approval::before {{ background: #fdba74; }}
  .legend .applied::before {{ background: #86efac; }}
{DASHBOARD_INTERACTION_CSS}
  .session-table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  .session-table th {{ background: var(--surface-2); padding: 8px 10px; text-align: left; border: 1px solid var(--line); font-weight: 700; color: var(--ink); }}
  .session-table td {{ padding: 7px 10px; border: 1px solid var(--line); color: var(--text); vertical-align: top; }}
  .session-table tr:nth-child(even) td {{ background: #fafbfc; }}
  footer {{ padding: 22px clamp(14px, 3vw, 42px); color: var(--muted); border-top: 1px solid var(--line); font-size: 13px; }}
  @media (max-width: 840px) {{
    .hero-grid {{ grid-template-columns: 1fr; }}
    .summary, .compare-grid {{ grid-template-columns: repeat(2, 1fr); }}
    .next-list li {{ grid-template-columns: 1fr; }}
    .trend-row {{ grid-template-columns: 1fr; }}
  }}
  @media (max-width: 520px) {{
    .summary, .compare-grid {{ grid-template-columns: 1fr; }}
    .bars {{ grid-template-columns: 1fr; }}
    .command-actions {{ grid-template-columns: 1fr; }}
    .message-actions {{ justify-content: stretch; }}
    .message-actions button {{ flex: 1; }}
    .knowledge-intake .intake-grid, .knowledge-intake .file-row {{ grid-template-columns: 1fr; }}
    .intake-actions {{ justify-content: stretch; }}
    .intake-actions button {{ flex: 1; }}
    .command-tray {{ left: 8px; right: 8px; bottom: 8px; max-height: 88vh; overflow: auto; }}
  }}
</style>
</head>
<body>
<header>
  <nav>
    <a href="index.html">레포대시보드</a>
    <a href="wishket.html">위시켓</a>
    <a href="daily-plus.html" class="active">오늘의플러스</a>
    <a href="ai-usage.html">AI사용량</a>
    <a href="https://github.com/jaeha81/obsidian-agent-brain-system" target="_blank" rel="noreferrer">깃허브</a>
    <a href="login.html" class="auth-start">로그인</a>
    <a href="/api/logout">로그아웃</a>
  </nav>
  <h1>오늘의 플러스 운영 리포트</h1>
  <p>ChatGPT Pulse 수집 결과를 Bucky가 운영 관점으로 분류한 대시보드입니다. 첫 오늘의 플러스({esc(first_date)}) 대비 얼마나 진화했는지, 오늘 무엇이 처리됐고 무엇을 구현해야 하는지, 어떤 항목이 효율성과 호환성 측면에서 우선인지 한 화면에서 확인합니다.</p>
</header>
<main>
  <section class="hero-grid">
    <div class="panel">
      <h2>{esc(date)} 처리 요약</h2>
      <div class="status-line">
        <span class="pill">수집: {esc(capture_meta.get("collected_at", "unknown"))}</span>
        <span class="pill">리포트: {esc(report_meta.get("status", "unknown"))}</span>
        <span class="pill">Bucky 관리: AgentBus 기반</span>
      </div>
      <div class="summary">
        <div class="stat blue"><strong>{len(candidates)}</strong><span>오늘의 플러스 후보</span></div>
        <div class="stat green"><strong>{implemented_count}</strong><span>직접 구현 반영</span></div>
        <div class="stat amber"><strong>{queued_count + staged_count}</strong><span>큐 또는 스테이징</span></div>
        <div class="stat red"><strong>{approval_count}</strong><span>사용자 승인 필요</span></div>
      </div>
      <p class="muted">오늘의 플러스는 원문을 보존하고, 바로 구현하지 않는 항목은 큐/승인대기로 분리합니다. 현재 대시보드 기준 직접 적용된 후보는 {implemented_count}개이며, 운영 파이프라인 자체는 수집, 진화 리포트, Bucky 처리까지 연결되어 있습니다.</p>
    </div>
    <aside class="panel">
      <h2>효율성/호환성</h2>
      <div class="summary" style="grid-template-columns:1fr 1fr">
        <div class="stat blue"><strong>{avg_efficiency}</strong><span>평균 효율성</span></div>
        <div class="stat green"><strong>{avg_compatibility}</strong><span>평균 호환성</span></div>
      </div>
      <div class="mini-grid">
        {category_rows}
      </div>
    </aside>
  </section>

  <section>
    <div class="section-title">
      <h2>Bucky Knowledge Intake</h2>
      <span class="muted">Discord webhook -> Bucky -> Obsidian raw storage</span>
    </div>
    <div class="panel knowledge-intake">
      <div class="intake-grid">
        <select id="dailyPlusIntakeType" aria-label="Intake type">
          <option value="auto">Auto detect</option>
          <option value="link">Link or YouTube</option>
          <option value="note">Note or article</option>
          <option value="file">File/material</option>
          <option value="pulse">Daily Plus context</option>
        </select>
        <input id="dailyPlusIntakeTitle" type="text" placeholder="Title or short label">
      </div>
      <textarea id="dailyPlusIntakeBody" placeholder="Paste URL, YouTube address, article text, memo, or instructions for Bucky"></textarea>
      <div class="file-row">
        <input id="dailyPlusIntakeTags" type="text" placeholder="Tags, comma separated">
        <input id="dailyPlusIntakeFiles" type="file" multiple>
      </div>
      <div class="intake-actions">
        <button type="button" class="copy" id="copyDailyPlusIntake">Copy payload</button>
        <button type="button" class="send-discord" id="sendDailyPlusIntake">Discord로 Bucky Intake 전송</button>
      </div>
      <p class="muted">Discord webhook URL은 Repo Dashboard와 같은 브라우저 저장값(<code>bucky-webhook</code>)을 사용합니다. 파일은 Discord 첨부로 전송되고 Bucky bot이 RAW_IMPORT/Discord 및 Obsidian 01_RAW에 기록합니다.</p>
    </div>
  </section>

  <section>
    <div class="section-title">
      <h2>Bucky 메시지</h2>
      <span class="muted">사용자 메시지로 전달</span>
    </div>
    <div class="panel message-box">
      <textarea id="buckyMessage" placeholder="Bucky에게 보낼 메시지"></textarea>
      <input id="buckyEndpoint" type="url" placeholder="Bucky OS HTTPS intake URL" aria-label="Bucky OS intake endpoint">
      <div class="message-actions">
        <button type="button" class="send" id="sendBuckyMessage">Bucky 전송</button>
        <button type="button" class="copy" id="copyBuckyMessage">복사</button>
      </div>
      <p class="muted" id="messageStatus">Bucky OS 수신 URL 설정 후 전송합니다.</p>
    </div>
  </section>

  <section>
    <div class="section-title">
      <h2>첫 오늘의 플러스 대비 진화</h2>
      <span class="muted">매일 09:00 보고 기준</span>
    </div>
    <div class="panel">
      {render_history_table(history)}
      <div class="trend-wrap">
        {render_trend(history)}
      </div>
      <div class="legend">
        <span class="candidate">전체 후보</span>
        <span class="approval">승인 필요</span>
        <span class="applied">구현 반영</span>
      </div>
    </div>
  </section>

  <section>
    <div class="section-title">
      <h2>다음 실행 항목</h2>
      <span class="muted">P1과 승인 필요 항목 우선</span>
    </div>
    <div class="panel">
      <ul class="next-list">
        {next_rows}
      </ul>
    </div>
  </section>

  {f'''<section>
    <div class="section-title">
      <h2>이번 세션 업데이트 내용 요약</h2>
      <span class="muted">AgentBus Phase 1 게이트 완료 + 구현 상세</span>
    </div>
    <div class="panel">
      {session_html}
    </div>
  </section>''' if session_html else ""}

  <section>
    <div class="section-title">
      <h2>후보별 운영 판단</h2>
      <span class="muted">우선순위 {esc(dict(priority_counts))} · 상태 {esc(dict(status_counts))}</span>
    </div>
    <div class="grid">
      {render_cards(candidates)}
    </div>
  </section>

  <section>
    <div class="section-title">
      <h2>Bucky 관리 연결</h2>
      <span class="muted">사용자가 다시 묻지 않아도 매일 갱신되도록 관리</span>
    </div>
    <div class="panel source">
      <div>관리자: <code>Bucky Dashboard Bot / BuckyDailyPlus</code></div>
      <div>보고 시간: <code>매일 09:00 KST, BuckyDailyPlusDashboard 작업</code></div>
      <div>공개 산출물: <code>docs/daily-plus.html</code></div>
      <div>원본 수집: <code>{esc(capture_path.relative_to(ROOT))}</code></div>
      <div>진화 리포트: <code>{esc(report_path.relative_to(ROOT))}</code></div>
      <div>생성 시각: <code>{esc(generated_at)}</code></div>
    </div>
  </section>
</main>
<footer>
  Source of truth is the Obsidian vault. This page is a generated operational view for fast user review.
</footer>
{DASHBOARD_INTERACTION_JS}
</body>
</html>
"""


def generate(date: str | None) -> Path:
    report_path = latest_report(date)
    report_text = read_text(report_path)
    report_meta = parse_frontmatter(report_text)
    date = report_meta.get("date") or report_path.stem

    capture_path = VAULT / "04_Wiki" / "daily-plus" / f"{date}.md"
    capture_meta = parse_frontmatter(read_text(capture_path)) if capture_path.exists() else {}

    candidates = parse_candidates(report_text)
    attach_statuses(date, candidates)
    history = load_history()

    if not candidates:
        raise RuntimeError(f"No candidates parsed from {report_path}")

    session = parse_session_log(SESSION_LOG_PATH)
    session_html = render_session_section(session)

    DOCS.mkdir(parents=True, exist_ok=True)
    output = DOCS / "daily-plus.html"
    html_text = render_dashboard(date, capture_meta, report_meta, candidates, history, report_path, capture_path, session_html)
    html_text = "\n".join(line.rstrip() for line in html_text.splitlines()) + "\n"
    output.write_text(
        html_text,
        encoding="utf-8",
        newline="\n",
    )
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate docs/daily-plus.html")
    parser.add_argument("--date", help="Report date, e.g. 2026-05-28")
    args = parser.parse_args()
    output = generate(args.date)
    print(f"[daily-plus-dashboard] wrote {output}")


if __name__ == "__main__":
    main()
