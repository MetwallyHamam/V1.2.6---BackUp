@echo off
setlocal
pushd "%~dp0"
if not exist "venv\Scripts\python.exe" (
  echo Local AI virtual environment was not found in "%CD%\venv".
  echo Install Python 3.12 or newer, then recreate it with: python -m venv venv
  popd
  exit /b 1
)
"venv\Scripts\python.exe" -c "import sys" >nul 2>&1
if errorlevel 1 (
  echo The Local AI virtual environment is broken or was copied from another computer.
  echo Delete the local-ai\venv folder, install Python 3.12 or newer, and run:
  echo   python -m venv venv
  echo   venv\Scripts\python.exe -m pip install -r requirements.txt
  popd
  exit /b 1
)
"venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8090
set "EXIT_CODE=%ERRORLEVEL%"
popd
exit /b %EXIT_CODE%
