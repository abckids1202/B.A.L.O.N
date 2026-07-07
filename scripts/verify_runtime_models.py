from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.model_training_common import dataset


if __name__ == "__main__":
    X, delay, breach, carbon = dataset()
    print("verify_runtime_models: OK")
    print({"rows": len(X), "features": X.shape[1]})
