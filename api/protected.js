const fs = require('fs');
const path = require('path');

function parseCookies(cookieHeader) {
  const cookies = {};
  if (!cookieHeader) return cookies;
  cookieHeader.split(';').forEach(pair => {
    const [key, ...vals] = pair.trim().split('=');
    if (key) cookies[key.trim()] = vals.join('=').trim();
  });
  return cookies;
}

module.exports = async (req, res) => {
  const page = req.query.page;
  const validPages = ['bucky-daily', 'wishket', 'investment-report'];

  if (!validPages.includes(page)) {
    res.status(404).send('Not Found');
    return;
  }

  const cookies = parseCookies(req.headers.cookie);
  const sessionToken = process.env.SESSION_TOKEN;

  if (!sessionToken || cookies.bucky_session !== sessionToken) {
    const redirect = encodeURIComponent('/' + page + '.html');
    res.writeHead(302, { Location: `/login.html?redirect=${redirect}` });
    res.end();
    return;
  }

  const filePath = path.join(process.cwd(), 'docs', page + '.html');
  try {
    const html = fs.readFileSync(filePath, 'utf8');
    res.setHeader('Content-Type', 'text/html; charset=utf-8');
    res.setHeader('Cache-Control', 'private, no-cache, no-store');
    res.status(200).send(html);
  } catch (err) {
    res.status(500).send('페이지를 불러올 수 없습니다.');
  }
};
