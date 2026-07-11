$ErrorActionPreference = "Stop"
Write-Host "Validating package dataset..."
python scripts\cv\validate_package_dataset.py
Write-Host "Validating damage dataset..."
python scripts\cv\validate_damage_dataset.py
Write-Host ""
Write-Host "No training is started automatically."
Write-Host "To train package model:"
Write-Host "python scripts\cv\train_package_detector.py --data `"Package and label detection.v4i.yolov11\data.yaml`" --project models\cv\package_detector"
Write-Host "To train damage model:"
Write-Host "python scripts\cv\train_damage_detector.py --data `"Parcel Damage Detection.v2-roboflow-instant-2--eval-.yolov11\data.yaml`" --project models\cv\damage_detector"
