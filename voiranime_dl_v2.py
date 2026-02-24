#!/usr/bin/env python3
"""
VoirAnime Downloader V2 - Jellyfin Edition
Utilisation : py voiranime_dl.py
"""

import os, re, sys, time, json, subprocess, logging, requests
from queue import Queue
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

try:
    from tqdm import tqdm
    TQDM_OK = True
except ImportError:
    TQDM_OK = False

try:
    import questionary
    from questionary import Style
    QUESTIONARY_OK = True
except ImportError:
    QUESTIONARY_OK = False

# ─────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────
OUTPUT_DIR  = "D:\\Anime"
MAX_WORKERS = 8
DELAY_PAGE  = 10   # timeout max WebDriverWait (secondes)
LOG_FILE    = os.path.join(os.getcwd(), "voiranime_dl.log")
BASE_URL    = "https://v6.voiranime.com/anime"
AJAX_URL    = "https://v6.voiranime.com/wp-admin/admin-ajax.php"

CUSTOM_STYLE = Style([
    ("qmark",      "fg:#00d7ff bold"),
    ("question",   "fg:#ffffff bold"),
    ("answer",     "fg:#00ff87 bold"),
    ("pointer",    "fg:#00d7ff bold"),
    ("highlighted","fg:#00d7ff bold"),
    ("selected",   "fg:#00ff87"),
    ("separator",  "fg:#444444"),
    ("instruction","fg:#888888"),
])

# ─────────────────────────────────────────
# CHROMEDRIVER CACHE
# ─────────────────────────────────────────
print("  ⚙️   Initialisation ChromeDriver...", end=" ", flush=True)
DRIVER_PATH = ChromeDriverManager().install()
print("\033[92m✓\033[0m")

# ─────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

def log(msg, level="info"):
    print(msg)
    getattr(logging, level)(re.sub(r'[^\x00-\x7F]', '', msg))

# ─────────────────────────────────────────
# UTILS
# ─────────────────────────────────────────
def sanitize(name):
    return re.sub(r'[<>:"/\\|?*]', '', name).strip()

def zpad(n, width=2):
    return str(n).zfill(width)

def clear():
    os.system("cls" if os.name == "nt" else "clear")

def banner():
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
    print("  \033[93m  Jellyfin Edition V2  •  Auto-detect  •  Multi-DL  •  VF / VOSTFR\033[0m")
    print("  \033[90m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m\n")

# ─────────────────────────────────────────
# POOL DE DRIVERS SELENIUM
# ─────────────────────────────────────────
def make_driver(headless=True):
    options = Options()
    if headless:
        options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--log-level=3")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    service = Service(executable_path=DRIVER_PATH)
    return webdriver.Chrome(service=service, options=options)

def build_driver_pool(size):
    print(f"  ⚙️   Initialisation du pool ({size} drivers)...", end=" ", flush=True)
    pool = Queue()
    for _ in range(size):
        pool.put(make_driver())
    print("\033[92m✓\033[0m\n")
    return pool

# Pool global — initialisé dans main() après le banner
DRIVER_POOL = None

def get_driver():
    """Emprunte un driver du pool (bloquant si tous occupés)."""
    return DRIVER_POOL.get()

def release_driver(driver):
    """Rend le driver au pool."""
    DRIVER_POOL.put(driver)

def close_driver_pool():
    """Ferme tous les drivers proprement à la fin."""
    while not DRIVER_POOL.empty():
        d = DRIVER_POOL.get_nowait()
        try:
            d.quit()
        except Exception:
            pass

