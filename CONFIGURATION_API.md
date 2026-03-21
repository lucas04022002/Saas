# 🔑 Configuration des Clés API

## 📋 Étapes pour configurer vos clés API

### 1. **Créer le fichier de configuration**

Le fichier `config.py` a été créé automatiquement. Si ce n'est pas le cas, copiez le fichier exemple :

```bash
# Windows PowerShell
Copy-Item config.example.py config.py

# Linux/Mac
cp config.example.py config.py
```

### 2. **Obtenir vos clés API**

#### 🔵 API-Football (https://www.api-football.com/)
1. Allez sur https://dashboard.api-football.com/
2. Créez un compte ou connectez-vous
3. Allez dans l'onglet "API" ou "Subscription"
4. Copiez votre clé API (format : `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`)

#### 🟢 The-Odds-API (https://the-odds-api.com/)
1. Allez sur https://the-odds-api.com/
2. Créez un compte gratuit
3. Allez dans "API Keys" dans votre dashboard
4. Copiez votre clé API (format : `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`)

### 3. **Ajouter vos clés dans config.py**

Ouvrez `config.py` et remplacez les placeholders :

```python
# Avant
KEY_API_FOOTBALL = "TA_CLE_API_FOOTBALL_ICI"
KEY_THE_ODDS = "TA_CLE_THE_ODDS_ICI"

# Après (avec vos vraies clés)
KEY_API_FOOTBALL = "votre_vraie_cle_api_football_ici"
KEY_THE_ODDS = "votre_vraie_cle_the_odds_ici"
```

### 4. **Vérifier la configuration**

Lancez le script principal pour tester :

```bash
python "Algo plus APi.py"
```

Si vous voyez des erreurs d'authentification, vérifiez que :
- ✅ Vos clés sont correctement copiées (pas d'espaces avant/après)
- ✅ Vos clés sont actives (pas expirées)
- ✅ Vous n'avez pas dépassé votre quota API

---

## ⚠️ Sécurité

### **IMPORTANT : Ne partagez JAMAIS votre fichier config.py !**

- ✅ Le fichier `config.py` est dans `.gitignore` (ne sera pas partagé sur GitHub)
- ✅ Le fichier `config.example.py` peut être partagé (sans vraies clés)
- ❌ Ne commitez jamais `config.py` avec vos vraies clés

---

## 🔧 Dépannage

### Erreur : "ModuleNotFoundError: No module named 'config'"
**Solution** : Assurez-vous que `config.py` existe dans le même dossier que les autres scripts.

### Erreur : "Invalid API key"
**Solution** : 
- Vérifiez que vous avez copié la clé complète
- Vérifiez que la clé n'a pas expiré
- Vérifiez votre quota API

### Erreur : "Quota exceeded"
**Solution** :
- Vous avez dépassé votre limite de requêtes
- Attendez 24h ou passez à un plan payant
- Vérifiez votre utilisation sur le dashboard de l'API

---

## 📊 Quotas API (Gratuits)

### API-Football (Plan Gratuit)
- **100 requêtes/jour**
- **3 requêtes/minute**

### The-Odds-API (Plan Gratuit)
- **500 requêtes/mois**
- **8 requêtes/minute**

**Astuce** : Le script fait des pauses automatiques pour respecter les quotas.

---

## ✅ Vérification

Une fois configuré, vous devriez voir :

```
╔════════════════════════════════════════╗
║  ALGORITHME D'ANALYSE DE COTES      ║
║  Elo + Poisson + XGBoost            ║
║  Détection des favoris + Value Bets ║
╚════════════════════════════════════════╝

=== SCAN DE : Premier League (Ang) ===
   -> X matchs trouvés. Récupération des cotes...
```

Si vous voyez des erreurs d'API, vérifiez vos clés !

---

**Configuration terminée ! 🎯**
