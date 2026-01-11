import json
import re
from pathlib import Path
from collections import defaultdict
import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime
import hashlib
import os

# Configuration de base
def main():
    # Initialisation de la session
    if "page" not in st.session_state:
        st.session_state.page = "login"

    # Configuration de la page
    st.set_page_config(page_title="OPR Army Builder FR", layout="centered")

    # Définir les chemins
    BASE_DIR = Path(__file__).resolve().parent
    FACTIONS_DIR = BASE_DIR / "lists" / "data" / "factions"
    SAVE_DIR = BASE_DIR / "saves"
    PLAYERS_DIR = BASE_DIR / "players"

    # Créer les dossiers s'ils n'existent pas
    SAVE_DIR.mkdir(exist_ok=True, parents=True)
    PLAYERS_DIR.mkdir(exist_ok=True, parents=True)

    # Règles spécifiques par jeu
    GAME_RULES = {
        "Age of Fantasy": {
            "hero_per_points": 375,
            "unit_copies": {750: 1},
            "max_unit_percentage": 35,
            "unit_per_points": 150,
        }
    }

    # Initialisation de l'état de la session
    def init_session_state():
        defaults = {
            "game": None,
            "faction": None,
            "points": 1000,
            "list_name": "",
            "army_list": [],
            "army_total_cost": 0,
            "is_army_valid": True,
            "validation_errors": [],
            "current_player": None,
            "player_army_lists": [],
            "units": []
        }
        for key, default in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = default

    init_session_state()

    @st.cache_data
    def load_factions():
        try:
            faction_files = list(FACTIONS_DIR.glob("*.json"))
            factions = []

            for fp in faction_files:
                try:
                    with open(fp, encoding="utf-8") as f:
                        data = json.load(f)
                        factions.append({
                            "name": data["faction"],
                            "game": data["game"],
                            "file": fp
