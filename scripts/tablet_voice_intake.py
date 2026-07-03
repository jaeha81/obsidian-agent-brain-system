#!/usr/bin/env python3
"""
태블릿 음성 인테이크 스크립트 (Phase 1 — 로컬 Whisper, 무과금)

Samsung Galaxy Tab (Android, Termux) 또는 일반 Python 환경에서 실행.
마이크 30초 청크 캡처 → 로컬 Whisper STT → bucky_stt_enhancer 처리
→ manifest 형식으로 패키징 → bucky_chat_server:8765/tablet-intake 전송.

Usage:
    python tablet_voice_intake.py --start
    python tablet_voice_intake.py --start --config ~/.bucky_tablet_config.json
    python tablet_voice_intake.py --start --server http://192.168.1.100:8765
    python tablet_voice_intake.py --check   # 의존성 확인만

Phase 2 (실시간 ASR/클라우드) 는 CL-027 승인 게이트 이후 착수.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import struct
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

# ── Optional audio deps (graceful fallback) ──────────────────────────────────
try:
    import sounddevice as sd  # type: ignore
    import numpy as np        # type: ignore
    _HAS_AUDIO = True
except ImportError:
    _HAS_AUDIO = False

try:
    import whisper as _whisper_lib  # type: ignore
    _HAS_WHISPER = True
except ImportError:
    _HAS_WHISPER = False

try:
    import requests as _req  # type: ignore
    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False

try:
    import scipy.io.wavfile as _wavfile  # type: ignore
    _HAS_SCIPY = True
except ImportError:
    _HAS_SCIPY = False

# ── STT Enhancer (optional — bucky project scripts/) ─────────────────────────
_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

try:
    from bucky_stt_enhancer import process as _stt_enhance  # type: ignore
    _HAS_ENHANCER = True
except Exception:
    _HAS_ENHANCER = False

    def _stt_enhance(text: str, **_kwargs) -> dict:  # type: ignore
        return {"text": text, "intent": "INFORMATION", "entities": [], "confidence": 0.5}


# ── Default config ─────────────────────────────────────────────────────────
DEFAULT_CONFIG_PATH = Path.home() / ".bucky_tablet_config.json"
DEFAULT_CONFIG: dict = {
    "bucky_server": "http://127.0.0.1:8765",
    "device_name": "galaxy-tab-jh",
    "vault_path": "04_SiteLog",
    "stt_mode": "local-whisper",
    "whisper_model": "base",
    "auto_upload": True,
    "upload_interval_sec": 30,
    "sample_rate": 16000,
    "channels": 1,
}


def load_config(path: Path | None = None) -> dict:
    cfg_path = path or DEFAULT_CONFIG_PATH
    if cfg_path.exists():
        try:
            data = json.loads(cfg_path.read_text(encoding="utf-8"))
            return {**DEFAULT_CONFIG, **data}
        except Exception as e:
            print(f"[tablet-intake] config load error: {e}, using defaults")
    return dict(DEFAULT_CONFIG)


# ── Audio recording ───────────────────────────────────────────────────────────
def _to_wav_bytes(audio_ndarray, sample_rate: int, channels: int) -> bytes:
    """Convert numpy int16 array to minimal WAV bytes."""
    buf = io.BytesIO()
    if _HAS_SCIPY:
        _wavfile.write(buf, sample_rate, audio_ndarray)
        return buf.getvalue()
    data = audio_ndarray.tobytes()
    buf.write(b"RIFF")
    buf.write(struct.pack("<I", 36 + len(data)))
    buf.write(b"WAVE")
    buf.write(b"fmt ")
    buf.write(struct.pack(
        "<IHHIIHH", 16, 1, channels, sample_rate,
        sample_rate * channels * 2, channels * 2, 16,
    ))
    buf.write(b"data")
    buf.write(struct.pack("<I", len(data)))
    buf.write(data)
    return buf.getvalue()


def record_chunk(duration_sec: int, sample_rate: int, channels: int) -> tuple[bytes, int]:
    """Record audio for `duration_sec` seconds.  Returns (wav_bytes, actual_duration)."""
    if not _HAS_AUDIO:
        raise RuntimeError(
            "sounddevice/numpy 미설치. "
            "실행: pip install sounddevice numpy"
        )
    frames = int(sample_rate * duration_sec)
    print(f"[tablet-intake] 🎙 녹음 중 ({duration_sec}s)...", flush=True)
    audio = sd.rec(frames, samplerate=sample_rate, channels=channels, dtype="int16")
    sd.wait()
    return _to_wav_bytes(audio, sample_rate, channels), duration_sec


# ── Whisper STT ───────────────────────────────────────────────────────────────
_whisper_cache: dict[str, object] = {}


def transcribe(wav_bytes: bytes, model_name: str = "base") -> str:
    """Run local Whisper transcription. Returns Korean transcript string."""
    if not _HAS_WHISPER:
        raise RuntimeError(
            "openai-whisper 미설치. "
            "실행: pip install openai-whisper"
        )
    if model_name not in _whisper_cache:
        print(f"[tablet-intake] Whisper 모델 로드 중: {model_name} (최초 1회 느림)")
        _whisper_cache[model_name] = _whisper_lib.load_model(model_name)
    model = _whisper_cache[model_name]

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(wav_bytes)
        tmp = f.name
    try:
        result = model.transcribe(tmp, language="ko", fp16=False)  # type: ignore
        return str(result.get("text", "")).strip()
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


# ── Manifest builder ──────────────────────────────────────────────────────────
def build_manifest(
    chunks: list[dict],
    device_name: str,
    vault_path: str,
    tags: list[str] | None = None,
) -> dict:
    now = datetime.now(tz=timezone.utc).isoformat()
    date_str = datetime.now().strftime("%Y-%m-%d")
    return {
        "manifest_version": "1.1",
        "batch_id": f"batch-{date_str}-{uuid.uuid4().hex[:6]}",
        "idempotency_key": str(uuid.uuid4()),
        "source_device": device_name,
        "upload_time": now,
        "chunks": chunks,
        "total_chunks": len(chunks),
        "project": f"voice-intake-{date_str}",
        "vault_path": vault_path,
        "tags": tags or ["voice", "tablet", "intake"],
    }


# ── Upload ────────────────────────────────────────────────────────────────────
def upload_manifest(manifest: dict, server_url: str, timeout: int = 10) -> bool:
    url = server_url.rstrip("/") + "/tablet-intake"
    if not _HAS_REQUESTS:
        payload = json.dumps(manifest, ensure_ascii=False)
        print(f"[tablet-intake] requests 미설치. curl 커맨드:")
        print(f"  curl -X POST {url} -H 'Content-Type: application/json' -d '{payload[:200]}...'")
        return False
    try:
        resp = _req.post(url, json=manifest, timeout=timeout)
        if resp.status_code in (200, 201, 202):
            body = resp.json() if resp.content else {}
            print(f"[tablet-intake] ✅ 업로드 완료 (HTTP {resp.status_code})"
                  f"{' → ' + body.get('log_file', '') if body.get('log_file') else ''}")
            return True
        print(f"[tablet-intake] ⚠ 서버 {resp.status_code}: {resp.text[:120]}")
        return False
    except Exception as e:
        print(f"[tablet-intake] ❌ 업로드 실패: {e}")
        return False


# ── Main loop ─────────────────────────────────────────────────────────────────
def run_loop(cfg: dict) -> None:
    duration = int(cfg.get("upload_interval_sec", 30))
    sample_rate = int(cfg.get("sample_rate", 16000))
    channels = int(cfg.get("channels", 1))
    model_name = str(cfg.get("whisper_model", "base"))
    device_name = str(cfg.get("device_name", "galaxy-tab-jh"))
    vault_path = str(cfg.get("vault_path", "04_SiteLog"))
    server = str(cfg.get("bucky_server", "http://127.0.0.1:8765"))
    auto_upload = bool(cfg.get("auto_upload", True))
    chunk_index = 0

    print("══════════════════════════════════════")
    print(" BuckyOS 태블릿 음성 인테이크 시작됨")
    print(f"  서버:  {server}")
    print(f"  청크:  {duration}s | 모델: {model_name}")
    print(f"  기기:  {device_name}")
    print("  Ctrl+C 로 종료")
    print("══════════════════════════════════════")

    try:
        while True:
            chunk_index += 1
            try:
                wav_bytes, actual_dur = record_chunk(duration, sample_rate, channels)
            except KeyboardInterrupt:
                raise
            except Exception as e:
                print(f"[tablet-intake] 녹음 오류: {e}")
                time.sleep(2)
                continue

            # Transcribe
            try:
                transcript = transcribe(wav_bytes, model_name)
            except Exception as e:
                print(f"[tablet-intake] STT 오류: {e}")
                continue

            if not transcript.strip():
                print(f"[tablet-intake] 청크 {chunk_index:03d}: 무음 — 스킵")
                print()
                continue

            preview = transcript[:80] + ("..." if len(transcript) > 80 else "")
            print(f"[tablet-intake] 청크 {chunk_index:03d}: \"{preview}\"")

            # STT 고도화
            try:
                enhanced = _stt_enhance(transcript, context=[])
            except Exception:
                enhanced = {"text": transcript, "intent": "INFORMATION", "entities": []}

            sha = hashlib.sha256(wav_bytes).hexdigest()[:16]
            chunk_rec = {
                "chunk_id": f"chunk-{chunk_index:03d}",
                "chunk_index": chunk_index,
                "duration_sec": actual_dur,
                "sha256": sha,
                "size_bytes": len(wav_bytes),
                "transcript": transcript,
                "intent": enhanced.get("intent", "INFORMATION"),
                "entities": enhanced.get("entities", []),
                "ts": datetime.now(tz=timezone.utc).isoformat(),
            }

            if auto_upload:
                manifest = build_manifest([chunk_rec], device_name, vault_path)
                upload_manifest(manifest, server)
            else:
                print(f"[tablet-intake] auto_upload=false — 로컬 저장만")
            print()

    except KeyboardInterrupt:
        print(f"\n[tablet-intake] 종료됨. (총 {chunk_index}개 청크 처리)")


# ── CLI entry ─────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(
        description="BuckyOS 태블릿 음성 인테이크 — 로컬 Whisper STT 파이프라인",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("--start", action="store_true", help="녹음 루프 시작")
    parser.add_argument("--check", action="store_true", help="의존성 확인 후 종료")
    parser.add_argument("--config", type=Path, metavar="PATH",
                        help="설정 파일 경로 (기본: ~/.bucky_tablet_config.json)")
    parser.add_argument("--server", metavar="URL",
                        help="Bucky 서버 URL (예: http://192.168.1.100:8765)")
    parser.add_argument("--model", choices=["tiny", "base", "small", "medium"],
                        help="Whisper 모델 (기본: base)")
    parser.add_argument("--duration", type=int, metavar="SEC",
                        help="청크 녹음 길이(초, 기본: 30)")
    parser.add_argument("--device", metavar="NAME", help="기기 이름 레이블")
    args = parser.parse_args()

    if args.check:
        print("── 의존성 확인 ──────────────────────────")
        print(f"sounddevice : {'✅' if _HAS_AUDIO else '❌  pip install sounddevice numpy'}")
        print(f"whisper     : {'✅' if _HAS_WHISPER else '❌  pip install openai-whisper'}")
        print(f"requests    : {'✅' if _HAS_REQUESTS else '❌  pip install requests'}")
        print(f"scipy       : {'✅' if _HAS_SCIPY else '⚠  pip install scipy (선택)'}")
        print(f"stt_enhancer: {'✅' if _HAS_ENHANCER else '⚠  bucky_stt_enhancer.py 경로 외부'}")
        return

    if not args.start:
        parser.print_help()
        return

    cfg = load_config(args.config)
    if args.server:
        cfg["bucky_server"] = args.server
    if args.model:
        cfg["whisper_model"] = args.model
    if args.duration:
        cfg["upload_interval_sec"] = args.duration
    if args.device:
        cfg["device_name"] = args.device

    run_loop(cfg)


if __name__ == "__main__":
    main()
