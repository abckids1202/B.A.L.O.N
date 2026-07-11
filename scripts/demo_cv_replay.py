from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend-url", default="http://127.0.0.1:8000")
    parser.add_argument("--scenario", default="ALL", choices=["ALL", "PACKAGE_DAMAGE", "WRONG_LOADING", "LOADING_COMPLIANCE", "HUB_CONGESTION"])
    args = parser.parse_args()
    url = f"{args.backend_url.rstrip('/')}/api/cv/demo-replay?scenario={args.scenario}"
    req = urllib.request.Request(url, data=b"", method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            print(json.dumps(json.loads(response.read().decode("utf-8")), indent=2))
    except urllib.error.URLError as exc:
        raise SystemExit(f"Backend is not reachable at {args.backend_url}. Start it first with: python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000. Details: {exc}") from exc


if __name__ == "__main__":
    main()
