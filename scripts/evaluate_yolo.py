from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.model_training_common import register_yolo_demo

if __name__ == '__main__':
    register_yolo_demo()
