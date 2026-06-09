const COOKIE_NAME = "bucky_auth";
const COOKIE_MAX_AGE = 60 * 60 * 24 * 7;

const PUBLIC_PATHS = ["/portfolio.html", "/portfolio", "/login.html", "/login", "/favicon.ico"];

function isPublicPath(pathname) {
  return PUBLIC_PATHS.some(p => pathname === p || pathname.startsWith(p + "?"));
}

function safeRedirect(value, fallback) {
  const fb = fallback || "/";
  if (!value || typeof value !== "string") return fb;
  const t = value.trim();
  if (t.startsWith("//") || /^[a-zA-Z][a-zA-Z0-9+\-.]*:/.test(t) || !t.startsWith("/")) return fb;
  return t;
}

function getCookie(request, name) {
  const cookies = request.headers.get("Cookie") || "";
  const match = cookies.split(";").find(c => c.trim().startsWith(name + "="));
  return match ? match.trim().substring(name.length + 1) : null;
}

async function authToken(password) {
  const data = new TextEncoder().encode(password);
  const digest = await crypto.subtle.digest("SHA-256", data);
  return Array.from(new Uint8Array(digest), b => b.toString(16).padStart(2, "0")).join("");
}

export default async (request, context) => {
  const url = new URL(request.url);
  const { pathname } = url;
  const password = Deno.env.get("BUCKY_AUTH_PASSWORD") || "";

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
    return context.next();
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
    const loginUrl = new URL("/login.html", url);
    loginUrl.searchParams.set("error", "1");
    return Response.redirect(loginUrl, 302);
  }

  const authCookie = getCookie(request, COOKIE_NAME);
  if (password && authCookie === await authToken(password)) {
    return context.next();
  }

  const loginUrl = new URL("/login.html", url);
  loginUrl.searchParams.set("redirect", pathname + url.search);
  return Response.redirect(loginUrl, 302);
};
