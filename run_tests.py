"""Run OIL test suites (offline, deterministic)."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

SUITES = [
    "tests/test_ingest_index.py",
    "tests/test_loaders.py",
    "tests/test_answer.py",
    "tests/test_app.py",
    "tests/test_llm.py",
]


def main():
    failures = 0
    for suite in SUITES:
        print(f"\n{'=' * 60}\n  {suite}\n{'=' * 60}")
        if subprocess.run([sys.executable, suite], cwd=str(ROOT)).returncode != 0:
            failures += 1
    print(f"\n{'=' * 60}\n  SUITES: {len(SUITES) - failures}/{len(SUITES)} passed\n{'=' * 60}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
