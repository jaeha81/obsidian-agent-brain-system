async function parseBody(req) {
  return new Promise((resolve) => {
    let body = '';
    req.on('data', chunk => { body += chunk.toString(); });
    req.on('end', () => {
      const params = new URLSearchParams(body);
      resolve(Object.fromEntries(params));
    });
  });
}

module.exports = async (req, res) => {
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
    const maxAge = 60 * 60 * 24 * 7; // 7일
    const cookieStr = `bucky_session=${sessionToken}; HttpOnly; Secure; SameSite=Strict; Max-Age=${maxAge}; Path=/`;
    const location = redirect || '/bucky-daily.html';

    res.writeHead(302, {
      'Set-Cookie': cookieStr,
      'Location': location
    });
    res.end();
  } else {
    const errorUrl = '/login.html?error=1' + (redirect ? '&redirect=' + encodeURIComponent(redirect) : '');
    res.writeHead(302, { Location: errorUrl });
    res.end();
  }
};
