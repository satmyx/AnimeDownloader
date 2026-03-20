# VoirAnime Downloader V2 - Jellyfin Edition

### Structure du Projet

```
VoirAnimeDownloader/
├── voiranime_dl_v2.py        # 🚀 Point d'entrée principal
├── setup.py                   # Installation
├── start.bat                  # Script de démarrage Windows
├── .gitignore                 # Fichiers ignorés par Git
├── README.md                  # Documentation principale
│
├── src/                       # 📦 Modules Python
│   ├── __init__.py           # Package initializer
│   ├── config.py             # Configuration centralisée
│   ├── utils.py              # Fonctions utilitaires
│   ├── cloudflare.py         # Gestion Cloudflare
│   ├── driver_pool.py        # Pool de drivers SeleniumBase
│   ├── scraper.py            # Scraping VoirAnime
│   ├── downloader.py         # Téléchargement épisodes
│   ├── progress.py           # Monitoring avancé
│   └── README.md             # Documentation des modules
│
├── logs/                      # 📝 Fichiers de logs
│   └── voiranime_dl.log      # Log principal
│
├── chromedriver-win32/        # 🌐 Driver Chrome
└── downloaded_files/          # 📁 (Optionnel) Fichiers téléchargés
```

## 📦 Modules (dossier `src/`)

### `config.py`
Configuration centralisée du projet :
- Chemins de sortie (`OUTPUT_DIR`, `LOG_DIR`, `LOG_FILE`)
- Paramètres de téléchargement (`MAX_WORKERS`, `DELAY_PAGE`)
- Mode navigateur (`HEADLESS_MODE` - invisible ou visible)
- URLs du site (`BASE_URL`, `AJAX_URL`)
- Style de l'interface (`CUSTOM_STYLE`)
- Délais anti-détection

### `utils.py`
Fonctions utilitaires :
- `log()` : Logging écran + fichier
- `sanitize()` : Nettoyage des noms de fichiers
- `zpad()` : Zero-padding des numéros
- `banner()` : Affichage du banner ASCII
- `format_time()`, `format_size()`, `format_speed()` : Formatage des unités

### `cloudflare.py`
Résolution du challenge Cloudflare :
- `get_cf_clearance()` : Ouvre un navigateur pour obtenir le cookie cf_clearance
- `get_cookies()` : Retourne les cookies extraits
- `get_user_agent()` : Retourne le User-Agent du navigateur

### `driver_pool.py`
Gestion du pool de drivers réutilisables :
- `DriverPool` : Classe pour gérer un pool de drivers SeleniumBase
  - `initialize()` : Crée les drivers
  - `get()` : Récupère un driver du pool
  - `release()` : Remet un driver dans le pool
  - `close_all()` : Ferme tous les drivers

### `scraper.py`
Scraping des données VoirAnime :
- `search_anime()` : Recherche AJAX avec curl_cffi ou requests
- `scrape_episode_list()` : Extrait la liste des épisodes d'une saison
- `get_all_player_urls()` : Récupère tous les players d'un épisode

### `downloader.py`
Téléchargement des épisodes :
- `try_download()` : Télécharge avec yt-dlp
- `process_episode()` : Traite un épisode (essaie tous les players)
- `download_season()` : Télécharge une saison complète avec workers parallèles

### `progress.py`
Système de monitoring

#### `ProgressTracker`
Barre de progression avec :
- **Barre globale** : Progression totale sur toutes les saisons
- **Barre par saison** : Progression de la saison en cours
- **ETA dynamique** : Temps restant estimé basé sur vitesse réelle
- **Vitesse en temps réel** : Octets/seconde de téléchargement
- **Statistiques détaillées** : Succès/échecs, taille totale, temps écoulé

#### Features du monitoring :
```python
# Affichage global
🌍 Global (2 saison(s)): 45%|████████▌        | 18/40 [15:23<18:45, 0.48ep/s]
  ✅: 16  ❌: 2  💾: 8.5GB  ⚡: 9.2MB/s

# Affichage par saison
📦 Saison 01: 75%|█████████████▌   | 15/20 [08:12<02:45] ⬇️ S01E16 (player 2/3)
```

#### `SimpleProgressTracker`
Version fallback simple si tqdm n'est pas installé.

Le résumé final affiche maintenant :
```
🎉  Terminé !

  ✅  Season 01  │  20 téléchargé(s)  │  0 erreur(s)
  ⚠️  Season 02  │  18 téléchargé(s)  │  2 erreur(s)

📊  Total : 38 téléchargé(s)  |  2 erreur(s)
💾  Taille : 15.8 GB
⏱️   Durée : 28min
⚡  Vitesse moy. : 9.4 MB/s
📁  D:\Anime\Death Note
📝  Log : voiranime_dl.log
```

## 🔧 Configuration

Tous les paramètres sont maintenant dans [config.py](config.py) :

```python
# Modifier ces valeurs selon tes besoins
OUTPUT_DIR = "D:\\Anime"           # Dossier de sortie
MAX_WORKERS = 4                     # Nombre de téléchargements parallèles
DELAY_PAGE = 15                     # Timeout de chargement des pages
DELAY_BETWEEN_EPISODES = (1, 3)    # Délai aléatoire entre épisodes (secondes)
```

## 📝 Utilisation

Aucun changement pour l'utilisateurv:

```bash
py voiranime_dl_v2.py
```

Ajout de la V2.1 :
- ✅ Meilleur monitoring (barres de progression détaillées)
- ✅ Code plus propre et maintenable
- ✅ Statistiques avancées (vitesse, ETA, tailles)

## 🔮 Realised with claude and whats the problem ? (Need optimizations but its working and thats the original goal)

![Higuruma](https://media1.tenor.com/m/NzFYBVKRsR8AAAAd/higuruma-hiromi.gif)

Give a 💫
