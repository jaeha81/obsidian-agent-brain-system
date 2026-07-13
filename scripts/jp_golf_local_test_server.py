"""jp-golf 로컬 테스트 서버.

docs/jp-golf.html을 정적으로 서빙하고, POST /api/golf-chat 요청은
api/golf-chat.js와 동일한 로직(Gemini 2.5 Flash-Lite 무료 티어 호출)으로 처리한다.
Vercel 배포/도메인 확인 없이 사용자가 로컬 브라우저에서 즉시 채팅을 테스트할 수 있게 하기 위함.

.env는 요청마다 새로 읽으므로, API 키를 갱신한 뒤 서버 재시작 없이 바로 반영된다.
"""
import json
import os
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT / "docs"
ENV_FILE = ROOT / ".env"
PORT = 8787

SYSTEM_PROMPT = """당신은 일본 골프 예약을 도와주는 친근한 AI 어시스턴트입니다. 한국어로 답변합니다.

이용 가능한 골프장 목록 (인덱스 0~2):
0: 치바 그린 컨트리클럽 (千葉グリーンCC) — 도쿄 근교, ¥18,500, 티타임 7:42/7:50/8:06
1: 하코네 긴란 골프클럽 (箱根銀蘭GC) — 하코네, ¥28,500, 티타임 8:20/9:00
2: 나리타 노스 컨트리클럽 (成田ノースCC) — 나리타 인근, ¥16,800, 티타임 7:30/8:10

대화 규칙:
- 지역, 날짜, 인원, 예산 등 예약에 필요한 정보를 자연스럽게 파악하세요
- 코스를 보여줘야 할 때는 응답 끝에 [[SHOW_COURSES]] 를 추가하세요
- 특정 골프장 예약으로 진행할 때는 [[SHOW_BOOKING:n]] (n=인덱스)을 추가하세요
- 두 마커를 동시에 쓰지 마세요
- 마커 외 응답은 자연스러운 한국어 대화체로 작성하세요
- 예산이 맞지 않거나 원하는 지역이 없으면 솔직하게 알려주세요"""


def read_env():
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print("[jp-golf-local]", fmt % args)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/":
            path = "/jp-golf.html"
        target = DOCS_DIR / path.lstrip("/")
        if not target.is_file():
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not found")
            return
        self.send_response(200)
        content_type = "text/html; charset=utf-8" if target.suffix == ".html" else "application/octet-stream"
        self.send_header("Content-Type", content_type)
        self.end_headers()
        self.wfile.write(target.read_bytes())

    def do_POST(self):
        if self.path.split("?", 1)[0] != "/api/golf-chat":
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b""
        try:
            body = json.loads(raw.decode("utf-8") if raw else "{}")
        except (json.JSONDecodeError, UnicodeDecodeError):
            body = {}

        messages = body.get("messages")
        if not isinstance(messages, list) or not messages:
            self._json(400, {"error": "messages array required"})
            return

        env = read_env()
        api_key = os.environ.get("GEMINI_API_KEY") or env.get("GEMINI_API_KEY") \
            or os.environ.get("GOOGLE_AI_API_KEY") or env.get("GOOGLE_AI_API_KEY")
        if not api_key:
            self._json(500, {"error": "API key not configured"})
            return

        model = env.get("JP_GOLF_GEMINI_MODEL") or "gemini-2.5-flash-lite"
        payload = {
            "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": [
                {
                    "role": "model" if m.get("role") == "assistant" else "user",
                    "parts": [{"text": m.get("content", "")}],
                }
                for m in messages
            ],
        }
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent?key={api_key}"
        )
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"content-type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")
            self._json(502, {"error": "Upstream API error", "detail": detail})
            return

        content = (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "죄송해요, 잠시 오류가 발생했어요.")
        )
        self._json(200, {"content": content})

    def _json(self, status, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"jp-golf 로컬 테스트 서버 시작 → http://127.0.0.1:{PORT}/jp-golf.html")
    print("종료: Ctrl+C")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
