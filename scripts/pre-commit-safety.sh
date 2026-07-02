#!/bin/sh
# ============================================================
#  pre-commit 안전장치 (비개발자 보호용) - 마스터 복사본
#   1) 실수로 인한 파일 삭제 커밋 차단
#   2) _Private / .private 경로 커밋 차단 (기존 규칙 유지)
#
#  이 파일은 "원본"입니다. 각 PC에서 실제로 작동하게 하려면
#  저장소 루트의  안전장치설치.bat  를 더블클릭하세요.
#  (이 파일을 .git/hooks/pre-commit 로 복사해 활성화합니다)
# ============================================================

# ---------- 1) 삭제 방지 ----------
deleted=$(git diff --cached --name-only --diff-filter=D)
if [ -n "$deleted" ]; then

  # (a) 핵심 파일은 1개라도 삭제되면 무조건 차단
  hit=""
  for f in vercel.json package.json .gitignore .vercelignore .mcp.json CLAUDE.md AGENTS.md api/protected.js docs/shared/nav.js; do
    if printf '%s\n' "$deleted" | grep -Fxq "$f"; then
      hit="$hit$f
"
    fi
  done
  if [ -n "$hit" ]; then
    echo ""
    echo "============================================================"
    echo "[중단] 커밋을 멈췄습니다 - '중요 파일'이 삭제되려고 합니다!"
    echo "------------------------------------------------------------"
    printf '%s' "$hit" | sed 's/^/   X /'
    echo "------------------------------------------------------------"
    echo " 거의 항상 '실수'입니다. 되돌리려면 아래 한 줄을 복사+붙여넣기:"
    echo ""
    echo "      git restore --staged ."
    echo ""
    echo " 그 다음 다시 저장(커밋)하면 됩니다."
    echo "============================================================"
    exit 1
  fi

  # (b) 한 번에 4개 이상 삭제도 차단
  count=$(printf '%s\n' "$deleted" | grep -c .)
  if [ "$count" -gt 3 ]; then
    echo ""
    echo "============================================================"
    echo "[중단] 커밋을 멈췄습니다 - 한 번에 ${count}개 파일이 삭제됩니다!"
    echo "------------------------------------------------------------"
    printf '%s\n' "$deleted" | sed 's/^/   X /'
    echo "------------------------------------------------------------"
    echo " 의도한 삭제가 아니라면 아래 한 줄을 복사+붙여넣기:"
    echo ""
    echo "      git restore --staged ."
    echo ""
    echo " (정말 삭제가 맞다면:  git commit --no-verify ... )"
    echo "============================================================"
    exit 1
  fi
fi

# ---------- 2) _Private / .private 차단 (기존 규칙) ----------
blocked=$(git diff --cached --name-only | grep -E "(^|/)(_Private|\.private)/")
if [ -n "$blocked" ]; then
  echo "ERROR: _Private path blocked by pre-commit hook:"
  echo "$blocked"
  echo "Remove these files from staging (git restore --staged <file>) before committing."
  exit 1
fi

exit 0
