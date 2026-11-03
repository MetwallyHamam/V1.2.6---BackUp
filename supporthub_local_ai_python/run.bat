@echo off
setlocal
pushd "%~dp0"
if not exist "venv\Scripts\python.exe" (
  echo Local AI virtual environment was not found in "%CD%\venv".
  echo Run: python -m venv venv
  popd
  exit /b 1
)
"venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8090
set "EXIT_CODE=%ERRORLEVEL%"
popd
exit /b %EXIT_CODE%
