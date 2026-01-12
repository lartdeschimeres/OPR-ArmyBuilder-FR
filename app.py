import json
import re
from pathlib import Path
from collections import defaultdict
import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime
import hashlib
import os
import traceback

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

    def repair_army_list(army_list):
        """Répare une liste d'armée sauvegardée si elle a des problèmes de structure"""
        repaired_list = []
        for unit in army_list:
            try:
                if not isinstance(unit, dict):
                    continue

                # Créer une copie pour ne pas modifier l'original
                repaired_unit = unit.copy()

                # Ajouter les champs manquants avec des valeurs par défaut
                repaired_unit.setdefault("type", "Infantry")
                repaired_unit.setdefault("base_cost", repaired_unit.get("cost", 0))

                # Vérifier les champs obligatoires
                required_keys = ["name", "cost", "quality", "defense"]
                if all(key in repaired_unit for key in required_keys):
                    repaired_list.append(repaired_unit)
                else:
                    st.warning(f"Unité ignorée: {repaired_unit.get('name', 'Inconnue')} (champs manquants)")
            except Exception as e:
                st.warning(f"Erreur de réparation d'unité: {str(e)}")
                continue

        return repaired_list

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
            if not faction_files:
                st.warning(f"Aucun fichier JSON trouvé dans {FACTIONS_DIR}")

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
                        match = re.search(r'Coriace\s*\((\d+)\)', rule)
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
                                            match = re.search(r'Coriace\s*\((\d+)\)', rule)
                                            if match:
                                                try:
                                                    coriace_value += int(match.group(1))
                                                except:
                                                    continue
                        elif isinstance(option_group, dict) and 'special_rules' in option_group:
                            for rule in option_group['special_rules']:
                                if isinstance(rule, str):
                                    match = re.search(r'Coriace\s*\((\d+)\)', rule)
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
                        match = re.search(r'Coriace\s*\((\d+)\)', rule)
                        if match:
                            try:
                                coriace_value += int(match.group(1))
                            except:
                                continue

        except Exception as e:
            st.error(f"Erreur dans calculate_coriace_value: {str(e)}")
            return 0

        return coriace_value

    def validate_army(army_list, game_rules, total_cost, total_points):
        errors = []

        if not army_list:
            errors.append("Aucune unité dans l'armée")
            return False, errors

        # Vérification du dépassement de points
        if total_cost > total_points:
            errors.append(f"Dépassement de {total_cost - total_points} pts (max: {total_points} pts)")

        if game_rules and game_rules == GAME_RULES["Age of Fantasy"]:
            # 1. Vérification du nombre de héros
            heroes = sum(1 for u in army_list if u.get("type", "").lower() == "hero")
            max_heroes = max(1, total_points // game_rules["hero_per_points"])
            if heroes > max_heroes:
                errors.append(f"Trop de héros ({heroes}/{max_heroes} max pour {total_points} pts)")

            # 2. Vérification du nombre de copies d'une même unité
            unit_counts = defaultdict(int)
            for unit in army_list:
                unit_counts[unit["name"]] += 1

            max_copies = 1 + (total_points // 750)
            for unit_name, count in unit_counts.items():
                if count > max_copies:
                    errors.append(f"Trop de copies de '{unit_name}' ({count}/{max_copies} max)")

            # 3. Vérification du pourcentage maximum par unité
            for unit in army_list:
                percentage = (unit["cost"] / total_points) * 100
                if percentage > game_rules["max_unit_percentage"]:
                    errors.append(f"'{unit['name']}' ({unit['cost']} pts) dépasse {game_rules['max_unit_percentage']}% du total ({total_points} pts)")

            # 4. Vérification du nombre maximum d'unités
            max_units = total_points // game_rules["unit_per_points"]
            if len(army_list) > max_units:
                errors.append(f"Trop d'unités ({len(army_list)}/{max_units} max pour {total_points} pts)")

        return len(errors) == 0, errors

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

    # Charger les factions au démarrage
    if not st.session_state["factions"] or not st.session_state["games"]:
        st.session_state["factions"], st.session_state["games"] = load_factions()

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

                                # Utiliser la fonction de réparation
                                st.session_state.army_list = repair_army_list(army_list['army_list'])

                                st.session_state.page = "army"
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erreur lors du chargement: {str(e)}")
                                st.error(f"Détails: {traceback.format_exc()}")

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

        if not st.session_state["games"]:
            st.error("Aucun jeu disponible. Vérifiez que vos fichiers JSON sont dans le bon dossier.")
        else:
            st.session_state.game = st.selectbox(
                "Jeu",
                st.session_state["games"],
                index=0 if st.session_state["games"] else None
            )

            if st.session_state.game:
                available_factions = list(st.session_state["factions"][st.session_state.game].keys())
                if not available_factions:
                    st.warning(f"Aucune faction disponible pour {st.session_state.game}")
                else:
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
            combined_unit = st.checkbox("Unité combinée (x2 effectif, coût x2)", value=False)

        total_cost = unit["base_cost"]
        if combined_unit:
            total_cost = unit["base_cost"] * 2

        base_rules = list(unit.get("special_rules", []))
        options_selected = {}
        current_weapon = None
        mount_selected = None
        weapon_replaced = False
        weapon_cost_multiplier = 2 if combined_unit else 1

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
                    cost = opt.get("cost", 0) * weapon_cost_multiplier
                    total_cost += cost
                    options_selected[group["group"]] = opt

            # Remplacement d'arme (choix unique avec radio buttons et détails complets)
            elif group.get("type") == "weapon":
                weapon_options = ["— Garder l'arme de base —"]
                for opt in group["options"]:
                    weapon_name = opt["name"]
                    weapon_cost = opt.get("cost", 0) * weapon_cost_multiplier
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
                    cost = opt.get("cost", 0) * weapon_cost_multiplier
                    total_cost += cost
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

            # Options multiples (checkboxes)
            elif group.get("type") == "multiple":
                selected_options = []
                for opt in group["options"]:
                    display_cost = opt["cost"] * weapon_cost_multiplier if combined_unit else opt["cost"]
                    if st.checkbox(f"{opt['name']} (+{display_cost} pts)", key=f"{unit['name']}_{group['group']}_{opt['name']}"):
                        selected_options.append(opt)
                        total_cost += opt["cost"] * weapon_cost_multiplier

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
                "weapon_replaced": weapon_replaced,
                "weapon_info": {
                    "is_replaced": weapon_replaced,
                    "original_name": default_weapon.get("name", ""),
                    "current_name": current_weapon.get("name", "")
                }
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
            st.session_state.is_army_valid = st.session_state.army_total_cost <= st.session_state.points
            st.session_state.validation_errors = []
            if st.session_state.army_total_cost > st.session_state.points:
                st.session_state.is_army_valid = False
                st.session_state.validation_errors.append(
                    f"Dépassement de {st.session_state.army_total_cost - st.session_state.points} pts"
                )

        # Barre de progression et boutons
        st.divider()
        progress = min(1.0, st.session_state.army_total_cost / st.session_state.points) if st.session_state.points else 0
        st.progress(progress)
        st.markdown(f"**{st.session_state.army_total_cost} / {st.session_state.points} pts**")

        # Avertissements et erreurs
        if st.session_state.army_total_cost > st.session_state.points:
            excess = st.session_state.army_total_cost - st.session_state.points
            st.warning(f"⚠️ Votre armée dépasse de {excess} pts la limite de {st.session_state.points} pts")

        if not st.session_state.is_army_valid:
            st.warning("⚠️ La liste d'armée n'est pas valide :")
            for error in st.session_state.validation_errors:
                st.error(f"- {error}")

        # Liste de l'armée
        st.divider()
        st.subheader("Liste de l'armée")

        for i, u in enumerate(st.session_state.army_list):
            # Calcul de la valeur totale de Coriace
            coriace_value = calculate_coriace_value(u)

            # Génération du HTML pour la fiche
            html_content = f"""
            <style>
            .army-card {{
                border: 2px solid #4a89dc;
                border-radius: 15px;
                padding: 15px;
                margin-bottom: 20px;
                background: white;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }}
            .unit-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 10px;
            }}
            .unit-name {{
                font-size: 1.2em;
                font-weight: bold;
                color: #333;
                margin: 0;
            }}
            .unit-points {{
                color: #666;
                font-size: 0.9em;
            }}
            .badges-container {{
                display: flex;
                gap: 8px;
                margin-bottom: 15px;
                flex-wrap: wrap;
            }}
            .badge {{
                padding: 6px 12px;
                border-radius: 20px;
                font-size: 0.9em;
                font-weight: 500;
                color: white;
                text-align: center;
            }}
            .quality-badge {{
                background-color: #4a89dc;
            }}
            .defense-badge {{
                background-color: #4a89dc;
            }}
            .coriace-badge {{
                background-color: #4a89dc;
            }}
            .section {{
                margin-bottom: 12px;
            }}
            .section-title {{
                font-weight: bold;
                color: #4a89dc;
                margin-bottom: 5px;
                font-size: 0.95em;
            }}
            .section-content {{
                margin-left: 10px;
                font-size: 0.9em;
                color: #555;
            }}
            .combined-badge {{
                background-color: #28a745;
                color: white;
                padding: 4px 8px;
                border-radius: 12px;
                font-size: 0.8em;
                margin-left: 10px;
            }}
            </style>

            <div class="army-card">
                <div class="unit-header">
                    <h3 class="unit-name">{u['name']}</h3>
                    <span class="unit-points">{u['cost']} pts</span>
                </div>

                <div class="badges-container">
                    <span class="badge quality-badge">Qualité {u['quality']}+</span>
                    <span class="badge defense-badge">Défense {u['defense']}+</span>
            """

            if coriace_value > 0:
                html_content += f'<span class="badge coriace-badge">Coriace {coriace_value}</span>'

            if u.get("combined", False):
                html_content += '<span class="combined-badge">Unité combinée</span>'

            html_content += """
                </div>
            """

            # Règles spéciales
            if u.get("base_rules"):
                rules = [r for r in u['base_rules'] if not r.startswith("Coriace")]
                if rules:
                    html_content += f"""
                    <div class="section">
                        <div class="section-title">Règles spéciales</div>
                        <div class="section-content">{', '.join(rules)}</div>
                    </div>
                    """

            # Arme équipée
            if 'current_weapon' in u:
                weapon = u['current_weapon']
                weapon_name = weapon.get('name', 'Arme de base')
                attacks = weapon.get('attacks', '?')
                armor_piercing = weapon.get('armor_piercing', '?')

                weapon_line = f"{weapon_name} | A{attacks} | PA({armor_piercing})"

                if 'special_rules' in weapon and weapon['special_rules']:
                    weapon_line += f", {', '.join(weapon['special_rules'])}"

                html_content += f"""
                <div class="section">
                    <div class="section-title">Arme équipée</div>
                    <div class="section-content">{weapon_line}</div>
                </div>
                """

            # Options (toutes les options SAUF les armes ET les montures)
            other_options = []
            for group_name, opt_group in u.get("options", {}).items():
                # Exclure les groupes liés aux armes et aux montures
                if ("arme" in group_name.lower() or
                    "weapon" in group_name.lower() or
                    "monture" in group_name.lower() or
                    "mount" in group_name.lower()):
                    continue

                if isinstance(opt_group, list):
                    for opt in opt_group:
                        other_options.append(opt["name"])
                elif isinstance(opt_group, dict):
                    other_options.append(opt_group["name"])

            if other_options:
                html_content += f"""
                <div class="section">
                    <div class="section-title">Options</div>
                    <div class="section-content">{', '.join(other_options)}</div>
                </div>
                """

            # Améliorations d'unité (affichées séparément)
            if "Améliorations" in u.get("options", {}):
                improvements = []
                if isinstance(u["options"]["Améliorations"], list):
                    improvements = [opt["name"] for opt in u["options"]["Améliorations"]]
                elif isinstance(u["options"]["Améliorations"], dict):
                    improvements = [u["options"]["Améliorations"]["name"]]

                if improvements:
                    html_content += f"""
                    <div class="section">
                        <div class="section-title">Améliorations d'unité</div>
                        <div class="section-content">{', '.join(improvements)}</div>
                    </div>
                    """

            # Monture (si elle existe, affichée séparément)
            if u.get("mount"):
                mount = u['mount']
                mount_rules = []
                if 'special_rules' in mount:
                    mount_rules = mount['special_rules']

                html_content += f"""
                <div class="section">
                    <div class="section-title">Monture</div>
                    <div class="section-content">
                        <strong>{mount.get('name', '')}</strong>
                """

                if mount_rules:
                    html_content += f"<br>{', '.join(mount_rules)}"

                html_content += """
                    </div>
                </div>
                """

            html_content += "</div>"

            components.html(html_content, height=300)

            # Bouton de suppression
            if st.button(f"❌ Supprimer {u['name']}", key=f"del_{i}"):
                st.session_state.army_total_cost -= u["cost"]
                st.session_state.army_list.pop(i)
                st.rerun()

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("💾 Sauvegarder la liste"):
                if not st.session_state.list_name:
                    st.warning("Veuillez donner un nom à votre liste avant de sauvegarder")
                elif not st.session_state.current_player:
                    st.warning("Vous devez être connecté pour sauvegarder une liste")
                else:
                    army_list_data = {
                        "name": st.session_state.list_name,
                        "game": st.session_state.game,
                        "faction": st.session_state.faction,
                        "points": st.session_state.points,
                        "army_list": st.session_state.army_list,
                        "total_cost": st.session_state.army_total_cost,
                        "date": datetime.now().isoformat()
                    }

                    success = save_player_army_list(st.session_state.current_player, army_list_data)
                    if success:
                        st.success(f"Liste '{st.session_state.list_name}' sauvegardée avec succès!")
                        st.session_state.player_army_lists = load_player_army_lists(st.session_state.current_player)
                    else:
                        st.error("Erreur lors de la sauvegarde de la liste")

        with col2:
            if st.button("📄 Exporter en HTML"):
                html_content = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Liste d'armée OPR - {st.session_state.list_name}</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; margin: 20px; }}
                        h1 {{ color: #333; }}
                        .army-card {{
                            border: 2px solid #4a89dc;
                            border-radius: 15px;
                            padding: 15px;
                            margin-bottom: 20px;
                            background: white;
                            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                        }}
                        .unit-header {{
                            display: flex;
                            justify-content: space-between;
                            align-items: center;
                            margin-bottom: 10px;
                        }}
                        .unit-name {{
                            font-size: 1.2em;
                            font-weight: bold;
                            color: #333;
                            margin: 0;
                        }}
                        .unit-points {{
                            color: #666;
                            font-size: 0.9em;
                        }}
                        .badges-container {{
                            display: flex;
                            gap: 8px;
                            margin-bottom: 15px;
                            flex-wrap: wrap;
                        }}
                        .badge {{
                            padding: 6px 12px;
                            border-radius: 20px;
                            font-size: 0.9em;
                            font-weight: 500;
                            color: white;
                            text-align: center;
                        }}
                        .quality-badge {{
                            background-color: #4a89dc;
                        }}
                        .defense-badge {{
                            background-color: #4a89dc;
                        }}
                        .coriace-badge {{
                            background-color: #4a89dc;
                        }}
                        .section {{
                            margin-bottom: 12px;
                        }}
                        .section-title {{
                            font-weight: bold;
                            color: #4a89dc;
                            margin-bottom: 5px;
                            font-size: 0.95em;
                        }}
                        .section-content {{
                            margin-left: 10px;
                            font-size: 0.9em;
                            color: #555;
                        }}
                        .combined-badge {{
                            background-color: #28a745;
                            color: white;
                            padding: 4px 8px;
                            border-radius: 12px;
                            font-size: 0.8em;
                            margin-left: 10px;
                        }}
                        @media print {{
                            body {{
                                margin: 0;
                                padding: 20px;
                            }}
                            .army-card {{
                                border: none;
                                box-shadow: none;
                                margin-bottom: 10px;
                                page-break-inside: avoid;
                            }}
                        }}
                    </style>
                </head>
                <body>
                    <h1>Liste d'armée OPR - {st.session_state.list_name}</h1>
                    <h2>{st.session_state.game} - {st.session_state.faction} - {st.session_state.army_total_cost}/{st.session_state.points} pts</h2>
                """

                for u in st.session_state.army_list:
                    coriace_value = calculate_coriace_value(u)

                    html_content += f"""
                    <div class="army-card">
                        <div class="unit-header">
                            <h3 class="unit-name">{u['name']}</h3>
                            <span class="unit-points">{u['cost']} pts</span>
                        </div>

                        <div class="badges-container">
                            <span class="badge quality-badge">Qualité {u['quality']}+</span>
                            <span class="badge defense-badge">Défense {u['defense']}+</span>
                    """

                    if coriace_value > 0:
                        html_content += f'<span class="badge coriace-badge">Coriace {coriace_value}</span>'

                    if u.get("combined", False):
                        html_content += '<span class="combined-badge">Unité combinée</span>'

                    html_content += """
                        </div>
                    """

                    if u.get("base_rules"):
                        rules = [r for r in u['base_rules'] if not r.startswith("Coriace")]
                        if rules:
                            html_content += f"""
                            <div class="section">
                                <div class="section-title">Règles spéciales</div>
                                <div class="section-content">{', '.join(rules)}</div>
                            </div>
                            """

                    if 'current_weapon' in u:
                        weapon = u['current_weapon']
                        weapon_name = weapon.get('name', 'Arme de base')
                        attacks = weapon.get('attacks', '?')
                        armor_piercing = weapon.get('armor_piercing', '?')

                        weapon_line = f"{weapon_name} | A{attacks} | PA({armor_piercing})"

                        if 'special_rules' in weapon and weapon['special_rules']:
                            weapon_line += f", {', '.join(weapon['special_rules'])}"

                        html_content += f"""
                        <div class="section">
                            <div class="section-title">Arme équipée</div>
                            <div class="section-content">{weapon_line}</div>
                        </div>
                        """

                    other_options = []
                    for group_name, opt_group in u.get("options", {}).items():
                        # Exclure les groupes liés aux armes et aux montures
                        if ("arme" in group_name.lower() or
                            "weapon" in group_name.lower() or
                            "monture" in group_name.lower() or
                            "mount" in group_name.lower()):
                            continue

                        if isinstance(opt_group, list):
                            for opt in opt_group:
                                other_options.append(opt["name"])
                        elif isinstance(opt_group, dict):
                            other_options.append(opt_group["name"])

                    if other_options:
                        html_content += f"""
                        <div class="section">
                            <div class="section-title">Options</div>
                            <div class="section-content">{', '.join(other_options)}</div>
                        </div>
                        """

                    if "Améliorations" in u.get("options", {}):
                        improvements = []
                        if isinstance(u["options"]["Améliorations"], list):
                            improvements = [opt["name"] for opt in u["options"]["Améliorations"]]
                        elif isinstance(u["options"]["Améliorations"], dict):
                            improvements = [u["options"]["Améliorations"]["name"]]

                        if improvements:
                            html_content += f"""
                            <div class="section">
                                <div class="section-title">Améliorations d'unité</div>
                                <div class="section-content">{', '.join(improvements)}</div>
                            </div>
                            """

                    if u.get("mount"):
                        mount = u['mount']
                        mount_rules = []
                        if 'special_rules' in mount:
                            mount_rules = mount['special_rules']

                        html_content += f"""
                        <div class="section">
                            <div class="section-title">Monture</div>
                            <div class="section-content">
                                <strong>{mount.get('name', '')}</strong>
                        """

                        if mount_rules:
                            html_content += f"<br>{', '.join(mount_rules)}"

                        html_content += """
                            </div>
                        </div>
                        """

                    html_content += "</div>"

                html_content += """
                </body>
                </html>
                """

                filename = f"{st.session_state.list_name or 'army_list'}.html"
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(html_content)

                with open(filename, "r", encoding="utf-8") as f:
                    st.download_button(
                        label="Télécharger le fichier HTML",
                        data=f,
                        file_name=filename,
                        mime="text/html"
                    )

        with col3:
            if st.button("🧹 Réinitialiser la liste"):
                st.session_state.army_list = []
                st.session_state.army_total_cost = 0
                st.rerun()

if __name__ == "__main__":
    main()
