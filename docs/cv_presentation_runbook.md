# CV Presentation Runbook

Terminal 1:

```powershell
cd C:\Users\charl\OneDrive\Desktop\Routix
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Terminal 2:

```powershell
cd C:\Users\charl\OneDrive\Desktop\Routix
npm.cmd run dev --workspace frontend
```

Terminal 3:

```powershell
cd C:\Users\charl\OneDrive\Desktop\Routix
python -m cv_worker.main --camera-index 0
```

Proof sequence:

1. Confirm the OpenCV window shows raw webcam video.
2. Open `http://127.0.0.1:8765/docs`.
3. Press `1`, then `E` to emit a package quality event.
4. Confirm backend terminal receives the event and the web app Visual Intelligence pages update.
5. Repeat with keys `2`, `3`, and `4`.

## Verified runtime proof

- OpenCV version checked: installed.
- Camera index `0` was readable at `640x480`.
- Worker API `/health` returned online status.
- Backend accepted one desktop-style `PACKAGE_DAMAGE_DETECTED` event.
- Current limitation: the desktop window itself must be visually confirmed by the presenter because automated terminal verification cannot inspect the visible GUI window.
