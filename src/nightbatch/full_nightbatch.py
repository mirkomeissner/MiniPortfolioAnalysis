import os
import sys

# 1. PATH SETUP
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, os.pardir, os.pardir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import src.nightbatch.fx_update as fx_updater
from src.nightbatch.ishares_importer import process_all_ishares_assets


def run_full_nightbatch(dry_run: bool = False):
    env = os.environ.get("APP_ENV", "main")
    print(f"Starting full nightbatch run on environment {env} (dry_run={dry_run})...")

    print("Step 1: FX rates update")
    fx_summary = fx_updater.headless_load_missing_fx_rates(dry_run=dry_run)
    print(f"FX update summary: {fx_summary}")

    print("Step 2: iShares asset price update")
    summary = process_all_ishares_assets(dry_run=dry_run)
    print(f"iShares import summary: {summary}")

    return {"fx": fx_summary, "ishares": summary, "dry_run": dry_run}


if __name__ == "__main__":
    run_full_nightbatch(dry_run=False)
