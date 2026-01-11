import json
import re
from pathlib import Path
from collections import defaultdict
import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime
import hashlib
import base64
import os

# Configuration de base
st.set_page_config(page_title="OPR Army Builder FR", layout="centered")
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
if "page" not in st.session_state:
    st.session_state.page = "login"

for key, default in {
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
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

@st.cache_data
def load_factions():
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

    with open(player_file, "w", encoding="utf-8") as f:
        json.dump(player_data, f, ensure_ascii=False, indent=2)

    return True, "Compte créé avec succès"

def verify_player(username, password):
    player_file = PLAYERS_DIR / f"{username}.json"
    if not player_file.exists():
        return False, "Nom d'utilisateur ou mot de passe incorrect"

    with open(player_file, encoding="utf-8") as f:
        player_data = json.load(f)

    if player_data["password"] != hash_password(password):
        return False, "Nom d'utilisateur ou mot de passe incorrect"

    return True, "Connexion réussie"

def load_player_army_lists(username):
    player_file = PLAYERS_DIR / f"{username}.json"
    if not player_file.exists():
        return []

    with open(player_file, encoding="utf-8") as f:
        player_data = json.load(f)

    return player_data.get("army_lists", [])

def save_player_army_list(username, army_list_data):
    player_file = PLAYERS_DIR / f"{username}.json"
    if not player_file.exists():
        return False

    with open(player_file, encoding="utf-8") as f:
        player_data = json.load(f)

    player_data["army_lists"].append(army_list_data)

    with open(player_file, "w", encoding="utf-8") as f:
        json.dump(player_data, f, ensure_ascii=False, indent=2)

    return True

def validate_army(army_list, game_rules, total_cost, total_points):
    errors = []

    if not army_list:
        errors.append("Aucune unité dans l'armée")
        return False, errors

    if game_rules == GAME_RULES["Age of Fantasy"]:
        # 1 héros par tranche de 375 pts
        heroes = sum(1 for u in army_list if u.get("type", "").lower() == "hero")
        max_heroes = max(1, total_points // game_rules["hero_per_points"])
        if heroes > max_heroes:
            errors.append(f"Trop de héros (max: {max_heroes} pour {total_points} pts)")

        # 1+X copies de la même unité (X=1 pour 750 pts)
        unit_counts = defaultdict(int)
        for unit in army_list:
            unit_counts[unit["name"]] += 1

        max_copies = 1 + (total_points // 750)
        for unit_name, count in unit_counts.items():
            if count > max_copies:
                errors.append(f"Trop de copies de '{unit_name}' (max: {max_copies})")

        # Aucune unité ne peut valoir plus de 35% du total des points de l'armée
        for unit in army_list:
            percentage = (unit["cost"] / total_points) * 100
            if percentage > game_rules["max_unit_percentage"]:
                errors.append(f"'{unit['name']}' ({unit['cost']} pts) dépasse {game_rules['max_unit_percentage']}% du total ({total_points} pts)")

        # 1 unité max par tranche de 150 pts
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
if st.session_state.page == "setup":
    st.title("OPR Army Builder 🇫🇷")
    st.subheader(f"Bienvenue, {st.session_state.current_player}!")

    if st.button("🚪 Déconnexion"):
        st.session_state.current_player = None
        st.session_state.page = "login"
        st.rerun()

    st.subheader("Mes listes d'armées sauvegardées")
    if st.session_state.player_army_lists:
        for i, army_list in enumerate(st.session_state.player_army_lists):
            with st.expander(f"{army_list['name']} - {army_list['game']} - {army_list['total_cost']}/{army_list['points']} pts"):
                st.write(f"Créée le: {army_list['date'][:10]}")
                if st.button(f"Charger cette liste", key=f"load_{i}"):
                    st.session_state.game = army_list['game']
                    st.session_state.faction = army_list['faction']
                    st.session_state.points = army_list['points']
                    st.session_state.list_name = army_list['name']
                    st.session_state.army_list = army_list['army_list']
                    st.session_state.army_total_cost = army_list['total_cost']
                    st.session_state.page = "army"
                    st.rerun()
    else:
        st.info("Vous n'avez pas encore sauvegardé de listes d'armées")

    st.divider()
    st.subheader("Créer une nouvelle liste")

    st.session_state.game = st.selectbox(
        "Jeu",
        games,
        index=games.index(st.session_state.game) if st.session_state.game else 0
    )

    available_factions = [f for f in factions if f["game"] == st.session_state.game]
    faction_names = [f["name"] for f in available_factions]

    st.session_state.faction = st.selectbox(
        "Faction",
        faction_names,
        index=faction_names.index(st.session_state.faction) if st.session_state.faction in faction_names else 0
    )

    st.session_state.points = st.number_input(
        "Format de la partie (points)",
        min_value=250,
        step=250,
        value=st.session_state.points
    )

    st.session_state.list_name = st.text_input(
        "Nom de la liste",
        value=st.session_state.list_name
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("💾 Sauvegarder la configuration"):
            st.success("Configuration sauvegardée")

    with col2:
        if st.button("➡️ Ma liste"):
            faction_file = next(f["file"] for f in factions if f["name"] == st.session_state.faction)
            with open(faction_file, encoding="utf-8") as f:
                faction_data = json.load(f)
            st.session_state.units = faction_data.get("units", [])
            st.session_state.page = "army"
            st.rerun()

# PAGE 3 — Composition de l'armée
if st.session_state.page == "army":
    st.title(st.session_state.list_name or "Ma liste d'armée")
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

    total_cost = unit["base_cost"]
    base_rules = list(unit.get("special_rules", []))
    options_selected = {}
    mount_selected = None
    current_weapon = unit.get("weapons", [{"name": "Arme non définie", "attacks": "?", "armor_piercing": "?"}])[0]

    # Affichage des armes de base
    st.subheader("Armes de base")
    for w in unit.get("weapons", []):
        st.write(f"- **{w.get('name', 'Arme non définie')}** | A{w.get('attacks', '?')} | PA({w.get('armor_piercing', '?')})")

    # Options
    for group in unit.get("upgrade_groups", []):
        if group.get("type") == "multiple":
            st.write(f"### {group['group']}")
            if group.get("description"):
                st.caption(group["description"])

            selected_options = []
            for opt in group["options"]:
                if st.checkbox(f"{opt['name']} (+{opt['cost']} pts)", key=f"{unit['name']}_{group['group']}_{opt['name']}"):
                    selected_options.append(opt)
                    total_cost += opt["cost"]

            if selected_options:
                options_selected[group["group"]] = selected_options
        else:
            choice = st.selectbox(
                group["group"],
                ["— Aucun —"] + [o["name"] for o in group["options"]],
                key=f"{unit['name']}_{group['group']}"
            )

            if choice != "— Aucun —":
                opt = next(o for o in group["options"] if o["name"] == choice)
                total_cost += opt.get("cost", 0)
                options_selected[group["group"]] = opt
                if group["type"] == "weapon":
                    current_weapon = opt["weapon"]
                    current_weapon["name"] = opt["name"]

    # Calcul de la valeur de Coriace
    coriace_value = 0
    for rule in base_rules:
        match = re.search(r'Coriace \((\d+)\)', rule)
        if match:
            coriace_value += int(match.group(1))

    st.markdown(f"### 💰 Coût : **{total_cost} pts**")
    if coriace_value > 0:
        st.markdown(f"**Coriace totale : {coriace_value}**")

    if st.button("➕ Ajouter à l'armée"):
        unit_data = {
            "name": unit["name"],
            "cost": total_cost,
            "quality": unit["quality"],
            "defense": unit["defense"],
            "base_rules": base_rules,
            "options": options_selected,
            "current_weapon": current_weapon,
            "type": unit.get("type", "Infantry")
        }

        if coriace_value > 0:
            unit_data["coriace"] = coriace_value

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
    st.divider()
    st.subheader("Liste de l'armée")

    for i, u in enumerate(st.session_state.army_list):
        st.markdown(f"### {u['name']} — {u['cost']} pts")
        st.markdown(f"- Qualité: {u['quality']}+, Défense: {u['defense']}+")
        if u.get('coriace', 0) > 0:
            st.markdown(f"- Coriace: {u['coriace']}")

        if u.get("base_rules"):
            st.markdown(f"- **Règles spéciales**: {', '.join(u['base_rules'])}")

        if 'current_weapon' in u:
            weapon = u['current_weapon']
            st.markdown(f"- **Arme**: {weapon.get('name', 'Arme de base')} (A{weapon.get('attacks', '?')}, PA{weapon.get('armor_piercing', '?')})")

        if u.get("options"):
            options_text = []
            for opt_group in u['options'].values():
                if isinstance(opt_group, list):
                    options_text.extend([opt['name'] for opt in opt_group])
                else:
                    options_text.append(opt_group['name'])
            st.markdown(f"- **Options**: {', '.join(options_text)}")

        if st.button(f"❌ Supprimer {u['name']}", key=f"del_{i}"):
            st.session_state.army_total_cost -= u["cost"]
            st.session_state.army_list.pop(i)
            st.rerun()

    # Barre de progression et boutons
    st.divider()
    progress = st.session_state.army_total_cost / st.session_state.points if st.session_state.points else 0
    st.progress(progress)
    st.markdown(f"**{st.session_state.army_total_cost} / {st.session_state.points} pts**")

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
                    h1 {{ color: #4a89dc; }}
                    .army-card {{ border: 1px solid #ccc; border-radius: 8px; padding: 15px; margin-bottom: 15px; background: #f9f9f9; }}
                    .badge {{ display: inline-block; background: #4a89dc; color: white; padding: 6px 12px; border-radius: 15px; margin-right: 8px; margin-bottom: 5px; }}
                    .title {{ font-weight: bold; color: #4a89dc; margin-top: 10px; }}
                </style>
            </head>
            <body>
                <h1>Liste d'armée OPR - {st.session_state.list_name}</h1>
                <h2>{st.session_state.game} - {st.session_state.faction} - {st.session_state.army_total_cost}/{st.session_state.points} pts</h2>
            """

            for u in st.session_state.army_list:
                html_content += f"""
                <div class="army-card">
                    <h3>{u['name']} - {u['cost']} pts</h3>
                    <div>
                        <span class="badge">Qualité {u['quality']}+</span>
                        <span class="badge">Défense {u['defense']}+</span>
                """

                if u.get('coriace', 0) > 0:
                    html_content += f'<span class="badge">Coriace {u["coriace"]}</span>'

                html_content += """
                    </div>
                """

                if u.get("base_rules"):
                    html_content += f"""
                    <div class="title">Règles spéciales</div>
                    <div>{', '.join(u['base_rules'])}</div>
                    """

                if 'current_weapon' in u:
                    weapon = u['current_weapon']
                    html_content += f"""
                    <div class="title">Arme équipée</div>
                    <div>
                        {weapon.get('name', 'Arme de base')} | A{weapon.get('attacks', '?')} | PA({weapon.get('armor_piercing', '?')})
                    </div>
                    """

                if u.get("options"):
                    options_text = []
                    for opt_group in u['options'].values():
                        if isinstance(opt_group, list):
                            options_text.extend([opt['name'] for opt in opt_group])
                        else:
                            options_text.append(opt_group['name'])
                    html_content += f"""
                    <div class="title">Options sélectionnées</div>
                    <div>{', '.join(options_text)}</div>
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

    if st.session_state.game in GAME_RULES:
        st.divider()
        st.subheader("Règles spécifiques à " + st.session_state.game)
        rules = GAME_RULES[st.session_state.game]
        st.markdown(f"""
        - **Héros** : 1 par tranche de {rules['hero_per_points']} pts
        - **Copies d'unités** : 1+X (X=1 pour {list(rules['unit_copies'].keys())[0]} pts)
        - **Unité max** : {rules['max_unit_percentage']}% du total des points de l'armée
        - **Nombre d'unités** : 1 par tranche de {rules['unit_per_points']} pts
        """)
