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

# ─────────────────────────────────────────
# DÉTECTION DU TYPE DE PLAYER PAR URL
# ─────────────────────────────────────────
def guess_player_type_by_url(url):
    """Devine le type de player à partir de son domaine"""
    url_lower = url.lower()
    if 'vidmoly' in url_lower:
        return 'vidmoly'
    elif 'voe.sx' in url_lower:
        return 'voe'
    elif 'streamtape' in url_lower:
        return 'streamtape'
    elif 'streamhide' in url_lower:
        return 'streamhide'
    elif 'weneverbeenfree' in url_lower:
        return 'moon'
    elif 'my.mail.ru' in url_lower or 'myvi' in url_lower:
        return 'myvi'
    elif 'vudeo' in url_lower:
        return 'vudeo'
    elif 'uqload' in url_lower:
        return 'uqload'
    elif 'sendvid' in url_lower:
        return 'sendvid'
    elif 'sibnet' in url_lower:
        return 'sibnet'
    elif 'vidoza' in url_lower:
        return 'vidoza'
    return 'inconnu'

# ─────────────────────────────────────────
# RÉCUPÉRATION DE TOUS LES PLAYERS
# ─────────────────────────────────────────
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
        # Format réel: {"LECTEUR myTV": "<iframe src=\"https://...\" ...>", ...}
        # Les URLs sont échappées avec \" et \/ (échappement JSON dans JS)
        # ═══════════════════════════════════════════════════════════
        m = re.search(r'var\s+thisChapterSources\s*=\s*(\{.*?\})\s*;', page_source, re.DOTALL)
        if m:
            sources_block = m.group(1)
            
            # Identifier le type de player depuis sa clé (ex: "LECTEUR myTV")
            def guess_player_type(key):
                key_lower = key.lower()
                if 'mytv' in key_lower or 'vidmoly' in key_lower:
                    return 'vidmoly'
                elif 'moon' in key_lower:
                    return 'moon'
                elif 'sb' in key_lower:
                    return 'streamhide'
                elif 'voe' in key_lower:
                    return 'voe'
                elif 'stape' in key_lower or 'tape' in key_lower:
                    return 'streamtape'
                elif 'fhd' in key_lower or 'mail' in key_lower:
                    return 'myvi'
                return 'inconnu'
            
            # Extraire chaque paire clé-valeur de l'objet JS
            # Pattern: "CLÉ" ou 'CLÉ' : "valeur iframe" ou 'valeur iframe'
            pairs = re.findall(
                r"""["']([^"']*?)["']\s*:\s*["']((?:[^"']|\\"|\\')*?)["']\s*[,}]""",
                sources_block, re.DOTALL
            )
            
            for key, raw_html in pairs:
                # Déséchapper les caractères JSON (\", \/, \\)
                raw_html_unescaped = raw_html.replace('\\"', '"').replace("\\'", "'").replace('\\/', '/')
                
                # Extraire le src de l'iframe
                src_match = re.search(r'src\s*=\s*["\']([^"\']+)["\']', raw_html_unescaped)
                if src_match:
                    src = src_match.group(1)
                    if src.startswith("http") and src not in players_dict:
                        ptype = guess_player_type(key)
                        # Fallback: si la clé n'a pas donné de type, utiliser l'URL
                        if ptype == 'inconnu':
                            ptype = guess_player_type_by_url(src)
                        players_dict[src] = ptype
                        log(f"  🎯  [{ptype}] ← {key}: {src[:60]}...")
            
            # Fallback: capturer TOUS les src d'iframe dans le bloc (pour tout format)
            # D'abord déséchapper tout le bloc
            block_unescaped = sources_block.replace('\\"', '"').replace("\\'", "'").replace('\\/', '/')
            all_iframe_srcs = re.findall(r'<iframe[^>]+src\s*=\s*["\']([^"\']+)["\']', block_unescaped)
            for src in all_iframe_srcs:
                if src.startswith("http") and src not in players_dict:
                    ptype = guess_player_type_by_url(src)
                    players_dict[src] = ptype
                    log(f"  🔗  [{ptype}] Trouvé iframe (fallback): {src[:60]}...")
        
        # ═══════════════════════════════════════════════════════════
        # MÉTHODE 2 : Boutons de sélection de players
        # ═══════════════════════════════════════════════════════════
        try:
            # Chercher les boutons data-src ou data-player
            player_buttons = driver.find_elements(By.CSS_SELECTOR, "[data-src], [data-player], .player-option, .server-item")
            for btn in player_buttons:
                src = btn.get_attribute("data-src") or btn.get_attribute("data-player")
                if src and src.startswith("http") and src not in players_dict:
                    ptype = guess_player_type_by_url(src)
                    players_dict[src] = ptype
                    log(f"  🔘  [{ptype}] Trouvé via bouton: {src[:60]}...")
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
                    ptype = guess_player_type_by_url(src)
                    players_dict[src] = ptype
                    log(f"  📺  [{ptype}] Trouvé iframe DOM: {src[:60]}...")
        except Exception as e:
            log(f"  ⚠️  Erreur recherche iframes: {e}", "warning")
        
        # Convertir en liste, triée par priorité (meilleurs players d'abord)
        PLAYER_PRIORITY = {
            'vidmoly': 1, 'voe': 2, 'streamtape': 3,
            'streamhide': 4, 'moon': 5, 'myvi': 6,
        }
        def sort_key(url):
            ptype = players_dict.get(url, 'inconnu')
            return (PLAYER_PRIORITY.get(ptype, 99), url)
        
        players = sorted(players_dict.keys(), key=sort_key)
        
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
