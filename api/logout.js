export default function handler(req, res) {
  res.writeHead(302, {
    'Set-Cookie': 'bucky_auth=; Secure; SameSite=Strict; Max-Age=0; Path=/',
    'Location': '/login.html'
  });
  res.end();
};
