#!/usr/bin/env python3
"""
VoirAnime Downloader V2 - Jellyfin Edition (Modular)
Utilisation : 
  - Nouveau téléchargement: py voiranime_dl_v2.py
  - Reprendre une session: py voiranime_dl_v2.py --resume
  - Lister les sessions: py voiranime_dl_v2.py --list-sessions
"""

import os
import sys
import argparse

# Import des modules depuis src/
from src.config import OUTPUT_DIR, BASE_URL, CUSTOM_STYLE, LOG_FILE, MAX_WORKERS
from src.utils import banner, log, sanitize, zpad, ask
from src import cloudflare
from src.driver_pool import DriverPool
from src.scraper import search_anime, scrape_episode_list
from src.downloader import download_season
from src.progress import create_progress_tracker
from src.session import DownloadSession, list_sessions, load_session, find_incomplete_sessions

try:
    import questionary
    QUESTIONARY_OK = True
except ImportError:
    QUESTIONARY_OK = False

try:
    from curl_cffi import requests as curl_requests
    CURL_OK = True
except ImportError:
    CURL_OK = False

try:
    from tqdm import tqdm
    TQDM_OK = True
except ImportError:
    TQDM_OK = False

# ─────────────────────────────────────────
# HELPERS MENU
# ─────────────────────────────────────────

def select_langue():
    """Sélectionne la langue"""
    if QUESTIONARY_OK:
        return questionary.select("Langue ?",
            choices=["vostfr", "vf"], style=CUSTOM_STYLE).ask()
    return ask("Langue [vf/vostfr]", "vostfr")

# ─────────────────────────────────────────
# FLOW : recherche automatique multi-saisons
# ─────────────────────────────────────────
def flow_search(langue):
    """Flow de recherche automatique avec curl_cffi"""
    while True:
        if QUESTIONARY_OK:
            query = questionary.text("Rechercher un anime ?", style=CUSTOM_STYLE).ask()
        else:
            query = ask("Rechercher un anime")

        print(f"\n  🔍  Recherche de '{query}' ({langue.upper()})...")
        results = search_anime(query, langue)

        if not results:
            print("  ⚠️  Aucun résultat. Essaie un autre terme.\n")
            continue

        choices = [f"{title}  →  {slug}" for title, slug in results]

        if QUESTIONARY_OK:
            selected = questionary.checkbox(
                "Sélectionne les saisons à télécharger (ESPACE pour cocher, ENTRÉE pour valider) :",
                choices=choices,
                style=CUSTOM_STYLE,
                validate=lambda x: True if len(x) > 0 else "Coche au moins une saison avec ESPACE !"
            ).ask()
        else:
            print("\n  Résultats (numéros séparés par des virgules, ex: 1,2,3) :")
            for i, c in enumerate(choices, 1):
                print(f"    {i}. {c}")
            raw = ask("Saisons à télécharger", "1")
            selected = [choices[int(x.strip()) - 1] for x in raw.split(",") if x.strip().isdigit()]

        if not selected:
            print("  ⚠️  Aucune saison sélectionnée. Relance la recherche.\n")
            continue

        break

    first_idx  = choices.index(selected[0])
    first_name = results[first_idx][0]

    if QUESTIONARY_OK:
        common_name = questionary.text(
            "Nom commun pour les fichiers (toutes les saisons) ?",
            default=sanitize(first_name.split(".")[0].strip()),
            style=CUSTOM_STYLE
        ).ask()
    else:
        common_name = ask(
            "Nom commun pour les fichiers",
            sanitize(first_name.split(".")[0].strip())
        )

    seasons_plan = []
    for i, choice_str in enumerate(selected, start=1):
        idx         = choices.index(choice_str)
        title, slug = results[idx]
        if QUESTIONARY_OK:
            saison = int(questionary.text(
                f"Numéro de saison pour \"{title}\" ?",
                default=str(i), style=CUSTOM_STYLE
            ).ask())
        else:
            saison = int(ask(f"Numéro de saison pour '{title}'", str(i)))
        seasons_plan.append({
            "anime_name": title,
            "anime_slug": slug,
            "saison":     saison,
        })

    return common_name, seasons_plan

