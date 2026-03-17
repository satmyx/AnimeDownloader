#!/usr/bin/env python3
"""
Fonctions utilitaires pour VoirAnime Downloader
"""

import os
import re
import logging
from src.config import LOG_FILE, LOG_DIR

# ─────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────
# Créer le dossier logs s'il n'existe pas
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

def log(msg, level="info"):
    """Log un message à l'écran et dans le fichier"""
    print(msg)
    getattr(logging, level)(re.sub(r'[^\x00-\x7F]', '', msg))

# ─────────────────────────────────────────
# FORMATAGE
# ─────────────────────────────────────────
def sanitize(name):
    """Nettoie un nom de fichier"""
    return re.sub(r'[<>:"/\\|?*]', '', name).strip()

def zpad(n, width=2):
    """Zero-pad un nombre"""
    return str(n).zfill(width)

# ─────────────────────────────────────────
# INTERFACE
# ─────────────────────────────────────────
def clear():
    """Efface l'écran"""
    os.system("cls" if os.name == "nt" else "clear")

def banner():
    """Affiche le banner ASCII"""
    clear()
    print("\033[96m")
    print("  ██╗   ██╗ ██████╗ ██╗██████╗  █████╗ ███╗   ██╗██╗███╗   ███╗███████╗")
    print("  ██║   ██║██╔═══██╗██║██╔══██╗██╔══██╗████╗  ██║██║████╗ ████║██╔════╝")
    print("  ██║   ██║██║   ██║██║██████╔╝███████║██╔██╗ ██║██║██╔████╔██║█████╗  ")
    print("  ╚██╗ ██╔╝██║   ██║██║██╔══██╗██╔══██║██║╚██╗██║██║██║╚██╔╝██║██╔══╝  ")
    print("   ╚████╔╝ ╚██████╔╝██║██║  ██║██║  ██║██║ ╚████║██║██║ ╚═╝ ██║███████╗")
    print("    ╚═══╝   ╚═════╝ ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝╚═╝     ╚═╝╚══════╝")
    print("\033[0m")
    print("  \033[90m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m")
    print("  \033[93m  Jellyfin Edition V2  •  Anti-CF  •  Multi-DL  •  VF / VOSTFR\033[0m")
    print("  \033[90m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m\n")

# ─────────────────────────────────────────
# HELPERS MENU
# ─────────────────────────────────────────
def ask(prompt, default=None):
    """Demande une saisie utilisateur avec valeur par défaut"""
    suffix = f" [{default}]" if default else ""
    val = input(f"  ❯ {prompt}{suffix} : ").strip()
    return val if val else default

def format_time(seconds):
    """Formate un temps en secondes en format lisible"""
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        return f"{seconds/60:.1f}min"
    else:
        return f"{seconds/3600:.1f}h"

def format_size(bytes_count):
    """Formate une taille en octets en format lisible"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_count < 1024.0:
            return f"{bytes_count:.1f}{unit}"
        bytes_count /= 1024.0
    return f"{bytes_count:.1f}TB"

def format_speed(bytes_per_second):
    """Formate une vitesse en octets/seconde"""
    return f"{format_size(bytes_per_second)}/s"
