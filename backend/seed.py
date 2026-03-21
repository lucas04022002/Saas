from datetime import datetime, timedelta, timezone

from app.core.database import Base, SessionLocal, engine
from app.core.runtime_migrations import ensure_runtime_columns
from app.core.security import hash_password
from app.models.analysis import Analysis
from app.models.enums import MatchStatus, RiskLevel, SubscriptionPlan, SubscriptionStatus, TeamType, UserRole
from app.models.favorite import Favorite
from app.models.match import Match
from app.models.subscription import Subscription
from app.models.team_stats import TeamStats
from app.models.user import User
from app.models.warning_point import WarningPoint


def run_seed() -> None:
    ensure_runtime_columns(engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Reset quick dev seed
    db.query(Favorite).delete()
    db.query(WarningPoint).delete()
    db.query(TeamStats).delete()
    db.query(Analysis).delete()
    db.query(Subscription).delete()
    db.query(Match).delete()
    db.query(User).delete()
    db.commit()

    demo_user = User(
        first_name="Lucas",
        email="demo@rushplay.app",
        password_hash=hash_password("demo12345"),
        role=UserRole.USER,
        subscription_plan=SubscriptionPlan.PRO,
    )
    db.add(demo_user)
    db.flush()

    db.add(
        Subscription(
            user_id=demo_user.id,
            plan=SubscriptionPlan.PRO,
            status=SubscriptionStatus.ACTIVE,
            current_period_end=datetime.now(timezone.utc) + timedelta(days=30),
        )
    )

    fixtures = [
        ("Paris Saint Germain", "Olympique Marseille", "Ligue 1", "France"),
        ("Real Madrid", "Sevilla", "La Liga", "Spain"),
        ("Inter", "Atalanta", "Serie A", "Italy"),
        ("Liverpool", "Brighton", "Premier League", "England"),
        ("Bayern Munchen", "Bayer Leverkusen", "Bundesliga", "Germany"),
        ("AC Milan", "Napoli", "Serie A", "Italy"),
    ]

    created_matches = []
    now = datetime.now(timezone.utc)
    for idx, (home, away, league, country) in enumerate(fixtures):
        match = Match(
            home_team=home,
            away_team=away,
            league=league,
            country=country,
            kickoff_at=now + timedelta(days=idx + 1),
            status=MatchStatus.SCHEDULED,
            external_id=f"seed_{idx + 1}",
            last_analyzed_at=now,
        )
        db.add(match)
        db.flush()

        confidence = 54 + idx * 3
        analysis = Analysis(
            match_id=match.id,
            confidence_score=confidence,
            recommended_bet="Victoire domicile" if idx % 2 == 0 else "Match nul",
            bookmaker_odds=1.85 + (idx * 0.08),
            value_percent=4.2 + idx,
            risk_level=RiskLevel.LOW if confidence >= 62 else RiskLevel.MEDIUM,
            ai_explanation=f"Signal stable sur {home} vs {away} avec forme recente favorable.",
        )
        db.add(analysis)
        db.flush()

        db.add_all(
            [
                WarningPoint(analysis_id=analysis.id, label="Possibles rotations pre-coupe europeenne"),
                WarningPoint(analysis_id=analysis.id, label="Volatilite recente des cotes"),
            ]
        )

        db.add_all(
            [
                TeamStats(
                    match_id=match.id,
                    team_type=TeamType.HOME,
                    recent_form="WWDWL",
                    goals_scored=11,
                    goals_conceded=5,
                    xg=1.82,
                    xga=1.04,
                    possession_avg=58.0,
                    shots_on_target_avg=6.4,
                    clean_sheets=2,
                ),
                TeamStats(
                    match_id=match.id,
                    team_type=TeamType.AWAY,
                    recent_form="LDWDW",
                    goals_scored=8,
                    goals_conceded=7,
                    xg=1.35,
                    xga=1.29,
                    possession_avg=50.5,
                    shots_on_target_avg=4.2,
                    clean_sheets=1,
                ),
            ]
        )

        created_matches.append(match)

    db.add(Favorite(user_id=demo_user.id, match_id=created_matches[0].id))
    db.add(Favorite(user_id=demo_user.id, match_id=created_matches[3].id))

    db.commit()
    db.close()


if __name__ == "__main__":
    run_seed()
    print("Seed completed")