# ─────────────────────────────────────────
# RÉCAP DE CONFIRMATION
# ─────────────────────────────────────────
def confirm_recap(common_name, seasons_plan, langue):
    """Affiche et confirme le récapitulatif"""
    print(f"\n  \033[96m{'─'*60}\033[0m")
    print(f"  📺  Anime    : \033[93m{common_name}\033[0m")
    print(f"  🌐  Langue   : \033[93m{langue.upper()}\033[0m")
    print(f"  📦  {len(seasons_plan)} saison(s) planifiée(s) :\n")
    for s in seasons_plan:
        season_dir = os.path.join(OUTPUT_DIR, sanitize(common_name), f"Season {zpad(s['saison'])}")
        print(f"    \033[93mSeason {zpad(s['saison'])}\033[0m  ←  {s['anime_slug']}")
        print(f"             📁 {season_dir}")
        print(f"             🎬 {sanitize(common_name)} S{zpad(s['saison'])}E01.mkv\n")
    print(f"  \033[96m{'─'*60}\033[0m\n")

    if QUESTIONARY_OK:
        return questionary.confirm(
            "Ces informations sont correctes ?",
            default=True, style=CUSTOM_STYLE
        ).ask()
    return ask("Ces informations sont correctes ? [o/n]", "o").lower() == "o"

# ─────────────────────────────────────────
# GESTION DES SESSIONS
# ─────────────────────────────────────────
def display_sessions_list():
    """Affiche la liste des sessions sauvegardées"""
    sessions = list_sessions()
    
    if not sessions:
        print("  ℹ️   Aucune session sauvegardée.\n")
        return
    
    print(f"\n  📋  Sessions sauvegardées ({len(sessions)}) :\n")
    for i, s in enumerate(sessions, 1):
        status_icon = {
            "completed": "✅",
            "in_progress": "🔄",
            "partial": "⚠️",
            "failed": "❌"
        }.get(s["status"], "❓")
        
        print(f"    {i}. {status_icon}  {s['anime_name']} ({s['langue'].upper()})")
        print(f"        ID: {s['session_id']}")
        print(f"        Statut: {s['status']}")
        print(f"        Dernière MAJ: {s['last_update']}")
        print()

def select_session_to_resume():
    """Sélectionne une session à reprendre"""
    incomplete = find_incomplete_sessions()
    
    if not incomplete:
        print("  ℹ️   Aucune session incomplète à reprendre.\n")
        return None
    
    print(f"\n  🔄  Sessions à reprendre ({len(incomplete)}) :\n")
    
    if QUESTIONARY_OK:
        choices = []
        for s in incomplete:
            label = f"{s['anime_name']} ({s['langue'].upper()}) - {s['last_update']}"
            choices.append(label)
        
        if not choices:
            return None
            
        selected = questionary.select(
            "Quelle session reprendre ?",
            choices=choices,
            style=CUSTOM_STYLE
        ).ask()
        
        if selected:
            idx = choices.index(selected)
            return load_session(incomplete[idx]["file"])
    else:
        for i, s in enumerate(incomplete, 1):
            print(f"    {i}. {s['anime_name']} ({s['langue'].upper()})")
            print(f"        Dernière MAJ: {s['last_update']}")
        
        choice = ask("Numéro de session à reprendre", "1")
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(incomplete):
                return load_session(incomplete[idx]["file"])
        except:
            pass
    
    return None


