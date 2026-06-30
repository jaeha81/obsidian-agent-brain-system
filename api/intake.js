export default async function handler(req, res) {
  if (req.method !== 'POST') {
    res.status(405).json({ error: 'Method Not Allowed' });
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
    try { body = JSON.parse(raw); } catch { body = {}; }
  }

  const { content, source_dashboard_url, target_channel } = body;
  if (!content) {
    res.status(400).json({ error: 'content required' });
    return;
  }

  const webhookUrl = process.env.DISCORD_WEBHOOK_URL;
  if (!webhookUrl) {
    res.status(500).json({ error: 'Webhook not configured' });
    return;
  }

  const message = {
    username: 'Bucky Intake',
    embeds: [{
      title: '📬 새 포트폴리오 문의',
      description: content,
      color: 0x2563eb,
      fields: [
        { name: '채널', value: target_channel || '내소개', inline: true },
        { name: '출처', value: source_dashboard_url || '미상', inline: true },
      ],
      timestamp: new Date().toISOString(),
    }],
  };

  const discordRes = await fetch(webhookUrl, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(message),
  });

  if (!discordRes.ok) {
    res.status(502).json({ error: 'Discord webhook failed' });
    return;
  }

  res.status(200).json({ ok: true });
}
