# Local CV Desktop Architecture

`python -m cv_worker.main` runs two local components:

1. Worker API thread at `http://127.0.0.1:8765`.
2. OpenCV desktop window that owns camera access.

The desktop window is the physical demo surface. The browser is the command center and consumes backend events/digital twin updates. The local app sends normalized material events only; it does not upload every camera frame.
