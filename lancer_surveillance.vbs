Set WshShell = CreateObject("WScript.Shell")
' Utilise pythonw.exe pour exécuter le script sans fenêtre
cmd = """" & WshShell.ExpandEnvironmentStrings("%LOCALAPPDATA%") & _
      "\Programs\Python\Python313\pythonw.exe"" " & _
      """" & "C:\Users\Utilisateur\Desktop\cours-de-maths\autom_update_progression.py" & """"
WshShell.Run cmd, 0, False
