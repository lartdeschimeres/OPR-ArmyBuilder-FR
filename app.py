import json
import re
from pathlib import Path
from collections import defaultdict
import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime
import hashlib
import os

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
    for dir_path in [SAVE_DIR, PLAYERS_DIR, FACTIONS_DIR]:
        dir_path.mkdir(exist_ok=True, parents=True)

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
            "units": [],
            "factions": {},
            "games": []
        }
        for key, default in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = default

    init_session_state()

    @st.cache_data
    def load_factions():
        try:
            factions = {}
            games = set()

            # Charger les factions depuis les fichiers
            faction_files = list(FACTIONS_DIR.glob("*.json"))
            for fp in faction_files:
                try:
                    with open(fp, encoding="utf-8") as f:
                        data = json.load(f)
                        game = data["game"]
                        faction_name = data["faction"]

                        if game not in factions:
                            factions[game] = {}
                        factions[game][faction_name] = data
                        games.add(game)
                except Exception as e:
                    st.warning(f"Impossible de lire {fp.name} : {e}")

            return factions, sorted(games)
        except Exception as e:
            st.error(f"Erreur lors du chargement des factions: {str(e)}")
            return {}, []

    def calculate_coriace_value(unit_data):
        """Calcule la valeur totale de Coriace pour une unité"""
        coriace_value = 0

        try:
            # 1. Vérifier dans les règles spéciales de base
            if 'base_rules' in unit_data:
                for rule in unit_data['base_rules']:
                    if isinstance(rule, str):
                        match = re.search(r'Coriace\s*$(\d+)$', rule)
                        if match:
                            try:
                                coriace_value += int(match.group(1))
                            except:
                                continue

            # 2. Vérifier dans les options
            if 'options' in unit_data:
                for option_group in unit_data['options'].values():
                    try:
                        if isinstance(option_group, list):
                            for option in option_group:
                                if isinstance(option, dict) and 'special_rules' in option:
                                    for rule in option['special_rules']:
                                        if isinstance(rule, str):
                                            match = re.search(r'Coriace\s*$(\d+)$', rule)
                                            if match:
                                                try:
                                                    coriace_value += int(match.group(1))
                                                except:
                                                    continue
                        elif isinstance(option_group, dict) and 'special_rules' in option_group:
                            for rule in option_group['special_rules']:
                                if isinstance(rule, str):
                                    match = re.search(r'Coriace\s*$(\d+)$', rule)
                                    if match:
                                        try:
                                            coriace_value += int(match.group(1))
                                        except:
                                            continue
                    except:
                        continue

            # 3. Vérifier dans la monture
            if 'mount' in unit_data and isinstance(unit_data['mount'], dict) and 'special_rules' in unit_data['mount']:
                for rule in unit_data['mount']['special_rules']:
                    if isinstance(rule, str):
                        match = re.search(r'Coriace\s*$(\d+)$', rule)
                        if match:
                            try:
                                coriace_value += int(match.group(1))
                            except:
                                continue

        except Exception as e:
            st.error(f"Erreur dans calculate_coriace_value: {str(e)}")
            return 0

        return coriace_value

    # Charger les factions au démarrage
    if not st.session_state["factions"] or not st.session_state["games"]:
        st.session_state["factions"], st.session_state["games"] = load_factions()

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

    def validate_army(army_list, game_rules, total_cost, total_points):
        errors = []

        if not army_list:
            errors.append("Aucune unité dans l'armée")
            return False, errors

        if game_rules == GAME_RULES["Age of Fantasy"]:
            heroes = sum(1 for u in army_list if u.get("type", "").lower() == "hero")
            max_heroes = max(1, total_points // game_rules["hero_per_points"])
            if heroes > max_heroes:
                errors.append(f"Trop de héros (max: {max_heroes} pour {total_points} pts)")

            unit_counts = defaultdict(int)
            for unit in army_list:
                unit_counts[unit["name"]] += 1

            max_copies = 1 + (total_points // 750)
            for unit_name, count in unit_counts.items():
                if count > max_copies:
                    errors.append(f"Trop de copies de '{unit_name}' (max: {max_copies})")

            for unit in army_list:
                percentage = (unit["cost"] / total_points) * 100
                if percentage > game_rules["max_unit_percentage"]:
                    errors.append(f"'{unit['name']}' ({unit['cost']} pts) dépasse {game_rules['max_unit_percentage']}% du total ({total_points} pts)")

            max_units = total_points // game_rules["unit_per_points"]
            if len(army_list) > max_units:
                errors.append(f"Trop d'unités (max: {max_units} pour {total_points} pts)")

        return len(errors) == 0, errors

    # PAGE 1 — Connexion/Inscription
    if st.session_state.page == "login":
        st.title("OPR Army Builder 🇫🇷")
        st.subheader("Connexion")

        tab1, tab2 = st.tabs(["Connexion", "Inscription"])

        with tab1:
            username = st.text_input("Nom d'utilisateur")
            password = st.text_input("Mot de passe", type="password")

            if st.button("Se connecter"):
                success, message = verify_player(username, password)
                if success:
                    st.session_state.current_player = username
                    st.session_state.player_army_lists = load_player_army_lists(username)
                    st.session_state.page = "setup"
                    st.rerun()
                else:
                    st.error(message)

        with tab2:
            new_username = st.text_input("Nouveau nom d'utilisateur")
            new_password = st.text_input("Nouveau mot de passe", type="password")
            confirm_password = st.text_input("Confirmer le mot de passe", type="password")

            if new_password != confirm_password:
                st.warning("Les mots de passe ne correspondent pas")

            if st.button("Créer un compte") and new_password == confirm_password:
                success, message = create_player(new_username, new_password)
                st.info(message)
                if success:
                    st.session_state.current_player = new_username
                    st.session_state.page = "setup"
                    st.rerun()

    # PAGE 2 — Configuration de la liste
    elif st.session_state.page == "setup":
        st.title("OPR Army Builder 🇫🇷")
        st.subheader(f"Bienvenue, {st.session_state.current_player}!")

        if st.button("🚪 Déconnexion"):
            st.session_state.current_player = None
            st.session_state.page = "login"
            st.rerun()

        st.subheader("Mes listes d'armées sauvegardées")

        if st.session_state.player_army_lists:
            for i, army_list in enumerate(st.session_state.player_army_lists):
                col1, col2 = st.columns([4, 1])
                with col1:
                    with st.expander(f"{army_list['name']} - {army_list['game']} - {army_list['total_cost']}/{army_list['points']} pts"):
                        st.write(f"Créée le: {army_list['date'][:10]}")
                        if st.button(f"Charger cette liste", key=f"load_{i}"):
                            try:
                                required_keys = ["game", "faction", "points", "army_list", "total_cost", "name"]
                                if not all(key in army_list for key in required_keys):
                                    st.error("Données de liste incomplètes")
                                    continue

                                st.session_state.game = army_list['game']
                                st.session_state.faction = army_list['faction']
                                st.session_state.points = army_list['points']
                                st.session_state.list_name = army_list['name']
                                st.session_state.army_total_cost = army_list['total_cost']

                                valid_army_list = []
                                for unit in army_list['army_list']:
                                    unit_required_keys = ["name", "cost", "quality", "defense", "type"]
                                    if all(key in unit for key in unit_required_keys):
                                        if "base_cost" not in unit:
                                            unit["base_cost"] = unit.get("cost", 0)
                                        valid_army_list.append(unit)
                                    else:
                                        st.warning(f"Unité invalide ignorée: {unit.get('name', 'Inconnue')}")

                                st.session_state.army_list = valid_army_list
                                st.session_state.page = "army"
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erreur lors du chargement: {str(e)}")

                with col2:
                    if st.button(f"❌ Supprimer", key=f"delete_{i}"):
                        if delete_player_army_list(st.session_state.current_player, i):
                            st.session_state.player_army_lists = load_player_army_lists(st.session_state.current_player)
                            st.success(f"Liste '{army_list['name']}' supprimée avec succès!")
                            st.rerun()
                        else:
                            st.error("Erreur lors de la suppression de la liste")
        else:
            st.info("Vous n'avez pas encore sauvegardé de listes d'armées")

        st.divider()
        st.subheader("Créer une nouvelle liste")

        st.session_state.game = st.selectbox(
            "Jeu",
            st.session_state["games"],
            index=0 if st.session_state["games"] else None
        )

        if st.session_state.game:
            available_factions = list(st.session_state["factions"][st.session_state.game].keys())
            st.session_state.faction = st.selectbox(
                "Faction",
                available_factions,
                index=0 if available_factions else None
            )

            st.session_state.points = st.number_input(
                "Format de la partie (points)",
                min_value=250,
                step=250,
                value=1000
            )

            st.session_state.list_name = st.text_input(
                "Nom de la liste",
                value="Ma liste d'armée"
            )

            col1, col2 = st.columns(2)

            with col1:
                if st.button("💾 Sauvegarder la configuration"):
                    st.success("Configuration sauvegardée")

            with col2:
                if st.button("➡️ Ma liste"):
                    if st.session_state.game and st.session_state.faction:
                        faction_data = st.session_state["factions"][st.session_state.game][st.session_state.faction]
                        st.session_state.units = faction_data["units"]
                        st.session_state.page = "army"
                        st.rerun()
                    else:
                        st.error("Veuillez sélectionner un jeu et une faction")

    # PAGE 3 — Composition de l'armée
    elif st.session_state.page == "army":
        st.title(st.session_state.list_name)
        st.caption(f"{st.session_state.game} — {st.session_state.faction} — {st.session_state.army_total_cost}/{st.session_state.points} pts")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("⬅️ Retour configuration"):
                st.session_state.page = "setup"
                st.rerun()
        with col2:
            if st.button("🚪 Déconnexion"):
                st.session_state.current_player = None
                st.session_state.page = "login"
                st.rerun()

        units = st.session_state.units

        # Section pour ajouter une unité
        st.divider()
        st.subheader("Ajouter une unité")

        unit = st.selectbox(
            "Unité",
            units,
            format_func=lambda u: f"{u['name']} ({u['base_cost']} pts)",
        )

        # Option pour unité combinée (uniquement pour les unités non-héros)
        combined_unit = False
        if unit.get("type", "").lower() != "hero":
            combined_unit = st.checkbox("Unité combinée (x2 effectif, coût x2 hors améliorations)", value=False)

        total_cost = unit["base_cost"]
        if combined_unit:
            total_cost = unit["base_cost"] * 2

        base_rules = list(unit.get("special_rules", []))
        options_selected = {}
        current_weapon = None
        mount_selected = None
        weapon_replaced = False

        # Trouver l'arme de base par défaut
        default_weapon = unit.get("weapons", [{"name": "Arme non définie", "attacks": "?", "armor_piercing": "?"}])[0]
        current_weapon = default_weapon.copy()

        # Options standards
        for group in unit.get("upgrade_groups", []):
            group_name = group["group"]

            st.write(f"### {group_name}")
            if group.get("description"):
                st.caption(group.get("description", ""))

            # Cas spécial pour les améliorations de rôle (choix unique)
            if "rôle" in group_name.lower() or "role" in group_name.lower():
                choice = st.radio(
                    group_name,
                    ["— Aucun —"] + [f"{o['name']} (+{o['cost']} pts)" for o in group["options"]],
                    key=f"{unit['name']}_{group['group']}"
                )

                if choice != "— Aucun —":
                    opt_name = choice.split(" (+")[0]
                    opt = next(o for o in group["options"] if o["name"] == opt_name)
                    total_cost += opt.get("cost", 0)
                    options_selected[group["group"]] = opt

            # Remplacement d'arme (choix unique avec radio buttons et détails complets)
            elif group.get("type") == "weapon":
                weapon_options = ["— Garder l'arme de base —"]
                for opt in group["options"]:
                    weapon_name = opt["name"]
                    weapon_cost = opt.get("cost", 0)
                    weapon_details = []

                    # Récupérer les détails complets de l'arme
                    if "weapon" in opt:
                        weapon = opt["weapon"]
                        weapon_details.append(f"A{weapon.get('attacks', '?')}")
                        weapon_details.append(f"PA({weapon.get('armor_piercing', '?')})")

                        if "special_rules" in weapon and weapon["special_rules"]:
                            weapon_details.extend(weapon["special_rules"])

                    # Créer la description complète avec tous les détails
                    details_str = f" ({', '.join(weapon_details)})" if weapon_details else ""
                    weapon_options.append(f"{weapon_name} (+{weapon_cost} pts){details_str}")

                choice = st.radio(
                    group["group"],
                    weapon_options,
                    key=f"{unit['name']}_{group['group']}"
                )

                if choice != "— Garder l'arme de base —":
                    opt_name = choice.split(" (+")[0]
                    opt = next(o for o in group["options"] if o["name"] == opt_name)
                    total_cost += opt.get("cost", 0)
                    options_selected[group["group"]] = opt
                    current_weapon = opt["weapon"].copy()
                    current_weapon["name"] = opt["name"]
                    weapon_replaced = True

            # Montures (choix unique avec radio buttons)
            elif group.get("type") == "mount":
                mount_options = ["— Aucune monture —"]
                for opt in group["options"]:
                    mount_name = opt["name"]
                    mount_cost = opt.get("cost", 0)
                    mount_details = []

                    if "mount" in opt and "special_rules" in opt["mount"]:
                        mount_details = opt["mount"]["special_rules"]

                    details_str = f" ({', '.join(mount_details)})" if mount_details else ""
                    mount_options.append(f"{mount_name} (+{mount_cost} pts){details_str}")

                choice = st.radio(
                    group["group"],
                    mount_options,
                    key=f"{unit['name']}_{group['group']}"
                )

                if choice != "— Aucune monture —":
                    opt_name = choice.split(" (+")[0]
                    opt = next(o for o in group["options"] if o["name"] == opt_name)
                    total_cost += opt.get("cost", 0)
                    options_selected[group["group"]] = opt
                    mount_selected = opt.get("mount")

            # Améliorations d'unité (uniquement Icône du Ravage pour les unités non-héroiques)
            elif group.get("type") == "multiple" and group.get("group") == "Améliorations d'unité" and unit.get("type", "").lower() != "hero":
                selected_options = []
                for opt in group["options"]:
                    if opt["name"] == "Icône du Ravage":  # On ne montre que cette option
                        if st.checkbox(f"{opt['name']} (+{opt['cost']} pts)"):
                            selected_options.append(opt)
                            total_cost += opt["cost"]

                if selected_options:
                    options_selected[group["group"]] = selected_options

        # Calcul de la valeur de Coriace
        coriace_value = calculate_coriace_value({
            "base_rules": base_rules,
            "options": options_selected,
            "mount": mount_selected
        })

        st.markdown(f"### 💰 Coût : **{total_cost} pts**")
        if coriace_value > 0:
            st.markdown(f"**Coriace totale : {coriace_value}**")

        if st.button("➕ Ajouter à l'armée"):
            # Préparation des données de l'unité
            unit_data = {
                "name": unit["name"],
                "cost": total_cost,
                "quality": unit["quality"],
                "defense": unit["defense"],
                "base_rules": base_rules,
                "options": options_selected,
                "current_weapon": current_weapon,
                "type": unit.get("type", "Infantry"),
                "combined": combined_unit,
                "weapon_replaced": weapon_replaced
            }

            # Ajouter la monture si elle existe
            if mount_selected:
                unit_data["mount"] = mount_selected

            # Mise à jour du nom pour refléter l'unité combinée
            if combined_unit and "[10]" in unit_data["name"]:
                unit_data["name"] = unit_data["name"].replace("[10]", "[20]")

            st.session_state.army_list.append(unit_data)
            st.session_state.army_total_cost += total_cost
            st.rerun()

        # Validation de la liste d'armée
        if st.session_state.game in GAME_RULES:
            st.session_state.is_army_valid, st.session_state.validation_errors = validate_army(
                st.session_state.army_list,
                GAME_RULES[st.session_state.game],
                st.session_state.army_total_cost,
                st.session_state.points
            )
        else:
            st.session_state.is_army_valid = True
            st.session_state.validation_errors = []

        if not st.session_state.is_army_valid:
            st.warning("⚠️ La liste d'armée n'est pas valide :")
            for error in st.session_state.validation_errors:
                st.write(f"- {error}")

        # Liste de l'armée
        st.divider
