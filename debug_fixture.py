"""
Script pour déboguer la structure des fixtures
"""

import requests
from config import KEY_API_FOOTBALL
import json

# Récupérer un match terminé pour voir la structure
url = "https://v3.football.api-sports.io/fixtures"
headers = {
    'x-rapidapi-host': "v3.football.api-sports.io",
    'x-rapidapi-key': KEY_API_FOOTBALL
}
params = {
    "league": 39,  # Premier League
    "season": 2024,
    "status": "FT"  # Full Time
}

r = requests.get(url, headers=headers, params=params, timeout=10)
data = r.json()

if data.get('response'):
    fixture = data['response'][0]  # Premier match
    
    print("Structure d'un fixture:")
    print("=" * 60)
    print(json.dumps(fixture, indent=2, ensure_ascii=False)[:2000])
    
    print("\n" + "=" * 60)
    print("Extraction manuelle:")
    print("=" * 60)
    
    # Essayer différentes façons d'extraire les scores
    print("\n1. fixture['fixture']['status']['short']:")
    print(f"   {fixture.get('fixture', {}).get('status', {}).get('short')}")
    
    print("\n2. fixture['score']['fulltime']:")
    score_ft = fixture.get('score', {}).get('fulltime', {})
    print(f"   {score_ft}")
    print(f"   home: {score_ft.get('home')}")
    print(f"   away: {score_ft.get('away')}")
    
    print("\n3. fixture['goals']:")
    goals = fixture.get('goals', {})
    print(f"   {goals}")
    print(f"   home: {goals.get('home')}")
    print(f"   away: {goals.get('away')}")
    
    print("\n4. Toutes les clés de fixture:")
    print(f"   {list(fixture.keys())}")
    
    print("\n5. Toutes les clés de fixture['score']:")
    if 'score' in fixture:
        print(f"   {list(fixture['score'].keys())}")
