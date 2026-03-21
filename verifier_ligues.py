"""
Script de vérification : Vérifie que toutes les ligues sont bien configurées
"""

print("=" * 60)
print("VERIFICATION DES LIGUES CONFIGUREES")
print("=" * 60)

# Ligues dans Algo plus APi.py
LIGUES_ALGO = [
    {"nom": "Premier League (Ang)", "id_foot": 39, "key_odds": "soccer_epl"},
    {"nom": "Ligue 1 (Fra)", "id_foot": 61, "key_odds": "soccer_france_ligue_one"},
    {"nom": "La Liga (Esp)", "id_foot": 140, "key_odds": "soccer_spain_la_liga"},
    {"nom": "Bundesliga (All)", "id_foot": 78, "key_odds": "soccer_germany_bundesliga"},
    {"nom": "Serie A (Ita)", "id_foot": 135, "key_odds": "soccer_italy_serie_a"},
    {"nom": "Ligue des Champions", "id_foot": 2, "key_odds": "soccer_uefa_champs_league"}
]

# Ligues dans train_xgboost.py
LIGUES_TRAIN = [
    {"nom": "Premier League (Ang)", "id_foot": 39},
    {"nom": "Ligue 1 (Fra)", "id_foot": 61},
    {"nom": "La Liga (Esp)", "id_foot": 140},
    {"nom": "Bundesliga (All)", "id_foot": 78},
    {"nom": "Serie A (Ita)", "id_foot": 135},
    {"nom": "Ligue des Champions", "id_foot": 2},
]

SAISONS_CHAMPIONS = [2022, 2023, 2024, 2025]
SAISONS_UCL = [2022, 2023, 2024, 2025]

print("\n1. LIGUES DANS Algo plus APi.py:")
print("-" * 60)
for i, ligue in enumerate(LIGUES_ALGO, 1):
    print(f"   {i}. {ligue['nom']}")
    print(f"      ID: {ligue['id_foot']} | Key Odds: {ligue['key_odds']}")

print(f"\n   Total: {len(LIGUES_ALGO)} ligues")

print("\n2. LIGUES DANS train_xgboost.py:")
print("-" * 60)
for i, ligue in enumerate(LIGUES_TRAIN, 1):
    print(f"   {i}. {ligue['nom']}")
    print(f"      ID: {ligue['id_foot']}")

print(f"\n   Total: {len(LIGUES_TRAIN)} ligues")

print("\n3. VERIFICATION DE LA CORRESPONDANCE:")
print("-" * 60)
if len(LIGUES_ALGO) == len(LIGUES_TRAIN):
    print("   [OK] Même nombre de ligues")
else:
    print(f"   [ERREUR] Nombre différent: {len(LIGUES_ALGO)} vs {len(LIGUES_TRAIN)}")

# Vérifier que toutes les ligues sont présentes
ids_algo = {l['id_foot'] for l in LIGUES_ALGO}
ids_train = {l['id_foot'] for l in LIGUES_TRAIN}

if ids_algo == ids_train:
    print("   [OK] Toutes les ligues correspondent (mêmes IDs)")
else:
    missing_in_train = ids_algo - ids_train
    missing_in_algo = ids_train - ids_algo
    if missing_in_train:
        print(f"   [ERREUR] Ligues manquantes dans train_xgboost.py: {missing_in_train}")
    if missing_in_algo:
        print(f"   [ERREUR] Ligues manquantes dans Algo plus APi.py: {missing_in_algo}")

print("\n4. SAISONS CONFIGUREES:")
print("-" * 60)
print(f"   Championnats nationaux: {SAISONS_CHAMPIONS}")
print(f"   Ligue des Champions: {SAISONS_UCL}")
print(f"   Total saisons par ligue: {len(SAISONS_CHAMPIONS)} saisons")

print("\n5. CALCUL DU NOMBRE TOTAL DE REQUETES:")
print("-" * 60)
total_requetes = 0
for ligue in LIGUES_TRAIN:
    if ligue['id_foot'] == 2:
        saisons = SAISONS_UCL
    else:
        saisons = SAISONS_CHAMPIONS
    requetes_ligue = len(saisons)
    total_requetes += requetes_ligue
    print(f"   {ligue['nom']}: {requetes_ligue} requetes ({len(saisons)} saisons)")

print(f"\n   TOTAL: {total_requetes} requetes API nécessaires")
print(f"   (Plan gratuit: 100 req/jour - peut nécessiter plusieurs jours)")

print("\n6. ESTIMATION DU NOMBRE DE MATCHS:")
print("-" * 60)
# Estimation: ~380 matchs par saison pour les championnats, ~200 pour UCL
for ligue in LIGUES_TRAIN:
    if ligue['id_foot'] == 2:
        matchs_par_saison = 200
        saisons = SAISONS_UCL
    else:
        matchs_par_saison = 380
        saisons = SAISONS_CHAMPIONS
    total_matchs_ligue = matchs_par_saison * len(saisons)
    print(f"   {ligue['nom']}: ~{total_matchs_ligue} matchs ({matchs_par_saison} x {len(saisons)})")

total_estime = sum(
    (200 if l['id_foot'] == 2 else 380) * len(SAISONS_UCL if l['id_foot'] == 2 else SAISONS_CHAMPIONS)
    for l in LIGUES_TRAIN
)
print(f"\n   TOTAL ESTIME: ~{total_estime} matchs à collecter")

print("\n" + "=" * 60)
print("VERIFICATION TERMINEE")
print("=" * 60)

print("\n[RESUME]")
print(f"- {len(LIGUES_TRAIN)} ligues configurees")
print(f"- {len(SAISONS_CHAMPIONS)} saisons par ligue")
print(f"- {total_requetes} requetes API necessaires")
print(f"- ~{total_estime} matchs estimes a collecter")
print("\nTout est pret pour l'entrainement !")
