#!/usr/bin/env python3
"""
Bucky SKILL 자동 추출 도구.

작업 완료 후 대화/세션에서 반복 가능한 패턴을 SKILL 파일 초안으로 추출한다.
Hermes Agentic OS 패턴 적용: 작업 → 평가 → SKILL 저장 → 다음 작업 재사용.

동작:
  1. --session-note 또는 --text 로 작업 요약을 입력받는다.
  2. Gemini(gemini_client.py)로 SKILL 패턴 추출 (API 키 없으면 템플릿 생성).
  3. ObsidianVault/06_Context_Packs/_proposals/ 에 초안 저장.
  4. 사용자가 검토 후 승인하면 정식 Context Pack으로 이동.

CLI 예:
  python -X utf8 scripts/bucky_skill_extractor.py --text "메모리 압축 자동화 구현 완료"
  python -X utf8 scripts/bucky_skill_extractor.py --session-note path/to/session.md
  python -X utf8 scripts/bucky_skill_extractor.py --text "..." --dry-run
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import datetime
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

VAULT_ROOT = Path(__file__).parent.parent / "ObsidianVault"
PROPOSALS_DIR = VAULT_ROOT / "06_Context_Packs" / "_proposals"

SKILL_TEMPLATE = """\
---
type: context-pack-proposal
status: draft
created: {date}
source: auto-extracted
extractor: bucky_skill_extractor.py
reviewed: false
---

# SKILL 초안: {title}

> 자동 추출 초안입니다. 검토 후 `ObsidianVault/06_Context_Packs/` 로 이동하세요.

## 트리거 조건

{triggers}

## 핵심 절차

{steps}

## 입력 형식

{inputs}

## 출력 형식 / 검증 기준

{outputs}

## 재사용 예시

{examples}

## 관련 파일

{references}
"""

EXTRACTION_PROMPT = """\
아래 작업 요약을 읽고 Bucky 에이전트가 다음에 재사용할 수 있는 SKILL 패턴을 추출하라.

작업 요약:
{text}

다음 JSON 형식으로 답하라 (다른 텍스트 없이 JSON만):
{{
  "title": "SKILL 제목 (15자 이내, 한국어)",
  "triggers": ["트리거 조건 1", "트리거 조건 2"],
  "steps": ["단계 1", "단계 2", "단계 3"],
  "inputs": ["입력 형식 설명"],
  "outputs": ["출력/검증 기준"],
  "examples": ["재사용 예시"],
  "references": ["관련 파일 경로"]
}}
"""


def _slugify(text: str) -> str:
    text = re.sub(r"[^\w가-힣\- ]", "", text).strip()
    text = re.sub(r"\s+", "-", text)
    return text[:50].lower()


def _extract_with_gemini(text: str) -> dict | None:
    """Gemini로 SKILL 패턴 추출. 실패하면 None 반환."""
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from gemini_client import run_gemini  # type: ignore
        import json

        prompt = EXTRACTION_PROMPT.format(text=text[:3000])
        result = run_gemini("Gemini-Content", prompt)
        # JSON 블록 추출
        m = re.search(r"\{[\s\S]+\}", result)
        if m:
            return json.loads(m.group())
    except Exception as e:
        print(f"[skill_extractor] Gemini 추출 실패: {e}", file=sys.stderr)
    return None


def _build_from_template(text: str, extracted: dict | None) -> tuple[str, str]:
    """SKILL 파일 내용과 제목 반환."""
    date = datetime.now().strftime("%Y-%m-%d")

    if extracted:
        title = extracted.get("title", "미분류 SKILL")
        triggers = "\n".join(f"- {t}" for t in extracted.get("triggers", []))
        steps = "\n".join(f"{i+1}. {s}" for i, s in enumerate(extracted.get("steps", [])))
        inputs = "\n".join(f"- {x}" for x in extracted.get("inputs", []))
        outputs = "\n".join(f"- {x}" for x in extracted.get("outputs", []))
        examples = "\n".join(f"- {x}" for x in extracted.get("examples", []))
        references = "\n".join(f"- `{x}`" for x in extracted.get("references", []))
    else:
        title = "미분류 SKILL"
        snippet = text[:200].replace("\n", " ")
        triggers = f"- (수동 입력 필요)\n- 원문: {snippet}..."
        steps = "1. (수동 입력 필요)"
        inputs = "- (수동 입력 필요)"
        outputs = "- (수동 입력 필요)"
        examples = "- (수동 입력 필요)"
        references = "- (수동 입력 필요)"

    content = SKILL_TEMPLATE.format(
        date=date,
        title=title,
        triggers=triggers or "(없음)",
        steps=steps or "(없음)",
        inputs=inputs or "(없음)",
        outputs=outputs or "(없음)",
        examples=examples or "(없음)",
        references=references or "(없음)",
    )
    return content, title


def extract(text: str, dry_run: bool = False) -> Path | None:
    """텍스트에서 SKILL 초안 추출 및 저장. dry_run=True 면 저장 생략."""
    extracted = _extract_with_gemini(text)
    content, title = _build_from_template(text, extracted)

    date_str = datetime.now().strftime("%Y-%m-%d")
    slug = _slugify(title)
    filename = f"{date_str}-skill-{slug}.md"
    out_path = PROPOSALS_DIR / filename

    if dry_run:
        print(f"[skill_extractor] dry-run — would write: {out_path}")
        print("--- 초안 미리보기 ---")
        print(content[:800])
        return None

    PROPOSALS_DIR.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content, encoding="utf-8")
    source = "Gemini" if extracted else "template"
    print(f"[skill_extractor] saved ({source}): {out_path}")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Bucky SKILL 자동 추출")
    parser.add_argument("--text", help="작업 요약 텍스트")
    parser.add_argument("--session-note", help="세션 노트 파일 경로")
    parser.add_argument("--dry-run", action="store_true", help="저장 없이 미리보기")
    args = parser.parse_args()

    if args.session_note:
        p = Path(args.session_note)
        if not p.exists():
            print(f"[skill_extractor] 파일 없음: {p}", file=sys.stderr)
            sys.exit(1)
        text = p.read_text(encoding="utf-8")
    elif args.text:
        text = args.text
    else:
        print("[skill_extractor] --text 또는 --session-note 가 필요합니다.", file=sys.stderr)
        sys.exit(1)

    result = extract(text, dry_run=args.dry_run)
    if result:
        print(f"[skill_extractor] 완료 → 검토 후 06_Context_Packs/ 로 이동하세요")


if __name__ == "__main__":
    main()
