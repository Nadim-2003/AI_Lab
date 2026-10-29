@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Virtual environment not found. Run these commands first:
  echo py -3.12 -m venv .venv
  echo .venv\Scripts\python.exe -m pip install -r requirements.lock
  exit /b 1
)
echo Preparing actual OpenStreetMap data. Downloads may take several minutes; --publish-partial uses saved checkpoints offline.
".venv\Scripts\python.exe" scripts\acquire_data.py %*
if errorlevel 1 (
  echo Data acquisition failed. Read the error above; no sample data was substituted.
  exit /b 1
)
echo Dataset saved. Stop and restart the backend, then click Check dataset status in the frontend.
endlocal
