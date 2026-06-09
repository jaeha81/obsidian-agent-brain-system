/**
 * Validate a post-login redirect target.
  * Allows only same-origin relative paths (starts with '/' but not '//').
   * Blocks external URLs, protocol-relative URLs, and javascript: URIs.
    */
function safeRedirect(value, fallback) {
      const fb = fallback || "/";
      if (!value || typeof value !== "string") return fb;
      const t = value.trim();
      if (t.startsWith("//") || /^[a-zA-Z][a-zA-Z0-9+\-.]*:/.test(t) || !t.startsWith("/")) {
              return fb;
      }
      return t;
}

async function parseBody(req) {
      if (req.body && typeof req.body === 'object') return req.body;
      if (req.body && typeof req.body === 'string') {
              return Object.fromEntries(new URLSearchParams(req.body));
      }
      return new Promise((resolve, reject) => {
              const chunks = [];
              req.on('data', chunk => chunks.push(chunk));
              req.on('end', () => {
                        const body = Buffer.concat(chunks).toString();
                        resolve(Object.fromEntries(new URLSearchParams(body)));
              });
      });
}

export default async (req, res) => {
      if (req.method !== 'POST') {
              res.status(405).send('Method Not Allowed');
              return;
      }
    
      const body = await parseBody(req);
      const { password, redirect } = body;
    
      const expectedPassword = (process.env.DASHBOARD_PASSWORD || '').trim();
      const sessionToken = (process.env.SESSION_TOKEN || '').trim();
    
      if (!expectedPassword || !sessionToken) {
              res.status(500).send('서버 설정 오류: 환경변수가 설정되지 않았습니다.');
              return;
      }
    
      if (password === expectedPassword) {
              const maxAge = 60 * 60 * 24 * 7;
              const cookieStr = `bucky_session=${sessionToken}; HttpOnly; Secure; SameSite=Strict; Max-Age=${maxAge}; Path=/`;
              res.setHeader('Set-Cookie', cookieStr);
              const target = safeRedirect(redirect, '/');
              res.writeHead(302, { Location: target });
              res.end();
      } else {
              res.writeHead(302, { Location: '/login.html?error=1' });
              res.end();
      }
};/**
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

async function parseBody(req) {
    if (req.body && typeof req.body === 'object') return req.body;
    if (req.body && typeof req.body === 'string') {
          return Object.fromEntries(new URLSearchParams(req.body));
    }
    return new Promise((resolve, reject) => {
          const chunks = [];
          req.on('data', chunk => chunks.push(chunk));
          req.on('end', () => {
                  const body = Buffer.concat(chunks).toString();
                  resolve(Object.fromEntries(new URLSearchParams(body)));
          });
    });
}

export default async (req, res) => {
    if (req.method !== 'POST') {
          res.status(405).send('Method Not Allowed');
          return;
    }

    const body = await parseBody(req);
    const { password, redirect } = body;

    const expectedPassword = (process.env.DASHBOARD_PASSWORD || process.env.BUCKY_AUTH_PASSWORD || '').trim();
    const sessionToken = (process.env.SESSION_TOKEN || '').trim();

    if (!expectedPassword || !sessionToken) {
          res.status(500).send('서버 설정 오류: 환경변수가 설정되지 않았습니다.');
          return;
    }

    if (password === expectedPassword) {
          const maxAge = 60 * 60 * 24 * 7; // 7일
      const cookieStr = `bucky_session=${sessionToken}; HttpOnly; Secure; SameSite=Strict; Max-Age=${maxAge}; Path=/`;
          res.setHeader('Set-Cookie', cookieStr);
          const target = safeRedirect(redirect, '/');
          res.status(200).json({ ok: true, redirect: target });
    } else {
          res.status(401).json({ ok: false, message: '비밀번호가 올바르지 않습니다.' });
    }
};
