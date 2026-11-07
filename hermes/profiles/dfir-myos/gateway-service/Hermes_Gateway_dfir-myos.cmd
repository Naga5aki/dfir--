@echo off
rem Hermes Agent Gateway - Messaging Platform Integration
cd /d C:\Users\TWK\AppData\Local\hermes\profiles\dfir-myos
set "HERMES_HOME=C:\Users\TWK\AppData\Local\hermes\profiles\dfir-myos"
set "PYTHONIOENCODING=utf-8"
set "HERMES_GATEWAY_DETACHED=1"
set "HERMES_SUPERVISED_CHILD=1"
set "VIRTUAL_ENV=C:\Users\TWK\AppData\Local\hermes\tools"
set "PYTHONPATH=C:\Users\TWK\AppData\Local\hermes\hermes-agent;%PYTHONPATH%"
C:\Users\TWK\AppData\Local\hermes\tools\python-3.14.9+20261021-win32-x64\python.exe -m hermes_cli.main --profile dfir-myos gateway run
exit /b 0
