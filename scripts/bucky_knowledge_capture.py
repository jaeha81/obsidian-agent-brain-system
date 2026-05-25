#!/usr/bin/env python3
"""
Bucky Knowledge Auto-Capture (P0) — CLI 버전
표준 라이브러리만 사용 (requests, pathlib, datetime, argparse, urllib)

사용법:
  python bucky_knowledge_capture.py --url "https://..." --title "제목" --tags "tag1,tag2"
  python bucky_knowledge_capture.py --text "텍스트 내용" --title "메모 제목"
  python bucky_knowledge_capture.py --discord-msg "메시지 내용" --author "사용자명"
"""

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen, Request
from urllib.error import URLError
from html.parser import HTMLParser

# ── 경로 설정 ──────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
VAULT = ROOT / "ObsidianVault"
RAW_DIR = VAULT / "01_RAW"
HANDOFF_LOG = VAULT / "00_System" / "HANDOFF_LOG.md"


# ── HTML 파서 (제목·설명 추출) ─────────────────────────────
class MetaExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title: str = ""
        self.description: str = ""
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == "title":
            self._in_title = True
        elif tag == "meta":
            name = attrs_dict.get("name", "").lower()
            prop = attrs_dict.get("property", "").lower()
            content = attrs_dict.get("content", "")
            if name in ("description", "og:description") or prop in ("og:description",):
                if not self.description:
                    self.description = content
            if prop == "og:title" and not self.title:
                self.title = content

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title and not self.title:
            self.title = data.strip()


def fetch_url_meta(url: str) -> dict:
    """URL에서 제목·설명·도메인을 추출한다."""
    result = {"url": url, "title": "", "description": "", "domain": ""}
    try:
        parsed = urlparse(url)
        result["domain"] = parsed.netloc

        req = Request(url, headers={"User-Agent": "Mozilla/5.0 (BuckyBot/1.0)"})
        with urlopen(req, timeout=10) as resp:
            charset = resp.headers.get_content_charset("utf-8")
            html = resp.read(32768).decode(charset, errors="replace")

        parser = MetaExtractor()
        parser.feed(html)
        result["title"] = parser.title or parsed.path or url
        result["description"] = parser.description or ""
    except URLError as e:
        result["title"] = url
        result["description"] = f"(URL 접근 실패: {e})"
    except Exception as e:
        result["title"] = url
        result["description"] = f"(파싱 오류: {e})"
    return result


# ── slug 생성 ─────────────────────────────────────────────
def to_slug(text: str) -> str:
    text = re.sub(r"[^\w가-힣\s-]", "", text)
    text = re.sub(r"\s+", "-", text.strip())
    return text[:50].lower() or "note"


# ── Obsidian 노트 저장 ────────────────────────────────────
def save_note(
    title: str,
    source_type: str,       # "url" | "text" | "discord"
    source_value: str,      # 원본 URL 또는 출처 표시
    body: str,
    tags: list[str],
    author: str = "",
) -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    slug = to_slug(title)
    filepath = RAW_DIR / f"{date_str}-{slug}.md"

    # 중복 방지: 같은 날짜·slug 존재 시 타임스탬프 추가
    if filepath.exists():
        ts = datetime.now().strftime("%H%M%S")
        filepath = RAW_DIR / f"{date_str}-{slug}-{ts}.md"

    tags_yaml = "\n".join(f"  - {t}" for t in tags) if tags else "  - auto-capture"
    author_line = f"\nauthor: \"{author}\"" if author else ""
    source_display = source_value if source_value else "manual"

    note_content = f"""---
title: "{title}"
source: "{source_display}"
source_type: {source_type}
date: {date_str}
captured_at: {datetime.now().isoformat(timespec='seconds')}
tags:
{tags_yaml}{author_line}
status: raw
---

# {title}

{body}
"""

    filepath.write_text(note_content.strip(), encoding="utf-8")
    return filepath


