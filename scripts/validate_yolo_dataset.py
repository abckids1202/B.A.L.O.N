from pathlib import Path

if __name__ == "__main__":
    root = Path("data/yolo")
    print({"dataset_exists": root.exists(), "note": "YOLO dataset is optional; demo mode is active until images/labels are provided."})
