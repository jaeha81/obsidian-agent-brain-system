#NoEnv
#SingleInstance Force
SetWorkingDir %A_ScriptDir%

; /watch 단축키 — Claude Code / Codex 채팅창 전용
;
; Ctrl+Shift+W  → 커서 위치에 /watch  삽입 (URL 직접 붙여넣기)
; Ctrl+Shift+Alt+W → URL 입력창 팝업 후 /watch URL 전송

; --- 기본: /watch + 공백 삽입 ---
^+w::
    SendInput /watch {Space}
return

; --- 고급: URL 입력창 팝업 후 엔터까지 자동 전송 ---
^+!w::
    InputBox, url, /watch 실행, YouTube 또는 로컬 파일 경로를 입력하세요:,, 500, 130
    if ErrorLevel
        return
    if (url = "")
        return
    SendInput /watch %url%{Enter}
return
