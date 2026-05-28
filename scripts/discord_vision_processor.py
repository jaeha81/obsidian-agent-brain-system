#!/usr/bin/env python3
"""
Discord Vision Processor — 이미지 첨부파일 OCR/Vision 분석 → Obsidian 저장

우선순위:
1. Claude Vision API (anthropic 패키지 + ANTHROPIC_API_KEY)
2. OpenAI Vision API (openai 패키지 + OPENAI_API_KEY)
3. Tesseract OCR fallback (pytesseract)
4. URL 저장만 (Vision 없을 때)

사용:
    from discord_vision_processor import process_image_attachment
    result = await process_image_attachment(attachment, message_content, channel_name, author_name)
"""

import asyncio
import base64
import hashlib
import mimetypes
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError

_ROOT = Path(__file__).parent.parent
VAULT = Path(os.getenv("VAULT_PATH", str(_ROOT / "ObsidianVault")))
UPLOAD_DIR = _ROOT / "runtime" / "uploads"
CAPTURES_DIR = VAULT / "Inbox" / "DiscordCaptures"

ALLOWED_CONTENT_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp", "image/gif"}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB

# ── Vision 백엔드 감지 ─────────────────────────────────────────────────────────

def _detect_vision_backend() -> str:
    """사용 가능한 Vision 백엔드 감지. 반환: 'claude' | 'gemini' | 'openai' | 'tesseract' | 'none'"""
    if os.getenv("ANTHROPIC_API_KEY"):
        try:
            import anthropic  # noqa
            return "claude"
        except ImportError:
            pass

    if os.getenv("GEMINI_API_KEY"):
        try:
            import google.generativeai  # noqa
            return "gemini"
        except ImportError:
            pass

    if os.getenv("OPENAI_API_KEY"):
        try:
            import openai  # noqa
            return "openai"
        except ImportError:
            pass

    try:
        import pytesseract  # noqa
        return "tesseract"
    except ImportError:
        pass

    return "none"


_VISION_BACKEND: str | None = None


def get_vision_backend() -> str:
    global _VISION_BACKEND
    if _VISION_BACKEND is None:
        _VISION_BACKEND = _detect_vision_backend()
    return _VISION_BACKEND


# ── 이미지 다운로드 ────────────────────────────────────────────────────────────

def _download_image(url: str, dest: Path) -> bool:
    """이미지를 dest 경로로 다운로드. 성공 시 True."""
    try:
        req = Request(url, headers={"User-Agent": "BuckyBot/1.0"})
        with urlopen(req, timeout=30) as resp:
            data = resp.read(MAX_FILE_SIZE + 1)
            if len(data) > MAX_FILE_SIZE:
                return False
            dest.write_bytes(data)
        return True
    except Exception as e:
        print(f"[Vision] 다운로드 실패: {e}", flush=True)
        return False


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _to_base64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode()


# ── Vision 분석 ─────────────────────────────────────────────────────────────

def _analyze_claude(image_path: Path, content_type: str) -> dict:
    import anthropic
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    b64 = _to_base64(image_path)
    safe_type = content_type if content_type in ALLOWED_CONTENT_TYPES else "image/jpeg"

    response = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": safe_type, "data": b64},
                },
                {
                    "type": "text",
                    "text": (
                        "이 이미지를 분석하세요. 다음을 포함해 한국어로 답변:\n"
                        "1. 이미지 전체 설명 (2-3문장)\n"
                        "2. 이미지 내 텍스트 전체 (OCR)\n"
                        "3. UI 캡처라면 어떤 화면인지\n"
                        "4. 코드 스크린샷이라면 언어와 내용\n"
                        "5. GPT Plus/ChatGPT 화면이라면 '오늘의 플러스' 기능 내용\n"
                        "형식: JSON {summary, ocr_text, ui_context, special_notes}"
                    ),
                },
            ],
        }],
    )
    raw = response.content[0].text.strip()
    return _parse_vision_json(raw)


def _analyze_gemini(image_path: Path, content_type: str) -> dict:
    import google.generativeai as genai
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel("gemini-2.0-flash")
    import PIL.Image
    img = PIL.Image.open(image_path)
    prompt = (
        "이 이미지를 분석하세요. 한국어로:\n"
        "1. 전체 설명\n2. OCR 텍스트\n3. UI 화면 정보\n4. 특이사항\n"
        "형식: JSON {summary, ocr_text, ui_context, special_notes}"
    )
    response = model.generate_content([prompt, img])
    raw = response.text.strip()
    return _parse_vision_json(raw)


