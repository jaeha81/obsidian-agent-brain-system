#!/usr/bin/env python3
"""
Knowledge Distiller — Phase 3
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

Phase 3 추가 기능:
    - auto_tag()          : 키워드 기반 카테고리 자동 태깅 (법률/개발/건설/AI)
    - detect_duplicates() : 콘텐츠 해시 기반 전체 중복 감지 (파일명 무관)
    - generate_wikilinks(): 기존 노트와 토픽 유사도로 wikilink 자동 생성
    - priority_score()    : 최신성 + 빈도 기반 우선순위 점수 산출
"""

import argparse
import hashlib
import json
import os
import re
import sys
import textwrap
import time
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from pathlib import Path

import anthropic

# ── 경로 설정 ──────────────────────────────────────────────────────────────────
VAULT_BASE   = Path("G:/내 드라이브/obsidian-agent-brain-system/ObsidianVault")
RAW_DIR      = VAULT_BASE / "01_RAW"
INBOX_DIR    = RAW_DIR / "inbox"
# Phase 2: 출력 경로를 06_Knowledge/distilled 로 변경
#   (06_Knowledge 디렉터리가 없으면 03_Knowledge/distilled 로 fallback)
_KNOWLEDGE_06 = VAULT_BASE / "06_Knowledge" / "distilled"
_KNOWLEDGE_03 = VAULT_BASE / "03_Knowledge" / "distilled"
OUTPUT_BASE  = _KNOWLEDGE_06 if _KNOWLEDGE_06.parent.exists() else _KNOWLEDGE_03

# Phase 2: 증분 처리 대상 추가 소스 경로
CLAUDE_SESSIONS_DIR = RAW_DIR / "claude-sessions"
CODEX_SESSIONS_DIR  = RAW_DIR / "codex-sessions"

SCRIPTS_DIR  = Path(__file__).parent
STATE_FILE   = SCRIPTS_DIR / ".distiller_cache.json"
RETRY_QUEUE  = SCRIPTS_DIR / ".distiller_retry_queue.json"
# Stage 20: 01_RAW 불변 유지 — 처리 완료 여부는 이 사이드카 인덱스에만 기록한다.
PROCESSED_INDEX_FILE = SCRIPTS_DIR.parent / "data" / "memory" / "processed_index.jsonl"

MODEL        = "claude-sonnet-4-6"
MAX_TOKENS   = 2048

# 재시도 설정
RETRY_MAX    = 3
RETRY_BASE   = 2.0   # 초 (exponential backoff: 2, 4, 8)

# 청크 처리 설정
CHUNK_MAX_CHARS = 8000  # 이 이상이면 분할 처리
CHUNK_SIZE      = 7500  # 각 청크 크기

# 에러 리포트 경로
ERROR_REPORT = VAULT_BASE / "00_System" / "distiller-errors.md"

# ── 소스 유형 감지 ─────────────────────────────────────────────────────────────
# 파일명 또는 경로에서 소스 유형을 판별하는 키워드
SOURCE_PATTERNS = {
    "gpt":    re.compile(r"gpt|chatgpt|openai", re.IGNORECASE),
    "claude": re.compile(r"claude|anthropic", re.IGNORECASE),
    "codex":  re.compile(r"codex|copilot|code-?gen", re.IGNORECASE),
}

SOURCE_TAG_MAP = {
    "gpt":     "source/gpt",
    "claude":  "source/claude",
    "codex":   "source/codex",
    "unknown": "source/unknown",
}

# ── Phase 3: 카테고리 자동 태깅 키워드 맵 ──────────────────────────────────────
# 각 카테고리는 (한글 키워드, 영문 키워드) 튜플 목록으로 구성.
# 우선순위: 앞에 있을수록 높음 (점수가 높은 카테고리가 선택됨).
CATEGORY_KEYWORD_MAP: dict[str, list[str]] = {
    "법률": [
        "계약", "법률", "법원", "소송", "판례", "법령", "조항", "민법", "형법", "상법",
        "규정", "위반", "처벌", "벌칙", "손해배상", "청구", "분쟁", "조정", "중재",
        "법적", "의무", "권리", "의뢰", "변호", "공증", "등기", "허가", "인허가",
        "contract", "law", "legal", "lawsuit", "litigation", "regulation", "clause",
        "penalty", "damages", "dispute", "arbitration", "attorney",
    ],
    "개발": [
        "코드", "개발", "프로그래밍", "함수", "클래스", "API", "데이터베이스", "서버",
        "프론트엔드", "백엔드", "배포", "테스트", "디버그", "리팩터", "알고리즘",
        "라이브러리", "프레임워크", "Git", "CI/CD", "Docker", "Python", "JavaScript",
        "TypeScript", "React", "FastAPI", "SQL", "NoSQL", "REST", "GraphQL",
        "code", "function", "class", "deploy", "debug", "refactor", "algorithm",
        "library", "framework", "database", "server", "frontend", "backend",
    ],
    "건설/인테리어": [
        "건설", "인테리어", "시공", "설계", "견적", "공사", "자재", "도면", "시방서",
        "발주", "하도급", "현장", "공정", "기초", "골조", "마감", "전기", "배관",
        "단열", "방수", "타일", "바닥재", "조명", "가구", "리모델링", "인테리어",
        "건축", "구조", "토목", "철근", "콘크리트", "방음",
        "construction", "interior", "renovation", "design", "material", "blueprint",
        "contractor", "subcontractor", "estimate", "flooring", "plumbing", "wiring",
    ],
    "AI/에이전트": [
        "AI", "인공지능", "머신러닝", "딥러닝", "LLM", "에이전트", "프롬프트",
        "임베딩", "벡터", "RAG", "파인튜닝", "모델", "추론", "Claude", "GPT",
        "Anthropic", "OpenAI", "토큰", "컨텍스트", "체인", "오케스트레이션",
        "자동화", "워크플로", "챗봇", "어시스턴트", "지식그래프", "지식베이스",
        "agent", "prompt", "embedding", "vector", "fine-tuning", "inference",
        "context", "chain", "orchestration", "automation", "workflow", "chatbot",
        "knowledge graph", "knowledge base", "assistant",
    ],
}

# 카테고리 → Obsidian 태그 형식
CATEGORY_TAG_MAP: dict[str, str] = {
    "법률":       "category/법률",
    "개발":       "category/개발",
    "건설/인테리어": "category/건설-인테리어",
    "AI/에이전트": "category/AI-에이전트",
}

# ── Phase 3: 중복 감지 캐시 파일 ──────────────────────────────────────────────
CONTENT_HASH_REGISTRY = SCRIPTS_DIR / ".distiller_content_hashes.json"

