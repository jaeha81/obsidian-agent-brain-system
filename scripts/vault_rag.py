#!/usr/bin/env python3
"""ObsidianVault 벡터 RAG — 의미 기반 검색 파이프라인.

nomic-embed-text (ollama) + numpy/JSON 경량 벡터 저장소.
ChromaDB 불필요 — 손상 위험 없음, 원자적 저장.

Commands:
  index   - 볼트 전체 인덱싱 (신규/변경 파일만 재색인)
  search  - 의미 기반 검색
  stats   - 인덱스 상태 출력
  clear   - 인덱스 초기화

Usage:
  python vault_rag.py index [--vault PATH] [--force]
  python vault_rag.py search "RAG와 LLM Wiki 차이" [--top 5]
  python vault_rag.py stats
  python vault_rag.py clear
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Iterator

try:
    import numpy as np
except ImportError:
    print("numpy 미설치: pip install numpy", file=sys.stderr)
    sys.exit(1)

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    print("sentence-transformers 미설치: pip install sentence-transformers", file=sys.stderr)
    sys.exit(1)

# ---------------------------------------------------------------------------
# 경로 설정
# ---------------------------------------------------------------------------

ROOT = Path(__file__).parent.parent
VAULT_DEFAULT = ROOT / "ObsidianVault"
RAG_DIR = ROOT / ".rag"
EMBED_FILE = RAG_DIR / "embeddings.npy"
META_FILE = RAG_DIR / "index_meta.json"    # {rel_path: file_hash}
DOCS_FILE = RAG_DIR / "documents.json"    # [{source, section, title, text}, ...]

# 다국어 지원 모델 (한국어 포함, 384차원)
EMBED_MODEL = os.getenv("EMBED_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")
_st_model: "SentenceTransformer | None" = None

# 청크 설정
CHUNK_SIZE = 1500
CHUNK_OVERLAP = 200
MAX_CHUNKS_PER_FILE = 50

# 제외 경로
EXCLUDE_DIRS = {".obsidian", ".trash", "09_Archive", ".claude", ".rag"}

# ---------------------------------------------------------------------------
# 임베딩 (ollama)
# ---------------------------------------------------------------------------


def _get_model() -> "SentenceTransformer":
    global _st_model
    if _st_model is None:
        _st_model = SentenceTransformer(EMBED_MODEL)
    return _st_model


def _embed_batch(texts: list[str]) -> list[list[float]]:
    """배치 임베딩 — 다국어 지원 (한국어 포함)."""
    model = _get_model()
    vecs = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return vecs.tolist()


def _embed_one(text: str) -> list[float]:
    return _embed_batch([text])[0]


def _check_model() -> bool:
    try:
        _get_model()
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# 청킹
# ---------------------------------------------------------------------------


def _chunk_markdown(text: str) -> list[dict]:
    chunks = []
    sections = re.split(r'(?=^#{1,3} )', text, flags=re.MULTILINE)
    for section in sections:
        section = section.strip()
        if not section or len(section) < 30:
            continue
        header_match = re.match(r'^(#{1,3})\s+(.+)', section)
        section_title = header_match.group(2).strip() if header_match else ""
        if len(section) <= CHUNK_SIZE:
            chunks.append({"text": section, "section": section_title})
        else:
            start = 0
            while start < len(section):
                end = start + CHUNK_SIZE
                chunk_text = section[start:end]
                if chunk_text.strip():
                    chunks.append({"text": chunk_text, "section": section_title})
                if end >= len(section):
                    break
                start = end - CHUNK_OVERLAP
    return chunks[:MAX_CHUNKS_PER_FILE]


# ---------------------------------------------------------------------------
# 파일 스캔
# ---------------------------------------------------------------------------


def _scan_vault(vault: Path) -> Iterator[Path]:
    for md in vault.rglob("*.md"):
        parts = set(md.relative_to(vault).parts)
        if parts & EXCLUDE_DIRS:
            continue
        yield md


def _file_hash(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# 벡터 저장소 (numpy + JSON)
# ---------------------------------------------------------------------------


def _load_store() -> tuple[np.ndarray | None, list[dict], dict]:
    """(embeddings, documents, file_meta) 로드."""
    embeddings = None
    documents = []
    file_meta = {}

    if EMBED_FILE.exists():
        embeddings = np.load(str(EMBED_FILE))
    if DOCS_FILE.exists():
        documents = json.loads(DOCS_FILE.read_text(encoding="utf-8"))
    if META_FILE.exists():
        file_meta = json.loads(META_FILE.read_text(encoding="utf-8"))

    return embeddings, documents, file_meta


def _save_store(embeddings: np.ndarray, documents: list[dict], file_meta: dict) -> None:
    """원자적 저장 — 임시 파일 후 교체."""
    RAG_DIR.mkdir(parents=True, exist_ok=True)

    # numpy 저장 (np.save가 .npy 자동 추가하므로 직접 저장)
    np.save(str(EMBED_FILE), embeddings)

    # JSON 원자적 저장
    tmp_docs = str(DOCS_FILE) + ".tmp"
    Path(tmp_docs).write_text(json.dumps(documents, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp_docs, str(DOCS_FILE))

    tmp_meta = str(META_FILE) + ".tmp"
    Path(tmp_meta).write_text(json.dumps(file_meta, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp_meta, str(META_FILE))


def _cosine_similarity(query_vec: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    q = query_vec / (np.linalg.norm(query_vec) + 1e-10)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-10
    normed = matrix / norms
    return normed @ q


# ---------------------------------------------------------------------------
# index 명령
# ---------------------------------------------------------------------------


def cmd_index(vault: Path, force: bool = False) -> None:
    if not _check_model():
        print(f"[오류] 임베딩 모델 로드 실패: {EMBED_MODEL}")
        sys.exit(1)
    print(f"[모델] {EMBED_MODEL} 로드됨")

    embeddings_list, documents, file_meta = _load_store()
    if force:
        embeddings_list, documents, file_meta = None, [], {}

    # 파일→청크 인덱스 구축 (삭제용)
    source_to_indices: dict[str, list[int]] = {}
    for i, doc in enumerate(documents):
        src = doc.get("source", "")
        source_to_indices.setdefault(src, []).append(i)

    files = sorted(_scan_vault(vault))
    print(f"[인덱싱] {len(files)}개 파일 스캔 중...")

    added = updated = skipped = 0
    emb_array = np.array(embeddings_list) if embeddings_list is not None else None

    for i, md_path in enumerate(files, 1):
        rel = str(md_path.relative_to(vault))
        try:
            file_hash = _file_hash(md_path)
        except OSError:
            continue

        if not force and file_meta.get(rel) == file_hash:
            skipped += 1
            continue

        try:
            text = md_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        chunks = _chunk_markdown(text)
        if not chunks:
            continue

        # 기존 청크 제거
        old_indices = source_to_indices.pop(rel, [])
        if old_indices:
            keep = [j for j in range(len(documents)) if j not in set(old_indices)]
            documents = [documents[j] for j in keep]
            emb_array = emb_array[keep] if emb_array is not None and len(keep) < len(old_indices) + len(documents) else (
                emb_array[keep] if emb_array is not None else None
            )

        # 새 청크 배치 임베딩
        chunk_texts = [c["text"] for c in chunks]
        try:
            new_embs = _embed_batch(chunk_texts)
        except Exception as e:
            print(f"  [skip] {rel}: {e}")
            continue

        if not new_embs:
            continue

        new_docs = [
            {
                "source": rel,
                "section": c["section"],
                "title": md_path.stem,
                "text": c["text"][:500],
            }
            for c in chunks
        ]

        # 추가
        new_arr = np.array(new_embs, dtype=np.float32)
        if emb_array is None:
            emb_array = new_arr
        else:
            emb_array = np.vstack([emb_array, new_arr])
        documents.extend(new_docs)

        if file_meta.get(rel):
            updated += 1
        else:
            added += 1
        file_meta[rel] = file_hash

        if i % 10 == 0:
            _save_store(emb_array, documents, file_meta)
            print(f"  {i}/{len(files)} (추가:{added} 업데이트:{updated} 스킵:{skipped})")

    if emb_array is not None:
        _save_store(emb_array, documents, file_meta)

    print(f"\n[완료] 추가:{added} 업데이트:{updated} 스킵:{skipped}")
    print(f"[인덱스] 총 {len(documents)}개 청크 ({RAG_DIR})")


# ---------------------------------------------------------------------------
# search 명령
# ---------------------------------------------------------------------------


def cmd_search(query: str, top_k: int = 5) -> list[dict]:
    emb_array, documents, _ = _load_store()

    if emb_array is None or len(documents) == 0:
        print("[오류] 인덱스가 비어 있습니다. 먼저 'index'를 실행하세요.")
        return []

    try:
        q_emb = np.array(_embed_one(query), dtype=np.float32)
    except Exception as e:
        print(f"[오류] 쿼리 임베딩 실패: {e}")
        return []

    sims = _cosine_similarity(q_emb, emb_array)
    top_indices = np.argsort(-sims)[:top_k]

    results = []
    for idx in top_indices:
        doc = documents[idx]
        results.append({
            "source": doc.get("source", ""),
            "title": doc.get("title", ""),
            "section": doc.get("section", ""),
            "similarity": round(float(sims[idx]), 3),
            "preview": doc.get("text", "")[:300].replace("\n", " "),
        })

    return results


def _print_results(results: list[dict]) -> None:
    if not results:
        print("결과 없음")
        return
    for i, r in enumerate(results, 1):
        bar = "█" * int(r["similarity"] * 10)
        print(f"\n[{i}] {r['source']}")
        if r["section"]:
            print(f"    섹션: {r['section']}")
        print(f"    유사도: {r['similarity']:.3f} {bar}")
        print(f"    미리보기: {r['preview'][:200]}")


# ---------------------------------------------------------------------------
# stats / clear
# ---------------------------------------------------------------------------


def cmd_stats() -> None:
    _, documents, file_meta = _load_store()
    print(f"인덱싱된 파일: {len(file_meta)}개")
    print(f"총 청크 수:    {len(documents)}개")
    print(f"임베딩 모델:   {EMBED_MODEL}")
    print(f"저장 위치:     {RAG_DIR}")
    emb_size = EMBED_FILE.stat().st_size // 1024 if EMBED_FILE.exists() else 0
    print(f"임베딩 파일:   {emb_size} KB")


def cmd_clear() -> None:
    for f in [EMBED_FILE, DOCS_FILE, META_FILE]:
        if f.exists():
            f.unlink()
    print("[초기화] 인덱스 삭제 완료")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="ObsidianVault 벡터 RAG")
    sub = parser.add_subparsers(dest="cmd")

    p_index = sub.add_parser("index", help="볼트 인덱싱")
    p_index.add_argument("--vault", default=str(VAULT_DEFAULT))
    p_index.add_argument("--force", action="store_true")

    p_search = sub.add_parser("search", help="의미 기반 검색")
    p_search.add_argument("query")
    p_search.add_argument("--top", type=int, default=5)
    p_search.add_argument("--json", dest="as_json", action="store_true")

    sub.add_parser("stats")
    sub.add_parser("clear")

    args = parser.parse_args()

    if args.cmd == "index":
        cmd_index(Path(args.vault), force=args.force)
    elif args.cmd == "search":
        results = cmd_search(args.query, top_k=args.top)
        if getattr(args, "as_json", False):
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            _print_results(results)
    elif args.cmd == "stats":
        cmd_stats()
    elif args.cmd == "clear":
        cmd_clear()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
