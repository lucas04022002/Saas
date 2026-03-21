"""
Génère un rapport drift/performance rolling à partir de predictions_log.json.
"""

from __future__ import annotations

import json
from datetime import datetime

from prediction_tracker import get_drift_report, print_drift_report


OUTPUT_FILE = "drift_report.json"


def generate_and_save(window_days=30, min_samples=20, output_file=OUTPUT_FILE):
    report = get_drift_report(window_days=window_days, min_samples=min_samples)
    report["generated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    return report


if __name__ == "__main__":
    rep = generate_and_save(window_days=30, min_samples=20)
    print_drift_report(window_days=30, min_samples=20)
    print(f"[OK] Rapport sauvegardé: {OUTPUT_FILE}")