# ─────────────────────────────────────────
# RECHERCHE AJAX VoirAnime
# ─────────────────────────────────────────
def search_anime(query, langue):
    asid = "3" if langue == "vostfr" else "2"
    payload = {
        "action":      "ajaxsearchpro_search",
        "aspp":        query,
        "asid":        asid,
        "asp_inst_id": f"{asid}_1",
        "options": (
            f"aspf[vf_1]={langue}"
            "&asp_gen[]=excerpt&asp_gen[]=content&asp_gen[]=title"
            "&filters_initial=1&filters_changed=0"
            "&qtranslate_lang=0&current_page_id=0"
        ),
    }
    headers = {
        "User-Agent":       "Mozilla/5.0",
        "X-Requested-With": "XMLHttpRequest",
        "Referer":          "https://v6.voiranime.com/",
    }
    try:
        r = requests.post(AJAX_URL, data=payload, headers=headers, timeout=10)
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
        link  = item.get("link", "")
        title = item.get("title", "")
        slug_m = re.search(r'/anime/([^/]+)/?$', link)
        if slug_m:
            results.append((title, slug_m.group(1)))
    return results

# ─────────────────────────────────────────
# SELENIUM — scraping avec pool + WebDriverWait
# ─────────────────────────────────────────
def scrape_episode_list(anime_slug, langue):
    url    = f"{BASE_URL}/{anime_slug}/"
    driver = get_driver()
    episodes     = []
    episode_slug = anime_slug
    try:
        driver.get(url)
        # Attend que les liens d'épisodes soient présents
        try:
            WebDriverWait(driver, DELAY_PAGE).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "a[href*='-vf'], a[href*='-vostfr']")
                )
            )
        except Exception:
            pass  # timeout → on tente quand même avec ce qui est chargé

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
        release_driver(driver)
    return episodes, episode_slug

def get_all_player_urls(episode_url):
    driver  = get_driver()
    players = []
    try:
        driver.get(episode_url)
        # Attend que thisChapterSources soit injecté dans le DOM
        # ou qu'un iframe soit présent en fallback
        try:
            WebDriverWait(driver, DELAY_PAGE).until(
                lambda d: "thisChapterSources" in d.page_source
                          or len(d.find_elements(By.TAG_NAME, "iframe")) > 0
            )
        except Exception:
            pass

        page_source = driver.page_source

        # Méthode principale : thisChapterSources
        m = re.search(r'var\s+thisChapterSources\s*=\s*(\{.*?\})\s*;', page_source, re.DOTALL)
        if m:
            srcs = re.findall(r'src\s*=\s*["\']([^"\']+)["\']', m.group(1))
            for src in srcs:
                if src.startswith("http") and src not in players:
                    players.append(src)
            if players:
                log(f"  🎬  {len(players)} player(s) via thisChapterSources")

        # Fallback DOM
        if not players:
            log("  ⚠️  Fallback DOM...")
            for iframe in driver.find_elements(By.TAG_NAME, "iframe"):
                src = iframe.get_attribute("src")
                if src and src.startswith("http") and src not in players:
                    players.append(src)
            if players:
                log(f"  🎬  {len(players)} player(s) via DOM")
    finally:
        release_driver(driver)
    return players

# ─────────────────────────────────────────
# YT-DLP
# ─────────────────────────────────────────
def try_download(player_url, output_path):
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
def process_episode(ep_num, ep_url, output_path, anime_clean, saison):
    label = f"S{zpad(saison)}E{zpad(ep_num)}"
    log(f"\n🔍  [{label}] Récupération des players...")
    players = get_all_player_urls(ep_url)
    if not players:
        log(f"  ❌  [{label}] Aucun player trouvé.", "error")
        return False
    for i, player_url in enumerate(players, start=1):
        log(f"  🔗  [{label}] Player {i}/{len(players)} : {player_url[:70]}...")
        success, stderr = try_download(player_url, output_path)
        if success:
            log(f"  ✅  [{label}] Succès (player {i})")
            return True
        else:
            log(f"  ⚠️  [{label}] Player {i} KO — {stderr[:120]}", "warning")
            if os.path.exists(output_path):
                os.remove(output_path)
    log(f"  ❌  [{label}] Tous les players ont échoué.", "error")
    return False

# ─────────────────────────────────────────
# HELPERS MENU
# ─────────────────────────────────────────
def ask(prompt, default=None):
    suffix = f" [{default}]" if default else ""
    val = input(f"  ❯ {prompt}{suffix} : ").strip()
    return val if val else default

