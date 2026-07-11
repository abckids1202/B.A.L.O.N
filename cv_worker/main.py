from __future__ import annotations

import uvicorn

from cv_worker.config import config


def main() -> None:
    uvicorn.run("cv_worker.api:app", host="127.0.0.1", port=config.worker_port, reload=False)


if __name__ == "__main__":
    main()
