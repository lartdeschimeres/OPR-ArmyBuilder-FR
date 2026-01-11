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
                        })
                except Exception as e:
                    st.warning(f"Impossible de lire {fp.name} : {e}")

            games = sorted(set(f["game"] for f in factions))
            return factions, games
        except Exception as e:
            st.error(f"Erreur lors du chargement des factions: {str(e)}")
            return [], []

    factions, games = load_factions()

    # Fonctions pour la gestion des comptes joueurs
    def hash_password(password):
        return hashlib.sha256(password.encode()).hexdigest()

    def create_player(username, password):
        player_file = PLAYERS_DIR / f"{username}.json"
        if player_file.exists():
            return False, "Ce nom d'utilisateur existe déjà"

        player_data = {
            "username": username,
            "password": hash_password(password),
            "army_lists": []
        }

        try:
            with open(player_file, "w", encoding="utf-8") as f:
                json.dump(player_data, f, ensure_ascii=False, indent=2)
            return True, "Compte créé avec succès"
        except Exception as e:
            return False, f"Erreur lors de la création du compte: {str(e)}"

    def verify_player(username, password):
        player_file = PLAYERS_DIR / f"{username}.json"
        if not player_file.exists():
            return False, "Nom d'utilisateur ou mot de passe incorrect"

        try:
            with open(player_file, encoding="utf-8") as f:
                player_data = json.load(f)

            if player_data["password"] != hash_password(password):
                return False, "Nom d'utilisateur ou mot de passe incorrect"

            return True, "Connexion réussie"
        except Exception as e:
            return False, f"Erreur lors de la vérification: {str(e)}"

    def load_player_army_lists(username):
        player_file = PLAYERS_DIR / f"{username}.json"
        if not player_file.exists():
            return []

        try:
            with open(player_file, encoding="utf-8") as f:
                player_data = json.load(f)
            return player_data.get("army_lists", [])
        except Exception as e:
            st.error(f"Erreur lors du chargement des listes: {str(e)}")
            return []

    def save_player_army_list(username, army_list_data):
        player_file = PLAYERS_DIR / f"{username}.json"
        if not player_file.exists():
            return False

        try:
            with open(player_file, encoding="utf-8") as f:
                player_data = json.load(f)

            player_data["army_lists"].append(army_list_data)

            with open(player_file, "w", encoding="utf-8") as f:
                json.dump(player_data, f, ensure_ascii=False, indent=2)

            return True
        except Exception as e:
            st.error(f"Erreur lors de la sauvegarde: {str(e)}")
            return False

    def delete_player_army_list(username, list_index):
        player_file = PLAYERS_DIR / f"{username}.json"
        if not player_file.exists():
            return False

        try:
            with open(player_file, encoding="utf-8") as f:
                player_data = json.load(f)

            if list_index < 0 or list_index >= len(player_data["army_lists"]):
                return False

            player_data["army_lists"].pop(list_index)

            with open(player_file, "w", encoding="utf-8") as f:
                json.dump(player_data, f, ensure_ascii=False, indent=2)

            return True
        except Exception as e:
            st.error(f"Erreur lors de la suppression: {str(e)}")
            return False

    def calculate_coriace_value(unit_data):
        """Calcule la valeur totale de Coriace pour une unité"""
        coriace_value = 0

        # 1. Vérifier la valeur de base de Coriace
        if 'coriace' in unit_data:
            coriace_value += unit_data['coriace']

        # 2. Vérifier dans les règles spéciales
        if 'base_rules' in unit_data:
            for rule in unit_data['base_rules']:
                if isinstance(rule, str):
                    match = re.search(r'Coriace $(\d+)$', rule)
                    if match:
                        coriace_value += int(match.group(1))

        # 3. Vérifier dans les options
        if 'options' in unit_data:
            for option_group in unit_data['options'].values():
                if isinstance(option_group, list):
                    for option in option_group:
                        if isinstance(option, dict) and 'special_rules' in option:
                            for rule in option['special_rules']:
                                if isinstance(rule, str):
                                    match = re.search(r'Coriace $(\d+)$', rule)
                                    if match:
                                        coriace_value += int(match.group(1))
                elif isinstance(option_group, dict) and 'special_rules' in option_group:
                    for rule in option_group['special_rules']:
                        if isinstance(rule, str):
                            match = re.search(r'Coriace $(\d+)$', rule)
                            if match:
                                coriace_value += int(match.group(1))

        # 4. Vérifier dans l'arme équipée
        if 'current_weapon' in unit_data and 'special_rules' in unit_data['current_weapon']:
            for rule in unit_data['current_weapon']['special_rules']:
                if isinstance(rule, str):
                    match = re.search(r'Coriace $(\d+)$', rule)
                    if match:
                        coriace_value += int(match
