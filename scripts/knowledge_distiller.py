#!/usr/bin/env python3
"""
Knowledge Distiller
ObsidianVault/01_RAW/ 의 원시 대화 파일을 Claude API로 정제하여
구조화된 지식 노트로 변환한다.

출력: ObsidianVault/03_Knowledge/distilled/YYYY-MM/YYYY-MM-DD-<slug>.md

사용법:
    python knowledge_distiller.py               # 미처리 파일 전체 처리
    python knowledge_distiller.py --limit 5     # 최대 5개 처리
    python knowledge_distiller.py --dry-run     # 대상 목록만 출력 (API 미호출)
    python knowledge_distiller.py --reset       # 처리 이력 초기화
"""

import argparse
import hashlib
import json
import os
import re
import sys
import textwrap
from datetime import datetime
from pathlib import Path

import anthropic

# ── 경로 설정 ──────────────────────────────────────────────────────────────────
VAULT_BASE   = Path("G:/내 드라이브/obsidian-agent-brain-system/ObsidianVault")
RAW_DIR      = VAULT_BASE / "01_RAW"
OUTPUT_BASE  = VAULT_BASE / "03_Knowledge" / "distilled"
SCRIPTS_DIR  = Path(__file__).parent
STATE_FILE   = SCRIPTS_DIR / ".distiller_state.json"

MODEL        = "claude-sonnet-4-6"
MAX_TOKENS   = 2048
# ──────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = textwrap.dedent("""
    당신은 지식 정제 전문가입니다.
    사용자가 제공하는 원시 대화/메모 파일을 분석하여 구조화된 지식 노트를 생성합니다.

    반드시 다음 JSON 형식으로만 응답하세요. 다른 텍스트는 포함하지 마세요.

    {
      "topics": ["태그1", "태그2", ...],
      "confidence": 0.0~1.0 사이 숫자,
      "insights": [
        "핵심 인사이트 1 (구체적이고 실행 가능한 내용)",
        "핵심 인사이트 2",
        ...
      ],
      "related_knowledge": ["[[연관 개념1]]", "[[연관 개념2]]", ...],
      "tasks": [
        "[ ] 실행 가능한 태스크 1",
        "[ ] 실행 가능한 태스크 2"
      ],
      "summary": "이 문서 전체를 1~2문장으로 요약"
    }

    규칙:
    - insights는 3~7개. 구체적이고 재사용 가능한 지식으로 압축.
    - topics는 2~6개의 소문자 영문 또는 한글 태그.
    - related_knowledge는 [[wikilink]] 형태로 연관 개념/주제 2~5개.
    - tasks는 문서에서 실행 가능한 행동이 있을 때만 포함, 없으면 빈 배열 [].
    - confidence는 내용 명확도 (0.9=매우 명확, 0.5=모호/노이즈 많음).
    - 파일 인코딩 문제로 깨진 텍스트가 있어도 읽을 수 있는 내용 위주로 처리.
""").strip()

USER_PROMPT_TEMPLATE = textwrap.dedent("""
    다음 원시 파일을 분석하여 지식 노트를 생성하세요.

    파일 경로: {file_path}
    파일 날짜: {file_date}

    --- 파일 내용 시작 ---
    {content}
    --- 파일 내용 끝 ---
