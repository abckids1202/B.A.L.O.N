from __future__ import annotations

import argparse
import time


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-index", type=int, default=5)
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args()
    try:
        import cv2  # type: ignore
    except Exception as exc:
        raise SystemExit(f"OpenCV is not installed: {exc}") from exc

    working = []
    for index in range(args.max_index + 1):
        capture = cv2.VideoCapture(index)
        backend = "default"
        if not capture.isOpened():
            capture.release()
            capture = cv2.VideoCapture(index, cv2.CAP_DSHOW)
            backend = "CAP_DSHOW"
        ok, frame = capture.read() if capture.isOpened() else (False, None)
        if ok:
            h, w = frame.shape[:2]
            print(f"index {index}: OK via {backend}, frame {w}x{h}")
            working.append(index)
            if args.preview:
                started = time.time()
                while time.time() - started < 5:
                    ok, frame = capture.read()
                    if not ok:
                        break
                    cv2.imshow(f"camera {index}", frame)
                    if (cv2.waitKey(1) & 0xFF) in {ord("q"), 27}:
                        break
                cv2.destroyAllWindows()
        else:
            print(f"index {index}: unavailable")
        capture.release()
    if not working:
        raise SystemExit("No readable camera indexes found.")
    print(f"Readable camera indexes: {working}")


if __name__ == "__main__":
    main()
