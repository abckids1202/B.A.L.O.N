"""Vercel FastAPI entrypoint.

Vercel looks for Python serverless functions under api/. This file imports
and exposes the real application from backend.main so Vercel has one clear
FastAPI app target instead of guessing between backend/main.py and tests.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Vercel's deployed filesystem is not a good place for mutable SQLite files.
# /tmp is writable for serverless execution; set an explicit env var in Vercel
# if you want a different path.
os.environ.setdefault("LOGISENSE_DB_PATH", "/tmp/logisense.db")
os.environ.setdefault("LOGISENSE_TIMEZONE", "Asia/Jakarta")
os.environ.setdefault("LOGISENSE_RANDOM_SEED", "42")

from backend.main import app  # noqa: E402
from database.connection import initialize_database  # noqa: E402

initialize_database()
