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

const FREE_MODEL = process.env.JP_GOLF_GEMINI_MODEL || 'gemini-2.5-flash-lite';

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

  // MVP 무료 검증 단계: 전 모드 Gemini 2.5 Flash-Lite 무료 티어 사용.
  // 결제 연동(가이드모드) 완료 후 Claude Haiku 4.5 유료 전환 예정 — ObsidianVault/03_Projects/jp-golf/2026-07-04-ai-api-stack.md 참조.
  const apiKey = process.env.GEMINI_API_KEY || process.env.GOOGLE_AI_API_KEY;
  if (!apiKey) {
    res.status(500).json({ error: 'API key not configured' });
    return;
  }

  const geminiRes = await fetch(
    `https://generativelanguage.googleapis.com/v1beta/models/${FREE_MODEL}:generateContent?key=${apiKey}`,
    {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        system_instruction: { parts: [{ text: SYSTEM_PROMPT }] },
        contents: messages.map(m => ({
          role: m.role === 'assistant' ? 'model' : 'user',
          parts: [{ text: m.content }],
        })),
      }),
    }
  );

  if (!geminiRes.ok) {
    const err = await geminiRes.text();
    res.status(502).json({ error: 'Upstream API error', detail: err });
    return;
  }

  const data = await geminiRes.json();
  const content = data?.candidates?.[0]?.content?.parts?.[0]?.text ?? '죄송해요, 잠시 오류가 발생했어요.';

  res.status(200).json({ content });
}
