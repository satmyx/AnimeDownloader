#!/usr/bin/env python3
"""
Progress Tracker - monitoring avancé avec barres de progression
"""

import time
from src.utils import format_time, format_size, format_speed, zpad

try:
    from tqdm import tqdm
    TQDM_OK = True
except ImportError:
    TQDM_OK = False

# ─────────────────────────────────────────
# PROGRESS TRACKER
# ─────────────────────────────────────────
class ProgressTracker:
    """
    Tracker de progression avancé avec barres de progression globale et par saison
    
    Features:
    - Barre de progression globale (tous épisodes)
    - Barre de progression par saison (épisode actuel)
    - Calcul ETA basé sur vitesse réelle
    - Statistiques de vitesse de téléchargement
    - Compteurs de succès/échecs
    """
    
    def __init__(self, total_episodes, seasons_count):
        """
        Initialise le tracker
        
        Args:
            total_episodes: Nombre total d'épisodes à télécharger
            seasons_count: Nombre de saisons
        """
        self.total_episodes = total_episodes
        self.seasons_count = seasons_count
        self.tqdm_available = TQDM_OK
        
        # Statistiques globales
        self.global_success = 0
        self.global_fail = 0
        self.global_downloaded = 0
        self.total_bytes = 0
        self.start_time = time.time()
        
        # Statistiques par saison
        self.current_season = None
        self.season_episodes_total = 0
        self.season_success = 0
        self.season_fail = 0
        self.season_start_time = None
        self.season_bytes = 0
        
        # Barres de progression
        self.global_bar = None
        self.season_bar = None
        
        # Initialisation de la barre globale
        if self.tqdm_available:
            self.global_bar = tqdm(
                total=total_episodes,
                desc=f"🌍 Global ({seasons_count} saison(s))",
                unit="ep",
                ncols=100,
                colour="green",
                position=0,
                leave=True,
                bar_format='{desc}: {percentage:3.0f}%|{bar}| {n}/{total} [{elapsed}<{remaining}, {rate_fmt}]'
            )
    
    def start_season(self, season_num, episodes_count):
        """
        Démarre le tracking d'une nouvelle saison
        
        Args:
            season_num: Numéro de la saison
            episodes_count: Nombre d'épisodes dans cette saison
        """
        self.current_season = season_num
        self.season_episodes_total = episodes_count
        self.season_success = 0
        self.season_fail = 0
        self.season_start_time = time.time()
        self.season_bytes = 0
        
        if self.tqdm_available and self.season_bar is None:
            self.season_bar = tqdm(
                total=episodes_count,
                desc=f"📦 Saison {zpad(season_num)}",
                unit="ep",
                ncols=100,
                colour="cyan",
                position=1,
                leave=False,
                bar_format='{desc}: {percentage:3.0f}%|{bar}| {n}/{total} [{elapsed}<{remaining}] {postfix}'
            )
    
    def update_episode(self, event_type, ep_num, label, *args, **kwargs):
        """
        Met à jour la progression d'un épisode
        
        Args:
            event_type: Type d'événement ('start', 'downloading', 'success', 'error')
            ep_num: Numéro de l'épisode
            label: Label de l'épisode (ex: S01E05)
            *args, **kwargs: Arguments additionnels selon le type d'événement
        """
        if event_type == 'start':
            if self.season_bar:
                self.season_bar.set_postfix_str(f"🔍 {label}")
        
        elif event_type == 'downloading':
            player_num = args[0] if len(args) > 0 else 1
            player_total = args[1] if len(args) > 1 else 1
            if self.season_bar:
                self.season_bar.set_postfix_str(f"⬇️  {label} (player {player_num}/{player_total})")
        
        elif event_type == 'success':
            file_size = kwargs.get('file_size', 0)
            self.season_bytes += file_size
            self.total_bytes += file_size
            
            # Calculer la vitesse
            elapsed = time.time() - self.season_start_time
            speed = self.season_bytes / elapsed if elapsed > 0 else 0
            
            if self.season_bar:
                self.season_bar.set_postfix_str(
                    f"✅ {label} ({format_size(file_size)}) • {format_speed(speed)}"
                )
        
        elif event_type == 'error':
            if self.season_bar:
                self.season_bar.set_postfix_str(f"❌ {label}")
    
    def update_season_progress(self, success, fail):
        """
        Met à jour la progression de la saison et globale
        
        Args:
            success: Nombre de succès dans la saison
            fail: Nombre d'échecs dans la saison
        """
        # Mise à jour saison
        if self.season_bar:
            completed = success + fail
            if completed > self.season_bar.n:
                self.season_bar.update(completed - self.season_bar.n)
                
                # Calculer statistiques
                elapsed = time.time() - self.season_start_time
                avg_speed = self.season_bytes / elapsed if elapsed > 0 else 0
                
                postfix = {
                    "✅": success,
                    "❌": fail,
                    "⚡": format_speed(avg_speed)
                }
                self.season_bar.set_postfix(postfix)
        
        # Mise à jour globale
        if self.global_bar:
            total_completed = success + fail
            global_completed = self.global_downloaded + total_completed
            if global_completed > self.global_bar.n:
                self.global_bar.update(global_completed - self.global_bar.n)
                
                # Statistiques globales
                global_elapsed = time.time() - self.start_time
                global_speed = self.total_bytes / global_elapsed if global_elapsed > 0 else 0
                
                postfix = {
                    "✅": self.global_success + success,
                    "❌": self.global_fail + fail,
                    "💾": format_size(self.total_bytes),
                    "⚡": format_speed(global_speed)
                }
                self.global_bar.set_postfix(postfix)
    
    def finish_season(self, season_num, success, fail):
        """
        Termine le tracking d'une saison
        
        Args:
            season_num: Numéro de la saison
            success: Nombre de succès
            fail: Nombre d'échecs
        """
        self.global_success += success
        self.global_fail += fail
        self.global_downloaded += (success + fail)
        
        # Fermer la barre de saison
        if self.season_bar:
            # Statistiques finales de la saison
            elapsed = time.time() - self.season_start_time
            avg_speed = self.season_bytes / elapsed if elapsed > 0 else 0
            
            # Afficher le résumé final
            status = "✅" if fail == 0 else "⚠️"
            self.season_bar.set_description(
                f"{status} Saison {zpad(season_num)} terminée"
            )
            self.season_bar.set_postfix({
                "✅": success,
                "❌": fail,
                "💾": format_size(self.season_bytes),
                "⏱️": format_time(elapsed),
                "⚡": format_speed(avg_speed)
            })
            self.season_bar.close()
            self.season_bar = None
        
        # Réinitialiser les stats de saison
        self.current_season = None
        self.season_bytes = 0
        
        print()  # Ligne vide pour séparer les saisons
    
    def finish(self):
        """Termine le tracking global"""
        if self.global_bar:
            total_elapsed = time.time() - self.start_time
            avg_speed = self.total_bytes / total_elapsed if total_elapsed > 0 else 0
            
            # Stats finales
            self.global_bar.set_description("🎉 Téléchargement terminé")
            self.global_bar.set_postfix({
                "✅": self.global_success,
                "❌": self.global_fail,
                "💾": format_size(self.total_bytes),
                "⏱️": format_time(total_elapsed),
                "⚡": format_speed(avg_speed)
            })
            self.global_bar.close()
    
    def get_stats(self):
        """
        Retourne les statistiques de téléchargement
        
        Returns:
            dict: Dictionnaire avec les statistiques
        """
        total_elapsed = time.time() - self.start_time
        avg_speed = self.total_bytes / total_elapsed if total_elapsed > 0 else 0
        
        return {
            'total_episodes': self.total_episodes,
            'success': self.global_success,
            'fail': self.global_fail,
            'total_bytes': self.total_bytes,
            'total_time': total_elapsed,
            'avg_speed': avg_speed,
            'total_size_formatted': format_size(self.total_bytes),
            'total_time_formatted': format_time(total_elapsed),
            'avg_speed_formatted': format_speed(avg_speed)
        }

