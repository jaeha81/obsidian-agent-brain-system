---
title: 삼성 태블릿 원클릭 설치 가이드
date: 2026-06-09
source: daily-plus/2026-06-09.md (Card 3)
priority: P1
category: knowledge
status: distilled
tags:
  - samsung-tablet
  - adb
  - stt
  - android
  - install
  - daily-plus
  - knowledge
---

# 삼성 태블릿 원클릭 설치 가이드

> ChatGPT Pulse 2026-06-09 Card 3 증류 (P1 · knowledge-candidate)

## 목적

삼성 태블릿에서 음성 녹음→자동 STT→템플릿 적용까지 한 번에 설치·테스트하는 원클릭 패키지. ADB + USB 디버깅 기반, 비개발자 기준.

## 설치 전 준비사항

1. 삼성 태블릿: Android 11 이상
2. PC: ADB 드라이버 설치 (삼성 USB 드라이버)
3. USB 케이블: 데이터 전송 가능한 USB-C
4. 태블릿에서 개발자 옵션 활성화:
   - 설정 → 디바이스 정보 → 소프트웨어 정보 → 빌드 번호 7번 탭
   - 설정 → 개발자 옵션 → USB 디버깅 ON

## ADB 명령

```bash
# 연결 확인
adb devices

# APK 설치 (RecForge II 또는 자체 앱)
adb install voice-recorder.apk

# 설정 파일 밀어넣기
adb push recorder-config.json /sdcard/Download/

# VOSK 모델 업로드
adb push vosk-model-small-ko-0.22.zip /sdcard/Download/

# 설치 스크립트 실행
adb shell "sh /sdcard/Download/install.sh"
```

## STT 설정

```bash
# VOSK 초기화 (태블릿 내 터미널 또는 Termux)
cd /sdcard/Download
unzip vosk-model-small-ko-0.22.zip
mv vosk-model-small-ko-0.22 vosk-model

# Python STT 스크립트 실행 테스트
python3 stt_test.py --model vosk-model --audio test.wav
```

## 현장 데모 테스트 방법

1. RecForge II 앱 실행 → 16kHz Mono WAV 녹음
2. 5초 테스트 녹음: "현장 테스트 일, 이, 삼"
3. STT 파이프라인 실행: 텍스트 변환 결과 확인
4. 결과를 템플릿에 자동 입력: 현장명, 날짜, 작업 내용
5. 생성된 보고서 PDF 미리보기

## 비개발자 설치 체크리스트

- [ ] ADB 드라이버 설치 완료
- [ ] USB 디버깅 ON 확인
- [ ] `adb devices` → 태블릿 인식 확인
- [ ] APK 설치 완료
- [ ] VOSK 모델 업로드 완료
- [ ] 5초 녹음 테스트 통과
- [ ] STT 결과 텍스트 변환 확인

## 관련 컨텍스트

- [[samsung-tablet-voice-setup]]
- [[privacy-first-stt-ops]]
- [[one-click-deploy-package]]
