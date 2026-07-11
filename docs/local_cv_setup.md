# Local CV Setup

1. Start backend: `python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000`
2. Start frontend: `npm.cmd run dev --workspace frontend`
3. Start worker: `python -m cv_worker.main`
4. Open the Visual Intelligence pages.
5. If no weights are trained, use replay: `python scripts/demo_cv_replay.py --scenario ALL`.

## Desktop proof controls

Run:

```powershell
python -m cv_worker.main --camera-index 0
```

Keys:

- `1`: Package Quality
- `2`: Dispatch Validation
- `3`: Loading Compliance
- `4`: Hub Vision
- `E`: emit one material normalized CV event to FastAPI
- `B`: toggle backend event sending
- `S`: start/resume camera
- `P`: pause camera
- `R`: reset latest local result
- `Q` or `Esc`: quit cleanly

The app starts even when weights are missing. It should still show raw camera video and clearly label `WEIGHTS_MISSING`.
