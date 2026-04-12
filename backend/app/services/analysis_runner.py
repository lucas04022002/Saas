import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.analysis import Analysis
from app.models.enums import RiskLevel
from app.models.match import Match
from app.models.warning_point import WarningPoint
from app.services.prediction_service import prediction_service

log = logging.getLogger("rushplay.analysis")


def build_warning_points(prediction: dict) -> list[str]:
    warnings: list[str] = []

    confidence = float(prediction.get("confidence_score", 0))
    value_percent = float(prediction.get("value_percent", 0))
    risk_level = str(prediction.get("risk_level", "HIGH"))
    probs = prediction.get("probabilities", {}) or {}
    home_prob = float(probs.get("home", 0.33))
    away_prob = float(probs.get("away", 0.33))
    draw_prob = float(probs.get("draw", 0.33))
    xg_total = float(prediction.get("expected_home_goals", 0)) + float(prediction.get("expected_away_goals", 0))

    if risk_level == RiskLevel.HIGH.value:
        warnings.append("Risque eleve: le modele classe ce signal en HIGH.")
    if confidence < 50:
        warnings.append("Confiance limitee: probabilite max inferieure a 50%.")
    if value_percent < 0:
        warnings.append("Value negative versus cote de reference.")
    if abs(home_prob - away_prob) < 0.08:
        warnings.append("Match equilibre: ecart faible entre home et away.")
    if draw_prob >= 0.30:
        warnings.append("Probabilite de nul elevee, resultat potentiellement volatil.")
    if xg_total < 2.0:
        warnings.append("Projection xG basse: match potentiellement ferme.")

    if not warnings:
        warnings.append("Aucun signal critique detecte par les regles de risque.")

    return warnings


def upsert_analysis_for_match(
    db: Session,
    match: Match,
    odds_by_outcome: dict[str, float] | None = None,
) -> tuple[Analysis, list[str], bool]:
    prediction = prediction_service.get_prediction(
        match.home_team, match.away_team, match.league, odds_by_outcome=odds_by_outcome
    )

    try:
        risk_level = RiskLevel(prediction["risk_level"])
    except ValueError:
        risk_level = RiskLevel.HIGH

    analysis = db.scalar(select(Analysis).where(Analysis.match_id == match.id))
    created = analysis is None

    if analysis is None:
        analysis = Analysis(match_id=match.id)

    analysis.confidence_score = prediction["confidence_score"]
    analysis.recommended_bet = prediction["recommended_bet"]
    analysis.bookmaker_odds = prediction["bookmaker_odds"]
    analysis.value_percent = prediction["value_percent"]
    analysis.risk_level = risk_level
    analysis.ai_explanation = prediction["ai_explanation"]

    match.last_analyzed_at = datetime.now(timezone.utc)

    db.add(analysis)
    db.add(match)
    db.flush()

    db.query(WarningPoint).filter(WarningPoint.analysis_id == analysis.id).delete(synchronize_session=False)
    warning_labels = build_warning_points(prediction)
    db.add_all([WarningPoint(analysis_id=analysis.id, label=label) for label in warning_labels])

    return analysis, warning_labels, created


BATCH_SIZE = 50


def run_bulk_analyses(
    db: Session,
    matches: list[Match],
    odds_map: dict[str, dict[str, float]] | None = None,
) -> dict:
    created_count = 0
    updated_count = 0
    errors: list[dict[str, str]] = []
    pending_batch: list[tuple[Match, bool]] = []

    for match in matches:
        added_current = False
        match_odds = (odds_map or {}).get(match.external_id or "") if odds_map else None
        try:
            _, _, created = upsert_analysis_for_match(db, match, odds_by_outcome=match_odds)
            pending_batch.append((match, created))
            added_current = True

            if len(pending_batch) >= BATCH_SIZE:
                db.commit()
                created_count += sum(1 for _, was_created in pending_batch if was_created)
                updated_count += sum(1 for _, was_created in pending_batch if not was_created)
                pending_batch.clear()
        except Exception as exc:
            db.rollback()
            log.error("Analysis failed for %s vs %s: %s", match.home_team, match.away_team, exc)
            if pending_batch:
                for pending_match, _ in pending_batch:
                    errors.append(
                        {
                            "match_id": str(pending_match.id),
                            "match": f"{pending_match.home_team} vs {pending_match.away_team}",
                            "error": f"Rolled back batch: {exc}",
                        }
                    )
                pending_batch.clear()

            if not added_current:
                errors.append(
                    {
                        "match_id": str(match.id),
                        "match": f"{match.home_team} vs {match.away_team}",
                        "error": str(exc),
                    }
                )

    if pending_batch:
        try:
            db.commit()
            created_count += sum(1 for _, was_created in pending_batch if was_created)
            updated_count += sum(1 for _, was_created in pending_batch if not was_created)
            pending_batch.clear()
        except Exception as exc:
            db.rollback()
            log.error("Final batch commit failed: %s", exc)
            for pending_match, _ in pending_batch:
                errors.append(
                    {
                        "match_id": str(pending_match.id),
                        "match": f"{pending_match.home_team} vs {pending_match.away_team}",
                        "error": f"Rolled back final batch: {exc}",
                    }
                )
            pending_batch.clear()

    return {
        "processed": len(matches),
        "created": created_count,
        "updated": updated_count,
        "failed": len(errors),
        "errors": errors,
    }
