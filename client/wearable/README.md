# AutoInsta - Guide Wearable & Montres Connectées

Ce dossier explique comment connecter vos appareils portables (montres connectées, bracelets d'activité) au serveur AutoInsta pour la télémétrie cardiaque et le bouton de l'homme mort.

---

## 1. Principe de Fonctionnement

Le serveur AutoInsta expose une API REST simple pour recevoir les données de santé :
- **Endpoint HTTP** : `POST http://<IP_DU_PC>:8000/api/sensors/health`
- **Format JSON** :
  ```json
  {
    "heart_rate": 78,
    "location": "Maison / Montre",
    "steps": 5120
  }
  ```

Si la fréquence cardiaque descend sous `hr_min_bpm` (ex: 45 BPM) ou dépasse `hr_max_bpm` (ex: 145 BPM), le **Bouton de l'Homme Mort** s'enclenche automatiquement :
1. Compte à rebours de 10 secondes avec son et vibrations.
2. Possibilité pour l'utilisateur d'annuler manuellement via l'interface ou le téléphone.
3. Si le compte à rebours expire sans réponse, dispatch de l'alerte de secours (selon vos autorisations).

---

## 2. Tester immédiatement avec le simulateur

Pour tester la réception des données de santé sans montre physique :
```bash
# Tester un rythme normal
py client/wearable/simulate_wearable.py --bpm 72

# Tester le déclenchement d'urgence (Tachycardie)
py client/wearable/simulate_wearable.py --emergency tachy

# Tester le déclenchement d'urgence (Bradycardie)
py client/wearable/simulate_wearable.py --emergency brady
```

---

## 3. Connexion d'une Montre Physique

### Option A : Gadgetbridge (Recommandé pour montres ouvertes / Android)
[Gadgetbridge](https://gadgetbridge.org/) est une application open-source pour Android qui se connecte aux montres (Pebble, Amazfit, Mi Band, Fossil, Garmin, Casio...).
- Gadgetbridge émet des Intents Android à chaque mesure de fréquence cardiaque.
- Notre client Termux ou Tasker peut capter ces Intents et appeler automatiquement l'API `POST /api/sensors/health`.

### Option B : Wear OS (Pixel Watch, Galaxy Watch...)
- Installez l'application gratuite **HTTP Shortcuts** sur Wear OS ou sur votre téléphone Android.
- Configurez un raccourci ou un webhook automatique lors de la détection de fréquence cardiaque vers `http://<IP_DU_PC>:8000/api/sensors/health`.

### Option C : Apple Watch
- Utilisez l'application native **Raccourcis (Shortcuts)** sur iOS / watchOS.
- Définissez une automatisation : *"Lorsque la fréquence cardiaque est supérieure à 140"* -> Action *"Obtenir le contenu de l'URL"* (`POST /api/sensors/health`).
