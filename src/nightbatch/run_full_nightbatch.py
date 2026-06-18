import os
import sys

# 1. PATH SETUP
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, os.pardir, os.pardir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import src.nightbatch.run_fx_update as fx_updater
from src.nightbatch.ishares_importer import process_all_ishares_assets


def run_full_nightbatch():
    print("Starting full nightbatch run...")

    print("Step 1: FX rates update")
    fx_updater.headless_load_missing_fx_rates()

    print("Step 2: iShares asset price update")
    summary = process_all_ishares_assets(dry_run=False)
    print(f"iShares import summary: {summary}")


if __name__ == "__main__":
    run_full_nightbatch()
