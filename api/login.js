export default async (req, res) => {
   if (req.method !== 'POST') {
        res.status(405).send('Method Not Allowed');
        return;
   }

   let body = {};
   if (req.body && typeof req.body === 'object') {
        body = req.body;
   } else {
        const raw = await new Promise((resolve) => {
               const chunks = [];
               req.on('data', c => chunks.push(c));
               req.on('end', () => resolve(Buffer.concat(chunks).toString()));
        });
        body = Object.fromEntries(new URLSearchParams(raw));
   }

   const { password, redirect } = body;
   const expectedPassword = (process.env.DASHBOARD_PASSWORD || '').trim();
   const sessionToken = (process.env.SESSION_TOKEN || '').trim();

   if (!expectedPassword || !sessionToken) {
        res.status(500).send('Server config error');
        return;
   }

   if (password === expectedPassword) {
        const maxAge = 60 * 60 * 24 * 7;
        res.setHeader('Set-Cookie', `bucky_session=${sessionToken}; HttpOnly; Secure; SameSite=Strict; Max-Age=${maxAge}; Path=/`);
        const target = (redirect && redirect.startsWith('/') && !redirect.startsWith('//')) ? redirect : '/';
        res.writeHead(302, { Location: target });
        res.end();
   } else {
        res.writeHead(302, { Location: '/login.html?error=1' });
        res.end();
   }
};