# ── Phase 3: 우선순위 점수 상수 ────────────────────────────────────────────────
PRIORITY_RECENCY_DAYS   = 30   # 최근 N일 이내 파일에 가중치
PRIORITY_RECENCY_BONUS  = 3.0  # 최근 파일 보너스 점수
PRIORITY_MENTION_WEIGHT = 0.5  # 토픽 1회 언급당 추가 점수
PRIORITY_CONFIDENCE_W   = 2.0  # confidence 가중치

# ──────────────────────────────────────────────────────────────────────────────

def detect_source_type(path: Path) -> str:
    """파일명·경로에서 소스 유형(gpt/claude/codex/unknown)을 감지한다."""
    search_str = str(path).lower()
    for src, pattern in SOURCE_PATTERNS.items():
        if pattern.search(search_str):
            return src
    return "unknown"


# ── 소스별 시스템 프롬프트 ─────────────────────────────────────────────────────

_BASE_SCHEMA = textwrap.dedent("""
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

    공통 규칙:
    - insights는 3~7개. 구체적이고 재사용 가능한 지식으로 압축.
    - topics는 2~6개의 소문자 영문 또는 한글 태그.
    - related_knowledge는 [[wikilink]] 형태로 연관 개념/주제 2~5개.
    - tasks는 문서에서 실행 가능한 행동이 있을 때만 포함, 없으면 빈 배열 [].
    - confidence는 내용 명확도 (0.9=매우 명확, 0.5=모호/노이즈 많음).
    - 파일 인코딩 문제로 깨진 텍스트가 있어도 읽을 수 있는 내용 위주로 처리.
""").strip()

SYSTEM_PROMPTS: dict[str, str] = {
    "gpt": textwrap.dedent("""
        당신은 ChatGPT/GPT 세션 정제 전문가입니다.
        GPT 대화 기록에서 핵심 지식·패턴·프롬프트 전략을 추출합니다.
        GPT 특유의 장황한 설명체를 걸러내고 실질적 인사이트만 보존하세요.
        프롬프트 엔지니어링 팁, 모델 행동 패턴, 활용 전략에 주목하세요.
    """).strip() + "\n\n" + _BASE_SCHEMA,

    "claude": textwrap.dedent("""
        당신은 Claude 세션 정제 전문가입니다.
        Claude 대화 기록에서 추론 과정, 아키텍처 결정, 코드 설계 원칙을 추출합니다.
        Claude의 사고 체인과 대안 검토 과정에서 재사용 가능한 패턴을 도출하세요.
        시스템 설계, 에이전트 패턴, 프롬프트 캐싱 전략에 주목하세요.
    """).strip() + "\n\n" + _BASE_SCHEMA,

    "codex": textwrap.dedent("""
        당신은 Codex/코드 생성 세션 정제 전문가입니다.
        코드 생성 세션에서 재사용 가능한 코드 패턴, 알고리즘, 구현 전략을 추출합니다.
        코드 품질 원칙, 리팩터링 기법, 테스트 전략, 성능 최적화 패턴에 주목하세요.
        구체적인 코드 스니펫보다는 설계 원칙과 패턴을 우선 추출하세요.
    """).strip() + "\n\n" + _BASE_SCHEMA,

    "unknown": textwrap.dedent("""
        당신은 지식 정제 전문가입니다.
        사용자가 제공하는 원시 대화/메모 파일을 분석하여 구조화된 지식 노트를 생성합니다.
    """).strip() + "\n\n" + _BASE_SCHEMA,
}

# 기본 시스템 프롬프트 (하위 호환)
SYSTEM_PROMPT = SYSTEM_PROMPTS["unknown"]

