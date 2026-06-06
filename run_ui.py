"""Launch the OIL local web UI: python run_ui.py  ->  http://127.0.0.1:5000
Set OIL_MODEL=cloud only for demos on non-confidential documents.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from oil.app import main

if __name__ == "__main__":
    main()
