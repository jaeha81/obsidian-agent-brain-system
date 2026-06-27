# estimate_analyzer — 견적서 분석 엔진 (Track C)

"견적서를 만들지 않는다, 들어온 견적서를 7대 차원에서 해부한다."

## 1차 MVP 범위

| 차원 | 설명 | 구현 |
|------|------|------|
| D2   | 사양 코드 정합성 | 완료 |
| D4   | 중복 계상 탐지   | 완료 |
| D6   | Loss율 적정성    | 완료 |
| D7   | 제경비 적정성    | 완료 |
| D1/D3/D5 | 단가 비교·물량 산출·공기 분석 | 미구현 (2차) |

## 사용법

```bash
# 기본 실행 (xlsx + spec-codes 포함)
python -X utf8 scripts/estimate_analyzer/runner.py \
  --project "신규_현장" \
  --file "path/to/estimate.xlsx" \
  --spec-codes "path/to/spec_codes.yml"

# dry-run (파일 저장 없이 stdout 출력)
python -X utf8 scripts/estimate_analyzer/runner.py \
  --dry-run \
  --file "path/to/estimate.xlsx"

# spec-codes 없이 실행 (D2 건너뜀)
python -X utf8 scripts/estimate_analyzer/runner.py \
  --project "내역서_검토" \
  --file "path/to/estimate.xlsx"
```

## spec-codes YAML 형식

```yaml
spec_codes:
  F2: "BOH FLOOR TILE"
  F1: "BOH FLOOR TILE (TYPE 2)"
  WT1: "주방 타일"
  WT2: "화장실 타일"
  B2: "바닥 보더"
```

## 출력 결과

```
ObsidianVault/03_Projects/estimate-analyzer/results/<date>-<project>/
  findings.json      # 구조화된 알람 목록
  analysis_report.md # 마크다운 보고서
```

## 의존성

- `openpyxl>=3.0` — xlsx 파싱
- `xlrd>=2.0` — xls 파싱 (선택)
- `pyyaml>=6.0` — spec-codes YAML 읽기

## 테스트

```bash
python -m pytest scripts/estimate_analyzer/tests/ -v
```

## 데이터 보안

- `tests/fixtures/` 에 실데이터 절대 금지
- `benchmarks/market_prices.json` 은 시드 파일 (단가 없음)
- 실단가·협력사 정보는 커밋하지 않는다
