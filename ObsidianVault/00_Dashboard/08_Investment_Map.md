---
type: system-doc
status: active
created: 2026-05-31
owner: Bucky
tags:
  - #status/active
---

# 08 Investment Map

주식 / 가상화폐 투자 메모 허브.

---

## 핵심 태그

`#area/stock_investment` `#area/crypto_investment`

---

## 투자 메모 대시보드

```dataview
TABLE summary AS "요약", keywords AS "키워드", status AS "상태", next_action AS "다음 행동"
FROM #area/stock_investment OR #area/crypto_investment
SORT file.mtime DESC
```
