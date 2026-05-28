#!/usr/bin/env python3
"""Bucky Voice — 마이크 입력 → Whisper STT → Bucky → pyttsx3 TTS

사용법:
    python scripts/bucky_voice.py              # 기본 (whisper small, 한국어)
    python scripts/bucky_voice.py --model base # 더 빠른 모델
    python scripts/bucky_voice.py --lang en    # 영어 모드

Enter → 녹음 시작 / 다시 Enter → 녹음 중지 → Bucky 답변 → TTS 재생
q + Enter → 종료
"""

from __future__ import annotations

import argparse
import io
import os
import queue
import sys
import threading
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env", encoding="utf-8")

import numpy as np
import pyttsx3
import sounddevice as sd
import whisper

from bucky_client import BuckyError, run_bucky

SAMPLE_RATE = 16000
CHANNELS = 1

SYSTEM_PROMPT = """# Bucky 음성 대화

당신은 Bucky입니다. 사용자의 Obsidian 지식 관리 시스템과 연결된 AI 에이전트입니다.
음성 답변이므로 짧고 명확하게 한국어로 답변하세요.
마크다운, 코드블록, 특수기호 사용 금지. 자연스러운 구어체로만 답변.
PC 환경 감지 메시지(집 PC, 노트북 등) 절대 출력 금지.
"""


def record_until_enter(sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Enter를 누를 때까지 마이크 녹음 후 numpy array 반환."""
    audio_queue: queue.Queue[np.ndarray] = queue.Queue()
    stop_event = threading.Event()

    def callback(indata: np.ndarray, frames: int, time_info, status) -> None:
        audio_queue.put(indata.copy())

    stream = sd.InputStream(
        samplerate=sample_rate,
        channels=CHANNELS,
        dtype="float32",
        callback=callback,
    )

    print("🎙️  녹음 중... (Enter → 중지)", flush=True)
    with stream:
        input()
        stop_event.set()

    chunks: list[np.ndarray] = []
    while not audio_queue.empty():
        chunks.append(audio_queue.get())

    return np.concatenate(chunks, axis=0).flatten() if chunks else np.zeros(0, dtype="float32")


def transcribe(audio: np.ndarray, model: whisper.Whisper, lang: str) -> str:
    result = model.transcribe(audio, language=lang, fp16=False)
    return result.get("text", "").strip()


def speak(engine: pyttsx3.Engine, text: str) -> None:
    engine.say(text)
    engine.runAndWait()


def build_tts_engine(rate: int = 180) -> pyttsx3.Engine:
    engine = pyttsx3.init()
    engine.setProperty("rate", rate)
    # Windows SAPI5 한국어 음성 선택 시도
    voices = engine.getProperty("voices")
    for v in voices:
        if "korean" in v.name.lower() or "ko" in v.id.lower():
            engine.setProperty("voice", v.id)
            break
    return engine


def main() -> None:
    parser = argparse.ArgumentParser(description="Bucky 음성 대화")
    parser.add_argument("--model", default="small", help="Whisper 모델 (tiny/base/small/medium)")
    parser.add_argument("--lang", default="ko", help="인식 언어 (ko/en/ja 등)")
    parser.add_argument("--tts-rate", type=int, default=180, help="TTS 말하기 속도")
    args = parser.parse_args()

    print(f"Whisper '{args.model}' 모델 로딩 중...", flush=True)
    whisper_model = whisper.load_model(args.model)
    tts_engine = build_tts_engine(rate=args.tts_rate)

    conversation: list[dict] = []

    print("\n✅ Bucky 음성 대화 준비 완료")
    print("   Enter → 녹음 시작 | 녹음 중 Enter → 중지 | q → 종료\n")

    while True:
        cmd = input("[ Enter 녹음 / q 종료 ] ").strip().lower()
        if cmd == "q":
            print("종료합니다.")
            break

        audio = record_until_enter()
        if audio.size < SAMPLE_RATE:
            print("⚠️  너무 짧습니다. 다시 시도하세요.", flush=True)
            continue

        print("🔍 음성 인식 중...", flush=True)
        user_text = transcribe(audio, whisper_model, args.lang)
        if not user_text:
            print("⚠️  인식 결과 없음. 다시 시도하세요.", flush=True)
            continue

        print(f"👤 나: {user_text}", flush=True)

        conversation.append({"role": "user", "content": user_text})
        history_str = "\n".join(
            f"{m['role'].title()}: {m['content']}" for m in conversation[-10:]
        )
        prompt = f"{SYSTEM_PROMPT}\n\n## 대화\n\n{history_str}"

        print("🤖 Bucky 생각 중...", flush=True)
        try:
            # 음성 대화 → task_type='chat' (Sonnet 기본, 한도 시 폴백)
            reply = run_bucky(prompt, task_type="chat")
        except BuckyError as e:
            print(f"⚠️  Bucky 오류: {e}", flush=True)
            continue

        conversation.append({"role": "assistant", "content": reply})
        print(f"🤖 Bucky: {reply}\n", flush=True)

        speak(tts_engine, reply)


if __name__ == "__main__":
    main()
