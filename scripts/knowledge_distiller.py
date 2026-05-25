#!/usr/bin/env python3
"""
Knowledge Distiller — Phase 2
ObsidianVault/01_RAW/ 의 원시 대화 파일을 Claude API로 정제하여
구조화된 지식 노트로 변환한다.

출력: ObsidianVault/03_Knowledge/distilled/YYYY-MM/YYYY-MM-DD-<slug>.md

사용법:
    python knowledge_distiller.py               # 미처리 파일 전체 처리
    python knowledge_distiller.py --limit 5     # 최대 5개 처리
    python knowledge_distiller.py --batch-size 3  # 3개씩 배치 처리
    python knowledge_distiller.py --dry-run     # 대상 목록만 출력 (API 미호출)
    python knowledge_distiller.py --reset       # 처리 이력 초기화
    python knowledge_distiller.py --watch       # inbox 폴더 실시간 감시
"""

import argparse
import hashlib
import json
import os
import re
import sys
import textwrap
import time
from datetime import datetime
from pathlib import Path

import anthropic

# ── 경로 설정 ──────────────────────────────────────────────────────────────────
VAULT_BASE   = Path("G:/내 드라이브/obsidian-agent-brain-system/ObsidianVault")
RAW_DIR      = VAULT_BASE / "01_RAW"
INBOX_DIR    = RAW_DIR / "inbox"
OUTPUT_BASE  = VAULT_BASE / "03_Knowledge" / "AI-Distilled"
SCRIPTS_DIR  = Path(__file__).parent
STATE_FILE   = SCRIPTS_DIR / ".distiller_cache.json"
RETRY_QUEUE  = SCRIPTS_DIR / ".distiller_retry_queue.json"

MODEL        = "claude-haiku-4-5"
MAX_TOKENS   = 2048

# 재시도 설정
RETRY_MAX    = 3
RETRY_BASE   = 2.0   # 초 (exponential backoff: 2, 4, 8)
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


# ── 재시도 큐 관리 ─────────────────────────────────────────────────────────────

