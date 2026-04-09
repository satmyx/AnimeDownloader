#!/usr/bin/env python3
"""
Scraper VoirAnime - recherche et extraction des épisodes
"""

import re
import json
import time
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from src.config import BASE_URL, AJAX_URL, DELAY_PAGE, DELAY_AFTER_PAGE_LOAD, DELAY_PLAYER_CHECK
from src.utils import log
from src import cloudflare

try:
    from curl_cffi import requests as curl_requests
    CURL_OK = True
except ImportError:
    import requests as curl_requests
    CURL_OK = False

# ─────────────────────────────────────────
# RECHERCHE AJAX
# ─────────────────────────────────────────
def search_anime(query, langue):
    """Recherche un anime via l'API AJAX de VoirAnime"""
    asid = "3" if langue == "vostfr" else "2"
    payload = {
        "action": "ajaxsearchpro_search",
        "aspp": query,
        "asid": asid,
        "asp_inst_id": f"{asid}_1",
        "options": (
            f"aspf[vf_1]={langue}"
            "&asp_gen[]=excerpt&asp_gen[]=content&asp_gen[]=title"
            "&filters_initial=1&filters_changed=0"
            "&qtranslate_lang=0&current_page_id=0"
        ),
    }
    headers = {
        "User-Agent": cloudflare.get_user_agent(),
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://voir-anime.to/",
        "Origin": "https://voir-anime.to",
    }

    try:
        if CURL_OK:
            r = curl_requests.post(
                AJAX_URL,
                data=payload,
                headers=headers,
                cookies=cloudflare.get_cookies(),
                timeout=15,
                impersonate="chrome124"
            )
        else:
            session = curl_requests.Session()
            r = session.post(AJAX_URL, data=payload, headers=headers, timeout=15)
        r.raise_for_status()
    except Exception as e:
        log(f"  ⚠️  Erreur recherche AJAX : {e}", "warning")
        return []

    m = re.search(r'___ASPSTART_DATA___(.*?)___ASPEND_DATA___', r.text, re.DOTALL)
    if not m:
        return []
    try:
        data = json.loads(m.group(1))
    except json.JSONDecodeError:
        return []

    results = []
    for item in data.get("results", []):
        link = item.get("link", "")
        title = item.get("title", "")
        slug_m = re.search(r'/anime/([^/]+)/?$', link)
        if slug_m:
            results.append((title, slug_m.group(1)))
    return results

# ─────────────────────────────────────────
# SCRAPING SELENIUM
# ─────────────────────────────────────────
def scrape_episode_list(driver_pool, anime_slug, langue):
    """Scrape la liste des épisodes d'une saison"""
    url = f"{BASE_URL}/{anime_slug}/"
    driver = driver_pool.get()
    episodes = []
    episode_slug = anime_slug
    
    try:
        driver.uc_open_with_reconnect(url, reconnect_time=4)
        try:
            driver.uc_gui_click_captcha()
        except Exception:
            pass

        # Délai aléatoire anti-détection
        time.sleep(random.uniform(*DELAY_AFTER_PAGE_LOAD))

        try:
            WebDriverWait(driver, DELAY_PAGE).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "a[href*='-vf'], a[href*='-vostfr']")
                )
            )
        except Exception:
            pass

        links = driver.find_elements(
            By.CSS_SELECTOR, "a[href*='-vf'], a[href*='-vostfr']"
        )
        seen = set()
        for link in links:
            href = link.get_attribute("href") or ""
            if langue not in href:
                continue
            m = re.search(
                rf"/anime/{re.escape(anime_slug)}/([^/]+)-(\d+)-{langue}", href
            )
            if not m:
                continue
            detected_ep_slug = m.group(1)
            ep_num = int(m.group(2))
            if detected_ep_slug != episode_slug and episode_slug == anime_slug:
                episode_slug = detected_ep_slug
                log(f"  ⚠️  Slug épisode auto-détecté : '{episode_slug}'")
            if href not in seen:
                seen.add(href)
                episodes.append((ep_num, href))
        episodes.sort(key=lambda x: x[0])
    finally:
        driver_pool.release(driver)
    
    return episodes, episode_slug

