Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
rootDir = fso.GetParentFolderName(scriptDir)
watchdog = fso.BuildPath(scriptDir, "discord_bot_watchdog.py")
logDir = fso.BuildPath(rootDir, ".logs")
If Not fso.FolderExists(logDir) Then
  fso.CreateFolder(logDir)
End If
' 검증된 인터프리터(Python312) 고정 — bare "python"은 WindowsApps 스텁/Python314가
' 잡힐 수 있어 예약작업 환경에서 불안정. 없으면 PATH의 python으로 폴백.
pythonExe = "C:\Users\user1\AppData\Local\Programs\Python\Python312\python.exe"
If Not fso.FileExists(pythonExe) Then
  pythonExe = "python"
End If
cmd = "cmd.exe /c cd /d """ & rootDir & """ && """ & pythonExe & """ -X utf8 """ & watchdog & """ > """ & fso.BuildPath(logDir, "watchdog_out.log") & """ 2> """ & fso.BuildPath(logDir, "watchdog_err.log") & """"
shell.Run cmd, 0, False
