#!/usr/bin/env python3
"""
Gemini Agent Layer — 버키 산하 보조 전문가 5종
역할: Research / RAG / Multimodal / Content / Validator

버키가 라우팅 결정 후 이 모듈을 호출. Gemini는 최종결정권 없음.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env", encoding="utf-8-sig", override=True)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
VAULT = ROOT / "ObsidianVault"

# Obsidian 저장 폴더 규칙 (사용자 지정)
OBSIDIAN_FOLDERS = {
    "research":    "08_Content",
    "rag":         "07_AI_Agent",
    "multimodal":  "04_SiteLog",
    "content":     "08_Content",
    "validator":   "07_AI_Agent",
}

ROLE_SYSTEM_PROMPTS = {
    "research": (
        "너는 Gemini-Research다. 웹·문서·시장·기술 리서치 전문가.\n"
        "최신 정보를 검색하고 출처 기반으로 요약한다. 확인되지 않은 정보는 반드시 '[미확인]'으로 표시.\n"
        "결과 형식: 📌 핵심요약 → 📋 세부내용 → 🔗 출처/근거 → ⚠️ 불확실한 부분"
    ),
    "rag": (
        "너는 Gemini-RAG다. Obsidian Vault 지식베이스 검색·요약·재구성 전문가.\n"
        "주어진 Vault 컨텍스트를 기반으로 답변하고, 관련 노트 경로를 명시한다.\n"
        "결과 형식: 📌 핵심답변 → 📁 참조노트 → 🔗 연결개념 → 💡 추가 탐색 제안"
    ),
    "multimodal": (
        "너는 Gemini-Multimodal이다. 이미지·도면·현장사진·자재사진 분석 전문가.\n"
        "시각 정보를 구체적으로 설명하고 인테리어·건축·자재 컨텍스트에서 해석한다.\n"
        "결과 형식: 📸 관찰내용 → 🏗️ 전문해석 → 📋 권장사항 → ❓ 추가확인 필요사항"
    ),
    "content": (
        "너는 Gemini-Content다. 블로그·유튜브 쇼츠·광고문구·영상프롬프트 생성 전문가.\n"
        "한국어 콘텐츠 최적화. SEO·바이럴 관점에서 작성.\n"
        "결과 형식: 📝 메인 콘텐츠 → 🏷️ 해시태그/키워드 → 📱 쇼츠 버전(60초) → 🎬 영상프롬프트"
    ),
    "validator": (
        "너는 Gemini-Validator다. Claude/Codex 산출물의 누락·모순·리스크 교차검증 전문가.\n"
        "편향 없이 독립적으로 검토. 문제가 없으면 '이상 없음'으로 명시.\n"
        "결과 형식: ✅ 확인된 부분 → ⚠️ 모순/누락 → 🚨 리스크 → 💡 개선제안"
    ),
}


def _get_client():
    """google.genai 클라이언트 반환. 없으면 ImportError."""
    try:
        from google import genai  # type: ignore
        return genai.Client(api_key=GEMINI_API_KEY)
    except ImportError:
        raise ImportError(
            "google-genai 패키지가 없습니다. 설치: pip install google-genai"
        )


def run_gemini(role: str, prompt: str, *, image_path: str | None = None, timeout: int = 120) -> str:
    """
    Gemini 호출 진입점.

    Args:
        role: research | rag | multimodal | content | validator
        prompt: 사용자 요청 텍스트
        image_path: multimodal 역할 시 이미지 경로 (선택)
        timeout: 초 (현재 미사용, 향후 async 대응용)

    Returns:
        Gemini 응답 문자열
    """
    if not GEMINI_API_KEY:
        return (
            "❌ GEMINI_API_KEY가 .env에 없습니다.\n"
            "설정: GEMINI_API_KEY=your_key_here"
        )

    if role not in ROLE_SYSTEM_PROMPTS:
        return f"❌ 알 수 없는 Gemini 역할: {role}. 가능한 역할: {list(ROLE_SYSTEM_PROMPTS)}"

    from google.genai import types as genai_types  # type: ignore

    client = _get_client()
    system_prompt = ROLE_SYSTEM_PROMPTS[role]

    # RAG: Vault 컨텍스트 주입
    if role == "rag":
        vault_context = _search_vault(prompt)
        if vault_context:
            prompt = f"[Vault 검색 결과]\n{vault_context}\n\n[질문]\n{prompt}"

    config = genai_types.GenerateContentConfig(system_instruction=system_prompt)

    # Multimodal: 이미지 첨부
    if role == "multimodal" and image_path and Path(image_path).exists():
        try:
            image_data = Path(image_path).read_bytes()
            import mimetypes
            mime = mimetypes.guess_type(image_path)[0] or "image/jpeg"
            contents = [
                genai_types.Part.from_bytes(data=image_data, mime_type=mime),
                genai_types.Part.from_text(text=prompt),
            ]
        except Exception as e:
            contents = [f"[이미지 로드 실패: {e}]\n{prompt}"]
    else:
        contents = [prompt]

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=contents,
        config=config,
    )

    result = response.text.strip() if hasattr(response, "text") else str(response)

    # Obsidian 자동 저장
    _save_to_obsidian(role, prompt, result)

    return result


def _search_vault(query: str, max_results: int = 5) -> str:
    """Vault에서 키워드로 노트 검색 후 컨텍스트 구성."""
    keywords = [w for w in query.split() if len(w) >= 2][:5]
    matched: list[tuple[int, Path, str]] = []

    for md_file in VAULT.rglob("*.md"):
        try:
            text = md_file.read_text(encoding="utf-8", errors="ignore")
            score = sum(1 for kw in keywords if kw in text)
            if score > 0:
                matched.append((score, md_file, text[:800]))
        except Exception:
            continue

    matched.sort(key=lambda x: x[0], reverse=True)
    if not matched:
        return ""

    parts = []
    for score, path, excerpt in matched[:max_results]:
        rel = path.relative_to(ROOT)
        parts.append(f"### {rel}\n{excerpt}\n")
    return "\n".join(parts)


def _save_to_obsidian(role: str, prompt: str, result: str) -> None:
    """결과를 Obsidian 지정 폴더에 YAML 포함 노트로 저장."""
    from datetime import datetime

    folder_key = OBSIDIAN_FOLDERS.get(role, "07_AI_Agent")
    save_dir = VAULT / folder_key / "gemini"
    save_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"gemini-{role}-{ts}.md"

    prompt_preview = prompt[:80].replace("\n", " ")
    content = (
        f"---\n"
        f"type: gemini-{role}\n"
        f"agent: Gemini-{role.capitalize()}\n"
        f"source: discord\n"
        f"status: done\n"
        f"created: {datetime.now().isoformat()}\n"
        f"next_action: review\n"
        f"---\n\n"
        f"# Gemini {role.capitalize()} — {ts}\n\n"
        f"**요청:** {prompt_preview}\n\n"
        f"---\n\n"
        f"{result}\n"
    )

    try:
        (save_dir / filename).write_text(content, encoding="utf-8")
        print(f"[Gemini] Obsidian 저장: {folder_key}/gemini/{filename}", flush=True)
    except Exception as e:
        print(f"[Gemini] Obsidian 저장 실패: {e}", flush=True)


# ── CLI 직접 실행 ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("사용법: python gemini_client.py <role> <prompt>")
        print("역할: research | rag | multimodal | content | validator")
        sys.exit(1)
    _role = sys.argv[1]
    _prompt = " ".join(sys.argv[2:])
    print(run_gemini(_role, _prompt))
