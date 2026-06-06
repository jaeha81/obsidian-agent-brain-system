const COOKIE_NAME = "bucky_auth";
const COOKIE_MAX_AGE = 60 * 60 * 24 * 7;

const PUBLIC_PATHS = ["/portfolio.html", "/portfolio", "/login.html", "/login", "/favicon.ico"];

function isPublicPath(pathname) {
  return PUBLIC_PATHS.some(path => pathname === path || pathname.startsWith(path));
}

/**
 * Validate a post-login redirect target.
 * Allows only same-origin relative paths (starts with '/' but not '//').
 * Blocks external URLs, protocol-relative URLs, and javascript: URIs.
 */
function safeRedirect(value, fallback) {
  const fb = fallback || "/";
  if (!value || typeof value !== "string") return fb;
  const t = value.trim();
  // Block: //evil.com (protocol-relative), http:// / javascript: (absolute), bare hostnames
  if (t.startsWith("//") || /^[a-zA-Z][a-zA-Z0-9+\-.]*:/.test(t) || !t.startsWith("/")) {
    return fb;
  }
  return t;
}

function getCookie(request, name) {
  const cookies = request.headers.get("Cookie") || "";
  const match = cookies.split(";").find(cookie => cookie.trim().startsWith(name + "="));
  return match ? match.trim().split("=")[1] : null;
}

function getPassword(env) {
  return env && typeof env.BUCKY_AUTH_PASSWORD === "string" ? env.BUCKY_AUTH_PASSWORD : "";
}

async function authToken(password) {
  const data = new TextEncoder().encode(password);
  const digest = await crypto.subtle.digest("SHA-256", data);
  return Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, "0")).join("");
}

function loginPage(error) {
  const errHtml = error ? '<div class="error">' + error + "</div>" : "";
  const html = '<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>Bucky Agent OS 로그인</title><style>*{margin:0;padding:0;box-sizing:border-box}body{min-height:100vh;display:flex;align-items:center;justify-content:center;background:#0f0f0f;font-family:Segoe UI,sans-serif}.card{background:#1a1a1a;border:1px solid #333;border-radius:12px;padding:40px;width:360px;text-align:center}.logo{font-size:32px;margin-bottom:8px}h1{color:#fff;font-size:20px;margin-bottom:4px}p{color:#888;font-size:13px;margin-bottom:28px}input{width:100%;padding:12px 16px;background:#2a2a2a;border:1px solid #444;border-radius:8px;color:#fff;font-size:15px;margin-bottom:16px;outline:none}input:focus{border-color:#f6821f}button{width:100%;padding:12px;background:#f6821f;color:#fff;border:none;border-radius:8px;font-size:15px;font-weight:600;cursor:pointer}button:hover{background:#e07310}.error{color:#ff6b6b;font-size:13px;margin-top:12px}</style></head><body><div class="card"><div class="logo">B</div><h1>Bucky Agent OS</h1><p>운영 대시보드 접근</p><form method="POST" action="/api/login"><input type="password" name="password" placeholder="비밀번호" autofocus /><button type="submit">로그인</button>' + errHtml + "</form></div></body></html>";
  return new Response(html, {
    status: 401,
    headers: { "Content-Type": "text/html; charset=utf-8" },
  });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const { pathname } = url;
    const password = getPassword(env);

    if (pathname === "/login") {
      return Response.redirect(new URL("/login.html", url), 302);
    }

    if (pathname === "/api/logout") {
      return new Response(null, {
        status: 302,
        headers: {
          Location: "/login.html",
          "Set-Cookie": `${COOKIE_NAME}=; Max-Age=0; Path=/; HttpOnly; SameSite=Lax; Secure`,
        },
      });
    }

    if (isPublicPath(pathname)) {
      return env.ASSETS.fetch(request);
    }

    if (request.method === "POST" && (pathname === "/auth" || pathname === "/api/login")) {
      const formData = await request.formData();
      const submittedPassword = formData.get("password");
      if (password && submittedPassword === password) {
        const redirectTo = safeRedirect(formData.get("redirect") || url.searchParams.get("next"), "/");
        const token = await authToken(password);
        return new Response(null, {
          status: 302,
          headers: {
            Location: redirectTo,
            "Set-Cookie": `${COOKIE_NAME}=${token}; Max-Age=${COOKIE_MAX_AGE}; Path=/; HttpOnly; SameSite=Lax; Secure`,
          },
        });
      }
      return loginPage(password ? "비밀번호가 올바르지 않습니다." : "BUCKY_AUTH_PASSWORD가 설정되지 않았습니다.");
    }

    const authCookie = getCookie(request, COOKIE_NAME);
    if (password && authCookie === await authToken(password)) {
      return env.ASSETS.fetch(request);
    }

    return loginPage();
  },
};
