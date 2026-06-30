const SYSTEM_PROMPT = `당신은 일본 골프 예약을 도와주는 친근한 AI 어시스턴트입니다. 한국어로 답변합니다.

이용 가능한 골프장 목록 (인덱스 0~2):
0: 치바 그린 컨트리클럽 (千葉グリーンCC) — 도쿄 근교, ¥18,500, 티타임 7:42/7:50/8:06
1: 하코네 긴란 골프클럽 (箱根銀蘭GC) — 하코네, ¥28,500, 티타임 8:20/9:00
2: 나리타 노스 컨트리클럽 (成田ノースCC) — 나리타 인근, ¥16,800, 티타임 7:30/8:10

대화 규칙:
- 지역, 날짜, 인원, 예산 등 예약에 필요한 정보를 자연스럽게 파악하세요
- 코스를 보여줘야 할 때는 응답 끝에 [[SHOW_COURSES]] 를 추가하세요
- 특정 골프장 예약으로 진행할 때는 [[SHOW_BOOKING:n]] (n=인덱스)을 추가하세요
- 두 마커를 동시에 쓰지 마세요
- 마커 외 응답은 자연스러운 한국어 대화체로 작성하세요
- 예산이 맞지 않거나 원하는 지역이 없으면 솔직하게 알려주세요`;

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

  const { messages } = body;
  if (!Array.isArray(messages) || messages.length === 0) {
    res.status(400).json({ error: 'messages array required' });
    return;
  }

  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) {
    res.status(500).json({ error: 'API key not configured' });
    return;
  }

  const anthropicRes = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: {
      'x-api-key': apiKey,
      'anthropic-version': '2023-06-01',
      'content-type': 'application/json',
    },
    body: JSON.stringify({
      model: 'claude-haiku-4-5-20251001',
      max_tokens: 512,
      system: SYSTEM_PROMPT,
      messages: messages.map(m => ({ role: m.role, content: m.content })),
    }),
  });

  if (!anthropicRes.ok) {
    const err = await anthropicRes.text();
    res.status(502).json({ error: 'Upstream API error', detail: err });
    return;
  }

  const data = await anthropicRes.json();
  const content = data?.content?.[0]?.text ?? '죄송해요, 잠시 오류가 발생했어요.';

  res.status(200).json({ content });
}
