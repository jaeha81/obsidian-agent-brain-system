const PASSWORD = "ljh911314";
const COOKIE_NAME = "bucky_auth";
const COOKIE_MAX_AGE = 60 * 60 * 24 * 7;

const PUBLIC_PATHS = ["/portfolio.html", "/favicon.ico"];

function isPublicPath(pathname) {
  return PUBLIC_PATHS.some(p => pathname === p || pathname.startsWith(p));
}

function getCookie(request, name) {
  const cookies = request.headers.get("Cookie") || "";
  const match = cookies.split(";").find(c => c.trim().startsWith(name + "="));
  return match ? match.trim().split("=")[1] : null;
}

function loginPage(error) {
  const errHtml = error ? '<div class="error">' + error + '</div>' : '';
  const html = '<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Bucky Ops</title><style>*{margin:0;padding:0;box-sizing:border-box}body{min-height:100vh;display:flex;align-items:center;justify-content:center;background:#0f0f0f;font-family:Segoe UI,sans-serif}.card{background:#1a1a1a;border:1px solid #333;border-radius:12px;padding:40px;width:360px;text-align:center}.logo{font-size:32px;margin-bottom:8px}h1{color:#fff;font-size:20px;margin-bottom:4px}p{color:#888;font-size:13px;margin-bottom:28px}input{width:100%;padding:12px 16px;background:#2a2a2a;border:1px solid #444;border-radius:8px;color:#fff;font-size:15px;margin-bottom:16px;outline:none}input:focus{border-color:#f6821f}button{width:100%;padding:12px;background:#f6821f;color:#fff;border:none;border-radius:8px;font-size:15px;font-weight:600;cursor:pointer}button:hover{background:#e07310}.error{color:#ff6b6b;font-size:13px;margin-top:12px}</style></head><body><div class="card"><div class="logo">🔐</div><h1>Bucky Ops</h1><p>재하님 전용 공간입니다</p><form method="POST" action="/auth"><input type="password" name="password" placeholder="비밀번호 입력" autofocus /><button type="submit">접속</button>' + errHtml + '</form></div></body></html>';
  return new Response(html, { status: 401, headers: { "Content-Type": "text/html; charset=utf-8" } });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const { pathname } = url;

    if (isPublicPath(pathname)) {
      return fetch(request);
    }

    if (request.method === "POST" && pathname === "/auth") {
      const formData = await request.formData();
      const pw = formData.get("password");
      if (pw === PASSWORD) {
        const redirectTo = url.searchParams.get("next") || "/";
        return new Response(null, {
          status: 302,
          headers: {
            Location: redirectTo,
            "Set-Cookie": COOKIE_NAME + "=" + PASSWORD + "; Max-Age=" + COOKIE_MAX_AGE + "; Path=/; HttpOnly; SameSite=Lax",
          },
        });
      }
      return loginPage("❌ 비밀번호가 틀렸습니다");
    }

    const authCookie = getCookie(request, COOKIE_NAME);
    if (authCookie === PASSWORD) {
      return fetch(request);
    }

    return loginPage();
  },
};