# ─────────────────────────────────────────
# FALLBACK SANS TQDM
# ─────────────────────────────────────────
class SimpleProgressTracker:
    """Tracker simple sans tqdm (fallback)"""
    
    def __init__(self, total_episodes, seasons_count):
        self.total_episodes = total_episodes
        self.global_success = 0
        self.global_fail = 0
        self.start_time = time.time()
        self.total_bytes = 0
        print(f"\n📊 Téléchargement de {total_episodes} épisode(s) sur {seasons_count} saison(s)\n")
    
    def start_season(self, season_num, episodes_count):
        print(f"\n📦 Saison {zpad(season_num)} — {episodes_count} épisode(s)")
        self.season_start = time.time()
        self.season_bytes = 0
    
    def update_episode(self, event_type, ep_num, label, *args, **kwargs):
        if event_type == 'success':
            self.season_bytes += kwargs.get('file_size', 0)
            self.total_bytes += kwargs.get('file_size', 0)
    
    def update_season_progress(self, success, fail):
        pass
    
    def finish_season(self, season_num, success, fail):
        self.global_success += success
        self.global_fail += fail
        elapsed = time.time() - self.season_start
        print(f"  ✅ Saison {zpad(season_num)}: {success} OK, {fail} KO, {format_time(elapsed)}")
    
    def finish(self):
        elapsed = time.time() - self.start_time
        print(f"\n🎉 Terminé: {self.global_success} OK, {self.global_fail} KO")
        print(f"   💾 {format_size(self.total_bytes)} en {format_time(elapsed)}")
    
    def get_stats(self):
        elapsed = time.time() - self.start_time
        return {
            'success': self.global_success,
            'fail': self.global_fail,
            'total_bytes': self.total_bytes,
            'total_time': elapsed
        }

def create_progress_tracker(total_episodes, seasons_count):
    """
    Factory pour créer le bon type de tracker
    
    Args:
        total_episodes: Nombre total d'épisodes
        seasons_count: Nombre de saisons
    
    Returns:
        ProgressTracker ou SimpleProgressTracker
    """
    if TQDM_OK:
        return ProgressTracker(total_episodes, seasons_count)
    else:
        return SimpleProgressTracker(total_episodes, seasons_count)
