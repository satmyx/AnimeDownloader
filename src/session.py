#!/usr/bin/env python3
"""
Gestion des sessions de téléchargement - Sauvegarde/Reprise
"""

import os
import json
from datetime import datetime
from src.config import LOG_DIR
from src.utils import sanitize

# ─────────────────────────────────────────
# CHEMINS
# ─────────────────────────────────────────
SESSION_DIR = os.path.join(LOG_DIR, "sessions")
os.makedirs(SESSION_DIR, exist_ok=True)

# ─────────────────────────────────────────
# CLASSE SESSION
# ─────────────────────────────────────────
class DownloadSession:
    """Gère la sauvegarde et reprise d'une session de téléchargement"""
    
    def __init__(self, anime_name, langue, seasons_plan):
        """
        Initialise une nouvelle session
        
        Args:
            anime_name: Nom de l'anime
            langue: vf ou vostfr
            seasons_plan: Liste des saisons planifiées
        """
        self.anime_name = anime_name
        self.langue = langue
        self.seasons_plan = seasons_plan
        
        # Identifiant unique basé sur le nom et la date
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_id = f"{sanitize(anime_name)}_{langue}_{timestamp}"
        self.session_file = os.path.join(SESSION_DIR, f"{self.session_id}.json")
        
        # État de la session
        self.start_time = datetime.now().isoformat()
        self.last_update = self.start_time
        self.status = "in_progress"
        
        # Progression par saison
        self.seasons_progress = {}
        for s in seasons_plan:
            saison_num = s["saison"]
            self.seasons_progress[saison_num] = {
                "anime_slug": s["anime_slug"],
                "episodes_completed": [],
                "episodes_failed": [],
                "episodes_skipped": [],  # Déjà téléchargés avant cette session
                "total_episodes": 0,
                "start_time": None,
                "end_time": None,
                "status": "pending"  # pending, in_progress, completed, failed
            }
    
    def update_season_start(self, saison_num, total_episodes):
        """Marque le début du téléchargement d'une saison"""
        if saison_num in self.seasons_progress:
            self.seasons_progress[saison_num]["total_episodes"] = total_episodes
            self.seasons_progress[saison_num]["start_time"] = datetime.now().isoformat()
            self.seasons_progress[saison_num]["status"] = "in_progress"
            self.save()
    
    def update_episode_completed(self, saison_num, episode_num):
        """Marque un épisode comme téléchargé avec succès"""
        if saison_num in self.seasons_progress:
            completed = self.seasons_progress[saison_num]["episodes_completed"]
            if episode_num not in completed:
                completed.append(episode_num)
            # Retirer des failed si présent
            if episode_num in self.seasons_progress[saison_num]["episodes_failed"]:
                self.seasons_progress[saison_num]["episodes_failed"].remove(episode_num)
            self.save()
    
    def update_episode_failed(self, saison_num, episode_num):
        """Marque un épisode comme échoué"""
        if saison_num in self.seasons_progress:
            failed = self.seasons_progress[saison_num]["episodes_failed"]
            if episode_num not in failed:
                failed.append(episode_num)
            self.save()
    
    def update_episode_skipped(self, saison_num, episode_num):
        """Marque un épisode comme déjà présent (skippé)"""
        if saison_num in self.seasons_progress:
            skipped = self.seasons_progress[saison_num]["episodes_skipped"]
            if episode_num not in skipped:
                skipped.append(episode_num)
            self.save()
    
    def update_season_end(self, saison_num, success_count, fail_count):
        """Marque la fin du téléchargement d'une saison"""
        if saison_num in self.seasons_progress:
            self.seasons_progress[saison_num]["end_time"] = datetime.now().isoformat()
            if fail_count == 0:
                self.seasons_progress[saison_num]["status"] = "completed"
            elif success_count > 0:
                self.seasons_progress[saison_num]["status"] = "partial"
            else:
                self.seasons_progress[saison_num]["status"] = "failed"
            self.save()
    
    def complete_session(self):
        """Marque la session comme terminée"""
        self.status = "completed"
        self.last_update = datetime.now().isoformat()
        self.save()
        print(f"\n  💾  Session sauvegardée: {self.session_file}")
    
    def save(self):
        """Sauvegarde l'état actuel de la session"""
        self.last_update = datetime.now().isoformat()
        data = {
            "session_id": self.session_id,
            "anime_name": self.anime_name,
            "langue": self.langue,
            "seasons_plan": self.seasons_plan,
            "seasons_progress": self.seasons_progress,
            "start_time": self.start_time,
            "last_update": self.last_update,
            "status": self.status
        }
        
        try:
            with open(self.session_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"  ⚠️  Erreur sauvegarde session: {e}")
    
    def get_episodes_to_download(self, saison_num, all_episodes):
        """
        Retourne la liste des épisodes à télécharger pour une saison
        (exclut les épisodes déjà complétés)
        
        Args:
            saison_num: Numéro de saison
            all_episodes: Liste complète des épisodes [(num, url), ...]
        
        Returns:
            Liste des épisodes restants à télécharger
        """
        if saison_num not in self.seasons_progress:
            return all_episodes
        
        completed = set(self.seasons_progress[saison_num]["episodes_completed"])
        return [(num, url) for num, url in all_episodes if num not in completed]
    
    def get_failed_episodes(self, saison_num):
        """Retourne la liste des épisodes en échec pour une saison"""
        if saison_num in self.seasons_progress:
            return self.seasons_progress[saison_num]["episodes_failed"]
        return []
    
    def print_summary(self):
        """Affiche un résumé de la session"""
        print(f"\n  📊  Résumé de la session: {self.anime_name}")
        print(f"  🆔  ID: {self.session_id}")
        print(f"  🌐  Langue: {self.langue.upper()}")
        print(f"  ⏰  Démarré: {self.start_time}")
        print(f"  🔄  Dernière MAJ: {self.last_update}")
        print(f"\n  📦  Progression par saison:")
        
        for saison_num in sorted(self.seasons_progress.keys()):
            prog = self.seasons_progress[saison_num]
            total = prog["total_episodes"]
            completed = len(prog["episodes_completed"])
            failed = len(prog["episodes_failed"])
            skipped = len(prog["episodes_skipped"])
            
            status_icon = {
                "pending": "⏳",
                "in_progress": "🔄",
                "completed": "✅",
                "partial": "⚠️",
                "failed": "❌"
            }.get(prog["status"], "❓")
            
            print(f"    {status_icon}  Saison {saison_num:02d}: {completed}/{total} téléchargés")
            if failed > 0:
                print(f"         ❌ {failed} échec(s): {prog['episodes_failed']}")
            if skipped > 0:
                print(f"         ⏭️  {skipped} déjà présent(s)")

