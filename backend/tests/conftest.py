import os
import sys
from pathlib import Path

os.environ["DEMO_MODE"] = "true"
os.environ["DATABASE_URL"] = "sqlite:////private/tmp/docpilot-test.db"

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
