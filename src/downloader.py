#!/usr/bin/env python3
"""
Downloader - gestion des téléchargements d'épisodes
"""

import os
import sys
import time
import random
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.config import OUTPUT_DIR, MAX_WORKERS, DELAY_BETWEEN_EPISODES
from src.utils import log, sanitize, zpad
from src.scraper import get_all_player_urls

# ─────────────────────────────────────────
# YT-DLP
# ─────────────────────────────────────────
def try_download(player_url, output_path):
    """Tente de télécharger un épisode avec yt-dlp"""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--no-warnings", "--quiet", "--no-playlist",
        "--continue",
        "-f", "bestvideo+bestaudio/best",
        "--merge-output-format", "mkv",
        "-o", output_path,
        player_url
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0, result.stderr

# ─────────────────────────────────────────
# PROCESS UN ÉPISODE
# ─────────────────────────────────────────
def process_episode(driver_pool, ep_num, ep_url, output_path, anime_clean, saison, progress_callback=None, session=None):
    """
    Télécharge un épisode en essayant tous les players disponibles
    
    Args:
        driver_pool: Pool de drivers pour le scraping
        ep_num: Numéro de l'épisode
        ep_url: URL de la page de l'épisode
        output_path: Chemin de sortie du fichier
        anime_clean: Nom nettoyé de l'anime
        saison: Numéro de saison
        progress_callback: Fonction callback pour le monitoring (optionnel)
        session: Objet DownloadSession pour sauvegarder la progression (optionnel)
    
    Returns:
        tuple: (success: bool, file_size: int)
    """
    label = f"S{zpad(saison)}E{zpad(ep_num)}"
    
    if progress_callback:
        progress_callback('start', ep_num, label)
    
    log(f"\n🔍  [{label}] Récupération des players...")

    # Délai aléatoire entre épisodes pour éviter le burst
    time.sleep(random.uniform(*DELAY_BETWEEN_EPISODES))

    players = get_all_player_urls(driver_pool, ep_url)
    if not players:
        log(f"  ❌  [{label}] Aucun player trouvé.", "error")
        if progress_callback:
            progress_callback('error', ep_num, label)
        return False, 0
    
    log(f"  📋  [{label}] {len(players)} player(s) disponible(s), essai séquentiel...")
    
    for i, player_url in enumerate(players, start=1):
        # Identifier le type de player depuis l'URL
        player_type = "inconnu"
        if "vidmoly" in player_url.lower():
            player_type = "vidmoly"
        elif "sendvid" in player_url.lower():
            player_type = "sendvid"
        elif "sibnet" in player_url.lower():
            player_type = "sibnet"
        elif "myvi" in player_url.lower():
            player_type = "myvi"
        elif "vudeo" in player_url.lower():
            player_type = "vudeo"
        elif "uqload" in player_url.lower():
            player_type = "uqload"
        elif "vidoza" in player_url.lower():
            player_type = "vidoza"
        
        log(f"  🔗  [{label}] Player {i}/{len(players)} ({player_type}): {player_url[:70]}...")
        
        if progress_callback:
            progress_callback('downloading', ep_num, label, i, len(players))
        
        success, stderr = try_download(player_url, output_path)
        if success:
            # Obtenir la taille du fichier téléchargé
            file_size = os.path.getsize(output_path) if os.path.exists(output_path) else 0
            log(f"  ✅  [{label}] Succès avec {player_type} (player {i}/{len(players)})")
            if progress_callback:
                progress_callback('success', ep_num, label, file_size=file_size)
            # Sauvegarder dans la session
            if session:
                session.update_episode_completed(saison, ep_num)
            return True, file_size
        else:
            log(f"  ⚠️  [{label}] {player_type} KO (player {i}/{len(players)}) — {stderr[:100]}", "warning")
            if os.path.exists(output_path):
                os.remove(output_path)
            # Continuer avec le player suivant
            if i < len(players):
                log(f"  ➡️   [{label}] Essai du player suivant...")
    
    log(f"  ❌  [{label}] TOUS les {len(players)} players ont échoué.", "error")
    if progress_callback:
        progress_callback('error', ep_num, label)
    # Marquer comme échec dans la session
    if session:
        session.update_episode_failed(saison, ep_num)
    return False, 0

# ─────────────────────────────────────────
# TÉLÉCHARGEMENT D'UNE SAISON
# ─────────────────────────────────────────
def download_season(driver_pool, common_name, anime_slug, saison, langue, episodes_raw, episode_slug, progress_tracker=None, session=None):
    """
    Télécharge tous les épisodes d'une saison
    
    Args:
        driver_pool: Pool de drivers
        common_name: Nom commun de l'anime
        anime_slug: Slug URL de la série
        saison: Numéro de saison
        langue: Langue (vf/vostfr)
        episodes_raw: Liste des épisodes [(num, url), ...]
        episode_slug: Slug des épisodes
        progress_tracker: Objet de tracking de progression (optionnel)
        session: Objet DownloadSession pour sauvegarder/reprendre (optionnel)
    
    Returns:
        tuple: (success_count, fail_count, total_size)
    """
    anime_clean = sanitize(common_name)
    season_dir = os.path.join(OUTPUT_DIR, anime_clean, f"Season {zpad(saison)}")
    os.makedirs(season_dir, exist_ok=True)

    # Filtrer les épisodes avec la session (reprendre progression)
    if session:
        episodes_raw = session.get_episodes_to_download(saison, episodes_raw)

    # Préparer la liste des épisodes à télécharger
    to_download = []
    for ep_num, ep_url in episodes_raw:
        filename = f"{anime_clean} S{zpad(saison)}E{zpad(ep_num)}.mkv"
        path = os.path.join(season_dir, filename)
        if os.path.exists(path):
            print(f"  ⏭️   {filename} déjà présent, skip.")
            # Marquer comme skippé dans la session
            if session:
                session.update_episode_skipped(saison, ep_num)
        else:
            to_download.append((ep_num, ep_url, path))

    if not to_download:
        print(f"  ✅  S{zpad(saison)} — Tous les épisodes déjà téléchargés !")
        return 0, 0, 0

    print(f"\n  \033[92m🚀  S{zpad(saison)} — {len(to_download)} épisode(s) • {MAX_WORKERS} workers\033[0m")
    print(f"  📁  {season_dir}\n")
    log(f"SEASON START | {anime_clean} | S{zpad(saison)} | {langue.upper()} | {len(to_download)} eps")

    # Mettre à jour la session
    if session:
        session.update_season_start(saison, len(episodes_raw))

    # Créer le callback pour le progress tracker
    def progress_callback(*args, **kwargs):
        if progress_tracker:
            progress_tracker.update_episode(*args, **kwargs)

    ok, fail = 0, 0
    total_size = 0
    
    if progress_tracker:
        progress_tracker.start_season(saison, len(to_download))
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(
                process_episode, 
                driver_pool, 
                ep_num, 
                ep_url, 
                path, 
                anime_clean, 
                saison,
                progress_callback,
                session  # Passer la session
            ): ep_num
            for ep_num, ep_url, path in to_download
        }
        
        for future in as_completed(futures):
            success, file_size = future.result()
            if success:
                ok += 1
                total_size += file_size
            else:
                fail += 1
            
            if progress_tracker:
                progress_tracker.update_season_progress(ok, fail)

    if progress_tracker:
        progress_tracker.finish_season(saison, ok, fail)
    
    # Mettre à jour la session
    if session:
        session.update_season_end(saison, ok, fail)

    log(f"SEASON END | S{zpad(saison)} | {ok} succès | {fail} erreurs")
    return ok, fail, total_size
