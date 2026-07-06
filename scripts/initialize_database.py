from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.connection import initialize_database


if __name__ == "__main__":
    initialize_database()
    print("Initialized SQLite database.")