""").strip()


# ── 상태 관리 ──────────────────────────────────────────────────────────────────

def load_state() -> dict:
    """처리 이력 로드. 파일 없으면 빈 dict 반환."""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_state(state: dict) -> None:
    """처리 이력 저장."""
    STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def file_hash(path: Path) -> str:
    """파일 내용의 SHA-256 해시 (앞 64자)."""
    try:
        content = path.read_bytes()
    except OSError:
        return ""
    return hashlib.sha256(content).hexdigest()[:64]


# ── 파일 탐색 ──────────────────────────────────────────────────────────────────

def collect_raw_files() -> list[Path]:
    """
    01_RAW/ 하위의 .md 파일을 모두 수집한다.
    패턴: 01_RAW/**/YYYY-MM-DD*.md  또는  01_RAW/**/*.md
    날짜순 정렬.
    """
    candidates: list[Path] = []
    for md in RAW_DIR.rglob("*.md"):
        # index.md, README.md 등 메타 파일 제외
        if md.name.lower() in ("index.md", "readme.md"):
            continue
        candidates.append(md)
    # 파일명 기준 정렬 (날짜 접두어가 있으면 자연스럽게 시간순)
    candidates.sort(key=lambda p: p.name)
    return candidates


def extract_date_from_path(path: Path) -> str:
    """
    파일명 또는 부모 디렉터리명에서 YYYY-MM-DD 패턴 추출.
    없으면 오늘 날짜 반환.
    """
    date_pattern = re.compile(r"(\d{4}-\d{2}-\d{2})")
    # 파일명 우선
    m = date_pattern.search(path.name)
    if m:
        return m.group(1)
    # 부모 디렉터리
    for part in path.parts:
        m = date_pattern.search(part)
        if m:
            return m.group(1)
    return datetime.now().strftime("%Y-%m-%d")


def read_file_safe(path: Path, max_chars: int = 8000) -> str:
    """파일을 안전하게 읽는다. 인코딩 오류는 replace 처리."""
    for encoding in ("utf-8", "utf-8-sig", "cp949", "latin-1"):
        try:
            text = path.read_text(encoding=encoding, errors="replace")
            # 너무 길면 앞부분만 사용
            if len(text) > max_chars:
                text = text[:max_chars] + "\n\n[... 내용이 너무 길어 잘렸습니다 ...]"
            return text
        except OSError as e:
            print(f"  [WARN] {encoding} 읽기 실패: {e}")
    return "[파일 읽기 실패]"


# ── Claude API 호출 ────────────────────────────────────────────────────────────

def distill_with_claude(client: anthropic.Anthropic, file_path: Path, content: str, file_date: str) -> dict:
    """
    Claude API를 호출해 원시 파일에서 지식을 추출한다.
    반환: 파싱된 JSON dict
    """
    user_message = USER_PROMPT_TEMPLATE.format(
        file_path=str(file_path),
        file_date=file_date,
        content=content,
    )

    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    raw_text = response.content[0].text.strip()

    # JSON 블록 추출 (```json ... ``` 또는 순수 JSON)
    json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
    if json_match:
        raw_text = json_match.group(1)
    elif raw_text.startswith("{"):
        pass  # 이미 순수 JSON
    else:
        # JSON 블록이 없으면 { ... } 범위 추출 시도
        start = raw_text.find("{")
        end   = raw_text.rfind("}") + 1
        if start != -1 and end > start:
            raw_text = raw_text[start:end]

    return json.loads(raw_text)


# ── 출력 노트 생성 ─────────────────────────────────────────────────────────────

def slugify(text: str, max_len: int = 40) -> str:
    """간단한 파일명용 slug 생성."""
    text = re.sub(r"[^\w\s가-힣-]", "", text).strip()
    text = re.sub(r"[\s_]+", "-", text)
    return text[:max_len].strip("-")


def build_output_note(
    result: dict,
    source_path: Path,
    file_date: str,
) -> str:
    """
    추출 결과를 Obsidian Markdown 노트로 변환한다.
    """
    topics     = result.get("topics", [])
    confidence = result.get("confidence", 0.8)
    insights   = result.get("insights", [])
    related    = result.get("related_knowledge", [])
    tasks      = result.get("tasks", [])
    summary    = result.get("summary", "")

    topics_yaml  = "[" + ", ".join(topics) + "]"
    related_yaml = "[" + ", ".join(f'"{t}"' for t in related) + "]"

    insights_md = "\n".join(f"- {i}" for i in insights) if insights else "- (인사이트 없음)"
    related_md  = "\n".join(f"- {r}" for r in related)  if related  else "- (연관 지식 없음)"

    if tasks:
        tasks_md = "\n".join(tasks)
    else:
        tasks_md = "- (실행 태스크 없음)"

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    note = textwrap.dedent(f"""
        ---
        source: {source_path.name}
        date: {file_date}
        original_file: "{source_path}"
        topics: {topics_yaml}
        confidence: {confidence}
        distilled_at: {now_str}
        ---

        > {summary}

        ## 핵심 인사이트

        {insights_md}

        ## 연관 지식

        {related_md}

        ## 실행 가능한 태스크

        {tasks_md}

        ---
        *자동 생성: knowledge_distiller.py — 원본: `{source_path.name}`*
    """).lstrip()

    return note


def determine_output_path(file_date: str, source_path: Path) -> Path:
    """출력 파일 경로를 결정한다."""
    try:
        dt = datetime.strptime(file_date, "%Y-%m-%d")
        ym = dt.strftime("%Y-%m")
    except ValueError:
        ym = datetime.now().strftime("%Y-%m")

    # slug: 소스 파일명에서 날짜 제거 후 사용
    stem = source_path.stem
    stem_clean = re.sub(r"^\d{4}-\d{2}-\d{2}[-_]?", "", stem).strip("-_")
    slug = slugify(stem_clean) if stem_clean else slugify(stem)
    if not slug:
        slug = "note"

    output_dir = OUTPUT_BASE / ym
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{file_date}-{slug}.md"
    return output_dir / filename


# ── 메인 ──────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="ObsidianVault 01_RAW 파일을 Claude로 정제해 지식 노트 생성",
    )
    parser.add_argument(
        "--limit", "-n",
        type=int,
        default=None,
        metavar="N",
        help="처리할 최대 파일 수 (기본: 제한 없음)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="대상 파일 목록만 출력하고 API는 호출하지 않음",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="처리 이력(.distiller_state.json)을 초기화하고 모든 파일 재처리",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="이미 처리된 파일도 강제 재처리",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    # ── ANTHROPIC_API_KEY 확인 ─────────────────────────────────────────────────
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key and not args.dry_run:
        print(
            "\n[오류] ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다.\n"
            "\n  설정 방법 (Windows PowerShell):\n"
            "    $env:ANTHROPIC_API_KEY = 'sk-ant-...'\n"
            "\n  설정 방법 (bash/zsh):\n"
            "    export ANTHROPIC_API_KEY='sk-ant-...'\n"
            "\n  영구 등록: Windows 시스템 환경변수에 ANTHROPIC_API_KEY 추가\n",
            file=sys.stderr,
        )
        return 1

    # ── 처리 이력 ──────────────────────────────────────────────────────────────
    if args.reset:
        STATE_FILE.unlink(missing_ok=True)
        print("[INFO] 처리 이력을 초기화했습니다.")
    state = load_state()

    # ── 대상 파일 수집 ─────────────────────────────────────────────────────────
    all_files = collect_raw_files()
    if not all_files:
        print(f"[INFO] {RAW_DIR} 에서 .md 파일을 찾을 수 없습니다.")
        return 0

    # 이미 처리된 파일 필터링
    pending: list[Path] = []
    skipped = 0
    for f in all_files:
        fhash = file_hash(f)
        if not args.force and state.get(str(f)) == fhash:
            skipped += 1
            continue
        pending.append(f)

    print(f"[INFO] 전체 {len(all_files)}개 파일 | 미처리 {len(pending)}개 | 건너뜀 {skipped}개")

    if not pending:
        print("[INFO] 처리할 파일이 없습니다. --reset 또는 --force 옵션을 사용하세요.")
        return 0

    # --limit 적용
    if args.limit is not None and args.limit > 0:
        pending = pending[: args.limit]
        print(f"[INFO] --limit {args.limit} 적용 → {len(pending)}개만 처리")

    # ── dry-run ────────────────────────────────────────────────────────────────
    if args.dry_run:
        print("\n[DRY-RUN] 처리 예정 파일:")
        for i, f in enumerate(pending, 1):
            print(f"  {i:3}. {f.relative_to(VAULT_BASE)}")
        return 0

    # ── Claude 클라이언트 초기화 ───────────────────────────────────────────────
    client = anthropic.Anthropic(api_key=api_key)

    # ── 파일별 처리 ────────────────────────────────────────────────────────────
    success_count = 0
    fail_count    = 0

    for idx, raw_file in enumerate(pending, 1):
        rel_path  = raw_file.relative_to(VAULT_BASE)
        file_date = extract_date_from_path(raw_file)
        print(f"\n[{idx}/{len(pending)}] {rel_path}  (날짜: {file_date})")

        content = read_file_safe(raw_file)
        if content == "[파일 읽기 실패]":
            print("  [SKIP] 파일 읽기 실패")
            fail_count += 1
            continue

        # 내용이 너무 짧으면 건너뜀
        if len(content.strip()) < 30:
            print("  [SKIP] 내용이 너무 짧음 (30자 미만)")
            fail_count += 1
            continue

        # Claude API 호출
        try:
            result      = distill_with_claude(client, raw_file, content, file_date)
            note_text   = build_output_note(result, raw_file, file_date)
            output_path = determine_output_path(file_date, raw_file)

            output_path.write_text(note_text, encoding="utf-8")
            print(f"  [OK]  → {output_path.relative_to(VAULT_BASE)}")
            print(f"        토픽: {result.get('topics', [])}")
            print(f"        인사이트: {len(result.get('insights', []))}개  "
                  f"태스크: {len(result.get('tasks', []))}개  "
                  f"신뢰도: {result.get('confidence', '?')}")

            # 처리 완료 기록
            state[str(raw_file)] = file_hash(raw_file)
            save_state(state)
            success_count += 1

        except json.JSONDecodeError as e:
            print(f"  [FAIL] Claude 응답 JSON 파싱 오류: {e}")
            fail_count += 1
        except anthropic.APIError as e:
            print(f"  [FAIL] Claude API 오류: {e}")
            fail_count += 1
        except OSError as e:
            print(f"  [FAIL] 파일 저장 오류: {e}")
            fail_count += 1

    # ── 결과 요약 ──────────────────────────────────────────────────────────────
    print(f"\n{'─' * 50}")
    print(f"[완료] 성공 {success_count}개 | 실패 {fail_count}개")
    print(f"       출력 디렉터리: {OUTPUT_BASE}")
    print(f"       처리 이력: {STATE_FILE}")

    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