USER_PROMPT_TEMPLATE = textwrap.dedent("""
    다음 원시 파일을 분석하여 지식 노트를 생성하세요.

    파일 경로: {file_path}
    파일 날짜: {file_date}
    소스 유형: {source_type}

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
    Phase 2: claude-sessions/, codex-sessions/ 도 자동 포함.
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

    # Phase 2: claude-sessions/ 추가 스캔 (01_RAW 외부일 경우 대비)
    for sessions_dir in (CLAUDE_SESSIONS_DIR, CODEX_SESSIONS_DIR):
        if sessions_dir.exists() and sessions_dir not in RAW_DIR.parents and sessions_dir != RAW_DIR:
            for md in sessions_dir.rglob("*.md"):
                if md.name.lower() not in ("index.md", "readme.md"):
                    if md not in candidates:
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


def read_file_safe(path: Path) -> str:
    """파일을 안전하게 읽는다. 인코딩 오류는 replace 처리. 길이 제한 없음."""
    for encoding in ("utf-8", "utf-8-sig", "cp949", "latin-1"):
        try:
            return path.read_text(encoding=encoding, errors="replace")
        except OSError as e:
            print(f"  [WARN] {encoding} 읽기 실패: {e}")
    return "[파일 읽기 실패]"


def split_into_chunks(text: str, chunk_size: int = CHUNK_SIZE) -> list[str]:
    """
    텍스트를 chunk_size 문자 단위로 분할한다.
    단락 경계(빈 줄)를 우선 탐색하여 자연스럽게 분할.
    """
    if len(text) <= CHUNK_MAX_CHARS:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        if end >= len(text):
            chunks.append(text[start:])
            break
        # 단락 경계 탐색: end 앞쪽 500자 내에서 빈 줄 찾기
        boundary = text.rfind("\n\n", start, end)
        if boundary == -1 or boundary <= start:
            # 단락 경계가 없으면 줄 경계 탐색
            boundary = text.rfind("\n", start, end)
        if boundary == -1 or boundary <= start:
            boundary = end
        chunks.append(text[start:boundary])
        start = boundary
    return chunks


def merge_chunk_results(results: list[dict]) -> dict:
    """
    여러 청크의 distill 결과를 하나로 병합한다.
    - topics: 합집합 (중복 제거, 최대 8개)
    - insights: 합집합 (중복 제거, 최대 10개)
    - related_knowledge: 합집합 (중복 제거, 최대 7개)
    - tasks: 합집합
    - confidence: 평균
    - summary: 첫 번째 청크 요약 + 추가 요약 결합
    """
    if not results:
        return {}
    if len(results) == 1:
        return results[0]

    seen_insights:  set[str] = set()
    seen_topics:    set[str] = set()
    seen_related:   set[str] = set()
    seen_tasks:     set[str] = set()

    all_topics:   list[str] = []
    all_insights: list[str] = []
    all_related:  list[str] = []
    all_tasks:    list[str] = []
    all_summaries: list[str] = []
    confidence_sum = 0.0

    for r in results:
        for t in r.get("topics", []):
            if t not in seen_topics:
                seen_topics.add(t)
                all_topics.append(t)
        for i in r.get("insights", []):
            if i not in seen_insights:
                seen_insights.add(i)
                all_insights.append(i)
        for rel in r.get("related_knowledge", []):
            if rel not in seen_related:
                seen_related.add(rel)
                all_related.append(rel)
        for task in r.get("tasks", []):
            if task not in seen_tasks:
                seen_tasks.add(task)
                all_tasks.append(task)
        confidence_sum += r.get("confidence", 0.8)
        if r.get("summary"):
            all_summaries.append(r["summary"])

    summary = all_summaries[0] if all_summaries else ""
    if len(all_summaries) > 1:
        summary += " / " + " | ".join(all_summaries[1:])

    return {
        "topics":           all_topics[:8],
        "insights":         all_insights[:10],
        "related_knowledge": all_related[:7],
        "tasks":            all_tasks,
        "confidence":       round(confidence_sum / len(results), 2),
        "summary":          summary,
    }


# ── Claude API 호출 (재시도 + 프롬프트 캐싱) ──────────────────────────────────

def distill_with_claude(
    client: anthropic.Anthropic,
    file_path: Path,
    content: str,
    file_date: str,
    stats: dict,
    source_type: str = "unknown",
) -> dict:
    """
    Claude API를 호출해 원시 파일에서 지식을 추출한다.
    - source_type에 따라 전문화된 시스템 프롬프트 사용
    - system prompt에 cache_control 적용 (비용 절감)
    - 실패 시 exponential backoff 3회 재시도
    반환: 파싱된 JSON dict
    """
    system_prompt = SYSTEM_PROMPTS.get(source_type, SYSTEM_PROMPTS["unknown"])

    user_message = USER_PROMPT_TEMPLATE.format(
        file_path=str(file_path),
        file_date=file_date,
        source_type=source_type,
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
                        "text": system_prompt,
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


# ── 청크 처리 래퍼 ────────────────────────────────────────────────────────────

def distill_file(
    client: anthropic.Anthropic,
    file_path: Path,
    content: str,
    file_date: str,
    stats: dict,
    source_type: str = "unknown",
) -> dict:
    """
    파일 내용이 CHUNK_MAX_CHARS 초과 시 청크로 분할 처리 후 결과를 병합한다.
    8000자 이하이면 단일 API 호출.
    """
    chunks = split_into_chunks(content)
    if len(chunks) == 1:
        return distill_with_claude(client, file_path, content, file_date, stats, source_type)

    print(f"    [CHUNK] {len(content):,}자 → {len(chunks)}개 청크 분할 처리")
    results: list[dict] = []
    for i, chunk in enumerate(chunks, 1):
        print(f"    [CHUNK {i}/{len(chunks)}] {len(chunk):,}자 처리 중...")
        result = distill_with_claude(client, file_path, chunk, file_date, stats, source_type)
        results.append(result)

    merged = merge_chunk_results(results)
    print(f"    [CHUNK] 병합 완료 — 인사이트 {len(merged.get('insights', []))}개, "
          f"토픽 {len(merged.get('topics', []))}개")
    return merged


# ── Obsidian Wikilink 검증 ─────────────────────────────────────────────────────

_vault_filenames_cache: set[str] | None = None


def _load_vault_filenames() -> set[str]:
    """
    ObsidianVault 전체의 .md 파일 스템 목록을 캐싱하여 반환.
    첫 호출 시 glob으로 수집, 이후 캐시 재사용.
    """
    global _vault_filenames_cache
    if _vault_filenames_cache is not None:
        return _vault_filenames_cache

    names: set[str] = set()
    for md in VAULT_BASE.rglob("*.md"):
        names.add(md.stem)
        names.add(md.stem.lower())
    _vault_filenames_cache = names
    return names


def _extract_wikilink_name(link: str) -> str:
    """'[[파일명]]' 또는 '[[파일명|표시텍스트]]' 에서 파일명 추출."""
    inner = link.strip("[]")
    if "|" in inner:
        inner = inner.split("|")[0]
    if "#" in inner:
        inner = inner.split("#")[0]
    return inner.strip()


def validate_wikilinks(related: list[str]) -> list[str]:
    """
    related_knowledge 목록에서 Vault에 실제로 존재하는 파일과 매칭되는
    wikilink만 반환한다. 매칭되지 않는 링크는 원본 유지 (Obsidian이 자동으로
    새 파일 생성 제안). 매칭된 링크는 실제 파일명으로 보정.
    """
    vault_names = _load_vault_filenames()
    validated: list[str] = []

    for link in related:
        raw_name = _extract_wikilink_name(link)
        if not raw_name:
            continue

        # 정확히 일치하는지 확인
        if raw_name in vault_names:
            validated.append(f"[[{raw_name}]]")
            continue

        # 소문자 비교
        raw_lower = raw_name.lower()
        if raw_lower in vault_names:
            validated.append(f"[[{raw_name}]]")
            continue

        # 부분 매칭 (파일명이 링크 텍스트를 포함하는 경우)
        matched = [n for n in vault_names if raw_lower in n.lower() and len(n) < 60]
        if matched:
            # 가장 짧은(가장 구체적인) 매칭 선택
            best = min(matched, key=len)
            validated.append(f"[[{best}]]")
            continue

        # 매칭 없음 — 원본 유지
        if link.startswith("[["):
            validated.append(link)
        else:
            validated.append(f"[[{link}]]")

    # 중복 제거 (순서 유지)
    seen: set[str] = set()
    deduped: list[str] = []
    for v in validated:
        if v not in seen:
            seen.add(v)
            deduped.append(v)
    return deduped


# ── Phase 3: 자동 태깅 ────────────────────────────────────────────────────────

def auto_tag(content: str, topics: list[str]) -> list[str]:
    """
    Phase 3: 파일 내용과 토픽 목록에서 카테고리 태그를 자동 생성한다.

    탐지 방법:
    1. content + topics 를 합친 검색 문자열에서 카테고리별 키워드 출현 횟수 집계.
    2. 출현 횟수가 가장 많은 카테고리를 주 카테고리로, 2위(임계치 이상)를 부 카테고리로 선택.
    3. 반환 형식: ["category/AI-에이전트", "category/개발"] (CATEGORY_TAG_MAP 기준)

    Args:
        content: 원본 파일 텍스트
        topics:  Claude API가 반환한 topics 리스트

    Returns:
        Obsidian 태그 형식의 카테고리 태그 목록 (0~2개)
    """
    search_text = (content + " " + " ".join(topics)).lower()

    scores: dict[str, int] = {}
    for category, keywords in CATEGORY_KEYWORD_MAP.items():
        count = 0
        for kw in keywords:
            # 단어 경계 없이 단순 포함 여부로 계산 (한글 지원)
            count += search_text.count(kw.lower())
        scores[category] = count

    # 점수 0인 카테고리 제거
    scores = {k: v for k, v in scores.items() if v > 0}
    if not scores:
        return []

    # 내림차순 정렬
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    result_tags: list[str] = []
    top_score = ranked[0][1]

    # 1위 카테고리 (항상 포함)
    result_tags.append(CATEGORY_TAG_MAP[ranked[0][0]])

    # 2위 카테고리: 1위 점수의 40% 이상일 때만 포함 (노이즈 방지)
    if len(ranked) >= 2:
        second_score = ranked[1][1]
        if top_score > 0 and second_score / top_score >= 0.4:
            result_tags.append(CATEGORY_TAG_MAP[ranked[1][0]])

    return result_tags


# ── Phase 3: 콘텐츠 해시 기반 중복 감지 ────────────────────────────────────────

def _load_content_hash_registry() -> dict:
    """콘텐츠 해시 레지스트리 로드. 없으면 빈 dict 반환."""
    if CONTENT_HASH_REGISTRY.exists():
        try:
            return json.loads(CONTENT_HASH_REGISTRY.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_content_hash_registry(registry: dict) -> None:
    """콘텐츠 해시 레지스트리 저장."""
    CONTENT_HASH_REGISTRY.write_text(
        json.dumps(registry, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def content_hash(text: str) -> str:
    """
    텍스트 콘텐츠의 SHA-256 해시를 반환한다.
    공백·줄바꿈을 정규화한 뒤 해싱하여 공백 차이로 인한 미스매치를 방지.
    """
    normalized = re.sub(r"\s+", " ", text.strip())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:64]


def detect_duplicates(
    file_path: Path,
    content: str,
    registry: dict,
) -> tuple[bool, str | None]:
    """
    Phase 3: 콘텐츠 해시 기반 전역 중복 감지.

    파일명이 달라도 내용이 동일하면 중복으로 판정한다.
    registry는 {content_hash: file_path_str} 형태.

    Args:
        file_path: 현재 처리 대상 파일 경로
        content:   파일 내용 문자열
        registry:  콘텐츠 해시 → 최초 파일 경로 매핑 dict (in-place 업데이트)

    Returns:
        (is_duplicate, original_file_path_str)
        is_duplicate=True 이면 원본 파일 경로를 함께 반환.
    """
    chash = content_hash(content)
    file_str = str(file_path)

    if chash in registry:
        existing = registry[chash]
        if existing != file_str:
            # 동일 내용, 다른 파일 → 중복
            return True, existing

    # 신규 → 레지스트리에 등록
    registry[chash] = file_str
    return False, None


# ── Phase 3: 지식 그래프 wikilink 생성 ────────────────────────────────────────

def _load_distilled_topics() -> dict[str, list[str]]:
    """
    OUTPUT_BASE 디렉터리에 있는 기존 정제 노트들의
    {파일명 stem: topics 리스트} 맵을 반환한다.
    최대 500개 파일까지 스캔 (성능 보호).
    """
    topic_map: dict[str, list[str]] = {}
    if not OUTPUT_BASE.exists():
        return topic_map

    scanned = 0
    for md in OUTPUT_BASE.rglob("*.md"):
        if scanned >= 500:
            break
        topics = _extract_frontmatter_topics(md)
        if topics:
            topic_map[md.stem] = topics
        scanned += 1

    return topic_map


def generate_wikilinks(result: dict, current_output_stem: str | None = None) -> list[str]:
    """
    Phase 3: 기존 정제 노트와 토픽 유사도를 비교해 [[wikilink]] 를 자동 생성한다.

    알고리즘:
    1. OUTPUT_BASE 의 기존 노트 → {stem: topics} 맵 로드.
    2. 현재 result 의 topics 와 각 기존 노트의 topics 의 교집합 계산.
    3. 교집합이 1개 이상인 노트를 유사 노트로 선정.
    4. 교집합 크기 내림차순 정렬 → 상위 5개 선택.
    5. "[[파일명]]" 형태로 반환.

    Args:
        result:              distill 결과 dict (topics 키 사용)
        current_output_stem: 현재 출력 파일의 stem (자기 자신 링크 방지)

    Returns:
        [[wikilink]] 형태의 문자열 목록 (최대 5개, 중복 없음)
    """
    new_topics = set(result.get("topics", []))
    if not new_topics:
        return []

    distilled_map = _load_distilled_topics()
    if not distilled_map:
        return []

    # (overlap_count, note_stem) 목록
    candidates: list[tuple[int, str]] = []
    for stem, topics in distilled_map.items():
        if stem == current_output_stem:
            continue  # 자기 자신 제외
        overlap = len(new_topics & set(topics))
        if overlap >= 1:
            candidates.append((overlap, stem))

    # 교집합 크기 내림차순 정렬
    candidates.sort(key=lambda x: x[0], reverse=True)

    # 상위 5개 선택, wikilink 형식으로 변환
    links: list[str] = []
    seen: set[str] = set()
    for _, stem in candidates[:5]:
        link = f"[[{stem}]]"
        if link not in seen:
            seen.add(link)
            links.append(link)

    return links


# ── Phase 3: 우선순위 점수 산출 ───────────────────────────────────────────────

def _count_topic_mentions_in_vault(topics: list[str]) -> int:
    """
    OUTPUT_BASE 의 기존 정제 노트 frontmatter 에서 topics 가 언급된 총 횟수.
    성능 상 최대 300개 파일 스캔.
    """
    if not topics or not OUTPUT_BASE.exists():
        return 0

    topic_set = {t.lower() for t in topics}
    mention_count = 0
    scanned = 0

    for md in OUTPUT_BASE.rglob("*.md"):
        if scanned >= 300:
            break
        existing = _extract_frontmatter_topics(md)
        for t in existing:
            if t.lower() in topic_set:
                mention_count += 1
        scanned += 1

    return mention_count


def priority_score(
    result: dict,
    file_date: str,
    file_path: Path,
) -> float:
    """
    Phase 3: 지식 노트의 우선순위 점수를 산출한다.

    점수 구성:
    - 최신성 (recency)   : 파일 날짜가 최근 PRIORITY_RECENCY_DAYS 일 이내면 +PRIORITY_RECENCY_BONUS
    - 빈도 (frequency)   : Vault 기존 노트에서 동일 토픽 언급 횟수 × PRIORITY_MENTION_WEIGHT
    - 신뢰도 (confidence): result["confidence"] × PRIORITY_CONFIDENCE_W
    - 인사이트 수         : insights 개수 × 0.3

    점수 범위는 대략 0.0 ~ 10.0 (소수점 2자리 반올림).

    Args:
        result:    distill 결과 dict
        file_date: "YYYY-MM-DD" 형식 날짜 문자열
        file_path: 원본 파일 경로 (파일 수정시각 보조 활용)

    Returns:
        float 우선순위 점수 (높을수록 중요)
    """
    score = 0.0

    # 1. 최신성 점수
    try:
        file_dt = datetime.strptime(file_date, "%Y-%m-%d")
        days_old = (datetime.now() - file_dt).days
        if days_old <= PRIORITY_RECENCY_DAYS:
            score += PRIORITY_RECENCY_BONUS
        elif days_old <= PRIORITY_RECENCY_DAYS * 3:
            # 점진적 감쇠
            score += PRIORITY_RECENCY_BONUS * (1 - days_old / (PRIORITY_RECENCY_DAYS * 3))
    except ValueError:
        pass

    # 파일 수정시각도 보조로 활용 (실제 mtime 이 더 최신이면 보정)
    try:
        mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
        mtime_days_old = (datetime.now() - mtime).days
        if mtime_days_old <= PRIORITY_RECENCY_DAYS:
            score += PRIORITY_RECENCY_BONUS * 0.5  # 절반 보너스
    except OSError:
        pass

    # 2. 토픽 빈도 점수 (기존 Vault에서 같은 토픽이 많이 언급될수록 = 중요한 주제)
    topics = result.get("topics", [])
    mention_count = _count_topic_mentions_in_vault(topics)
    score += mention_count * PRIORITY_MENTION_WEIGHT

    # 3. 신뢰도 점수
    confidence = float(result.get("confidence", 0.8))
    score += confidence * PRIORITY_CONFIDENCE_W

    # 4. 인사이트 수 점수
    insight_count = len(result.get("insights", []))
    score += insight_count * 0.3

    return round(score, 2)


# ── Discord Webhook ────────────────────────────────────────────────────────────

def send_discord_summary(stats: dict, elapsed_sec: float) -> None:
    """
    처리 완료 통계를 Discord Webhook으로 전송한다.
    DISCORD_WEBHOOK_URL 환경변수가 없으면 건너뜀.
    """
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
    if not webhook_url:
        return

    mins, secs = divmod(int(elapsed_sec), 60)
    elapsed_str = f"{mins}분 {secs}초" if mins else f"{secs}초"

    cache_info = ""
    if stats.get("cache_creation_tokens") or stats.get("cache_read_tokens"):
        total_in = (
            stats["input_tokens"]
            + stats["cache_creation_tokens"]
            + stats["cache_read_tokens"]
        )
        hit_rate = (stats["cache_read_tokens"] / total_in * 100) if total_in > 0 else 0
        cache_info = (
            f"\n> 캐시 생성: {stats['cache_creation_tokens']:,}  "
            f"재사용: {stats['cache_read_tokens']:,}  "
            f"히트율: {hit_rate:.1f}%"
        )

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    content = (
        f"**[Knowledge Distiller] 처리 완료** — {now_str}\n"
        f"> 처리: **{stats['processed']}건**  "
        f"실패: {stats['failed']}건  "
        f"건너뜀: {stats['skipped']}건\n"
        f"> 소요시간: {elapsed_str}\n"
        f"> 토큰 — 입력: {stats['input_tokens']:,}  출력: {stats['output_tokens']:,}"
        f"{cache_info}"
    )

    payload = json.dumps({"content": content}).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status not in (200, 204):
                print(f"  [DISCORD] 전송 실패: HTTP {resp.status}")
            else:
                print(f"  [DISCORD] 통계 전송 완료")
    except urllib.error.URLError as e:
        print(f"  [DISCORD] 전송 오류: {e}")


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
    source_type: str = "unknown",
    category_tags: list[str] | None = None,
    graph_wikilinks: list[str] | None = None,
    p3_priority: float | None = None,
    source_conversation_id: str | None = None,
    supersedes: str | None = None,
    valid_until: str | None = None,
    last_verified: str | None = None,
) -> str:
    """
    추출 결과를 Obsidian Markdown 노트로 변환한다.

    Phase 3 추가 파라미터:
        category_tags   : auto_tag() 반환값 (카테고리 태그 목록)
        graph_wikilinks : generate_wikilinks() 반환값 (그래프 기반 wikilink)
        p3_priority     : priority_score() 반환값 (0.0~10.0 우선순위 점수)

    Stage 20 추가 파라미터 (01_RAW provenance, 모두 선택):
        source_conversation_id : 01_RAW frontmatter의 conversation_id 전파값
        supersedes/valid_until/last_verified : 향후 단계에서 채울 예약 필드 (현재는 배관만)
    """
    topics     = result.get("topics", [])
    confidence = result.get("confidence", 0.8)
    insights   = result.get("insights", [])
    related    = result.get("related_knowledge", [])
    tasks      = result.get("tasks", [])
    summary    = result.get("summary", "")

    # 소스 태그 자동 생성 (#source/gpt, #source/claude, #source/codex)
    source_tag = SOURCE_TAG_MAP.get(source_type, SOURCE_TAG_MAP["unknown"])

    # Phase 3: 카테고리 태그 병합
    cat_tags = category_tags or []

    # frontmatter tags: ai-distilled + source 태그 + category 태그
    fm_tags = ["ai-distilled", source_tag] + cat_tags
    # topics도 frontmatter tags에 포함
    all_tags = fm_tags + topics
    tags_yaml = "[" + ", ".join(all_tags) + "]"

    topics_yaml  = "[" + ", ".join(topics) + "]"
    related_yaml = "[" + ", ".join(f'"{t}"' for t in related) + "]"

    insights_md = "\n".join(f"- {i}" for i in insights) if insights else "- (인사이트 없음)"
    related_md  = "\n".join(f"- {r}" for r in related)  if related  else "- (연결 개념 없음)"
    tasks_md    = "\n".join(tasks) if tasks else "- (실행 태스크 없음)"

    # Phase 3: 지식 그래프 wikilink 섹션
    graph_links = graph_wikilinks or []
    graph_md = "\n".join(f"- {lnk}" for lnk in graph_links) if graph_links else "- (연결된 노트 없음)"

    # 인라인 태그 (소스 태그 + 카테고리 태그 + 토픽 태그)
    inline_tags_parts = [f"#{source_tag}"] + [f"#{ct}" for ct in cat_tags]
    if topics:
        inline_tags_parts += [f"#{t}" for t in topics]
    inline_tags = " ".join(inline_tags_parts)

    # Phase 3: 우선순위 레이블
    priority_label = ""
    if p3_priority is not None:
        if p3_priority >= 7.0:
            priority_label = " 🔴 HIGH"
        elif p3_priority >= 4.0:
            priority_label = " 🟡 MEDIUM"
        else:
            priority_label = " 🟢 LOW"

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    note = textwrap.dedent(f"""
        ---
        source: {source_path.name}
        source_type: {source_type}
        date: {file_date}
        original_file: "{source_path}"
        source_conversation_id: {f'"{source_conversation_id}"' if source_conversation_id else ""}
        source_file: "{source_path}"
        topics: {topics_yaml}
        related: {related_yaml}
        confidence: {confidence}
        priority: {p3_priority if p3_priority is not None else ""}
        category_tags: [{", ".join(cat_tags)}]
        distilled_at: {now_str}
        supersedes: {supersedes if supersedes else ""}
        valid_until: {valid_until if valid_until else ""}
        last_verified: {last_verified if last_verified else ""}
        tags: {tags_yaml}
        ---

        > {summary}

        ## 핵심 인사이트

        {insights_md}

        ## 연결 개념

        {related_md}

        ## 지식 그래프 링크{priority_label}

        {graph_md}

        ## 실행 가능한 태스크

        {tasks_md}

        ## 태그

        {inline_tags}

        ---
        *자동 생성: knowledge_distiller.py — 원본: `{source_path.name}` — 소스: {source_type}*
        *Phase 3 — 카테고리: {", ".join(cat_tags) or "없음"} — 우선순위: {p3_priority}*
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


# ── Stage 20: 원본 provenance 추출 ──────────────────────────────────────────

def extract_conversation_id(text: str) -> str | None:
    """
    01_RAW frontmatter에서 conversation_id 값을 추출한다. 없으면 None.
    """
    # 일부 볼트 md 파일은 선두에 UTF-8 BOM이 붙어 있어 frontmatter 시작(---) 매칭이 깨진다.
    text = text.lstrip("﻿")

    fm_match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not fm_match:
        return None

    fm_text = fm_match.group(1)
    cid_match = re.search(r"^conversation_id:\s*(.*)$", fm_text, re.MULTILINE)
    if not cid_match:
        return None

    value = cid_match.group(1).strip().strip('"').strip("'").strip()
    return value or None


# ── Phase 2: 주제 기반 중복 감지 및 병합 ──────────────────────────────────────

def _extract_frontmatter_topics(md_path: Path) -> list[str]:
    """
    기존 노트의 frontmatter에서 topics 목록을 추출한다.
    파싱 실패 시 빈 리스트 반환.
    """
    try:
        text = md_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    # frontmatter 블록 추출 (--- ... ---)
    fm_match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not fm_match:
        return []

    fm_text = fm_match.group(1)
    topics_match = re.search(r"^topics:\s*\[([^\]]*)\]", fm_text, re.MULTILINE)
    if not topics_match:
        return []

    raw = topics_match.group(1)
    topics = [t.strip().strip('"\'') for t in raw.split(",") if t.strip()]
    return topics


def find_existing_note_by_topic(result: dict, output_dir: Path) -> Path | None:
    """
    output_dir 내에 동일 주제 토픽을 2개 이상 공유하는 기존 노트를 탐색한다.
    찾으면 해당 Path 반환, 없으면 None.
    """
    new_topics = set(result.get("topics", []))
    if not new_topics or not output_dir.exists():
        return None

    for existing_md in output_dir.glob("*.md"):
        existing_topics = set(_extract_frontmatter_topics(existing_md))
        overlap = new_topics & existing_topics
        if len(overlap) >= 2:
            return existing_md
    return None


def merge_into_existing_note(
    existing_path: Path,
    result: dict,
    source_path: Path,
    source_conversation_id: str | None = None,
) -> None:
    """
    Phase 2: 같은 주제 노트가 이미 존재할 때 overwrite 하지 않고 병합한다.
    - 새로운 insights만 기존 노트 하단에 append
    - 새 topics/related_knowledge도 frontmatter에 병합
    - 기존 내용은 변경하지 않는다

    Stage 20: 병합 블록에도 원본 경로와 source_conversation_id를 기록한다. 기존 노트의
    frontmatter는 최초 원본만 가리키므로, 병합된 내용의 출처는 병합 블록이 유일한 근거다.
    """
    try:
        existing_text = existing_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return

    new_insights = result.get("insights", [])
    new_topics   = result.get("topics", [])
    new_related  = result.get("related_knowledge", [])
    new_tasks    = result.get("tasks", [])

    # 기존 노트에서 이미 있는 항목 추출 (중복 방지).
    # insights·related_knowledge는 둘 다 "- " 라인으로 기록되므로 같은 집합으로 판정한다.
    existing_bullets: set[str] = set(
        re.findall(r"^- (.+)$", existing_text, re.MULTILINE)
    )
    unique_insights = [i for i in new_insights if i not in existing_bullets]
    unique_related  = [r for r in new_related if r not in existing_bullets]
    # 태스크는 원문 그대로 기록되므로 본문 포함 여부로 판정한다.
    unique_tasks    = [t for t in new_tasks if t.strip() and t.strip() not in existing_text]

    if not unique_insights and not unique_tasks and not unique_related:
        # 추가할 내용이 없으면 병합 불필요 — 재처리(--reset/--retry)를 멱등하게 만든다.
        return

    now_str     = datetime.now().strftime("%Y-%m-%d %H:%M")
    # provenance 라인은 "- " 로 시작하지 않는다 — 위 existing_insights 정규식이
    # 다음 병합 때 이 라인들을 인사이트로 오인 수집하는 것을 막는다.
    append_lines = [
        f"\n\n---\n## 병합 추가 — {now_str} (원본: `{source_path.name}`)\n",
        f"**source_file**: `{source_path}`",
        f"**source_conversation_id**: `{source_conversation_id}`" if source_conversation_id
        else "**source_conversation_id**: (없음)",
    ]
    if unique_insights:
        append_lines.append("### 추가 인사이트\n")
        append_lines.extend(f"- {i}" for i in unique_insights)
    if unique_tasks:
        append_lines.append("\n### 추가 태스크\n")
        append_lines.extend(unique_tasks)
    if unique_related:
        append_lines.append("\n### 추가 연결 개념\n")
        append_lines.extend(f"- {r}" for r in unique_related)

    with existing_path.open("a", encoding="utf-8") as f:
        f.write("\n".join(append_lines))

    # frontmatter의 topics 업데이트 (기존 + 신규 합집합)
    existing_topics = set(_extract_frontmatter_topics(existing_path))
    merged_topics   = sorted(existing_topics | set(new_topics))
    if merged_topics != sorted(existing_topics):
        updated_text = existing_path.read_text(encoding="utf-8", errors="replace")
        new_topics_yaml = "[" + ", ".join(merged_topics) + "]"
        updated_text = re.sub(
            r"^(topics:\s*)\[[^\]]*\]",
            f"\\g<1>{new_topics_yaml}",
            updated_text,
            flags=re.MULTILINE,
        )
        existing_path.write_text(updated_text, encoding="utf-8")


# ── Stage 20: 처리 완료 사이드카 인덱스 ─────────────────────────────────────────

def append_processed_index(raw_file: Path, conversation_id: str | None, output_path: Path) -> None:
    """
    01_RAW 파일의 정제 완료 여부를 sidecar 인덱스에 append-only로 기록한다.
    01_RAW 원본은 절대 수정하지 않는다.
    """
    PROCESSED_INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "file": str(raw_file),
        "conversation_id": conversation_id,
        "output_path": str(output_path),
        "processed_at": datetime.now().isoformat(),
    }
    with PROCESSED_INDEX_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ── 에러 리포트 ────────────────────────────────────────────────────────────────

