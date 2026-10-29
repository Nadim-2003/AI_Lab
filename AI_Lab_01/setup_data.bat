@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Virtual environment not found. Run these commands first:
  echo py -3.12 -m venv .venv
  echo .venv\Scripts\python.exe -m pip install -r requirements.lock
  exit /b 1
)
echo Default area: Dhaka University and nearby roads. Full Dhaka is optional with --area dhaka.
echo Preparing OpenStreetMap data. --diagnose checks connectivity without downloading the dataset.
".venv\Scripts\python.exe" scripts\acquire_data.py %*
if errorlevel 1 (
  echo Command did not complete successfully. Read the specific error above; no sample data was substituted.
  exit /b 1
)
echo Command completed. If a dataset was installed, restart the backend and check dataset status in the frontend.
endlocal
