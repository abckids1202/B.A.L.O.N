$ErrorActionPreference = "Stop"
Write-Host "Starting only the local CV desktop application."
Write-Host "Make sure the backend is running if you want events to update B.A.L.O.N:"
Write-Host "python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000"
Write-Host ""
python -m cv_worker.main --camera-index 0
