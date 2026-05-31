Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
rootDir = fso.GetParentFolderName(scriptDir)
watchdog = fso.BuildPath(scriptDir, "discord_bot_watchdog.py")
logDir = fso.BuildPath(rootDir, ".logs")
If Not fso.FolderExists(logDir) Then
  fso.CreateFolder(logDir)
End If
cmd = "cmd.exe /c cd /d """ & rootDir & """ && python -X utf8 """ & watchdog & """ > """ & fso.BuildPath(logDir, "watchdog_out.log") & """ 2> """ & fso.BuildPath(logDir, "watchdog_err.log") & """"
shell.Run cmd, 0, False