def append_error_report(error_entries: list[dict]) -> None:
    """
    실패한 파일 목록을 ObsidianVault/00_System/distiller-errors.md에 기록한다.
    기존 파일에 이어 쓴다 (append).
    """
    if not error_entries:
        return

    ERROR_REPORT.parent.mkdir(parents=True, exist_ok=True)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = [f"\n## {now_str} — 오류 {len(error_entries)}건\n"]
    for entry in error_entries:
        lines.append(f"- `{entry['file']}` — {entry['error']}")
    lines.append("")

    with ERROR_REPORT.open("a", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"  [ERROR-REPORT] {len(error_entries)}건 기록 → {ERROR_REPORT}")


def _ensure_error_report_header() -> None:
    """에러 리포트 파일이 없으면 헤더를 생성한다."""
    if not ERROR_REPORT.exists():
        ERROR_REPORT.parent.mkdir(parents=True, exist_ok=True)
        ERROR_REPORT.write_text(
            textwrap.dedent("""
                ---
                title: Distiller Error Report
                tags: [system, error-log]
                ---

                # Knowledge Distiller 오류 기록

                > 자동 생성: `knowledge_distiller.py`
                > 실패한 파일은 `--retry` 옵션으로 재처리하세요.

            """).lstrip(),
            encoding="utf-8",
        )


