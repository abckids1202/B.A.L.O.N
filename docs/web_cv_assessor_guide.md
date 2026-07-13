# Web CV Assessor Guide

Open the deployed Vercel app and go to Visual Intelligence.

## Package Quality

1. Open Package Quality.
2. Press Start Camera.
3. Hold one package clearly in view.
4. Press Analyze Package.
5. Confirm the page shows the package box, damage status, backend decision, impact, and module event stream.

## Dispatch Validation

1. Open Dispatch Validation.
2. Select Wrong Context to test blocking or Correct Context to test release.
3. Press Start Camera.
4. Show the `SHP-LOAD-001` QR code.
5. Press Scan QR.
6. Confirm planned vehicle, active vehicle, VALID or WRONG_VEHICLE, and dispatch READY or BLOCKED.

## Loading Compliance

1. Open Loading Compliance.
2. Arrange packages in the loading area.
3. Press Capture Snapshot.
4. Confirm the count is frozen.
5. A result over five packages blocks dispatch; five or fewer is ready.

## Hub Vision

1. Open Hub Vision.
2. Place one package in the left Receiving zone.
3. Press Start Journey.
4. Move the package to Processing and press Send Observation.
5. Move it to Dispatch and press Send Observation.
6. Press Stop Journey.
7. Confirm stage times, projected dwell, estimated delay, risk score, and final event.

## Fallbacks

If browser camera access is denied, use Upload Image. Replay remains available and is labeled as replay, not live inference.
