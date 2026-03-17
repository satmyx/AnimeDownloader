# Changelog - VoirAnime Downloader V2

## [2.0.1] - 2026-03-17

### 🗂️ Réorganisation du Projet

#### Ajouté
- **Dossier `src/`** : Tous les modules Python sont maintenant dans `src/`
- **Dossier `logs/`** : Les fichiers de logs sont maintenant dans `logs/`
- **`.gitignore`** : Fichier pour ignorer les fichiers Python temporaires et logs
- **`src/README.md`** : Documentation des modules dans src/
- **`HEADLESS_MODE`** dans config : Option pour cacher les navigateurs (mode invisible)

#### Modifié
- **Structure des imports** : Tous les imports utilisent maintenant `from src.module import ...`
- **LOG_FILE** : Pointe maintenant vers `logs/voiranime_dl.log`
- **config.py** : Ajout de `LOG_DIR` et `HEADLESS_MODE`
- **Navigateurs** : Mode invisible par défaut (sauf pour Cloudflare)

#### Supprimé
- Anciens fichiers .py à la racine (déplacés dans `src/`)

### 📁 Nouvelle Structure
```
VoirAnimeDownloader/
├── voiranime_dl_v2.py        # Point d'entrée
├── src/                       # Modules Python
│   ├── config.py
│   ├── utils.py
│   ├── cloudflare.py
│   ├── driver_pool.py
│   ├── scraper.py
│   ├── downloader.py
│   └── progress.py
├── logs/                      # Fichiers de logs
└── [autres dossiers...]
```

### 🎯 Avantages
- ✅ **Code mieux organisé** : Séparation claire entre code source et fichiers de configuration
- ✅ **Logs centralisés** : Tous les logs dans un seul dossier
- ✅ **Git-friendly** : .gitignore pour ignorer les fichiers temporaires
- ✅ **Navigation invisible** : Les navigateurs ne repassent plus devant pendant les téléchargements
- ✅ **Maintenabilité** : Structure de dossiers professionnelle

---

## [2.0.0] - 2026-03-17

### ✨ Refactorisation Modulaire

#### Ajouté
- Architecture modulaire avec 8 modules spécialisés
- **ProgressTracker** : Double barre de progression (globale + par saison)
- **Statistiques avancées** : Vitesse, ETA, taille totale
- **Monitoring en temps réel** : Vitesse de téléchargement, temps écoulé

#### Caractéristiques
- 📊 Barre de progression globale sur toutes les saisons
- 📦 Barre de progression par saison en cours
- ⚡ Calcul de vitesse en temps réel (MB/s)
- ⏱️ ETA dynamique basé sur vitesse réelle
- 💾 Affichage de la taille totale téléchargée
- ✅ Compteurs succès/échecs détaillés