def _analyze_openai(image_path: Path, content_type: str) -> dict:
    import openai
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    b64 = _to_base64(image_path)
    safe_type = content_type if content_type in ALLOWED_CONTENT_TYPES else "image/jpeg"

    response = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{safe_type};base64,{b64}"},
                },
                {
                    "type": "text",
                    "text": (
                        "이 이미지를 분석하세요. 한국어로:\n"
                        "1. 전체 설명\n2. OCR 텍스트\n3. UI 화면 정보\n4. 특이사항\n"
                        "형식: JSON {summary, ocr_text, ui_context, special_notes}"
                    ),
                },
            ],
        }],
    )
    raw = response.choices[0].message.content.strip()
    return _parse_vision_json(raw)


def _analyze_tesseract(image_path: Path) -> dict:
    import pytesseract
    from PIL import Image
    tesseract_cmd = os.getenv("TESSERACT_CMD")
    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
    elif sys.platform == "win32":
        default_cmd = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
        if default_cmd.exists():
            pytesseract.pytesseract.tesseract_cmd = str(default_cmd)
    img = Image.open(image_path)
    text = pytesseract.image_to_string(img, lang="kor+eng")
    return {
        "summary": "Tesseract OCR 결과 (Vision AI 미사용)",
        "ocr_text": text.strip(),
        "ui_context": "",
        "special_notes": "",
    }


def _parse_vision_json(raw: str) -> dict:
    """Vision API 응답에서 JSON 파싱. 실패 시 raw를 summary로."""
    import json
    # ```json ... ``` 블록 제거
    clean = re.sub(r"```(?:json)?\s*", "", raw).replace("```", "").strip()
    try:
        data = json.loads(clean)
        return {
            "summary": data.get("summary", ""),
            "ocr_text": data.get("ocr_text", ""),
            "ui_context": data.get("ui_context", ""),
            "special_notes": data.get("special_notes", ""),
        }
    except Exception:
        return {"summary": raw, "ocr_text": "", "ui_context": "", "special_notes": ""}


# ── Markdown 생성 ─────────────────────────────────────────────────────────────

def _build_markdown(
    vision: dict,
    image_path: Path,
    image_url: str,
    message_content: str,
    channel: str,
    author: str,
    sha256: str,
) -> str:
    now = datetime.now()
    ts = now.strftime("%Y-%m-%dT%H:%M:%S")
    return f"""---
type: discord_image_capture
source: discord
created_at: {ts}
channel: {channel}
author: {author}
image_file: {image_path.name}
image_url: {image_url}
sha256: {sha256}
vision_backend: {get_vision_backend()}
---

# Vision Summary

{vision.get('summary') or '(요약 없음)'}

# OCR Text

{vision.get('ocr_text') or '(텍스트 없음)'}

# UI Context

{vision.get('ui_context') or '(UI 정보 없음)'}

# Special Notes

{vision.get('special_notes') or ''}

# User Context

{message_content or '(첨부만)'}

# Tags

#discord #vision #capture
"""


# ── Vault 저장 ────────────────────────────────────────────────────────────────

def _save_to_vault(markdown: str) -> Path:
    now = datetime.now()
    day_dir = CAPTURES_DIR / now.strftime("%Y-%m-%d")
    day_dir.mkdir(parents=True, exist_ok=True)
    filename = now.strftime("%H%M%S-image-note.md")
    out = day_dir / filename
    # 동일 초 충돌 방지
    i = 1
    while out.exists():
        out = day_dir / f"{now.strftime('%H%M%S')}-image-note-{i}.md"
        i += 1
    out.write_text(markdown, encoding="utf-8")
    return out


# ── RAG 인덱스 업데이트 ──────────────────────────────────────────────────────────

def _rag_index_file(vault_path: Path) -> None:
    """저장된 Vault 파일을 RAG 인덱스에 추가. ollama 미실행 시 조용히 스킵."""
    try:
        import sys as _sys
        scripts_dir = str(Path(__file__).parent)
        if scripts_dir not in _sys.path:
            _sys.path.insert(0, scripts_dir)
        from vault_rag import cmd_index, VAULT_DEFAULT
        vault = Path(os.getenv("VAULT_PATH", str(VAULT_DEFAULT)))
        cmd_index(vault, force=False)
        print(f"[Vision/RAG] 인덱스 업데이트 완료: {vault_path.name}", flush=True)
    except SystemExit:
        # ollama 미실행 시 cmd_index가 sys.exit(1) 호출
        print("[Vision/RAG] ollama 미실행 — RAG 인덱싱 스킵", flush=True)
    except Exception as e:
        print(f"[Vision/RAG] 인덱싱 실패 (무시): {e}", flush=True)


