
#!/usr/bin/env python3
"""
Setup VoirAnime Downloader V2
Lance ce script une seule fois avant d'utiliser voiranime_dl_v2.py
"""

import subprocess
import sys
import os

DEPS = [
    "selenium",
    "chromedriver-autoinstall",
    "yt-dlp",
    "tqdm",
    "questionary",
    "requests",
    "beautifulsoup4",
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

    if fail:
        print(f"  ❌  {len(fail)} échec(s) : {', '.join(fail)}")
        print(f"\n  Réessaie manuellement :")
        for f in fail:
            print(f"    py -m pip install {f}")
    else:
        print(f"\n  🎉  Tout est prêt ! Lance maintenant :")
        print(f"      py voiranime_dl_v2.py")

    print(f"{'━'*46}\n")

if __name__ == "__main__":
    main()
