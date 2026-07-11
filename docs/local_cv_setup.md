# Local CV Setup

1. Start backend: `python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000`
2. Start frontend: `npm.cmd run dev --workspace frontend`
3. Start worker: `python -m cv_worker.main`
4. Open the Visual Intelligence pages.
5. If no weights are trained, use replay: `python scripts/demo_cv_replay.py --scenario ALL`.
