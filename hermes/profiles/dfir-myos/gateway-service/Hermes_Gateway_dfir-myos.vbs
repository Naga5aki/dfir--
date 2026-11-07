' Hermes Agent Gateway - Messaging Platform Integration
Option Explicit
Dim sh, env, existing_pp
Set sh = CreateObject("WScript.Shell")
Set env = sh.Environment("PROCESS")
env.Item("HERMES_HOME") = "C:\Users\TWK\AppData\Local\hermes\profiles\dfir-myos"
env.Item("PYTHONIOENCODING") = "utf-8"
env.Item("HERMES_GATEWAY_DETACHED") = "1"
env.Item("HERMES_SUPERVISED_CHILD") = "1"
env.Item("VIRTUAL_ENV") = "C:\Users\TWK\AppData\Local\hermes\tools"
existing_pp = env.Item("PYTHONPATH")
If Len(existing_pp) > 0 Then
  env.Item("PYTHONPATH") = "C:\Users\TWK\AppData\Local\hermes\hermes-agent;" & existing_pp
Else
  env.Item("PYTHONPATH") = "C:\Users\TWK\AppData\Local\hermes\hermes-agent"
End If
sh.CurrentDirectory = "C:\Users\TWK\AppData\Local\hermes\profiles\dfir-myos"
sh.Run "C:\Users\TWK\AppData\Local\hermes\tools\python-3.14.9+20261021-win32-x64\python.exe -m hermes_cli.main --profile dfir-myos gateway run", 0, False
