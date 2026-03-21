"""
Affiche la liste des sports disponibles sur The-Odds-API (GET /v4/sports).
Utile pour trouver la bonne clé "key" pour la Ligue des Champions si 404.
Ne consomme pas de quota.
"""
import requests
from config import KEY_THE_ODDS

url = "https://api.the-odds-api.com/v4/sports"
params = {"apiKey": KEY_THE_ODDS}
# all=true pour voir aussi les sports hors saison
params_all = {"apiKey": KEY_THE_ODDS, "all": "true"}

def main():
    print("Sports en saison (soccer / champions / uefa):")
    print("-" * 50)
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        sports = r.json()
    except Exception as e:
        print("Erreur:", e)
        return
    for s in sports:
        key = s.get("key", "")
        title = s.get("title", "")
        if "soccer" in key.lower() or "champion" in key.lower() or "uefa" in key.lower():
            print(f"  key = {key!r}  title = {title}")
    print("\nTous les sports (all=true), soccer / champion / uefa:")
    print("-" * 50)
    try:
        r2 = requests.get(url, params=params_all, timeout=10)
        r2.raise_for_status()
        sports2 = r2.json()
    except Exception as e:
        print("Erreur:", e)
        return
    for s in sports2:
        key = s.get("key", "")
        title = s.get("title", "")
        if "soccer" in key.lower() or "champion" in key.lower() or "uefa" in key.lower():
            print(f"  key = {key!r}  title = {title}")

if __name__ == "__main__":
    main()
