#!/usr/bin/env python3
"""
Pool de drivers SeleniumBase UC pour VoirAnime
"""

from queue import Queue
from seleniumbase import Driver
from src.config import HEADLESS_MODE

# ─────────────────────────────────────────
# POOL DE DRIVERS
# ─────────────────────────────────────────
class DriverPool:
    """Pool de drivers SeleniumBase réutilisables"""
    
    def __init__(self, size):
        self.size = size
        self.pool = Queue()
        self._initialized = False
    
    def initialize(self):
        """Initialise le pool de drivers"""
        if self._initialized:
            return
        
        print(f"  ⚙️   Initialisation du pool ({self.size} drivers UC)...", end=" ", flush=True)
        for _ in range(self.size):
            self.pool.put(self._make_driver())
        print("\033[92m✓\033[0m\n")
        self._initialized = True
    
    def _make_driver(self):
        """Crée un nouveau driver"""
        return Driver(uc=True, headless=HEADLESS_MODE)
    
    def get(self):
        """Récupère un driver du pool"""
        if not self._initialized:
            self.initialize()
        return self.pool.get()
    
    def release(self, driver):
        """Remet un driver dans le pool"""
        self.pool.put(driver)
    
    def close_all(self):
        """Ferme tous les drivers du pool"""
        if not self._initialized:
            return
            
        print("\n  ⚙️   Fermeture des drivers...", end=" ", flush=True)
        while not self.pool.empty():
            try:
                driver = self.pool.get_nowait()
                driver.quit()
            except Exception:
                pass
        print("\033[92m✓\033[0m")
        self._initialized = False
