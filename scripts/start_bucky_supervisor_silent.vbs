Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
rootDir = fso.GetParentFolderName(scriptDir)
supervisor = fso.BuildPath(scriptDir, "bucky_bot_supervisor_patched.py")
logDir = fso.BuildPath(rootDir, ".logs")
If Not fso.FolderExists(logDir) Then
  fso.CreateFolder(logDir)
End If
cmd = "cmd.exe /c cd /d """ & rootDir & """ && python -X utf8 """ & supervisor & """ >> """ & fso.BuildPath(logDir, "supervisor_out.log") & """ 2>> """ & fso.BuildPath(logDir, "supervisor_err.log") & """"
shell.Run cmd, 0, False
