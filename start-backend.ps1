# Starts the Detective AI API (and serves the built frontend at http://127.0.0.1:8000 if frontend/dist exists).
Set-Location "$PSScriptRoot\backend"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