def select_langue():
    if QUESTIONARY_OK:
        return questionary.select("Langue ?",
            choices=["vostfr", "vf"], style=CUSTOM_STYLE).ask()
    return ask("Langue [vf/vostfr]", "vostfr")

def select_mode():
    if QUESTIONARY_OK:
        return questionary.select(
            "Mode de sélection de l'anime ?",
            choices=[
                "🔍  Recherche automatique (recommandé)",
                "✏️   Saisie manuelle des slugs",
            ],
            style=CUSTOM_STYLE
        ).ask()
    choice = ask("Mode [1=auto / 2=manuel]", "1")
    return "auto" if choice == "1" else "manuel"

# ─────────────────────────────────────────
# FLOW : recherche automatique multi-saisons
# ─────────────────────────────────────────
def flow_search(langue):
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
                "Sélectionne les saisons à télécharger (espace pour cocher) :",
                choices=choices,
                style=CUSTOM_STYLE
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
# FLOW : saisie manuelle
# ─────────────────────────────────────────
def flow_manual():
    if QUESTIONARY_OK:
        anime_name = questionary.text("Nom de l'anime ?",
            default="Death Note", style=CUSTOM_STYLE).ask()
        anime_slug = questionary.text("Slug URL (page série) ?",
            default=anime_name.lower().replace(" ", "-"), style=CUSTOM_STYLE).ask()
        saison = int(questionary.text("Numéro de saison ?",
            default="1", style=CUSTOM_STYLE).ask())
    else:
        anime_name = ask("Nom de l'anime", "Death Note")
        anime_slug = ask("Slug URL (page série)", anime_name.lower().replace(" ", "-"))
        saison     = int(ask("Numéro de saison", "1"))

    common_name  = sanitize(anime_name)
    seasons_plan = [{"anime_name": anime_name, "anime_slug": anime_slug, "saison": saison}]
    return common_name, seasons_plan

# ─────────────────────────────────────────
# RÉCAP DE CONFIRMATION
# ─────────────────────────────────────────
def confirm_recap(common_name, seasons_plan, langue):
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
# TÉLÉCHARGEMENT D'UNE SAISON
# ─────────────────────────────────────────
def download_season(common_name, anime_slug, saison, langue, auto_detect):
    anime_clean  = sanitize(common_name)
    episode_slug = anime_slug
    episodes_raw = []

    if auto_detect:
        print(f"\n  🔍  Scan S{zpad(saison)} ({anime_slug}) ({langue.upper()})...")
        episodes_raw, episode_slug = scrape_episode_list(anime_slug, langue)
        if episodes_raw:
            print(f"  ✅  {len(episodes_raw)} épisode(s) détecté(s) !")
        else:
            print("  ⚠️  Détection échouée, passage en mode manuel.")

    if not episodes_raw:
        if QUESTIONARY_OK:
            ep_debut = int(questionary.text(
                f"[S{zpad(saison)}] Épisode de départ ?", default="1", style=CUSTOM_STYLE).ask())
            ep_fin   = int(questionary.text(
                f"[S{zpad(saison)}] Épisode de fin ?",    default="13", style=CUSTOM_STYLE).ask())
        else:
            ep_debut = int(ask(f"[S{zpad(saison)}] Épisode de départ", "1"))
            ep_fin   = int(ask(f"[S{zpad(saison)}] Épisode de fin", "13"))

        for ep in range(ep_debut, ep_fin + 1):
            url = f"{BASE_URL}/{anime_slug}/{episode_slug}-{zpad(ep)}-{langue}/"
            episodes_raw.append((ep, url))

    season_dir = os.path.join(OUTPUT_DIR, anime_clean, f"Season {zpad(saison)}")
    os.makedirs(season_dir, exist_ok=True)

    to_download = []
    for ep_num, ep_url in episodes_raw:
        filename = f"{anime_clean} S{zpad(saison)}E{zpad(ep_num)}.mkv"
        path = os.path.join(season_dir, filename)
        if os.path.exists(path):
            print(f"  ⏭️   {filename} déjà présent, skip.")
        else:
            to_download.append((ep_num, ep_url, path))

    if not to_download:
        print(f"  ✅  S{zpad(saison)} — Tous les épisodes déjà téléchargés !")
        return 0, 0

    print(f"\n  \033[92m🚀  S{zpad(saison)} — {len(to_download)} épisode(s) • {MAX_WORKERS} workers\033[0m")
    print(f"  📁  {season_dir}\n")
    log(f"SEASON START | {anime_clean} | S{zpad(saison)} | {langue.upper()} | {len(to_download)} eps")

    progress = tqdm(
        total=len(to_download), unit="ep", ncols=70, colour="cyan",
        desc=f"S{zpad(saison)}"
    ) if TQDM_OK else None

    ok, fail = 0, 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(process_episode, ep_num, ep_url, path, anime_clean, saison): ep_num
            for ep_num, ep_url, path in to_download
        }
        for future in as_completed(futures):
            success = future.result()
            if success: ok += 1
            else:       fail += 1
            if progress:
                progress.update(1)
                progress.set_postfix({"✅": ok, "❌": fail})

    if progress:
        progress.close()

    log(f"SEASON END | S{zpad(saison)} | {ok} succès | {fail} erreurs")
    return ok, fail

