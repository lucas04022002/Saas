import requests
from datetime import datetime
from fuzz_fallback import fuzz, process
from colorama import Fore, Style, init
import time

init(autoreset=True)

# ==========================================
# 1. CONFIGURATION ET CLÉS
# ==========================================
KEY_API_FOOTBALL = "TA_CLE_API_FOOTBALL_ICI"
KEY_THE_ODDS = "TA_CLE_THE_ODDS_ICI"
SAISON = 2023 

# LE TABLEAU DE CORRESPONDANCE (C'est ça le secret de l'automatisation)
# J'ai pré-rempli les 5 grands championnats majeurs
LIGUES_A_SCANNER = [
    {"nom": "Premier League (Ang)", "id_foot": 39, "key_odds": "soccer_epl"},
    {"nom": "Ligue 1 (Fra)",       "id_foot": 61, "key_odds": "soccer_france_ligue_one"},
    {"nom": "La Liga (Esp)",       "id_foot": 140, "key_odds": "soccer_spain_la_liga"},
    {"nom": "Bundesliga (All)",    "id_foot": 78, "key_odds": "soccer_germany_bundesliga"},
    {"nom": "Serie A (Ita)",       "id_foot": 135, "key_odds": "soccer_italy_serie_a"}
]

# ==========================================
# 2. FONCTIONS TECHNIQUES
# ==========================================

def get_matchs_du_jour(ligue_id):
    """Récupère les matchs pour une ligue précise via API-Football"""
    date_jour = datetime.today().strftime('%Y-%m-%d')
    url = "https://v3.football.api-sports.io/fixtures"
    headers = {'x-rapidapi-host': "v3.football.api-sports.io", 'x-rapidapi-key': KEY_API_FOOTBALL}
    params = {"date": date_jour, "league": ligue_id, "season": SAISON}
    
    try:
        r = requests.get(url, headers=headers, params=params)
        return r.json().get('response', [])
    except:
        return []

def get_cotes_du_marche(ligue_key):
    """Récupère les cotes pour une ligue précise via The-Odds-API"""
    url = f'https://api.the-odds-api.com/v4/sports/{ligue_key}/odds'
    params = {'apiKey': KEY_THE_ODDS, 'regions': 'eu', 'markets': 'h2h', 'oddsFormat': 'decimal'}
    
    try:
        r = requests.get(url, params=params)
        # L'API renvoie parfois un message d'erreur si la quota est dépassée
        if isinstance(r.json(), list):
            return r.json()
        return []
    except:
        return []

def analyse_ligue(ligue):
    """Fonction principale qui traite une ligue entière"""
    print(f"\n{Fore.CYAN}=== SCAN DE : {ligue['nom']} ==={Style.RESET_ALL}")
    
    # 1. Calendrier
    matchs = get_matchs_du_jour(ligue['id_foot'])
    if not matchs:
        print("   -> Aucun match prévu aujourd'hui.")
        return

    print(f"   -> {len(matchs)} matchs trouvés. Récupération des cotes...")
    
    # 2. Cotes
    cotes = get_cotes_du_marche(ligue['key_odds'])
    if not cotes:
        print("   -> Impossible de récupérer les cotes (ou quota dépassé).")
        return

    # 3. Comparaison
    for match in matchs:
        home_team = match['teams']['home']['name']
        away_team = match['teams']['away']['name']
        
        # Matching Fuzzy
        teams_odds = [m['home_team'] for m in cotes]
        match_nom, score = process.extractOne(home_team, teams_odds, scorer=fuzz.token_sort_ratio)
        
        if score > 80:
            match_data = next((item for item in cotes if item["home_team"] == match_nom), None)
            
            # Recherche meilleure cote
            best_odd = 0
            best_bookie = ""
            total_odd = 0
            count = 0
            
            for bookie in match_data['bookmakers']:
                for market in bookie['markets']:
                    if market['key'] == 'h2h':
                        for outcome in market['outcomes']:
                            if outcome['name'] == match_nom: # Cote domicile
                                price = outcome['price']
                                if price > best_odd:
                                    best_odd = price
                                    best_bookie = bookie['title']
                                total_odd += price
                                count += 1
            
            avg_odd = total_odd / count if count > 0 else 0
            
            # Condition d'affichage (Value Bet simple)
            if best_odd > avg_odd * 1.05: # Si 5% meilleur que la moyenne
                print(f"{Fore.GREEN}   [VALUE] {home_team} vs {away_team}")
                print(f"   Moyenne: {round(avg_odd, 2)} | Top: {best_odd} ({best_bookie}){Style.RESET_ALL}")
            else:
                # On affiche quand même pour vérifier que ça marche
                print(f"   [RAS] {home_team} (Cote: {best_odd})")
                
        else:
             print(f"   [SKIP] Pas de cotes trouvées pour {home_team}")

# ==========================================
# MAIN LOOP
# ==========================================
if __name__ == "__main__":
    print("Démarrage du scanner multi-ligues...")
    
    for ligue in LIGUES_A_SCANNER:
        analyse_ligue(ligue)
        # Petite pause pour être gentil avec les API
        time.sleep(1) 
        
    print("\nScan terminé.")