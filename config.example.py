"""
Fichier de configuration EXEMPLE pour les clés API
Copiez ce fichier en config.py et ajoutez vos vraies clés API
"""

# ==========================================
# CLÉS API - À REMPLACER PAR VOS CLÉS
# ==========================================

# Clé API-Football (https://www.api-football.com/)
# Obtenez votre clé sur : https://dashboard.api-football.com/
KEY_API_FOOTBALL = "TA_CLE_API_FOOTBALL_ICI"

# Clé The-Odds-API (https://the-odds-api.com/)
# Obtenez votre clé sur : https://the-odds-api.com/liveapi/guides/getting-started/
KEY_THE_ODDS = "TA_CLE_THE_ODDS_ICI"

# ==========================================
# CONFIGURATION GÉNÉRALE
# ==========================================

# Saison à analyser
SAISON = 2025

# Seuil pour identifier un favori (cote <= à ce seuil)
COTE_FAVORI_MAX = 2.0  # Cote de 2.0 = probabilité implicite de 50%
# Ne marquer "favori" que si le modèle donne au moins cette proba (%)
PROBA_FAVORI_MIN = 55

# Jour à scanner : 0 = aujourd'hui, 1 = demain
JOUR_A_SCANNER = 0
