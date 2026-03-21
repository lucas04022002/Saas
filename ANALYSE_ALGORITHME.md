# 📊 Analyse de l'Algorithme d'Analyse de Cotes

## 🎯 Objectif
Créer un algorithme qui analyse les cotes de paris sportifs pour identifier les **favoris** et les **value bets** (paris à valeur) dans les matchs de football.

---

## 🔍 Analyse du Code Original

### ✅ Points Forts
- Utilisation de deux APIs complémentaires (API-Football + The-Odds-API)
- Matching flou pour gérer les différences de noms d'équipes
- Structure modulaire et lisible
- Détection basique de value bets

### ❌ Problèmes Identifiés

1. **Saison obsolète** : `SAISON = 2023` (devrait être 2025)
2. **Pas de détection de favoris** : Le code analysait seulement les cotes mais ne déterminait pas qui était favori
3. **Matching incomplet** : Ne vérifiait que l'équipe à domicile, ignorait l'équipe à l'extérieur
4. **Gestion d'erreurs faible** : `except:` trop large masquait les erreurs
5. **Pas de calcul de probabilité implicite** : Ne convertissait pas les cotes en probabilités
6. **Logique limitée** : Ne cherchait que les value bets, pas les favoris spécifiquement

---

## 🚀 Améliorations Apportées

### 1. **Détection des Favoris**
```python
COTE_FAVORI_MAX = 2.0  # Cote <= 2.0 = favori (probabilité >= 50%)
```
- Identifie automatiquement le favori (équipe avec la cote moyenne la plus basse)
- Filtre les matchs où le favori a une cote ≤ 2.0

### 2. **Calcul de Probabilité Implicite**
```python
def calculer_probabilite_implicite(cote):
    return (1 / cote) * 100
```
- Convertit les cotes décimales en probabilités implicites
- Aide à comprendre les chances réelles de victoire

### 3. **Matching Amélioré**
- Vérifie maintenant **home_team ET away_team**
- Utilise le meilleur match trouvé entre les deux
- Gère mieux les cas où les noms diffèrent entre les APIs

### 4. **Analyse Complète des Cotes**
- Analyse les 3 issues possibles : **Home**, **Away**, **Draw**
- Calcule la moyenne et la meilleure cote pour chaque issue
- Identifie le bookmaker offrant la meilleure cote

### 5. **Gestion d'Erreurs Robuste**
- Gestion spécifique des erreurs HTTP
- Vérification des réponses API
- Messages d'erreur clairs et informatifs

### 6. **Résumé des Favoris**
- Affiche un résumé à la fin de chaque ligue
- Liste tous les favoris trouvés avec leurs statistiques
- Indique clairement les value bets

---

## 📈 Fonctionnement de l'Algorithme

### Étape 1 : Récupération des Matchs
```
API-Football → Liste des matchs du jour pour chaque ligue
```

### Étape 2 : Récupération des Cotes
```
The-Odds-API → Cotes de tous les bookmakers pour chaque match
```

### Étape 3 : Matching
```
Fuzzy Matching → Correspondance entre noms d'équipes des 2 APIs
```

### Étape 4 : Analyse
```
Pour chaque match :
  1. Calculer moyenne des cotes pour Home/Away/Draw
  2. Identifier le favori (cote moyenne la plus basse)
  3. Vérifier si favori (cote ≤ 2.0)
  4. Calculer probabilité implicite
  5. Détecter value bet (meilleure cote > moyenne × 1.05)
```

### Étape 5 : Affichage
```
- [FAVORI + VALUE] : Favori avec value bet (vert)
- [FAVORI] : Favori sans value bet (jaune)
- [VALUE] : Value bet mais pas favori (cyan)
- [SKIP] : Pas de données disponibles
```

---

## 🎲 Critères de Sélection

### Favori
- **Cote moyenne ≤ 2.0** (probabilité implicite ≥ 50%)
- Identifié automatiquement comme l'équipe avec la cote la plus basse

### Value Bet
- **Meilleure cote > Moyenne × 1.05** (5% meilleur que la moyenne du marché)
- Indique une cote sous-évaluée par rapport au marché

### Favori + Value Bet (Idéal)
- Combine les deux critères
- Favori avec une cote meilleure que la moyenne
- **Meilleur signal pour placer un pari**

---

## ⚙️ Configuration

### Variables Importantes

```python
SAISON = 2025  # Saison à analyser
COTE_FAVORI_MAX = 2.0  # Seuil pour identifier un favori
```

### Personnalisation Possible

- **COTE_FAVORI_MAX** : Ajuster selon votre stratégie
  - `1.5` = Favoris très clairs (≥66% probabilité)
  - `2.0` = Favoris modérés (≥50% probabilité)
  - `2.5` = Favoris légers (≥40% probabilité)

- **Seuil Value Bet** : Actuellement 5% (`1.05`)
  - Augmenter pour être plus sélectif
  - Diminuer pour plus d'opportunités

---

## 📝 Utilisation

1. **Configurer les clés API** :
   ```python
   KEY_API_FOOTBALL = "votre_clé_ici"
   KEY_THE_ODDS = "votre_clé_ici"
   ```

2. **Lancer le script** :
   ```bash
   python "Algo plus APi.py"
   ```

3. **Analyser les résultats** :
   - Chercher les `[FAVORI + VALUE]` en vert
   - Vérifier les probabilités implicites
   - Comparer avec vos propres analyses

---

## ⚠️ Avertissements

1. **Les cotes ne garantissent pas le résultat** : Elles reflètent les probabilités estimées, pas la réalité
2. **Gestion du bankroll** : Ne jamais parier plus que ce que vous pouvez perdre
3. **Limites API** : Respecter les quotas des APIs pour éviter les blocages
4. **Analyse complémentaire** : Utiliser cet outil avec d'autres analyses (statistiques, forme, blessures, etc.)

---

## 🔮 Améliorations Futures Possibles

1. **Historique des performances** : Tracker les résultats des favoris identifiés
2. **Filtres avancés** : Forme récente, confrontations directes, blessures
3. **Alertes automatiques** : Notifications pour les meilleures opportunités
4. **Base de données** : Stocker les données pour analyse historique
5. **Machine Learning** : Prédiction basée sur les données historiques
6. **Gestion de bankroll** : Calcul automatique des mises selon le Kelly Criterion

---

## 📊 Exemple de Sortie

```
╔════════════════════════════════════════╗
║  ALGORITHME D'ANALYSE DE COTES      ║
║  Détection des favoris + Value Bets ║
╚════════════════════════════════════════╝

=== SCAN DE : Premier League (Ang) ===
   -> 5 matchs trouvés. Récupération des cotes...
   [FAVORI + VALUE] Manchester City vs Burnley
   Favori: Manchester City | Cote moyenne: 1.45 | Meilleure: 1.52 (Bet365)
   Probabilité implicite: 65.8%

   === RÉSUMÉ: 2 favori(s) trouvé(s) ===
   • Manchester City (Manchester City vs Burnley) - Cote: 1.45 (68.9%) [VALUE]
   • Liverpool (Liverpool vs Brighton) - Cote: 1.85 (54.1%)
```

---

**Bon trading ! 🎯**
