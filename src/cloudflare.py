#!/usr/bin/env python3
"""
Gestion du challenge Cloudflare pour VoirAnime
"""

import time
from seleniumbase import Driver
from src.config import DEFAULT_USER_AGENT

# ─────────────────────────────────────────
# VARIABLES GLOBALES
# ─────────────────────────────────────────
CF_COOKIES = {}
CF_UA = DEFAULT_USER_AGENT

def get_cf_clearance():
    """
    Ouvre une fenêtre Chrome visible pour résoudre le challenge Cloudflare,
    extrait le cookie cf_clearance et le User-Agent réel du navigateur.
    
    Note: Ce navigateur reste TOUJOURS visible (headless=False) car Cloudflare
    détecte les navigateurs headless. Les autres navigateurs du pool peuvent
    être en mode invisible.
    """
    global CF_COOKIES, CF_UA
    print("  🛡️   Résolution du challenge Cloudflare...", flush=True)
    print("  \033[93m⚠️  Une fenêtre Chrome va s'ouvrir — ne la fermez pas !\033[0m\n")

    driver = Driver(uc=True, headless=False)  # TOUJOURS visible pour CF
    try:
        # Reconnexion UC : attend que CF laisse passer
        driver.uc_open_with_reconnect("https://voir-anime.to/", reconnect_time=5)

        # Tente de cliquer sur le Turnstile si présent
        try:
            driver.uc_gui_click_captcha()
        except Exception:
            pass

        # Attente supplémentaire pour que CF valide la session
        time.sleep(4)

        raw_cookies = driver.get_cookies()
        CF_COOKIES = {c["name"]: c["value"] for c in raw_cookies}
        CF_UA = driver.execute_script("return navigator.userAgent")

        if "cf_clearance" in CF_COOKIES:
            print("  \033[92m✓  cf_clearance obtenu !\033[0m\n")
        else:
            print("  \033[93m⚠️  cf_clearance absent — le site n'a peut-être pas de challenge actif.\033[0m\n")

    finally:
        driver.quit()

def get_cookies():
    """Retourne les cookies Cloudflare"""
    return CF_COOKIES

def get_user_agent():
    """Retourne le User-Agent"""
    return CF_UA
