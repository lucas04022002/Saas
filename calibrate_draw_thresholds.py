"""
Calibration automatique des seuils de sélection du nul (draw) par ligue.

Source: fichiers backtest_*.json contenant la clé "results" avec probabilités 1X2.
Sortie: draw_thresholds_by_league.json
"""

from __future__ import annotations

import glob
import json
from datetime import datetime
from pathlib import Path

from draw_policy import DRAW_THRESHOLDS_FILE, DEFAULT_THRESHOLDS, build_default_thresholds_config


LEAGUE_NAME_TO_ID = {
    "Premier League (Ang)": 39,
    "Ligue 1 (Fra)": 61,
    "La Liga (Esp)": 140,
    "Bundesliga (All)": 78,
    "Serie A (Ita)": 135,
    "Ligue des Champions": 2,
    "Europa League": 3,
    "Conference League": 848,
}

GRID_DRAW_PROB_MIN = [22.0, 24.0, 25.0, 26.0, 28.0, 30.0]
GRID_DRAW_BALANCE_MAX = [6.0, 8.0, 10.0, 12.0, 15.0]
GRID_DRAW_MARGIN_TO_BEST = [2.0, 3.0, 4.0, 5.0, 6.0]


def _predict_outcome(prob_model: dict[str, float], cfg: dict[str, float]) -> str:
    home = float(prob_model.get("home", 0.0))
    draw = float(prob_model.get("draw", 0.0))
    away = float(prob_model.get("away", 0.0))

    home_pct = home * 100.0
    draw_pct = draw * 100.0
    away_pct = away * 100.0

    best_non_draw = max(home_pct, away_pct)
    if (
        draw_pct >= cfg["draw_prob_min"]
        and abs(home_pct - away_pct) <= cfg["draw_balance_max"]
        and draw_pct >= best_non_draw - cfg["draw_margin_to_best"]
    ):
        return "draw"

    return "home" if home >= away else "away"


def _evaluate(results: list[dict], cfg: dict[str, float]) -> dict[str, float]:
    total = len(results)
    if total == 0:
        return {"accuracy": 0.0, "draw_accuracy": 0.0, "pred_draw": 0, "draw_total": 0, "correct": 0}

    correct = 0
    draw_total = 0
    draw_correct = 0
    pred_draw = 0

    for r in results:
        actual = r.get("actual_result")
        probs = r.get("probabilities") or {}
        pred = _predict_outcome(probs, cfg)
        if pred == actual:
            correct += 1
        if pred == "draw":
            pred_draw += 1
        if actual == "draw":
            draw_total += 1
            if pred == "draw":
                draw_correct += 1

    accuracy = correct / total * 100.0
    draw_accuracy = (draw_correct / draw_total * 100.0) if draw_total else 0.0
    return {
        "accuracy": accuracy,
        "draw_accuracy": draw_accuracy,
        "pred_draw": pred_draw,
        "draw_total": draw_total,
        "correct": correct,
    }


def _best_config_for_league(results: list[dict]) -> tuple[dict[str, float], dict[str, float], dict[str, float]]:
    baseline = _evaluate(
        results,
        {
            "draw_prob_min": float(DEFAULT_THRESHOLDS["draw_prob_min"]),
            "draw_balance_max": float(DEFAULT_THRESHOLDS["draw_balance_max"]),
            "draw_margin_to_best": float(DEFAULT_THRESHOLDS["draw_margin_to_best"]),
        },
    )

    best_cfg = None
    best_metrics = None
    best_score = None

    target_draw_count = max(1, int(baseline["draw_total"] * 0.10)) if baseline["draw_total"] else 0

    for draw_prob_min in GRID_DRAW_PROB_MIN:
        for draw_balance_max in GRID_DRAW_BALANCE_MAX:
            for draw_margin_to_best in GRID_DRAW_MARGIN_TO_BEST:
                cfg = {
                    "draw_prob_min": draw_prob_min,
                    "draw_balance_max": draw_balance_max,
                    "draw_margin_to_best": draw_margin_to_best,
                }
                metrics = _evaluate(results, cfg)

                # Objectif: accuracy d'abord, puis qualité sur les nuls.
                score = (
                    round(metrics["accuracy"], 6),
                    round(metrics["draw_accuracy"], 6),
                    -abs(metrics["pred_draw"] - target_draw_count),
                    metrics["pred_draw"],
                )

                if best_score is None or score > best_score:
                    best_score = score
                    best_cfg = cfg
                    best_metrics = metrics

    return baseline, best_cfg or dict(DEFAULT_THRESHOLDS), best_metrics or baseline


def calibrate_draw_thresholds(output_path: str = DRAW_THRESHOLDS_FILE) -> dict:
    files = sorted(
        f for f in glob.glob("backtest_*_*.json")
        if "summary" not in Path(f).name
    )

    config = build_default_thresholds_config()
    config["source_files"] = files
    config["metrics"] = {}

    # Pour éviter d'écraser une ligue avec un petit échantillon,
    # on ne garde que le fichier le plus riche en "results" par ligue.
    best_file_by_league = {}
    for path in files:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        league_name = data.get("league", Path(path).stem)
        results = data.get("results", [])
        current = best_file_by_league.get(league_name)
        if current is None or len(results) > len(current["results"]):
            best_file_by_league[league_name] = {"path": path, "results": results}

    config["selected_files"] = {k: v["path"] for k, v in best_file_by_league.items()}

    for league_name, payload in best_file_by_league.items():
        results = payload["results"]
        if not results:
            continue

        baseline, best_cfg, best_metrics = _best_config_for_league(results)
        league_id = LEAGUE_NAME_TO_ID.get(league_name)

        config["leagues"][league_name] = best_cfg
        if league_id is not None:
            config["leagues"][str(league_id)] = best_cfg

        config["metrics"][league_name] = {
            "baseline_accuracy": round(baseline["accuracy"], 2),
            "baseline_draw_accuracy": round(baseline["draw_accuracy"], 2),
            "optimized_accuracy": round(best_metrics["accuracy"], 2),
            "optimized_draw_accuracy": round(best_metrics["draw_accuracy"], 2),
            "optimized_pred_draw": int(best_metrics["pred_draw"]),
            "draw_total": int(best_metrics["draw_total"]),
            "matches": len(results),
        }

    config["generated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    return config


if __name__ == "__main__":
    cfg = calibrate_draw_thresholds()
    print(f"[OK] Calibration terminée: {DRAW_THRESHOLDS_FILE}")
    for league, metrics in cfg.get("metrics", {}).items():
        print(
            f"- {league}: {metrics['baseline_accuracy']:.2f}% -> "
            f"{metrics['optimized_accuracy']:.2f}% | "
            f"draw {metrics['baseline_draw_accuracy']:.2f}% -> "
            f"{metrics['optimized_draw_accuracy']:.2f}%"
        )
