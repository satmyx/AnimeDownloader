#!/usr/bin/env python3
"""
Configuration centralisée pour VoirAnime Downloader
"""

import os
from questionary import Style

# ─────────────────────────────────────────
# CHEMINS ET RÉPERTOIRES
# ─────────────────────────────────────────
OUTPUT_DIR = "C:\\Anime"
LOG_DIR = os.path.join(os.getcwd(), "logs")
LOG_FILE = os.path.join(LOG_DIR, "voiranime_dl.log")

# ─────────────────────────────────────────
# TÉLÉCHARGEMENT
# ─────────────────────────────────────────
MAX_WORKERS = 6  # Nombre de workers parallèles
DELAY_PAGE = 10  # Timeout pour le chargement des pages

# ─────────────────────────────────────────
# NAVIGATEURS
# ─────────────────────────────────────────
HEADLESS_MODE = True  # Mettre les navigateurs en arrière-plan (invisible)
                       # Note: Le navigateur Cloudflare reste toujours visible

# ─────────────────────────────────────────
# URLs
# ─────────────────────────────────────────
BASE_URL = "https://voir-anime.to/anime"
AJAX_URL = "https://voir-anime.to/wp-admin/admin-ajax.php"

# ─────────────────────────────────────────
# USER AGENT
# ─────────────────────────────────────────
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

# ─────────────────────────────────────────
# STYLE QUESTIONARY
# ─────────────────────────────────────────
CUSTOM_STYLE = Style([
    ("qmark", "fg:#00d7ff bold"),
    ("question", "fg:#ffffff bold"),
    ("answer", "fg:#00ff87 bold"),
    ("pointer", "fg:#00d7ff bold"),
    ("highlighted", "fg:#00d7ff bold"),
    ("selected", "fg:#00ff87"),
    ("separator", "fg:#444444"),
    ("instruction", "fg:#888888"),
])

# ─────────────────────────────────────────
# DÉLAIS ANTI-DÉTECTION
# ─────────────────────────────────────────
DELAY_BETWEEN_EPISODES = (1, 3)  # secondes (min, max)
DELAY_AFTER_PAGE_LOAD = (2, 4)   # secondes (min, max)
DELAY_PLAYER_CHECK = (1, 3)      # secondes (min, max)