# ─────────────────────────────────────────
# MENU PRINCIPAL
# ─────────────────────────────────────────
def main():
    """Fonction principale du programme"""
    
    # Parse des arguments CLI
    parser = argparse.ArgumentParser(description="VoirAnime Downloader V2")
    parser.add_argument("--resume", action="store_true", help="Reprendre une session incomplète")
    parser.add_argument("--list-sessions", action="store_true", help="Lister toutes les sessions")
    args = parser.parse_args()
    
    banner()
    
    # Mode liste des sessions
    if args.list_sessions:
        display_sessions_list()
        return
    
    # Mode reprise de session
    if args.resume:
        print("  🔄  Mode reprise de session\n")
        session = select_session_to_resume()
        if not session:
            print("  ❌  Aucune session sélectionnée.")
            return
        
        session.print_summary()
        
        if QUESTIONARY_OK:
            confirm = questionary.confirm(
                "\n  Reprendre cette session ?",
                default=True, style=CUSTOM_STYLE
            ).ask()
        else:
            confirm = ask("\nReprendre cette session ? [o/n]", "o").lower() == "o"
        
        if not confirm:
            print("  ❌  Annulé.")
            return
        
        # Restaurer les données
        common_name = session.anime_name
        seasons_plan = session.seasons_plan
        langue = session.langue
        auto_detect = True  # Les épisodes sont déjà dans la session
        
        # Passer directement au téléchargement
        print("\n  ▶️   Reprise du téléchargement...\n")
        
        # Vérification dépendances
        missing = []
        if not TQDM_OK:        missing.append("tqdm")
        if not QUESTIONARY_OK: missing.append("questionary")
        if not CURL_OK:        missing.append("curl_cffi")
        if missing:
            print(f"  \033[93m⚠️  Installe dépendances:\033[0m py -m pip install {' '.join(missing)}\n")
        
        # Cloudflare
        cloudflare.get_cf_clearance()
        
    else:
        # Mode normal (nouveau téléchargement)
        
        # Vérification dépendances
        missing = []
        if not TQDM_OK:        missing.append("tqdm")
        if not QUESTIONARY_OK: missing.append("questionary")
        if not CURL_OK:        missing.append("curl_cffi")
        if missing:
            print(f"  \033[93m⚠️  Installe dépendances:\033[0m py -m pip install {' '.join(missing)}\n")

        # ── Résolution Cloudflare en premier ──
        cloudflare.get_cf_clearance()

        langue = select_langue()
        common_name, seasons_plan = flow_search(langue)

        if not confirm_recap(common_name, seasons_plan, langue):
            print("  ↩️   Relance le script pour corriger.\n")
            return

        if QUESTIONARY_OK:
            auto_detect = questionary.confirm(
                "Auto-détecter les épisodes pour chaque saison ? (recommandé)",
                default=True, style=CUSTOM_STYLE).ask()
        else:
            auto_detect = ask("Auto-détecter les épisodes ? [o/n]", "o").lower() == "o"

        if QUESTIONARY_OK:
            dry_run = questionary.confirm("Afficher la liste avant de télécharger ?",
                default=False, style=CUSTOM_STYLE).ask()
        else:
            dry_run = ask("Afficher la liste avant de télécharger ? [o/n]", "n").lower() == "o"

        if dry_run:
            print(f"\n  \033[96m{'─'*60}\033[0m")
            print(f"  📋  Plan de téléchargement :\n")
            for s in sorted(seasons_plan, key=lambda x: x["saison"]):
                print(f"    Season {zpad(s['saison'])}  ←  {s['anime_slug']}")
            print(f" \033[96m{'─'*60}\033[0m\n")
            if QUESTIONARY_OK:
                go = questionary.confirm("Lancer le téléchargement ?",
                    default=True, style=CUSTOM_STYLE).ask()
            else:
                go = ask("Lancer ? [o/n]", "o").lower() == "o"
            if not go:
                print("  Annulé.")
                return
        
        # Créer la session
        session = DownloadSession(common_name, langue, seasons_plan)
        if QUESTIONARY_OK:
            go = questionary.confirm("Lancer le téléchargement ?",
                default=True, style=CUSTOM_STYLE).ask()
        else:
            go = ask("Lancer ? [o/n]", "o").lower() == "o"
        if not go:
            print("  Annulé.")
            return

    # ── Initialisation du pool de drivers ──
    driver_pool = DriverPool(MAX_WORKERS)
    
    # ── Scanner les épisodes de toutes les saisons en auto-detect ──
    print(f"\n  \033[96m{'━'*60}\033[0m")
    print(f"  🔍  Scan des saisons...")
    print(f"  \033[96m{'━'*60}\033[0m")
    
    for s in sorted(seasons_plan, key=lambda x: x["saison"]):
        if auto_detect:
            print(f"\n  🔍  S{zpad(s['saison'])} - Scan de {s['anime_slug']} ({langue.upper()})...")
            episodes_raw, episode_slug = scrape_episode_list(driver_pool, s["anime_slug"], langue)
            if episodes_raw:
                print(f"  ✅  {len(episodes_raw)} épisode(s) détecté(s) !")
                s["episodes"] = episodes_raw
                s["episode_slug"] = episode_slug
            else:
                print(f"  ⚠️  Scan échoué pour S{zpad(s['saison'])}, saisie manuelle requise.")
                if QUESTIONARY_OK:
                    ep_debut = int(questionary.text(
                        f"[S{zpad(s['saison'])}] Épisode de départ ?", 
                        default="1", style=CUSTOM_STYLE).ask())
                    ep_fin = int(questionary.text(
                        f"[S{zpad(s['saison'])}] Épisode de fin ?", 
                        default="13", style=CUSTOM_STYLE).ask())
                else:
                    ep_debut = int(ask(f"[S{zpad(s['saison'])}] Épisode de départ", "1"))
                    ep_fin = int(ask(f"[S{zpad(s['saison'])}] Épisode de fin", "13"))
                
                episode_slug = s["anime_slug"]
                episodes = []
                for ep in range(ep_debut, ep_fin + 1):
                    url = f"{BASE_URL}/{s['anime_slug']}/{episode_slug}-{zpad(ep)}-{langue}/"
                    episodes.append((ep, url))
                s["episodes"] = episodes
                s["episode_slug"] = episode_slug
        else:
            # Mode manuel
            if QUESTIONARY_OK:
                ep_debut = int(questionary.text(
                    f"[S{zpad(s['saison'])}] Épisode de départ ?", 
                    default="1", style=CUSTOM_STYLE).ask())
                ep_fin = int(questionary.text(
                    f"[S{zpad(s['saison'])}] Épisode de fin ?", 
                    default="13", style=CUSTOM_STYLE).ask())
            else:
                ep_debut = int(ask(f"[S{zpad(s['saison'])}] Épisode de départ", "1"))
                ep_fin = int(ask(f"[S{zpad(s['saison'])}] Épisode de fin", "13"))
            
            episode_slug = s["anime_slug"]
            episodes = []
            for ep in range(ep_debut, ep_fin + 1):
                url = f"{BASE_URL}/{s['anime_slug']}/{episode_slug}-{zpad(ep)}-{langue}/"
                episodes.append((ep, url))
            s["episodes"] = episodes
            s["episode_slug"] = episode_slug

    # ── Calculer le nombre total d'épisodes ──
    total_episodes = sum(len(s.get("episodes", [])) for s in seasons_plan)
    
    # ── Créer le tracker de progression ──
    progress_tracker = create_progress_tracker(total_episodes, len(seasons_plan))

    try:
        total_ok, total_fail = 0, 0
        total_size = 0
        results_summary = []

        for s in sorted(seasons_plan, key=lambda x: x["saison"]):
            print(f"\n  \033[96m{'━'*60}\033[0m")
            print(f"  📦  Saison {s['saison']} — {s['anime_slug']}")
            print(f"  \033[96m{'━'*60}\033[0m")
            
            ok, fail, size = download_season(
                driver_pool,
                common_name,
                s["anime_slug"],
                s["saison"],
                langue,
                s.get("episodes", []),
                s.get("episode_slug", s["anime_slug"]),
                progress_tracker,
                session  # Passer la session
            )
            total_ok += ok
            total_fail += fail
            total_size += size
            results_summary.append((s["saison"], ok, fail))

    finally:
        driver_pool.close_all()
        progress_tracker.finish()
        
        # Marquer la session comme terminée
        if session:
            session.complete_session()

    # ── Bilan final ──
    stats = progress_tracker.get_stats()
    print(f"\n  \033[92m{'━'*60}\033[0m")
    print(f"  🎉  Terminé !\n")
    for saison_num, ok, fail in results_summary:
        status = "✅" if fail == 0 else "⚠️ "
        print(f"    {status}  Season {zpad(saison_num)}  │  {ok} téléchargé(s)  │  {fail} erreur(s)")
    print(f"\n  📊  Total : {stats['success']} téléchargé(s)  |  {stats['fail']} erreur(s)")
    print(f"  💾  Taille : {stats.get('total_size_formatted', 'N/A')}")
    print(f"  ⏱️   Durée : {stats.get('total_time_formatted', 'N/A')}")
    print(f"  ⚡  Vitesse moy. : {stats.get('avg_speed_formatted', 'N/A')}")
    print(f"  📁  {os.path.join(OUTPUT_DIR, sanitize(common_name))}")
    print(f"  📝  Log : {LOG_FILE}")
    print(f"  \033[92m{'━'*60}\033[0m\n")

if __name__ == "__main__":
    main()