# ─────────────────────────────────────────
# GESTION DES SESSIONS
# ─────────────────────────────────────────
def list_sessions():
    """Liste toutes les sessions sauvegardées"""
    sessions = []
    if not os.path.exists(SESSION_DIR):
        return sessions
    
    for filename in os.listdir(SESSION_DIR):
        if filename.endswith('.json'):
            filepath = os.path.join(SESSION_DIR, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    sessions.append({
                        "file": filepath,
                        "session_id": data.get("session_id"),
                        "anime_name": data.get("anime_name"),
                        "langue": data.get("langue"),
                        "status": data.get("status"),
                        "last_update": data.get("last_update"),
                        "data": data
                    })
            except Exception as e:
                print(f"  ⚠️  Erreur lecture {filename}: {e}")
    
    # Trier par date (plus récent en premier)
    sessions.sort(key=lambda x: x.get("last_update", ""), reverse=True)
    return sessions

def load_session(session_file):
    """
    Charge une session depuis un fichier
    
    Args:
        session_file: Chemin du fichier de session
    
    Returns:
        DownloadSession ou None
    """
    try:
        with open(session_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Recréer l'objet session
        session = DownloadSession(
            data["anime_name"],
            data["langue"],
            data["seasons_plan"]
        )
        
        # Restaurer l'état
        session.session_id = data["session_id"]
        session.session_file = session_file
        session.start_time = data["start_time"]
        session.last_update = data["last_update"]
        session.status = data["status"]
        session.seasons_progress = data["seasons_progress"]
        
        return session
    except Exception as e:
        print(f"  ❌  Erreur chargement session: {e}")
        return None

def find_incomplete_sessions():
    """Trouve toutes les sessions incomplètes (à reprendre)"""
    sessions = list_sessions()
    return [s for s in sessions if s["status"] in ["in_progress", "partial"]]

def delete_session(session_file):
    """Supprime un fichier de session"""
    try:
        if os.path.exists(session_file):
            os.remove(session_file)
            print(f"  🗑️   Session supprimée: {os.path.basename(session_file)}")
            return True
    except Exception as e:
        print(f"  ❌  Erreur suppression: {e}")
    return False
