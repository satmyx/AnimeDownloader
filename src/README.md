# Modules Source - VoirAnime Downloader

Ce dossier contient tous les modules Python du projet.

## Structure

```
src/
├── __init__.py        # Package initializer
├── config.py          # Configuration centralisée
├── utils.py           # Fonctions utilitaires (log, formatage)
├── cloudflare.py      # Résolution challenge Cloudflare
├── driver_pool.py     # Pool de drivers SeleniumBase
├── scraper.py         # Scraping VoirAnime (recherche + épisodes)
├── downloader.py      # Téléchargement avec yt-dlp
└── progress.py        # Système de monitoring avancé
```

## Imports

Tous les modules s'importent depuis `src.` :

```python
from src.config import OUTPUT_DIR, MAX_WORKERS
from src.utils import log, sanitize
from src.driver_pool import DriverPool
```

## Maintenance

- **Ajouter un nouveau module** : Créer le fichier dans `src/` et importer avec `from src.nouveau_module import ...`
- **Modifier la config** : Éditer `config.py`
- **Ajouter des utilitaires** : Ajouter dans `utils.py`