# ─────────────────────────────────────────
# MENU PRINCIPAL
# ─────────────────────────────────────────
def main():
    global DRIVER_POOL

    banner()

    missing = []
    if not TQDM_OK:        missing.append("tqdm")
    if not QUESTIONARY_OK: missing.append("questionary")
    if missing:
        print(f"  \033[93m⚠️  Installe les dépendances pour la meilleure expérience :\033[0m")
        print(f"  \033[90m   py -m pip install {' '.join(missing)}\033[0m\n")

    langue = select_langue()
    mode   = select_mode()

    if "Recherche" in mode or mode == "auto":
        common_name, seasons_plan = flow_search(langue)
    else:
        common_name, seasons_plan = flow_manual()

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
        print(f"  \033[96m{'─'*60}\033[0m\n")
        if QUESTIONARY_OK:
            go = questionary.confirm("Lancer le téléchargement ?",
                default=True, style=CUSTOM_STYLE).ask()
        else:
            go = ask("Lancer ? [o/n]", "o").lower() == "o"
        if not go:
            print("  Annulé.")
            return

    # ── Initialisation du pool juste avant le téléchargement ──
    DRIVER_POOL = build_driver_pool(MAX_WORKERS)

    try:
        total_ok, total_fail = 0, 0
        results_summary = []

        for s in sorted(seasons_plan, key=lambda x: x["saison"]):
            print(f"\n  \033[96m{'━'*60}\033[0m")
            print(f"  📦  Saison {s['saison']} — {s['anime_slug']}")
            print(f"  \033[96m{'━'*60}\033[0m")
            ok, fail = download_season(
                common_name, s["anime_slug"], s["saison"], langue, auto_detect
            )
            total_ok   += ok
            total_fail += fail
            results_summary.append((s["saison"], ok, fail))

    finally:
        # Ferme tous les drivers proprement même en cas d'erreur
        print("\n  ⚙️   Fermeture des drivers...", end=" ", flush=True)
        close_driver_pool()
        print("\033[92m✓\033[0m")

    # ── Bilan final ──
    print(f"\n  \033[92m{'━'*60}\033[0m")
    print(f"  🎉  Terminé !\n")
    for saison_num, ok, fail in results_summary:
        status = "✅" if fail == 0 else "⚠️ "
        print(f"    {status}  Season {zpad(saison_num)}  │  {ok} téléchargé(s)  │  {fail} erreur(s)")
    print(f"\n  📊  Total : {total_ok} téléchargé(s)  |  {total_fail} erreur(s)")
    print(f"  📁  {os.path.join(OUTPUT_DIR, sanitize(common_name))}")
    print(f"  📝  Log : {LOG_FILE}")
    print(f"  \033[92m{'━'*60}\033[0m\n")

if __name__ == "__main__":
    main()