# ── 공개 인터페이스 ────────────────────────────────────────────────────────────

async def process_image_attachment(
    attachment,  # discord.Attachment
    message_content: str,
    channel_name: str,
    author_name: str,
) -> dict:
    """
    Discord 이미지 첨부파일 전체 파이프라인.
    반환: {
        ok: bool,
        vault_path: str,
        summary: str,
        ocr_text: str,
        backend: str,
        error: str,
    }
    """
    result = {
        "ok": False,
        "vault_path": "",
        "summary": "",
        "ocr_text": "",
        "backend": get_vision_backend(),
        "error": "",
    }

    # 파일 크기 검증
    if attachment.size and attachment.size > MAX_FILE_SIZE:
        result["error"] = f"파일 크기 초과: {attachment.size // 1024 // 1024}MB (최대 20MB)"
        return result

    # MIME 검증
    content_type = (attachment.content_type or "").split(";")[0].strip().lower()
    if content_type not in ALLOWED_CONTENT_TYPES:
        result["error"] = f"지원하지 않는 이미지 형식: {content_type}"
        return result

    # 다운로드 경로 준비
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now()
    safe_name = re.sub(r"[^\w\-.]", "_", attachment.filename or "image.png")
    local_path = UPLOAD_DIR / f"{now.strftime('%Y%m%d%H%M%S')}-{author_name[:8]}-{safe_name}"

    # 다운로드 (blocking → thread)
    ok = await asyncio.to_thread(_download_image, attachment.url, local_path)
    if not ok:
        result["error"] = "이미지 다운로드 실패"
        return result

    sha = await asyncio.to_thread(_sha256, local_path)

    # Vision 분석 — 폴백 체인 (claude → openai → tesseract)
    _initial_backend = get_vision_backend()
    _chain_map = {
        "claude": ["claude", "gemini", "openai", "tesseract"],
        "gemini": ["gemini", "tesseract"],
        "openai": ["openai", "gemini", "tesseract"],
        "tesseract": ["tesseract"],
        "none": [],
    }
    fallback_chain = _chain_map.get(_initial_backend, [])

    vision: dict = {}
    backend = _initial_backend
    _tried_errors: list[str] = []

    for _try_backend in fallback_chain:
        try:
            if _try_backend == "claude":
                vision = await asyncio.to_thread(_analyze_claude, local_path, content_type)
            elif _try_backend == "gemini":
                vision = await asyncio.to_thread(_analyze_gemini, local_path, content_type)
            elif _try_backend == "openai":
                vision = await asyncio.to_thread(_analyze_openai, local_path, content_type)
            elif _try_backend == "tesseract":
                vision = await asyncio.to_thread(_analyze_tesseract, local_path)
            backend = _try_backend
            break
        except Exception as _e:
            _tried_errors.append(f"{_try_backend}: {_e}")
            print(f"[Vision] {_try_backend} 실패 → 다음 백엔드 시도: {_e}", flush=True)
    else:
        # 모든 백엔드 실패
        if not fallback_chain:
            vision = {
                "summary": f"이미지 파일: {attachment.filename} ({attachment.size // 1024}KB)",
                "ocr_text": "(Vision API 미설정 — ANTHROPIC_API_KEY 또는 OPENAI_API_KEY 필요)",
                "ui_context": "",
                "special_notes": "",
            }
        else:
            vision = {
                "summary": f"Vision 분석 실패 (모든 백엔드 시도): {'; '.join(_tried_errors)}",
                "ocr_text": "",
                "ui_context": "",
                "special_notes": "",
            }

    # Markdown 생성 + Vault 저장
    md = _build_markdown(vision, local_path, attachment.url, message_content, channel_name, author_name, sha)
    vault_path = await asyncio.to_thread(_save_to_vault, md)

    # RAG 인덱스 업데이트 (비차단 — 실패해도 파이프라인 계속)
    asyncio.ensure_future(asyncio.to_thread(_rag_index_file, vault_path))

    result.update({
        "ok": True,
        "vault_path": str(vault_path),
        "summary": vision.get("summary", ""),
        "ocr_text": vision.get("ocr_text", ""),
        "backend": backend,
    })
    return result


def is_image_attachment(attachment) -> bool:
    """discord.Attachment가 이미지인지 확인."""
    ct = (attachment.content_type or "").split(";")[0].strip().lower()
    if ct in ALLOWED_CONTENT_TYPES:
        return True
    name = (attachment.filename or "").lower()
    return any(name.endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".webp", ".gif"))
