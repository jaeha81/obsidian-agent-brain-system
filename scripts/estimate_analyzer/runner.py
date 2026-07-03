"""
estimate_analyzer 실행기 (CLI)

사용법:
  python -X utf8 scripts/estimate_analyzer/runner.py --project <name> --file <path.xlsx>
  python -X utf8 scripts/estimate_analyzer/runner.py --project <name> --spec-codes spec.yml
  python -X utf8 scripts/estimate_analyzer/runner.py --dry-run --file <path.xlsx>

출력:
  ObsidianVault/03_Projects/estimate-analyzer/results/<date>-<project>/
    findings.json
    analysis_report.md
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional

# 패키지 루트를 sys.path에 추가 (어느 위치에서 실행해도 동작)
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.estimate_analyzer.parsers.spc_2024 import SPCEstimateParser
from scripts.estimate_analyzer.analyzers.d2_spec import analyze as analyze_d2
from scripts.estimate_analyzer.analyzers.d4_duplicate import analyze as analyze_d4
from scripts.estimate_analyzer.analyzers.d6_loss import analyze as analyze_d6
from scripts.estimate_analyzer.analyzers.d7_overhead import analyze as analyze_d7


_RESULTS_BASE = (
    _REPO_ROOT / "ObsidianVault" / "03_Projects" / "estimate-analyzer" / "results"
)


def _load_spec_codes(spec_path: str) -> Dict[str, str]:
    """YAML または JSON から spec_codes を読み込む."""
    p = Path(spec_path)
    if not p.exists():
        raise FileNotFoundError(f"spec-codes 파일 없음: {spec_path}")

    suffix = p.suffix.lower()
    if suffix in (".yaml", ".yml"):
        try:
            import yaml
        except ImportError as exc:
            raise ImportError("pyyaml 패키지가 필요합니다: pip install pyyaml") from exc
        with open(p, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        # {"spec_codes": {"F2": "...", ...}} 또는 {"F2": "..."} 형태 모두 허용
        return data.get("spec_codes", data) if isinstance(data, dict) else {}

    if suffix == ".json":
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("spec_codes", data) if isinstance(data, dict) else {}

    raise ValueError(f"지원하지 않는 spec-codes 형식: {suffix}")


def _build_report(
    project_name: str,
    summary: dict,
    all_findings: List[dict],
    dry_run: bool,
) -> str:
    """분석 결과를 마크다운 보고서로 변환."""
    red_count = sum(1 for f in all_findings if f.get("severity") == "RED")
    yellow_count = sum(1 for f in all_findings if f.get("severity") == "YELLOW")
    info_count = sum(1 for f in all_findings if f.get("severity") == "INFO")

    lines = [
        f"# 견적서 분석 보고서 — {project_name}",
        f"",
        f"분석일: {date.today().isoformat()}{'  [DRY-RUN]' if dry_run else ''}",
        f"",
        f"## 요약",
        f"",
        f"| 항목 | 값 |",
        f"|------|-----|",
        f"| 자재비 합계 | {summary['total_material']:,.0f}원 |",
        f"| 인건비 합계 | {summary['total_labor']:,.0f}원 |",
        f"| 전체 합계   | {summary['total_sum']:,.0f}원 |",
        f"| RED 알람    | {red_count}건 |",
        f"| YELLOW 알람 | {yellow_count}건 |",
        f"| INFO       | {info_count}건 |",
        f"",
        f"## 차원별 분석 결과",
        f"",
    ]

    dimensions = ["D2", "D4", "D6", "D7"]
    dim_labels = {
        "D2": "사양 코드 정합성",
        "D4": "중복 계상",
        "D6": "Loss율 적정성",
        "D7": "제경비 적정성",
    }

    for dim in dimensions:
        dim_findings = [f for f in all_findings if f.get("dimension") == dim]
        lines.append(f"### {dim}: {dim_labels[dim]} ({len(dim_findings)}건)")
        lines.append("")
        if not dim_findings:
            lines.append("이상 없음.")
        else:
            for finding in dim_findings:
                sev = finding.get("severity", "INFO")
                badge = {"RED": "🔴", "YELLOW": "🟡", "INFO": "ℹ️"}.get(sev, "")
                lines.append(f"- {badge} **{finding['id']}** {finding['message']}")
        lines.append("")

    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="견적서 분석 엔진 (Track C) — D2/D4/D6/D7 룰베이스 분석"
    )
    parser.add_argument("--project", default="unnamed", help="프로젝트 이름 (결과 폴더명)")
    parser.add_argument("--file", help="분석할 .xlsx/.xls 파일 경로")
    parser.add_argument("--spec-codes", help="도면 자재표 YAML/JSON 파일 경로")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="파일 저장 없이 결과를 stdout으로만 출력",
    )
    args = parser.parse_args(argv)

    if not args.file:
        parser.print_help()
        print("\n[오류] --file 옵션이 필요합니다.", file=sys.stderr)
        return 1

    # 1. 파싱
    print(f"[1/4] 파싱 중: {args.file}")
    try:
        parsed = SPCEstimateParser().parse(args.file)
    except FileNotFoundError as exc:
        print(f"[오류] {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"[오류] 파싱 실패: {exc}", file=sys.stderr)
        return 1

    project_name = args.project if args.project != "unnamed" else parsed["project_name"]
    rows = parsed["rows"]
    rows_direct = parsed["rows_direct"]
    summary = parsed["summary"]

    print(
        f"       프로젝트: {project_name} | "
        f"내역서 {len(rows)}행 | 직사입 {len(rows_direct)}행 | "
        f"합계 {summary['total_sum']:,.0f}원"
    )

    # 2. 분석 실행
    print("[2/4] D2/D4/D6/D7 분석 중...")
    all_findings: List[dict] = []

    # D2: spec_codes 없으면 건너뜀
    if args.spec_codes:
        spec_codes = _load_spec_codes(args.spec_codes)
        d2 = analyze_d2(rows, spec_codes)
        print(f"       D2(사양코드): {len(d2)}건")
        all_findings.extend(d2)
    else:
        print("       D2(사양코드): --spec-codes 미지정, 건너뜀")

    d4 = analyze_d4(rows)
    print(f"       D4(중복계상): {len(d4)}건")
    all_findings.extend(d4)

    d6 = analyze_d6(rows)
    print(f"       D6(Loss율):  {len(d6)}건")
    all_findings.extend(d6)

    d7 = analyze_d7(rows, rows_direct)
    print(f"       D7(제경비):  {len(d7)}건")
    all_findings.extend(d7)

    # 3. 결과 집계
    red_count = sum(1 for f in all_findings if f.get("severity") == "RED")
    yellow_count = sum(1 for f in all_findings if f.get("severity") == "YELLOW")
    print(f"[3/4] 집계: 총 {len(all_findings)}건 (RED {red_count}, YELLOW {yellow_count})")

    # 4. 저장
    report_md = _build_report(project_name, summary, all_findings, args.dry_run)

    if args.dry_run:
        print("[4/4] DRY-RUN — 파일 저장 생략\n")
        print("=" * 60)
        print(report_md)
        return 0

    date_str = date.today().strftime("%Y-%m-%d")
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in project_name)
    result_dir = _RESULTS_BASE / f"{date_str}-{safe_name}"
    result_dir.mkdir(parents=True, exist_ok=True)

    findings_path = result_dir / "findings.json"
    report_path = result_dir / "analysis_report.md"

    findings_payload = {
        "project_name": project_name,
        "analyzed_at": date.today().isoformat(),
        "summary": summary,
        "findings": all_findings,
    }
    with open(findings_path, "w", encoding="utf-8") as f:
        json.dump(findings_payload, f, ensure_ascii=False, indent=2)

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_md)

    print(f"[4/4] 저장 완료:")
    print(f"       {findings_path}")
    print(f"       {report_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
