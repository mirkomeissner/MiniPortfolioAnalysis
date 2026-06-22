import os
import sys

# 1. PATH SETUP
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, os.pardir, os.pardir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import src.nightbatch.fx_update as fx_updater
from src.nightbatch.eodhd_price_importer import process_all_eodhd_assets
from src.nightbatch.ishares_importer import process_all_ishares_assets
import src.database as database


def run_full_nightbatch(dry_run: bool = False):
    database.initialize_runtime_from_env(strict=False)
    env = os.environ.get("APP_ENV", "main")
    print(f"Starting full nightbatch run on environment {env} (dry_run={dry_run})...")

    print("Step 1: FX rates update")
    fx_summary = fx_updater.headless_load_missing_fx_rates(dry_run=dry_run)
    print(f"FX update summary: {fx_summary}")

    print("Step 2: EODHD asset price update")
    eodhd_summary = process_all_eodhd_assets(dry_run=dry_run)
    print(f"EODHD import summary: {eodhd_summary}")

    print("Step 3: iShares asset price update")
    ishares_summary = process_all_ishares_assets(dry_run=dry_run)
    print(f"iShares import summary: {ishares_summary}")

    return {"fx": fx_summary, "eodhd": eodhd_summary, "ishares": ishares_summary, "dry_run": dry_run}


if __name__ == "__main__":
    run_full_nightbatch(dry_run=False)
