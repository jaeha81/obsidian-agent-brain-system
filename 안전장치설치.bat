@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo ============================================================
echo   커밋 안전장치 설치
echo   (실수로 파일이 삭제되는 커밋을 자동으로 막아줍니다)
echo ============================================================
echo.

if not exist ".git\hooks" (
  echo  [오류] 이 폴더는 git 저장소가 아닙니다.
  echo  obsidian-agent-brain-system 폴더에서 실행하세요.
  echo.
  pause
  exit /b 1
)

copy /Y "scripts\pre-commit-safety.sh" ".git\hooks\pre-commit" >nul

if %errorlevel%==0 (
  echo  [완료] 안전장치가 설치되었습니다!
  echo.
  echo  이제 이 PC에서는 실수로 중요한 파일이나
  echo  여러 파일이 삭제되는 커밋이 자동으로 차단됩니다.
) else (
  echo  [오류] 설치에 실패했습니다. scripts\pre-commit-safety.sh 파일을 확인하세요.
)

echo.
pause
