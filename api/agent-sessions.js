// GET /api/agent-sessions?agent=codex
// Supabase agent_commands 큐를 읽어 대시보드용 세션 목록을 반환한다.
// 로그인 쿠키(bucky_auth == SESSION_TOKEN) 검증. Supabase 접근은 service_role 키(서버 전용).
function parseCookies(header) {
  const cookies = {};
  if (!header) return cookies;
  header.split(';').forEach(pair => {
    const [key, ...vals] = pair.trim().split('=');
    if (key) cookies[key.trim()] = vals.join('=').trim();
  });
  return cookies;
}

export default async function handler(req, res) {
  const sessionToken = (process.env.SESSION_TOKEN || '').trim();
  const cookies = parseCookies(req.headers.cookie);
  if (!sessionToken || cookies.bucky_auth !== sessionToken) {
    res.status(401).json({ error: 'unauthorized' });
    return;
  }

  const url = (process.env.SUPABASE_URL || '').trim();
  const key = (process.env.SUPABASE_SERVICE_ROLE_KEY || '').trim();
  if (!url || !key) {
    res.status(500).json({ error: 'supabase not configured' });
    return;
  }

  const agent = String(req.query.agent || 'codex').replace(/[^a-z0-9_-]/gi, '') || 'codex';
  const q = `${url}/rest/v1/agent_commands?agent=eq.${agent}&order=created_at.desc&limit=50`;

  try {
    const r = await fetch(q, { headers: { apikey: key, Authorization: `Bearer ${key}` } });
    if (!r.ok) {
      res.status(502).json({ error: 'supabase read failed' });
      return;
    }
    const rows = await r.json();
    const sessions = rows.map(row => ({
      id: row.id,
      title: row.title || row.content || '코드 리뷰',
      status: row.status,
      created: new Date(row.created_at).toLocaleString('ko-KR', { timeZone: 'Asia/Seoul' }),
      result: row.result || '',
    }));
    res.setHeader('Cache-Control', 'no-store');
    res.status(200).json({ sessions });
  } catch (e) {
    res.status(500).json({ error: String(e) });
  }
}
