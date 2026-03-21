# 📋 Ligues Configurées pour l'Analyse

## ✅ **Ligues Actuellement Configurées**

1. **Premier League (Angleterre)**
   - ID API-Football: `39`
   - Key The-Odds-API: `soccer_epl`

2. **Ligue 1 (France)**
   - ID API-Football: `61`
   - Key The-Odds-API: `soccer_france_ligue_one`

3. **La Liga (Espagne)**
   - ID API-Football: `140`
   - Key The-Odds-API: `soccer_spain_la_liga`

4. **Bundesliga (Allemagne)**
   - ID API-Football: `78`
   - Key The-Odds-API: `soccer_germany_bundesliga`

5. **Serie A (Italie)**
   - ID API-Football: `135`
   - Key The-Odds-API: `soccer_italy_serie_a`

6. **Ligue des Champions** ⭐ NOUVEAU
   - ID API-Football: `2`
   - Key The-Odds-API: `soccer_uefa_champions_league`

---

## 🎯 **Total : 6 Ligues**

Votre algorithme analysera maintenant :
- ✅ Les 5 grands championnats européens
- ✅ La Ligue des Champions (compétition européenne majeure)

---

## 📝 **Note sur la Ligue des Champions**

- **Format** : Compétition à élimination directe + phase de groupes
- **Saison** : 2024-2025 (utilise la saison configurée dans `SAISON = 2025`)
- **Matchs** : Principalement les mardis et mercredis
- **Équipes** : Les meilleures équipes d'Europe

---

## 🔧 **Ajouter d'Autres Ligues**

Pour ajouter une ligue, ajoutez simplement une ligne dans `LIGUES_A_SCANNER` :

```python
{"nom": "Nom de la Ligue", "id_foot": ID_API_FOOTBALL, "key_odds": "key_the_odds_api"}
```

**Où trouver les IDs ?**
- API-Football : https://dashboard.api-football.com/ → Apis → API-Football → Ids → Leagues
- The-Odds-API : https://the-odds-api.com/liveapi/guides/v4/#sports-request

---

**La Ligue des Champions est maintenant incluse ! 🏆**
