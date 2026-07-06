Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

appDir = fso.GetParentFolderName(WScript.ScriptFullName)
shell.CurrentDirectory = appDir

' Install dependencies quietly on startup.
shell.Run "py -m pip install -r requirements.txt -q", 0, True

' Start the permanent local server without a console window.
shell.Run "pyw server.py", 0, False

WScript.Sleep 1500
shell.Run "http://127.0.0.1:5050", 1, False
