#!/usr/bin/env python3
"""
Whisper 자동 전사 — 오디오 파일을 텍스트로 변환.

openai-whisper 패키지가 없으면 None을 반환 (graceful fallback).

Usage (단독 실행):
    python scripts/whisper_transcribe.py audio.mp3
    python scripts/whisper_transcribe.py audio.wav --model small --language ko

Usage (모듈로 임포트):
    from scripts.whisper_transcribe import transcribe
    text = transcribe(Path("audio.mp3"))  # 실패 시 None 반환

모델 크기별 특성:
    tiny   — 가장 빠름, 정확도 낮음
    base   — 기본값, 속도/정확도 균형
    small  — 한국어 정확도 향상
    medium — 높은 정확도, 느림
    large  — 최고 정확도, 매우 느림
"""

import argparse
import sys
from pathlib import Path


def transcribe(audio_path: Path, model_name: str = "base", language: str = "ko") -> str | None:
    """
    오디오 파일을 전사. openai-whisper 미설치 시 None 반환.

    Args:
        audio_path: 오디오 파일 경로 (.wav / .mp3 / .m4a / .ogg / .flac)
        model_name: Whisper 모델 크기 (tiny/base/small/medium/large)
        language: 전사 언어 코드 (ko=한국어, en=영어, None=자동감지)

    Returns:
        전사 텍스트 문자열, 실패 시 None
    """
    try:
        import whisper
    except ImportError:
        print("Warning: openai-whisper 미설치. pip install openai-whisper 실행 후 재시도.")
        return None

    if not audio_path.exists():
        print(f"Error: 오디오 파일 없음 — {audio_path}")
        return None

    print(f"Whisper 전사 시작: {audio_path.name} (model={model_name}, lang={language})")
    try:
        model = whisper.load_model(model_name)
        options = {}
        if language:
            options["language"] = language
        result = model.transcribe(str(audio_path), **options)
        text = result.get("text", "").strip()
    except Exception as e:
        print(f"Error: Whisper 전사 실패 — {e}")
        return None

    if not text:
        print("Warning: 전사 결과가 비어 있습니다.")
        return None

    print(f"전사 완료: {len(text)}자")
    return text


def main():
    parser = argparse.ArgumentParser(description="Whisper 오디오 전사")
    parser.add_argument("audio", type=Path, help="오디오 파일 경로")
    parser.add_argument("--model", default="base", help="Whisper 모델 (기본: base)")
    parser.add_argument("--language", default="ko", help="언어 코드 (기본: ko)")
    parser.add_argument("--output", type=Path, help="전사 결과 저장 경로 (.txt). 미지정 시 stdout 출력")
    args = parser.parse_args()

    text = transcribe(args.audio, model_name=args.model, language=args.language)

    if text is None:
        sys.exit(1)

    if args.output:
        args.output.write_text(text, encoding="utf-8")
        print(f"저장 완료: {args.output}")
    else:
        print("\n--- 전사 결과 ---")
        print(text)


if __name__ == "__main__":
    main()
