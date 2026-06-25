import Anthropic from '@anthropic-ai/sdk';

const COURSES = [
  { id: 0, name: '치바 그린 컨트리클럽', jp: '千葉グリーンCC', region: '도쿄 근교', time: '7:42 / 7:50 / 8:06 가능', price: 18500, tag: '추천' },
  { id: 1, name: '하코네 긴란 골프클럽', jp: '箱根銀蘭GC', region: '하코네', time: '8:20 / 9:00 가능', price: 28500 },
  { id: 2, name: '나리타 노스 컨트리클럽', jp: '成田ノースCC', region: '나리타 인근', time: '7:30 / 8:10 가능', price: 16800 }
];

const SYSTEM_PROMPT = `당신은 일본 골프 예약 전문 상담 AI "JP"입니다. 친근하고 전문적인 한국어로 대화합니다.

## 역할
- 일본 골프 여행 상담 및 골프장 추천
- 지역·날짜·인원·선호시간·특별요청 수집
- 수집 완료 후 아래 골프장 3곳 추천
- 공식 예약 페이지 안내 (직접 예약 처리 불가)
- 이 서비스는 베타 데모로, 모든 데이터는 예시입니다

## 추천 가능 골프장
- [0] 치바 그린 컨트리클럽 (千葉グリーンCC): 도쿄 근교, 티오프 7:42/7:50/8:06, ¥18,500/인, 추천 코스
- [1] 하코네 긴란 골프클럽 (箱根銀蘭GC): 하코네 후지산 뷰, 8:20/9:00 가능, ¥28,500/인
- [2] 나리타 노스 컨트리클럽 (成田ノースCC): 나리타 공항 인근, 7:30/8:10 가능, ¥16,800/인

## 대화 흐름
1. 지역 파악 (도쿄/오사카/하코네/후쿠오카 등)
2. 날짜·인원 확인
3. 선호 시간대 확인
4. 특별 요청 확인
5. 정보 요약 후 골프장 추천 카드 표시 → [[SHOW_COURSES]] 마커 출력
6. 사용자가 골프장 선택 시 → [[SHOW_BOOKING:N]] 마커 출력 (N = 0, 1, 2)

## 마커 규칙 (반드시 준수)
- 골프장 3개를 추천할 준비가 됐을 때: 응답 맨 마지막에 빈 줄 후 [[SHOW_COURSES]] 추가
- 특정 골프장 선택이 확정됐을 때: 응답 맨 마지막에 빈 줄 후 [[SHOW_BOOKING:N]] 추가
- 마커는 응답 텍스트의 맨 끝에 단독으로 한 줄만 작성
- 두 마커를 동시에 출력하지 않음

## 응답 스타일
- 2~3문장으로 짧고 자연스럽게
- 이모지 적당히 (😊 ~ ! 정도)
- "베타 데모", "예시 데이터"는 자연스럽게 언급
- 예약은 항상 공식 페이지로 안내`;

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    res.status(200).end();
    return;
  }

  if (req.method !== 'POST') {
    res.status(405).json({ error: 'Method Not Allowed' });
    return;
  }

  try {
    let body = req.body;
    if (!body || typeof body !== 'object') {
      const chunks = [];
      await new Promise((resolve, reject) => {
        req.on('data', c => chunks.push(c));
        req.on('end', resolve);
        req.on('error', reject);
      });
      body = JSON.parse(Buffer.concat(chunks).toString());
    }

    const { messages } = body;
    if (!messages || !Array.isArray(messages) || messages.length === 0) {
      res.status(400).json({ error: 'messages array required' });
      return;
    }

    const apiKey = process.env.ANTHROPIC_API_KEY;
    if (!apiKey) {
      res.status(500).json({ error: 'API key not configured' });
      return;
    }

    const client = new Anthropic({ apiKey });

    const response = await client.messages.create({
      model: 'claude-haiku-4-5-20251001',
      max_tokens: 500,
      system: SYSTEM_PROMPT,
      messages
    });

    const content = response.content[0]?.text ?? '죄송해요, 잠시 오류가 발생했어요.';
    res.status(200).json({ content });

  } catch (error) {
    console.error('golf-chat error:', error);
    res.status(500).json({ error: 'AI 응답 오류가 발생했습니다.' });
  }
}
