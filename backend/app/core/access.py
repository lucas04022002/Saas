"""Règles d'accès par plan d'abonnement.

Source de vérité côté serveur pour le paywall. Le frontend applique le même
comportement pour l'affichage, mais la donnée premium n'est jamais renvoyée à
un utilisateur non autorisé, quel que soit le client utilisé.
"""
from app.models.enums import SubscriptionPlan
from app.models.user import User

# Nombre de signaux détaillés offerts aux comptes STARTER (et visiteurs anonymes).
FREE_SLOTS = 2

PAID_PLANS = {SubscriptionPlan.PRO, SubscriptionPlan.ELITE}

# Champs "premium" masqués dans la liste des matchs pour les non-abonnés.
# On garde `confidence_score` et `risk_level` comme teaser (le compteur et les
# cartes verrouillées de l'UI en ont besoin) : sans le pari conseillé ni la cote,
# ils ne sont pas exploitables. On masque uniquement le pronostic monétisable.
PREMIUM_MATCH_FIELDS = (
    "recommended_bet",
    "bookmaker_odds",
    "value_percent",
)


def is_pro(user: User | None) -> bool:
    return user is not None and user.subscription_plan in PAID_PLANS


def gate_match_items(items: list[dict], user: User | None) -> list[dict]:
    """Marque `locked` et masque les champs premium selon le plan.

    Les abonnés voient tout. Les non-abonnés gardent l'accès complet aux
    `FREE_SLOTS` matchs à plus haute confiance (le "teaser"), le reste est
    verrouillé et ses champs premium sont mis à None.
    """
    if is_pro(user):
        for item in items:
            item["locked"] = False
        return items

    ranked = sorted(
        range(len(items)),
        key=lambda i: (
            items[i].get("confidence_score") is not None,
            items[i].get("confidence_score") or 0,
        ),
        reverse=True,
    )
    free = set(ranked[:FREE_SLOTS])
    for i, item in enumerate(items):
        locked = i not in free
        item["locked"] = locked
        if locked:
            for field in PREMIUM_MATCH_FIELDS:
                item[field] = None
    return items
