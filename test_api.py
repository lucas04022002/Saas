"""
Script de test pour vérifier la clé API
"""

import requests
import os
# Désactiver le proxy si nécessaire
os.environ['NO_PROXY'] = '*'
os.environ['no_proxy'] = '*'

from config import KEY_API_FOOTBALL

print("Test de la clé API...")
print(f"Clé utilisée: {KEY_API_FOOTBALL[:10]}...")

# Test simple : récupérer les matchs d'aujourd'hui
url = "https://v3.football.api-sports.io/fixtures"
headers = {
    'x-rapidapi-host': "v3.football.api-sports.io",
    'x-rapidapi-key': KEY_API_FOOTBALL
}
params = {
    "date": "2025-01-26",  # Date d'aujourd'hui
    "league": 39,  # Premier League
    "season": 2025  # Saison requise
}

try:
    # Désactiver le proxy pour cette requête
    session = requests.Session()
    session.trust_env = False
    r = session.get(url, headers=headers, params=params, timeout=10)
    print(f"\nCode de statut: {r.status_code}")
    
    if r.status_code == 200:
        data = r.json()
        if data.get('errors'):
            print(f"Erreurs API: {data.get('errors')}")
        else:
            fixtures = data.get('response', [])
            print(f"[OK] API fonctionne ! {len(fixtures)} matchs trouves")
    elif r.status_code == 403:
        print("[ERREUR] 403: Acces refuse")
        print("\nCauses possibles:")
        print("1. Clé API invalide ou expirée")
        print("2. Quota API dépassé (100 requêtes/jour en gratuit)")
        print("3. Plan gratuit ne permet pas l'accès aux données historiques")
        try:
            error_data = r.json()
            print(f"\nDétails de l'erreur: {error_data}")
        except:
            print(f"\nRéponse brute: {r.text[:200]}")
    else:
        print(f"[ERREUR] HTTP {r.status_code}")
        try:
            error_data = r.json()
            print(f"Détails: {error_data}")
        except:
            print(f"Réponse: {r.text[:200]}")
            
except Exception as e:
    print(f"[ERREUR] {e}")
