# Loading Compliance Vision

Loading compliance uses package detection plus tracking and configured regions of interest. It estimates whether the dock process is visually compliant before the vehicle departs.

Core signals:

- package track entered loading ROI
- package track crossed vehicle threshold
- package track remained inside vehicle ROI
- loaded package track count
- visual utilization estimate
- dispatch allowed or blocked

This is not a true volume, weight, or legal load measurement. It should be reconciled with WMS, scanner events, vehicle capacity, and operator confirmation before production enforcement.
