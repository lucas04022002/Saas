"""
Système de tracking des prédictions : log chaque prédiction + résultat réel.
Fichier de sortie : predictions_log.json
"""
import json
import os
from datetime import datetime, timedelta

PREDICTIONS_FILE = "predictions_log.json"


def _load_log():
    if not os.path.exists(PREDICTIONS_FILE):
        return []
    try:
        with open(PREDICTIONS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []


def _save_log(log):
    with open(PREDICTIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(log, f, indent=2, ensure_ascii=False)


def log_prediction(date, league, home_team, away_team,
                   predicted_outcome, prob_home, prob_draw, prob_away,
                   odds_home=None, odds_draw=None, odds_away=None,
                   is_value_bet=False, kelly_pct=0.0, fixture_id=None):
    """
    Enregistre une prédiction dans predictions_log.json.

    predicted_outcome : 'home' | 'draw' | 'away'
    prob_* : float entre 0 et 1
    odds_* : cote décimale bookmakers (ou None si inconnue)
    """
    log = _load_log()
    entry_id = f"{date}_{home_team}_{away_team}"

    entry = {
        'id': entry_id,
        'fixture_id': fixture_id,
        'date': date,
        'league': league,
        'home_team': home_team,
        'away_team': away_team,
        'predicted_outcome': predicted_outcome,
        'probabilities': {
            'home': round(float(prob_home), 4),
            'draw': round(float(prob_draw), 4),
            'away': round(float(prob_away), 4),
        },
        'odds': {
            'home': round(float(odds_home), 2) if odds_home else None,
            'draw': round(float(odds_draw), 2) if odds_draw else None,
            'away': round(float(odds_away), 2) if odds_away else None,
        },
        'is_value_bet': is_value_bet,
        'kelly_pct': kelly_pct,
        'actual_result': None,   # rempli par update_result()
        'is_correct': None,
        'logged_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'updated_at': None,
    }

    # Évite les doublons (écrase l'entrée si même clé)
    log = [e for e in log if e.get('id') != entry_id]
    log.append(entry)
    _save_log(log)


def update_result(date, home_team, away_team, actual_result):
    """
    Met à jour le résultat réel d'une prédiction.
    actual_result : 'home' | 'draw' | 'away'
    Retourne True si une entrée a été mise à jour.
    """
    log = _load_log()
    entry_id = f"{date}_{home_team}_{away_team}"
    updated = False
    for entry in log:
        if entry.get('id') == entry_id:
            entry['actual_result'] = actual_result
            entry['is_correct'] = (entry.get('predicted_outcome') == actual_result)
            entry['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            updated = True
            break
    if updated:
        _save_log(log)
    return updated


def get_stats(only_value_bets=False):
    """
    Retourne les statistiques de tracking.

    Calcule :
    - Précision globale
    - ROI (mise fixe 1 unité par prédiction sur l'outcome prédit)
    - Stats séparées pour value bets
    """
    log = _load_log()
    if only_value_bets:
        log = [e for e in log if e.get('is_value_bet')]

    resolved = [e for e in log if e.get('actual_result') is not None]
    pending  = [e for e in log if e.get('actual_result') is None]

    if not resolved:
        return {
            'total_logged': len(log),
            'total_pending': len(pending),
            'total_resolved': 0,
            'message': 'Aucune prédiction résolue pour le moment.'
        }

    correct = sum(1 for e in resolved if e.get('is_correct'))
    accuracy = correct / len(resolved) * 100

    # ROI flat bet (1 unité par pari, sur l'outcome prédit)
    total_stake = len(resolved)
    total_return = 0.0
    bets_with_odds = 0
    for e in resolved:
        outcome = e.get('predicted_outcome')
        odd = (e.get('odds') or {}).get(outcome)
        if odd and odd > 1.0:
            bets_with_odds += 1
            total_return += odd if e.get('is_correct') else 0.0
        else:
            # Pas de cote loggée → on compte 1.0 si gagné (remboursé)
            total_return += 1.0 if e.get('is_correct') else 0.0
    roi = (total_return - total_stake) / total_stake * 100

    # Value bets uniquement
    vb = [e for e in resolved if e.get('is_value_bet')]
    vb_correct = sum(1 for e in vb if e.get('is_correct'))
    vb_stake = len(vb)
    vb_return = 0.0
    for e in vb:
        outcome = e.get('predicted_outcome')
        odd = (e.get('odds') or {}).get(outcome)
        if odd and odd > 1.0:
            vb_return += odd if e.get('is_correct') else 0.0
        else:
            vb_return += 1.0 if e.get('is_correct') else 0.0
    vb_roi = (vb_return - vb_stake) / vb_stake * 100 if vb_stake > 0 else 0.0
    vb_accuracy = vb_correct / vb_stake * 100 if vb_stake > 0 else 0.0

    return {
        'total_logged': len(log),
        'total_pending': len(pending),
        'total_resolved': len(resolved),
        'correct': correct,
        'accuracy_pct': round(accuracy, 1),
        'roi_pct': round(roi, 1),
        'bets_with_odds': bets_with_odds,
        'value_bets': {
            'total': vb_stake,
            'correct': vb_correct,
            'accuracy_pct': round(vb_accuracy, 1),
            'roi_pct': round(vb_roi, 1),
        },
    }


def print_stats():
    """Affiche un résumé formaté des stats de tracking."""
    stats = get_stats()
    if not stats:
        print("   [TRACKER] Aucune donnée.")
        return

    print("\n" + "=" * 50)
    print("  TRACKING DES PRÉDICTIONS")
    print("=" * 50)
    print(f"   Prédictions loggées  : {stats['total_logged']}")
    print(f"   En attente de résultat : {stats.get('total_pending', '?')}")
    print(f"   Résolues             : {stats['total_resolved']}")

    if stats['total_resolved'] == 0:
        print(f"\n   {stats.get('message', 'Aucun résultat disponible.')}")
        return

    print(f"\n   Précision globale    : {stats['accuracy_pct']}%  ({stats['correct']}/{stats['total_resolved']})")
    print(f"   ROI flat bet         : {stats['roi_pct']}%")

    vb = stats.get('value_bets', {})
    if vb.get('total', 0) > 0:
        print(f"\n   Value Bets uniquement:")
        print(f"     Total             : {vb['total']}")
        print(f"     Précision         : {vb['accuracy_pct']}%  ({vb['correct']}/{vb['total']})")
        print(f"     ROI flat bet      : {vb['roi_pct']}%")
    print("=" * 50)


def _parse_entry_date(entry):
    """Date de référence pour les fenêtres rolling."""
    raw = entry.get("date")
    if isinstance(raw, str) and len(raw) >= 10:
        try:
            return datetime.strptime(raw[:10], "%Y-%m-%d")
        except ValueError:
            pass

    updated = entry.get("updated_at")
    if isinstance(updated, str) and len(updated) >= 10:
        try:
            return datetime.strptime(updated[:10], "%Y-%m-%d")
        except ValueError:
            return None
    return None


def _compute_accuracy(entries):
    if not entries:
        return 0.0, 0, 0
    correct = sum(1 for e in entries if e.get("is_correct"))
    total = len(entries)
    return correct / total * 100.0, correct, total


def _compute_roi(entries):
    if not entries:
        return 0.0
    total_stake = len(entries)
    total_return = 0.0
    for e in entries:
        outcome = e.get("predicted_outcome")
        odd = (e.get("odds") or {}).get(outcome)
        if odd and odd > 1.0:
            total_return += odd if e.get("is_correct") else 0.0
        else:
            total_return += 1.0 if e.get("is_correct") else 0.0
    return (total_return - total_stake) / total_stake * 100.0


def get_drift_report(window_days=30, min_samples=20):
    """
    Rapport de drift/performance rolling par ligue.

    - baseline: historique résolu complet
    - recent: entrées résolues sur les `window_days` derniers jours
    """
    log = _load_log()
    resolved = [e for e in log if e.get("actual_result") is not None and e.get("is_correct") is not None]
    if not resolved:
        return {
            "window_days": window_days,
            "min_samples": min_samples,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "message": "Aucune prédiction résolue.",
            "global": {},
            "leagues": [],
        }

    now = datetime.now()
    cutoff = now - timedelta(days=window_days)

    recent_global = [e for e in resolved if (_parse_entry_date(e) or now) >= cutoff]
    baseline_acc, baseline_correct, baseline_total = _compute_accuracy(resolved)
    recent_acc, recent_correct, recent_total = _compute_accuracy(recent_global)

    by_league = {}
    for entry in resolved:
        league = entry.get("league") or "Unknown"
        by_league.setdefault(league, []).append(entry)

    league_rows = []
    for league, entries in by_league.items():
        recent_entries = [e for e in entries if (_parse_entry_date(e) or now) >= cutoff]
        base_acc, base_correct, base_total = _compute_accuracy(entries)
        rec_acc, rec_correct, rec_total = _compute_accuracy(recent_entries)
        base_roi = _compute_roi(entries)
        rec_roi = _compute_roi(recent_entries)
        drift_pts = rec_acc - base_acc

        pred_draw_rate = 0.0
        if rec_total > 0:
            pred_draw_rate = sum(1 for e in recent_entries if e.get("predicted_outcome") == "draw") / rec_total * 100.0

        if rec_total < min_samples:
            status = "insufficient_data"
        elif drift_pts <= -8.0:
            status = "alert"
        elif drift_pts <= -4.0:
            status = "watch"
        else:
            status = "ok"

        league_rows.append(
            {
                "league": league,
                "status": status,
                "baseline": {
                    "matches": base_total,
                    "correct": base_correct,
                    "accuracy_pct": round(base_acc, 2),
                    "roi_pct": round(base_roi, 2),
                },
                "recent": {
                    "matches": rec_total,
                    "correct": rec_correct,
                    "accuracy_pct": round(rec_acc, 2),
                    "roi_pct": round(rec_roi, 2),
                    "pred_draw_rate_pct": round(pred_draw_rate, 2),
                },
                "drift_accuracy_pts": round(drift_pts, 2),
            }
        )

    league_rows.sort(key=lambda r: (r["status"], r["drift_accuracy_pts"], -r["recent"]["matches"]))

    return {
        "window_days": window_days,
        "min_samples": min_samples,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "global": {
            "baseline": {
                "matches": baseline_total,
                "correct": baseline_correct,
                "accuracy_pct": round(baseline_acc, 2),
                "roi_pct": round(_compute_roi(resolved), 2),
            },
            "recent": {
                "matches": recent_total,
                "correct": recent_correct,
                "accuracy_pct": round(recent_acc, 2),
                "roi_pct": round(_compute_roi(recent_global), 2),
            },
            "drift_accuracy_pts": round(recent_acc - baseline_acc, 2),
        },
        "leagues": league_rows,
    }


def print_drift_report(window_days=30, min_samples=20):
    report = get_drift_report(window_days=window_days, min_samples=min_samples)
    print("\n" + "=" * 60)
    print("  DRIFT / PERFORMANCE ROLLING")
    print("=" * 60)
    if report.get("message"):
        print(f"   {report['message']}")
        return

    g = report["global"]
    print(f"Fenêtre: {window_days} jours | Min samples/ligue: {min_samples}")
    print(
        f"Global accuracy: {g['baseline']['accuracy_pct']}% -> {g['recent']['accuracy_pct']}% "
        f"(drift {g['drift_accuracy_pts']:+.2f} pts)"
    )
    print(
        f"Global ROI: {g['baseline']['roi_pct']}% -> {g['recent']['roi_pct']}%"
    )
    print("\nPar ligue:")
    for row in report["leagues"]:
        print(
            f" - {row['league']} [{row['status']}]: "
            f"{row['baseline']['accuracy_pct']}% -> {row['recent']['accuracy_pct']}% "
            f"(drift {row['drift_accuracy_pts']:+.2f} pts, "
            f"n_recent={row['recent']['matches']}, draw_pred={row['recent']['pred_draw_rate_pct']}%)"
        )
    print("=" * 60)
