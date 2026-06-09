export default function handler(req, res) {
  const pw = process.env.DASHBOARD_PASSWORD || process.env.BUCKY_AUTH_PASSWORD || '';
  const token = process.env.SESSION_TOKEN || '';
  res.status(200).json({
    pw_set: pw.length > 0,
    pw_len: pw.length,
    pw_first: pw[0] || '',
    pw_last: pw[pw.length - 1] || '',
    token_set: token.length > 0,
    token_len: token.length,
  });
}
