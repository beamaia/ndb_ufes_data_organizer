#!/usr/bin/env python3
"""Top-level Phase 3 runner.

This script loads the Phase 3 fold-creation module and executes the pipeline.
"""

from pathlib import Path
import os
import sys

PROJECT_ROOT = Path(__file__).parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))
os.chdir(PROJECT_ROOT)

from src.phase3.phase3_fold_creation import main

if __name__ == "__main__":
    main()
