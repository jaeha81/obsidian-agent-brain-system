/**
 * Tests for safeRedirect() — open redirect prevention
 *
 * Run: node --test tests/test_safe_redirect.js
 * Requires: Node.js >= 18 (node:test built-in)
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";

// ── safeRedirect 인라인 (세 파일 공통 구현체를 여기서 직접 검증) ─────────────
function safeRedirect(value, fallback) {
  const fb = fallback || "/";
  if (!value || typeof value !== "string") return fb;
  const t = value.trim();
  if (t.startsWith("//") || /^[a-zA-Z][a-zA-Z0-9+\-.]*:/.test(t) || !t.startsWith("/")) {
    return fb;
  }
  return t;
}

// ── 차단되어야 하는 케이스 ───────────────────────────────────────────────────

describe("safeRedirect — blocked (open redirect attacks)", () => {
  const FALLBACK = "/";

  it("blocks protocol-relative //evil.com", () => {
    assert.equal(safeRedirect("//evil.com"), FALLBACK);
  });

  it("blocks protocol-relative //evil.com/path", () => {
    assert.equal(safeRedirect("//evil.com/path"), FALLBACK);
  });

  it("blocks https:// absolute URL", () => {
    assert.equal(safeRedirect("https://evil.com"), FALLBACK);
  });

  it("blocks http:// absolute URL", () => {
    assert.equal(safeRedirect("http://evil.com/page"), FALLBACK);
  });

  it("blocks javascript: URI", () => {
    assert.equal(safeRedirect("javascript:alert(1)"), FALLBACK);
  });

  it("blocks javascript: URI (mixed case)", () => {
    assert.equal(safeRedirect("JaVaScRiPt:alert(1)"), FALLBACK);
  });

  it("blocks data: URI", () => {
    assert.equal(safeRedirect("data:text/html,<script>evil</script>"), FALLBACK);
  });

  it("blocks bare hostname without slash", () => {
    assert.equal(safeRedirect("evil.com"), FALLBACK);
  });

  it("blocks bare hostname with path", () => {
    assert.equal(safeRedirect("evil.com/path"), FALLBACK);
  });

  it("blocks ftp:// URL", () => {
    assert.equal(safeRedirect("ftp://evil.com"), FALLBACK);
  });

  it("blocks URL with leading whitespace hiding scheme", () => {
    // trim() 후 차단돼야 함
    assert.equal(safeRedirect("  https://evil.com"), FALLBACK);
  });

  it("blocks URL with leading whitespace hiding protocol-relative", () => {
    assert.equal(safeRedirect("  //evil.com"), FALLBACK);
  });

  it("returns fallback for empty string", () => {
    assert.equal(safeRedirect(""), FALLBACK);
  });

  it("returns fallback for null", () => {
    assert.equal(safeRedirect(null), FALLBACK);
  });

  it("returns fallback for undefined", () => {
    assert.equal(safeRedirect(undefined), FALLBACK);
  });

  it("returns fallback for non-string number", () => {
    assert.equal(safeRedirect(42), FALLBACK);
  });
});

// ── 허용되어야 하는 케이스 ────────────────────────────────────────────────────

describe("safeRedirect — allowed (same-origin relative paths)", () => {
  it("allows root /", () => {
    assert.equal(safeRedirect("/"), "/");
  });

  it("allows simple path /dashboard", () => {
    assert.equal(safeRedirect("/dashboard"), "/dashboard");
  });

  it("allows path with extension /daily-plus.html", () => {
    assert.equal(safeRedirect("/daily-plus.html"), "/daily-plus.html");
  });

  it("allows path with query string /page?foo=bar", () => {
    assert.equal(safeRedirect("/page?foo=bar"), "/page?foo=bar");
  });

  it("allows path with hash /page#section", () => {
    assert.equal(safeRedirect("/page#section"), "/page#section");
  });

  it("allows deeply nested path /a/b/c/d", () => {
    assert.equal(safeRedirect("/a/b/c/d"), "/a/b/c/d");
  });

  it("trims surrounding whitespace from valid path", () => {
    assert.equal(safeRedirect("  /dashboard  "), "/dashboard");
  });
});

// ── fallback 파라미터 ─────────────────────────────────────────────────────────

describe("safeRedirect — custom fallback", () => {
  it("uses custom fallback for blocked external URL", () => {
    assert.equal(safeRedirect("https://evil.com", "/bucky-daily.html"), "/bucky-daily.html");
  });

  it("uses custom fallback for protocol-relative URL", () => {
    assert.equal(safeRedirect("//evil.com", "/bucky-daily.html"), "/bucky-daily.html");
  });

  it("uses custom fallback for null input", () => {
    assert.equal(safeRedirect(null, "/bucky-daily.html"), "/bucky-daily.html");
  });

  it("uses / when fallback is omitted and value is blocked", () => {
    assert.equal(safeRedirect("https://evil.com"), "/");
  });
});

// ── 각 파일에서의 사용 패턴 검증 ─────────────────────────────────────────────

describe("safeRedirect — usage pattern: api/login.js", () => {
  // login.js: safeRedirect(redirect, '/bucky-daily.html')
  const DEFAULT = "/bucky-daily.html";

  it("passes through valid redirect from form", () => {
    assert.equal(safeRedirect("/daily-plus.html", DEFAULT), "/daily-plus.html");
  });

  it("falls back to /bucky-daily.html when redirect is empty", () => {
    assert.equal(safeRedirect("", DEFAULT), DEFAULT);
  });

  it("falls back to /bucky-daily.html for external URL", () => {
    assert.equal(safeRedirect("https://phishing.example.com", DEFAULT), DEFAULT);
  });

  it("falls back to /bucky-daily.html for //evil.com", () => {
    assert.equal(safeRedirect("//evil.com", DEFAULT), DEFAULT);
  });
});

describe("safeRedirect — usage pattern: _worker.js / _middleware.js", () => {
  // worker/middleware: safeRedirect(formData.get("redirect") || url.searchParams.get("next"), "/")
  // formData.get() returns null when missing → safeRedirect(null, "/") = "/"
  const DEFAULT = "/";

  it("returns / when formData returns null", () => {
    assert.equal(safeRedirect(null, DEFAULT), DEFAULT);
  });

  it("returns / when both redirect and next are empty", () => {
    // null || null → safeRedirect(null, "/") = "/"
    assert.equal(safeRedirect(null || null, DEFAULT), DEFAULT);
  });

  it("passes through /daily-plus.html", () => {
    assert.equal(safeRedirect("/daily-plus.html", DEFAULT), "/daily-plus.html");
  });

  it("blocks attacker-controlled redirect param", () => {
    assert.equal(safeRedirect("//attacker.net", DEFAULT), DEFAULT);
  });
});
