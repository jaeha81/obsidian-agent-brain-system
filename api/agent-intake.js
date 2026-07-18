// POST /api/agent-intake
// 대시보드/디스코드 명령을 Supabase agent_commands 큐에 삽입·갱신한다.
// 지원 action: codex_review(신규), codex_rereview, codex_mark_pass, codex_mark_fail
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

async function readBody(req) {
  if (req.body && typeof req.body === 'object') return req.body;
  const raw = await new Promise((resolve) => {
    const chunks = [];
    req.on('data', c => chunks.push(c));
    req.on('end', () => resolve(Buffer.concat(chunks).toString()));
  });
  try { return JSON.parse(raw); } catch { return {}; }
}

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    res.status(405).json({ error: 'Method Not Allowed' });
    return;
  }

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
  const H = { apikey: key, Authorization: `Bearer ${key}`, 'Content-Type': 'application/json' };

  const body = await readBody(req);
  const action = String(body.action || '');

  try {
    if (action === 'codex_review') {
      if (!body.content) {
        res.status(400).json({ error: 'content required' });
        return;
      }
      const row = {
        agent: 'codex',
        action,
        title: String(body.content).slice(0, 80),
        content: String(body.content),
        source: body.source === 'discord' ? 'discord' : 'dashboard',
        status: 'pending',
        payload: body,
      };
      const r = await fetch(`${url}/rest/v1/agent_commands`, {
        method: 'POST',
        headers: { ...H, Prefer: 'return=representation' },
        body: JSON.stringify(row),
      });
      if (!r.ok) {
        res.status(502).json({ error: 'insert failed', detail: await r.text() });
        return;
      }
      const inserted = await r.json();
      res.status(200).json({ ok: true, id: inserted[0] && inserted[0].id });
      return;
    }

    if (action === 'codex_rereview' || action === 'codex_mark_pass' || action === 'codex_mark_fail') {
      const id = String(body.session_id || '');
      if (!id) {
        res.status(400).json({ error: 'session_id required' });
        return;
      }
      const patch =
        action === 'codex_rereview'
          ? { status: 'pending', result: null, error: null, claimed_at: null, completed_at: null }
          : action === 'codex_mark_pass'
          ? { status: 'passed', completed_at: new Date().toISOString() }
          : { status: 'failed', completed_at: new Date().toISOString() };
      const r = await fetch(`${url}/rest/v1/agent_commands?id=eq.${encodeURIComponent(id)}`, {
        method: 'PATCH',
        headers: H,
        body: JSON.stringify(patch),
      });
      if (!r.ok) {
        res.status(502).json({ error: 'update failed', detail: await r.text() });
        return;
      }
      res.status(200).json({ ok: true });
      return;
    }

    res.status(400).json({ error: 'unknown action' });
  } catch (e) {
    res.status(500).json({ error: String(e) });
  }
}
