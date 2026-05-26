#!/usr/bin/env bash
# Codex pre-commit hook 설치 스크립트
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
HOOK_DIR="$(git rev-parse --git-dir)/hooks"

cp "$ROOT/.githooks/pre-commit" "$HOOK_DIR/pre-commit"
chmod +x "$HOOK_DIR/pre-commit"

echo "✅ Codex pre-commit hook 설치 완료"
echo "   위치: $HOOK_DIR/pre-commit"
echo ""
echo "옵션 환경변수:"
echo "  CODEX_PRECOMMIT_TIMEOUT=120   # 타임아웃(초)"
echo "  CODEX_PRECOMMIT_MAX_FILES=10  # 최대 검수 파일 수"
echo "  CODEX_COMMAND=codex           # Codex CLI 경로"
