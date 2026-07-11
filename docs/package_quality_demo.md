# Package Quality Demo

Use `PACKAGE_QUALITY` mode. Replay fallback: `python scripts/demo_cv_replay.py --scenario PACKAGE_DAMAGE`.

Production path: package detector finds the parcel, damage detector finds visible damage, persistence/cooldown prevents frame spam, and `/api/cv/events` receives `PACKAGE_DAMAGE_DETECTED`.