# ── 배치 처리 ──────────────────────────────────────────────────────────────────

def process_batch(
    client: anthropic.Anthropic,
    batch: list[Path],
    state: dict,
    stats: dict,
    batch_num: int,
    total_batches: int,
    content_hash_registry: dict | None = None,
) -> tuple[int, int]:
    """
    배치(N개 파일) 처리.
    - 소스 유형(gpt/claude/codex/unknown) 자동 감지
    - 중복 감지: 파일명 해시 기반으로 이미 처리된 파일 건너뜀
    - Phase 2: 같은 주제 노트 존재 시 병합 (overwrite 금지)
    - Phase 3: auto_tag / detect_duplicates / generate_wikilinks / priority_score 통합
    - 에러 발생 시 distiller-errors.md에 기록
    반환: (success_count, fail_count)
    """
    success = 0
    fail    = 0
    error_entries: list[dict] = []

    # Phase 3: 배치 전역 콘텐츠 해시 레지스트리 (전달 안 되면 새로 로드)
    if content_hash_registry is None:
        content_hash_registry = _load_content_hash_registry()

    print(f"\n[배치 {batch_num}/{total_batches}] {len(batch)}개 파일 처리 중...")

    for idx, raw_file in enumerate(batch, 1):
        global_idx = (batch_num - 1) * len(batch) + idx
        try:
            rel_path = raw_file.relative_to(VAULT_BASE)
        except ValueError:
            rel_path = raw_file  # VAULT_BASE 외부 경로(claude-sessions 등) 절대경로 표시
        file_date  = extract_date_from_path(raw_file)
        source_type = detect_source_type(raw_file)
        print(f"  [{global_idx}] {rel_path}  (날짜: {file_date}, 소스: {source_type})")

        content = read_file_safe(raw_file)
        if content == "[파일 읽기 실패]":
            print("    [SKIP] 파일 읽기 실패")
            fail += 1
            stats["failed"] += 1
            error_entries.append({"file": str(raw_file), "error": "파일 읽기 실패"})
            continue

        if len(content.strip()) < 30:
            print("    [SKIP] 내용이 너무 짧음 (30자 미만)")
            stats["skipped"] += 1
            continue

        # Phase 3: 콘텐츠 해시 기반 전역 중복 감지 (파일명 무관)
        is_dup, dup_original = detect_duplicates(raw_file, content, content_hash_registry)
        if is_dup:
            print(f"    [SKIP-P3] 콘텐츠 중복 — 원본: {dup_original}")
            stats["skipped"] += 1
            _save_content_hash_registry(content_hash_registry)
            continue

        # Phase 1/2 중복 감지: 출력 파일이 이미 동일 해시로 존재하는지 확인
        output_path_candidate = determine_output_path(file_date, raw_file)
        if output_path_candidate.exists():
            # 출력 파일의 source 메타에서 원본 해시를 state로 재확인
            current_hash = file_hash(raw_file)
            if state.get(str(raw_file)) == current_hash:
                print("    [SKIP] 중복 — 동일 내용이 이미 정제됨 (해시 일치)")
                stats["skipped"] += 1
                continue

        conversation_id = extract_conversation_id(content)

        try:
            result = distill_file(client, raw_file, content, file_date, stats, source_type)

            # wikilink 검증: 실제 Vault 파일과 매칭하여 유효한 링크만 유지
            if result.get("related_knowledge"):
                original_count = len(result["related_knowledge"])
                result["related_knowledge"] = validate_wikilinks(result["related_knowledge"])
                validated_count = len(result["related_knowledge"])
                if validated_count < original_count:
                    print(f"    [WIKI] wikilink {original_count}개 → {validated_count}개 (검증 후)")

            output_path = determine_output_path(file_date, raw_file)

            # ── Phase 3: 자동 태깅 ──────────────────────────────────────
            cat_tags = auto_tag(content, result.get("topics", []))
            if cat_tags:
                print(f"    [P3-TAG] 카테고리: {cat_tags}")

            # ── Phase 3: 지식 그래프 wikilink 생성 ──────────────────────
            graph_links = generate_wikilinks(result, current_output_stem=output_path.stem)
            if graph_links:
                print(f"    [P3-GRAPH] 연결 노트: {len(graph_links)}개 → {graph_links}")

            # ── Phase 3: 우선순위 점수 ────────────────────────────────────
            p3_score = priority_score(result, file_date, raw_file)
            priority_label = "HIGH" if p3_score >= 7.0 else ("MEDIUM" if p3_score >= 4.0 else "LOW")
            print(f"    [P3-PRIORITY] 점수: {p3_score} ({priority_label})")

            # Phase 2: 같은 주제 노트가 이미 존재하는지 확인 (overwrite 금지)
            actual_output_path = output_path
            existing_by_topic = find_existing_note_by_topic(result, output_path.parent)
            if existing_by_topic and existing_by_topic != output_path:
                # 동일 주제 노트에 병합 (append)
                actual_output_path = existing_by_topic
                merge_into_existing_note(
                    existing_by_topic, result, raw_file,
                    source_conversation_id=conversation_id,
                )
                print(f"    [MERGE] → {existing_by_topic.relative_to(VAULT_BASE)} (주제 병합)")
                print(f"             신규 인사이트: {len(result.get('insights', []))}개  "
                      f"토픽 겹침: {set(result.get('topics', [])) & set(_extract_frontmatter_topics(existing_by_topic))}")
            elif output_path.exists():
                # 동일 파일명 노트가 이미 있으면 **state 유무와 무관하게** 병합한다.
                # 과거에는 `and state.get(str(raw_file))` 조건이 붙어 있었다. 그 탓에 state가
                # 없는 재실행(sidecar 실패 복구, --reset)이 아래 신규 분기로 내려가 기존 노트를
                # write_text로 덮어썼고, 사용자 수정·이전 병합 내용이 유실될 수 있었다.
                merge_into_existing_note(
                    output_path, result, raw_file,
                    source_conversation_id=conversation_id,
                )
                print(f"    [MERGE] → {output_path.relative_to(VAULT_BASE)} (파일명 일치, 병합)")
            else:
                # 신규 노트 생성 (Phase 3 데이터 포함)
                note_text = build_output_note(
                    result,
                    raw_file,
                    file_date,
                    source_type,
                    category_tags=cat_tags,
                    graph_wikilinks=graph_links,
                    p3_priority=p3_score,
                    source_conversation_id=conversation_id,
                )
                # 원자적 생성("x" = O_EXCL). 위 exists() 검사와 이 쓰기 사이에 다른
                # 프로세스나 사용자가 같은 노트를 만들었다면 덮어쓰지 않고 병합으로 넘긴다.
                try:
                    with output_path.open("x", encoding="utf-8") as f:
                        f.write(note_text)
                    print(f"    [OK] → {output_path.relative_to(VAULT_BASE)}")
                except FileExistsError:
                    merge_into_existing_note(
                        output_path, result, raw_file,
                        source_conversation_id=conversation_id,
                    )
                    print(f"    [MERGE] → {output_path.relative_to(VAULT_BASE)} (생성 경합 감지, 병합)")

            print(f"         소스: {source_type}  "
                  f"토픽: {result.get('topics', [])}  "
                  f"인사이트: {len(result.get('insights', []))}개  "
                  f"신뢰도: {result.get('confidence', '?')}")

            # Phase 3: 콘텐츠 해시 레지스트리 저장 (처리 성공 시)
            _save_content_hash_registry(content_hash_registry)

            # Stage 20: sidecar 인덱스를 state보다 **먼저** 기록한다. 순서가 반대면
            # sidecar 기록이 실패해도 state가 남아 재실행이 이 파일을 스킵하고,
            # 인덱스 누락이 영구화된다.
            try:
                append_processed_index(raw_file, conversation_id, actual_output_path)
            except OSError as e:
                # 증류 자체는 성공했다(노트는 디스크에 있다). 실패로 집계하지 않는다.
                # state를 저장하지 않아 다음 실행이 인덱스를 다시 기록하게 둔다. 재실행은
                # 위 병합 분기를 타므로 기존 노트를 덮어쓰지 않는다.
                # retry queue에도 넣어 --retry 경로로도 복구할 수 있게 한다.
                err_msg = f"sidecar 인덱스 기록 실패 (증류 성공): {e}"
                print(f"    [WARN] {err_msg} — 다음 실행에서 재시도")
                add_to_retry_queue(raw_file, err_msg)
                error_entries.append({"file": str(raw_file), "error": err_msg})
            else:
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
            error_entries.append({"file": str(raw_file), "error": err_msg})
            fail += 1
            stats["failed"] += 1
        except anthropic.APIError as e:
            err_msg = f"API 오류: {e}"
            print(f"    [FAIL] Claude {err_msg}")
            raw_path = save_original_on_failure(content, raw_file, file_date)
            add_to_retry_queue(raw_file, err_msg)
            print(f"           원본 저장: {raw_path.name}")
            error_entries.append({"file": str(raw_file), "error": err_msg})
            fail += 1
            stats["failed"] += 1
        except OSError as e:
            err_msg = f"파일 저장 오류: {e}"
            print(f"    [FAIL] {err_msg}")
            error_entries.append({"file": str(raw_file), "error": err_msg})
            fail += 1
            stats["failed"] += 1

    # 이번 배치 오류를 리포트에 기록
    if error_entries:
        _ensure_error_report_header()
        append_error_report(error_entries)

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
    # Phase 3: watch 모드에서도 콘텐츠 해시 레지스트리 공유
    watch_content_registry = _load_content_hash_registry()
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
                process_batch(
                    client, new_files, state, stats, 1, total_batches,
                    content_hash_registry=watch_content_registry,
                )
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

    # Phase 3: 콘텐츠 해시 레지스트리를 전체 실행에 걸쳐 공유 (배치 간 중복 감지)
    content_hash_registry = _load_content_hash_registry()

    print(f"[INFO] 배치 크기: {batch_size}  →  총 {total_batches}개 배치\n")

    total_success = 0
    total_fail    = 0
    start_time    = time.time()

    for batch_num, batch in enumerate(batches, 1):
        s, f = process_batch(
            client, batch, state, stats, batch_num, total_batches,
            content_hash_registry=content_hash_registry,
        )
        total_success += s
        total_fail    += f

    elapsed = time.time() - start_time

    # ── 결과 요약 ──────────────────────────────────────────────────────────────
    _print_stats(stats)
    print(f"[완료] 출력 디렉터리: {OUTPUT_BASE}")
    print(f"       캐시 파일:     {STATE_FILE}")
    remaining_retry = len(load_retry_queue())
    if remaining_retry:
        print(f"       재시도 대기:  {remaining_retry}개 (--retry 옵션으로 재처리)")

    # ── Discord Webhook 전송 ────────────────────────────────────────────────────
    send_discord_summary(stats, elapsed)

    return 0 if total_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