def get_all_player_urls(driver_pool, episode_url):
    """
    Récupère TOUS les players disponibles pour un épisode
    Cherche dans plusieurs endroits : thisChapterSources, iframes, boutons de players
    """
    driver = driver_pool.get()
    players = []
    players_dict = {}  # Pour stocker les players avec leur nom/type
    
    try:
        driver.uc_open_with_reconnect(episode_url, reconnect_time=4)
        try:
            driver.uc_gui_click_captcha()
        except Exception:
            pass

        # Délai aléatoire anti-détection
        time.sleep(random.uniform(*DELAY_PLAYER_CHECK))

        try:
            WebDriverWait(driver, DELAY_PAGE).until(
                lambda d: "thisChapterSources" in d.page_source
                          or len(d.find_elements(By.TAG_NAME, "iframe")) > 0
            )
        except Exception:
            pass

        page_source = driver.page_source
        
        # ═══════════════════════════════════════════════════════════
        # MÉTHODE 1 : thisChapterSources (structure JavaScript)
        # ═══════════════════════════════════════════════════════════
        m = re.search(r'var\s+thisChapterSources\s*=\s*(\{.*?\})\s*;', page_source, re.DOTALL)
        if m:
            # Exemple de structure: {lecteur1: {src: "url1"}, lecteur2: {src: "url2"}}
            sources_block = m.group(1)
            
            # Méthode A: Chercher avec clés nommées (vidmoly, sendvid, etc.)
            player_patterns = [
                (r'vidmoly["\']?\s*:\s*\{[^}]*src\s*:\s*["\']([^"\']+)["\']', 'vidmoly'),
                (r'sendvid["\']?\s*:\s*\{[^}]*src\s*:\s*["\']([^"\']+)["\']', 'sendvid'),
                (r'sibnet["\']?\s*:\s*\{[^}]*src\s*:\s*["\']([^"\']+)["\']', 'sibnet'),
                (r'myvi["\']?\s*:\s*\{[^}]*src\s*:\s*["\']([^"\']+)["\']', 'myvi'),
                (r'vudeo["\']?\s*:\s*\{[^}]*src\s*:\s*["\']([^"\']+)["\']', 'vudeo'),
                (r'uqload["\']?\s*:\s*\{[^}]*src\s*:\s*["\']([^"\']+)["\']', 'uqload'),
                (r'vidoza["\']?\s*:\s*\{[^}]*src\s*:\s*["\']([^"\']+)["\']', 'vidoza'),
            ]
            
            for pattern, name in player_patterns:
                matches = re.findall(pattern, sources_block, re.IGNORECASE)
                for url in matches:
                    if url.startswith("http") and url not in players_dict:
                        players_dict[url] = name
                        log(f"  🎯  Trouvé {name}: {url[:60]}...")
            
            # Méthode B: Capturer TOUTES les URLs (fallback)
            all_srcs = re.findall(r'src\s*:\s*["\']([^"\']+)["\']', sources_block)
            for src in all_srcs:
                if src.startswith("http") and src not in players_dict:
                    players_dict[src] = 'inconnu'
                    log(f"  🔗  Trouvé player: {src[:60]}...")
        
        # ═══════════════════════════════════════════════════════════
        # MÉTHODE 2 : Boutons de sélection de players
        # ═══════════════════════════════════════════════════════════
        try:
            # Chercher les boutons data-src ou data-player
            player_buttons = driver.find_elements(By.CSS_SELECTOR, "[data-src], [data-player], .player-option, .server-item")
            for btn in player_buttons:
                src = btn.get_attribute("data-src") or btn.get_attribute("data-player")
                if src and src.startswith("http") and src not in players_dict:
                    players_dict[src] = 'bouton'
                    log(f"  🔘  Trouvé via bouton: {src[:60]}...")
        except Exception as e:
            log(f"  ⚠️  Erreur recherche boutons: {e}", "warning")
        
        # ═══════════════════════════════════════════════════════════
        # MÉTHODE 3 : iframes dans le DOM (toujours chercher)
        # ═══════════════════════════════════════════════════════════
        try:
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            for iframe in iframes:
                src = iframe.get_attribute("src")
                if src and src.startswith("http") and src not in players_dict:
                    players_dict[src] = 'iframe'
                    log(f"  📺  Trouvé iframe: {src[:60]}...")
        except Exception as e:
            log(f"  ⚠️  Erreur recherche iframes: {e}", "warning")
        
        # Convertir en liste
        players = list(players_dict.keys())
        
        # Afficher le résumé
        if players:
            log(f"  ✅  Total: {len(players)} player(s) trouvé(s)")
            # Afficher les types de players
            types_count = {}
            for url, ptype in players_dict.items():
                types_count[ptype] = types_count.get(ptype, 0) + 1
            log(f"  📊  Types: {', '.join([f'{k}({v})' for k, v in types_count.items()])}")
        else:
            log(f"  ❌  Aucun player trouvé !", "error")
            
    finally:
        driver_pool.release(driver)
    
    return players
