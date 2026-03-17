
#!/usr/bin/env python3
"""
Setup VoirAnime Downloader V2
Lance ce script une seule fois avant d'utiliser voiranime_dl_v2.py
"""

import subprocess
import sys
import os

DEPS = [
    "seleniumbase",      # Automation navigateur avec UC (undetected-chromedriver)
    "yt-dlp",            # Extraction vidéo des players
    "tqdm",              # Barres de progression
    "questionary",       # Menus interactifs
    "curl_cffi",         # Requêtes HTTP avec browser impersonation
]

def install(package):
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--upgrade", package],
        capture_output=True, text=True
    )
    return result.returncode == 0

def main():
    print("\n╔══════════════════════════════════════════╗")
    print("║   VoirAnime Downloader V2 — Setup        ║")
    print("╚══════════════════════════════════════════╝\n")

    print(f"  Python détecté : {sys.version.split()[0]}")
    print(f"  {len(DEPS)} dépendances à installer...\n")

    ok, fail = [], []

    for dep in DEPS:
        print(f"  ⬇️  Installation de {dep}...", end=" ", flush=True)
        if install(dep):
            print("✅")
            ok.append(dep)
        else:
            print("❌")
            fail.append(dep)

    print(f"\n{'━'*46}")
    print(f"  ✅  {len(ok)} installé(s) avec succès")

    # Créer les dossiers nécessaires
    os.makedirs("logs/sessions", exist_ok=True)
    print(f"  📁  Dossiers créés : logs/, logs/sessions/")

    if fail:
        print(f"\n  ❌  {len(fail)} échec(s) : {', '.join(fail)}")
        print(f"\n  Réessaie manuellement :")
        for f in fail:
            print(f"    py -m pip install {f}")
    else:
        print(f"\n  🎉  Tout est prêt ! Lance maintenant :")
        print(f"      py voiranime_dl_v2.py")
        print(f"\n  📖  Commandes disponibles :")
        print(f"      py voiranime_dl_v2.py              → Nouveau téléchargement")
        print(f"      py voiranime_dl_v2.py --resume     → Reprendre une session")
        print(f"      py voiranime_dl_v2.py --list-sessions → Liste des sessions")

    print(f"{'━'*46}\n")

if __name__ == "__main__":
    main()