def load_retry_queue() -> list:
    if RETRY_QUEUE.exists():
        try:
            return json.loads(RETRY_QUEUE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []
    return []


def save_retry_queue(queue: list) -> None:
    RETRY_QUEUE.write_text(
        json.dumps(queue, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def add_to_retry_queue(file_path: Path, error_msg: str) -> None:
    queue = load_retry_queue()
    queue = [e for e in queue if e.get("file") != str(file_path)]
    queue.append({
        "file": str(file_path),
        "error": error_msg,
        "queued_at": datetime.now().isoformat(),
    })
    save_retry_queue(queue)


def remove_from_retry_queue(file_path: Path) -> None:
    queue = load_retry_queue()
    queue = [e for e in queue if e.get("file") != str(file_path)]
    save_retry_queue(queue)


def save_original_on_failure(raw_content: str, source_path: Path, file_date: str) -> Path:
    """
    API 실패 시 원본 내용을 저장 — 나중에 재처리 가능하도록.
    경로: AI-Distilled/YYYY-MM/YYYY-MM-DD-<slug>-RAW.md
    """
    try:
        dt = datetime.strptime(file_date, "%Y-%m-%d")
        ym = dt.strftime("%Y-%m")
    except ValueError:
        ym = datetime.now().strftime("%Y-%m")

    stem       = source_path.stem
    stem_clean = re.sub(r"^\d{4}-\d{2}-\d{2}[-_]?", "", stem).strip("-_")
    slug       = slugify(stem_clean) if stem_clean else slugify(stem) or "note"

    output_dir = OUTPUT_BASE / ym
    output_dir.mkdir(parents=True, exist_ok=True)

    raw_path = output_dir / f"{file_date}-{slug}-RAW.md"
    now_str  = datetime.now().strftime("%Y-%m-%d %H:%M")

    raw_path.write_text(
        textwrap.dedent(f"""
            ---
            source: {source_path.name}
            date: {file_date}
            original_file: "{source_path}"
            distilled_at: {now_str}
            status: api-failed
            tags: [ai-distilled, retry-pending]
            ---

            > [!warning] API 정제 실패 — 원본 저장본
            > 재처리 대기 중입니다.

            ## 원본 내용

            {raw_content}
        """).lstrip(),
        encoding="utf-8",
    )
    return raw_path


# ── 파일 탐색 ──────────────────────────────────────────────────────────────────

def collect_raw_files(include_inbox: bool = False) -> list[Path]:
    """
    01_RAW/ 하위의 .md 파일을 모두 수집한다.
    include_inbox=True 이면 inbox 폴더도 포함.
    날짜순 정렬.
    """
    candidates: list[Path] = []
    for md in RAW_DIR.rglob("*.md"):
        # index.md, README.md 등 메타 파일 제외
        if md.name.lower() in ("index.md", "readme.md"):
            continue
        # inbox는 별도 처리 — 기본 수집에서 제외
        if not include_inbox and INBOX_DIR in md.parents:
            continue
        candidates.append(md)
    candidates.sort(key=lambda p: p.name)
    return candidates


def collect_inbox_files() -> list[Path]:
    """inbox/ 폴더의 미처리 .md 파일 수집."""
    if not INBOX_DIR.exists():
        return []
    candidates = [
        md for md in INBOX_DIR.glob("*.md")
        if md.name.lower() not in ("index.md", "readme.md")
    ]
    candidates.sort(key=lambda p: p.stat().st_mtime)
    return candidates


def extract_date_from_path(path: Path) -> str:
    """
    파일명 또는 부모 디렉터리명에서 YYYY-MM-DD 패턴 추출.
    없으면 오늘 날짜 반환.
    """
    date_pattern = re.compile(r"(\d{4}-\d{2}-\d{2})")
    m = date_pattern.search(path.name)
    if m:
        return m.group(1)
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
            if len(text) > max_chars:
                text = text[:max_chars] + "\n\n[... 내용이 너무 길어 잘렸습니다 ...]"
            return text
        except OSError as e:
            print(f"  [WARN] {encoding} 읽기 실패: {e}")
    return "[파일 읽기 실패]"


# ── Claude API 호출 (재시도 + 프롬프트 캐싱) ──────────────────────────────────

def distill_with_claude(
    client: anthropic.Anthropic,
    file_path: Path,
    content: str,
    file_date: str,
    stats: dict,
) -> dict:
    """
    Claude API를 호출해 원시 파일에서 지식을 추출한다.
    - system prompt에 cache_control 적용 (비용 절감)
    - 실패 시 exponential backoff 3회 재시도
    반환: 파싱된 JSON dict
    """
    user_message = USER_PROMPT_TEMPLATE.format(
        file_path=str(file_path),
        file_date=file_date,
        content=content,
    )

    last_error: Exception | None = None
    for attempt in range(1, RETRY_MAX + 1):
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=[
                    {
                        "type": "text",
                        "text": SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[{"role": "user", "content": user_message}],
            )

            # 토큰 사용량 누적
            usage = response.usage
            stats["input_tokens"]          += getattr(usage, "input_tokens", 0)
            stats["output_tokens"]         += getattr(usage, "output_tokens", 0)
            stats["cache_creation_tokens"] += getattr(usage, "cache_creation_input_tokens", 0)
            stats["cache_read_tokens"]     += getattr(usage, "cache_read_input_tokens", 0)

            raw_text = response.content[0].text.strip()

            # JSON 블록 추출
            json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
            if json_match:
                raw_text = json_match.group(1)
            elif not raw_text.startswith("{"):
                start = raw_text.find("{")
                end   = raw_text.rfind("}") + 1
                if start != -1 and end > start:
                    raw_text = raw_text[start:end]

            return json.loads(raw_text)

        except (anthropic.RateLimitError, anthropic.APIConnectionError, anthropic.InternalServerError) as e:
            last_error = e
            if attempt < RETRY_MAX:
                wait = RETRY_BASE ** attempt
                print(f"  [RETRY {attempt}/{RETRY_MAX}] {type(e).__name__} — {wait:.0f}s 후 재시도")
                time.sleep(wait)
            else:
                raise

        except anthropic.APIError as e:
            # 재시도해도 의미 없는 오류(4xx 등)는 즉시 raise
            raise

    # 여기까지 오면 마지막 에러를 재발생
    raise last_error  # type: ignore[misc]


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
    """추출 결과를 Obsidian Markdown 노트로 변환한다."""
    topics     = result.get("topics", [])
    confidence = result.get("confidence", 0.8)
    insights   = result.get("insights", [])
    related    = result.get("related_knowledge", [])
    tasks      = result.get("tasks", [])
    summary    = result.get("summary", "")

    topics_yaml  = "[" + ", ".join(topics) + "]"
    related_yaml = "[" + ", ".join(f'"{t}"' for t in related) + "]"

    insights_md = "\n".join(f"- {i}" for i in insights) if insights else "- (인사이트 없음)"
    related_md  = "\n".join(f"- {r}" for r in related)  if related  else "- (연결 개념 없음)"
    tasks_md    = "\n".join(tasks) if tasks else "- (실행 태스크 없음)"
    tags_md     = " ".join(f"#{t}" for t in topics)      if topics   else ""

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    note = textwrap.dedent(f"""
        ---
        source: {source_path.name}
        date: {file_date}
        original_file: "{source_path}"
        topics: {topics_yaml}
        related: {related_yaml}
        confidence: {confidence}
        distilled_at: {now_str}
        tags: [ai-distilled]
        ---

        > {summary}

        ## 핵심 인사이트

        {insights_md}

        ## 연결 개념

        {related_md}

        ## 실행 가능한 태스크

        {tasks_md}

        ## 태그

        {tags_md}

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

    stem = source_path.stem
    stem_clean = re.sub(r"^\d{4}-\d{2}-\d{2}[-_]?", "", stem).strip("-_")
    slug = slugify(stem_clean) if stem_clean else slugify(stem)
    if not slug:
        slug = "note"

    output_dir = OUTPUT_BASE / ym
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{file_date}-{slug}.md"
    return output_dir / filename


# ── 배치 처리 ──────────────────────────────────────────────────────────────────

def process_batch(
    client: anthropic.Anthropic,
    batch: list[Path],
    state: dict,
    stats: dict,
    batch_num: int,
    total_batches: int,
) -> tuple[int, int]:
    """
    배치(N개 파일) 처리.
    반환: (success_count, fail_count)
    """
    success = 0
    fail    = 0

    print(f"\n[배치 {batch_num}/{total_batches}] {len(batch)}개 파일 처리 중...")

    for idx, raw_file in enumerate(batch, 1):
        global_idx = (batch_num - 1) * len(batch) + idx
        rel_path   = raw_file.relative_to(VAULT_BASE)
        file_date  = extract_date_from_path(raw_file)
        print(f"  [{global_idx}] {rel_path}  (날짜: {file_date})")

        content = read_file_safe(raw_file)
        if content == "[파일 읽기 실패]":
            print("    [SKIP] 파일 읽기 실패")
            fail += 1
            stats["failed"] += 1
            continue

        if len(content.strip()) < 30:
            print("    [SKIP] 내용이 너무 짧음 (30자 미만)")
            stats["skipped"] += 1
            continue

        try:
            result      = distill_with_claude(client, raw_file, content, file_date, stats)
            note_text   = build_output_note(result, raw_file, file_date)
            output_path = determine_output_path(file_date, raw_file)

            output_path.write_text(note_text, encoding="utf-8")
            print(f"    [OK] → {output_path.relative_to(VAULT_BASE)}")
            print(f"         토픽: {result.get('topics', [])}  "
                  f"인사이트: {len(result.get('insights', []))}개  "
                  f"신뢰도: {result.get('confidence', '?')}")

            state[str(raw_file)] = file_hash(raw_file)
            save_state(state)
            remove_from_retry_queue(raw_file)
            success += 1
            stats["processed"] += 1

        except json.JSONDecodeError as e:
            err_msg = f"JSON 파싱 오류: {e}"
            print(f"    [FAIL] {err_msg}")
            raw_path = save_original_on_failure(content, raw_file, file_date)
            add_to_retry_queue(raw_file, err_msg)
            print(f"           원본 저장: {raw_path.name}")
            fail += 1
            stats["failed"] += 1
        except anthropic.APIError as e:
            err_msg = f"API 오류: {e}"
            print(f"    [FAIL] Claude {err_msg}")
            raw_path = save_original_on_failure(content, raw_file, file_date)
            add_to_retry_queue(raw_file, err_msg)
            print(f"           원본 저장: {raw_path.name}")
            fail += 1
            stats["failed"] += 1
        except OSError as e:
            print(f"    [FAIL] 파일 저장 오류: {e}")
            fail += 1
            stats["failed"] += 1

    return success, fail


# ── inbox 감시 ─────────────────────────────────────────────────────────────────

def watch_inbox(client: anthropic.Anthropic, state: dict, poll_interval: int = 10) -> None:
    """
    inbox/ 폴더를 주기적으로 감시하여 새 파일이 생기면 자동 처리한다.
    Ctrl+C로 종료.
    """
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[WATCH] inbox 감시 시작: {INBOX_DIR}")
    print(f"        폴링 간격: {poll_interval}초 | 종료: Ctrl+C\n")

    seen: set[str] = set(str(f) for f in collect_inbox_files()
                         if state.get(str(f)) == file_hash(f))

    stats = _make_stats()
    try:
        while True:
            inbox_files = collect_inbox_files()
            new_files = [
                f for f in inbox_files
                if str(f) not in seen
                and state.get(str(f)) != file_hash(f)
            ]

            if new_files:
                print(f"[WATCH] 새 파일 {len(new_files)}개 감지")
                for f in new_files:
                    seen.add(str(f))

                total_batches = 1
                process_batch(client, new_files, state, stats, 1, total_batches)
                _print_stats(stats)
            else:
                print(f"[WATCH] 대기 중... ({datetime.now().strftime('%H:%M:%S')})", end="\r")

            time.sleep(poll_interval)

    except KeyboardInterrupt:
        print("\n[WATCH] 감시 종료.")
        _print_stats(stats)


# ── 통계 ───────────────────────────────────────────────────────────────────────

def _make_stats() -> dict:
    return {
        "processed": 0,
        "failed": 0,
        "skipped": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_creation_tokens": 0,
        "cache_read_tokens": 0,
    }


def _print_stats(stats: dict) -> None:
    sep = "─" * 55
    print(f"\n{sep}")
    print(f"[통계] 처리: {stats['processed']}  실패: {stats['failed']}  건너뜀: {stats['skipped']}")
    print(f"[토큰] 입력: {stats['input_tokens']:,}  출력: {stats['output_tokens']:,}")
    if stats["cache_creation_tokens"] or stats["cache_read_tokens"]:
        print(f"[캐시] 생성: {stats['cache_creation_tokens']:,}  재사용: {stats['cache_read_tokens']:,}")
        total_in = stats["input_tokens"] + stats["cache_creation_tokens"] + stats["cache_read_tokens"]
        if total_in > 0:
            hit_rate = stats["cache_read_tokens"] / total_in * 100
            print(f"       캐시 히트율: {hit_rate:.1f}%")
    print(sep)


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
        "--batch-size",
        type=int,
        default=5,
        metavar="N",
        help="배치당 파일 수 (기본: 5)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="대상 파일 목록만 출력하고 API는 호출하지 않음",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="처리 이력(.distiller_cache.json)을 초기화하고 모든 파일 재처리",
    )
    parser.add_argument(
        "--retry",
        action="store_true",
        help="재시도 큐(.distiller_retry_queue.json)의 파일만 처리",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="이미 처리된 파일도 강제 재처리",
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="inbox/ 폴더를 실시간 감시하여 새 파일 자동 처리",
    )
    parser.add_argument(
        "--watch-interval",
        type=int,
        default=10,
        metavar="SEC",
        help="inbox 감시 폴링 간격(초, 기본: 10)",
    )
    parser.add_argument(
        "--include-inbox",
        action="store_true",
        help="inbox/ 폴더도 일반 처리 대상에 포함",
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

    # ── Claude 클라이언트 초기화 ───────────────────────────────────────────────
    client = anthropic.Anthropic(api_key=api_key) if not args.dry_run else None  # type: ignore[assignment]

    # ── watch 모드 ─────────────────────────────────────────────────────────────
    if args.watch:
        watch_inbox(client, state, poll_interval=args.watch_interval)
        return 0

    # ── inbox 폴더 보장 ────────────────────────────────────────────────────────
    INBOX_DIR.mkdir(parents=True, exist_ok=True)

    # ── --retry: 재시도 큐의 파일만 처리 ──────────────────────────────────────
    if args.retry:
        queue = load_retry_queue()
        if not queue:
            print("[INFO] 재시도 큐가 비어 있습니다.")
            return 0
        pending = [Path(e["file"]) for e in queue if Path(e["file"]).exists()]
        missing = [e["file"] for e in queue if not Path(e["file"]).exists()]
        if missing:
            print(f"[WARN] 큐에 있지만 파일이 없음: {len(missing)}개 — 큐에서 제거")
            for m in missing:
                remove_from_retry_queue(Path(m))
        print(f"[INFO] 재시도 큐: {len(pending)}개 파일")
    else:
        # ── 대상 파일 수집 ─────────────────────────────────────────────────────
        all_files = collect_raw_files(include_inbox=args.include_inbox)
        if args.include_inbox:
            inbox_files = collect_inbox_files()
            existing_paths = {str(f) for f in all_files}
            for f in inbox_files:
                if str(f) not in existing_paths:
                    all_files.append(f)
            all_files.sort(key=lambda p: p.name)

        if not all_files:
            print(f"[INFO] {RAW_DIR} 에서 .md 파일을 찾을 수 없습니다.")
            return 0

        # 미처리 파일 필터링
        pending = []
        skipped_cache = 0
        for f in all_files:
            fhash = file_hash(f)
            if not args.force and state.get(str(f)) == fhash:
                skipped_cache += 1
                continue
            pending.append(f)

        retry_count = len(load_retry_queue())
        print(f"[INFO] 전체 {len(all_files)}개 파일 | 미처리 {len(pending)}개 | 캐시 건너뜀 {skipped_cache}개")
        if retry_count:
            print(f"[INFO] 재시도 대기 중인 파일: {retry_count}개 (--retry 옵션으로 처리)")

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
        batch_size = args.batch_size
        total_batches = (len(pending) + batch_size - 1) // batch_size
        print(f"\n  배치 크기: {batch_size}  →  총 {total_batches}개 배치")
        return 0

    # ── 배치 분할 처리 ─────────────────────────────────────────────────────────
    batch_size    = max(1, args.batch_size)
    batches       = [pending[i:i + batch_size] for i in range(0, len(pending), batch_size)]
    total_batches = len(batches)
    stats         = _make_stats()

    print(f"[INFO] 배치 크기: {batch_size}  →  총 {total_batches}개 배치\n")

    total_success = 0
    total_fail    = 0

    for batch_num, batch in enumerate(batches, 1):
        s, f = process_batch(client, batch, state, stats, batch_num, total_batches)
        total_success += s
        total_fail    += f

    # ── 결과 요약 ──────────────────────────────────────────────────────────────
    _print_stats(stats)
    print(f"[완료] 출력 디렉터리: {OUTPUT_BASE}")
    print(f"       캐시 파일:     {STATE_FILE}")
    remaining_retry = len(load_retry_queue())
    if remaining_retry:
        print(f"       재시도 대기:  {remaining_retry}개 (--retry 옵션으로 재처리)")

    return 0 if total_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