# ── HANDOFF_LOG 업데이트 ──────────────────────────────────
def update_handoff_log(title: str, filepath: Path, source_type: str) -> None:
    if not HANDOFF_LOG.exists():
        return

    existing = HANDOFF_LOG.read_text(encoding="utf-8")
    now = datetime.now()
    date_str = now.strftime("%Y%m%d")
    time_str = now.strftime("%H:%M")
    session_id = now.strftime("%H%M%S")

    entry = f"""
## HANDOFF-{date_str}-KC{session_id}

- From: Knowledge Capture (bucky_knowledge_capture.py)
- To: User / Bucky
- Date: {now.strftime('%Y-%m-%d')} {time_str}
- Phase: Knowledge Auto-Capture P0
- Status: Completed
- Summary: [{source_type.upper()}] "{title}" → 01_RAW 저장 완료
- Next Action: 01_RAW 검토 후 03_Knowledge로 승격
- Files Changed: {filepath.relative_to(ROOT).as_posix()}
- Warnings: None

---
"""

    # 헤더(---) 구분선 첫 번째 이후 바로 삽입 (최신 항목을 위로)
    header_end = existing.find("\n---\n")
    if header_end != -1:
        insert_pos = header_end + 5  # "\n---\n" 다음
        new_content = existing[:insert_pos] + entry + existing[insert_pos:]
    else:
        new_content = existing + entry

    HANDOFF_LOG.write_text(new_content, encoding="utf-8")


# ── 메인 처리 ─────────────────────────────────────────────
def handle_url(url: str, title: str, tags: list[str]) -> Path:
    meta = fetch_url_meta(url)
    resolved_title = title or meta["title"] or url

    body_lines = []
    if meta["description"]:
        body_lines.append(f"> {meta['description']}\n")
    body_lines.append(f"## 원본 링크\n\n- [{resolved_title}]({url})")
    if meta["domain"]:
        body_lines.append(f"\n**도메인**: {meta['domain']}")

    body = "\n".join(body_lines)
    return save_note(
        title=resolved_title,
        source_type="url",
        source_value=url,
        body=body,
        tags=tags or ["url-capture"],
    )


def handle_text(text: str, title: str, tags: list[str]) -> Path:
    resolved_title = title or (text[:40].strip() + ("..." if len(text) > 40 else ""))
    return save_note(
        title=resolved_title,
        source_type="text",
        source_value="manual-text",
        body=text,
        tags=tags or ["text-capture"],
    )


def handle_discord_msg(msg: str, author: str, tags: list[str]) -> Path:
    first_line = msg.strip().splitlines()[0][:60] if msg.strip() else "Discord 메시지"
    title = f"Discord: {first_line}"
    return save_note(
        title=title,
        source_type="discord",
        source_value=f"discord/{author}" if author else "discord",
        body=f"> {author}: {msg}" if author else msg,
        tags=tags or ["discord", "auto-capture"],
        author=author,
    )


# ── Discord 봇 호환 인터페이스 ────────────────────────────
def capture_url(url: str, title: str = "", tags: list = None) -> Path:
    fp = handle_url(url, title, tags or [])
    update_handoff_log(fp.stem, fp, "URL")
    return fp


def capture_text(text: str, author: str = "", title: str = "", tags: list = None) -> Path:
    if author:
        fp = handle_discord_msg(text, author, tags or [])
        update_handoff_log(fp.stem, fp, "DISCORD")
    else:
        fp = handle_text(text, title, tags or [])
        update_handoff_log(fp.stem, fp, "TEXT")
    return fp


# ── CLI 진입점 ────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Bucky Knowledge Auto-Capture — 링크·텍스트·Discord 메시지를 Obsidian에 저장"
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--url", metavar="URL", help="저장할 URL")
    group.add_argument("--text", metavar="TEXT", help="저장할 텍스트 내용")
    group.add_argument("--discord-msg", metavar="MSG", help="Discord 메시지 내용")

    parser.add_argument("--title", default="", help="노트 제목 (생략 시 자동 감지)")
    parser.add_argument("--tags", default="", help="쉼표 구분 태그 (예: tag1,tag2)")
    parser.add_argument("--author", default="", help="--discord-msg 작성자명")

    args = parser.parse_args()
    tags = [t.strip() for t in args.tags.split(",") if t.strip()] if args.tags else []

    if args.url:
        filepath = handle_url(args.url, args.title, tags)
        source_type = "URL"
    elif args.text:
        filepath = handle_text(args.text, args.title, tags)
        source_type = "TEXT"
    else:  # discord-msg
        filepath = handle_discord_msg(args.discord_msg, args.author, tags)
        source_type = "DISCORD"

    title_in_file = filepath.stem
    update_handoff_log(title_in_file, filepath, source_type)

    print(f"[OK] 저장 완료: {filepath}")
    print(f"[OK] HANDOFF_LOG 업데이트 완료")


if __name__ == "__main__":
    main()
