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
        # Compter uniquement les héros indépendants (pas ceux rattachés)
        independent_heroes = sum(1 for u in army_list if u.get("type", "").lower() == "hero" and not u.get("attached_to_unit", False))
        max_heroes = max(1, total_points // game_rules["hero_per_points"])
        if independent_heroes > max_heroes:
            errors.append(f"Trop de héros indépendants (max: {max_heroes} pour {total_points} pts)")

        unit_counts = defaultdict(int)
        for unit in army_list:
            if not unit.get("attached_to_unit", False):  # Ne pas compter les héros rattachés
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
        if len([u for u in army_list if not u.get("attached_to_unit", False)]) > max_units:
            errors.append(f"Trop d'unités (max: {max_units} pour {total_points} pts)")

    return len(errors) == 0, errors

def export_to_html():
    if not st.session_state.army_list:
        st.warning("Aucune unité dans l'armée à exporter")
        return

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Liste d'armée OPR - {st.session_state.list_name}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1 {{ color: #4a89dc; }}
            .army-card {{ border: 1px solid #ccc; border-radius: 8px; padding: 15px; margin-bottom: 15px; background: #f9f9f9; }}
            .hero-card {{ border: 1px solid #e74c3c; border-radius: 8px; padding: 15px; margin-bottom: 15px; background: #fff0f0; margin-left: 20px; }}
            .badge {{ display: inline-block; background: #4a89dc; color: white; padding: 6px 12px; border-radius: 15px; margin-right: 8px; margin-bottom: 5px; }}
            .title {{ font-weight: bold; color: #4a89dc; margin-top: 10px; }}
            .valid {{ border-left: 4px solid #2ecc71; }}
            .invalid {{ border-left: 4px solid #e74c3c; }}
        </style>
    </head>
    <body>
        <h1>Liste d'armée OPR - {st.session_state.list_name}</h1>
        <h2>{st.session_state.game} - {st.session_state.faction} - {st.session_state.army_total_cost}/{st.session_state.points} pts</h2>
    """

    # Regrouper les unités avec leurs héros rattachés
    units_with_heroes = {}
    independent_heroes = []

    for unit in st.session_state.army_list:
        if unit.get("attached_to_unit"):
            # C'est un héros rattaché
            unit_name = unit["attached_to_unit"]
            if unit_name not in units_with_heroes:
                units_with_heroes[unit_name] = []
            units_with_heroes[unit_name].append(unit)
        elif unit.get("type", "").lower() == "hero" and unit.get("attached_hero"):
            # C'est une unité avec un héros rattaché
            units_with_heroes[unit["name"]] = [unit.get("attached_hero")]
        else:
            # C'est une unité normale ou un héros indépendant
            if unit.get("type", "").lower() == "hero":
                independent_heroes.append(unit)

    # Afficher les unités normales et leurs héros rattachés
    for unit in st.session_state.army_list:
        if unit.get("type", "").lower() != "hero" and not unit.get("attached_to_unit", False):
            # C'est une unité normale
            base_rules = unit.get("base_rules", [])
            weapon_rules = []
            option_rules = []
            mount_rules = []

            if 'current_weapon' in unit and 'special_rules' in unit['current_weapon']:
                weapon_rules = unit['current_weapon']['special_rules']

            for opt_group in unit.get("options", {}).values():
                if isinstance(opt_group, list):
                    for opt in opt_group:
                        if 'special_rules' in opt:
                            option_rules.extend(opt['special_rules'])
                elif 'special_rules' in opt_group:
                    option_rules.extend(opt_group['special_rules'])

            if 'mount' in unit and 'special_rules' in unit['mount']:
                mount_rules = unit['mount']['special_rules']

            html_content += f"""
            <div class="army-card">
                <h3>{unit['name']} - {unit['cost']} pts</h3>
                <div>
                    <span class="badge">Qualité {unit['quality']}+</span>
                    <span class="badge">Défense {unit['defense']}+</span>
                    {'<span class="badge">Coriace {}</span>'.format(unit.get('coriace', 0)) if unit.get('coriace', 0) > 0 else ''}
                </div>
            """

            if base_rules:
                html_content += f"""
                <div class="title">Règles spéciales de base</div>
                <div>{', '.join(base_rules)}</div>
                """

            if 'current_weapon' in unit:
                weapon = unit['current_weapon']
                html_content += f"""
                <div class="title">Arme équipée</div>
                <div>
                    {weapon.get('name', 'Arme de base')} | A{weapon.get('attacks', '?')} | PA({weapon.get('armor_piercing', '?')})
                    {f" | {', '.join(weapon_rules)}" if weapon_rules else ''}
                </div>
                """

            if unit.get("options"):
                html_content += f"""
                <div class="title">Options sélectionnées</div>
                <div>
                    {', '.join([opt['name'] for opt_group in unit['options'].values() for opt in (opt_group if isinstance(opt_group, list) else [opt_group])])}
                    {f" | {', '.join(option_rules)}" if option_rules else ''}
                </div>
                """

            if unit.get("mount"):
                mount = unit['mount']
                html_content += f"""
                <div class="title">Monture</div>
                <div>
                    <strong>{mount['name']}</strong> (+{mount.get('cost', 0)} pts)<br>
                    {', '.join(mount_rules) if mount_rules else 'Aucune règle spéciale'}
                </div>
                """

            # Afficher les héros rattachés à cette unité
            if unit["name"] in units_with_heroes:
                for hero in units_with_heroes[unit["name"]]:
                    if isinstance(hero, dict):  # Héros rattaché stocké dans l'unité
                        hero_data = hero
                    else:  # Héros rattaché stocké comme unité séparée
                        hero_data = next(h for h in st.session_state.army_list if h["name"] == hero)

                    html_content += f"""
                    <div class="hero-card">
                        <h4>⚔️ {hero_data['name']} (Héros rattaché) - {hero_data['cost']} pts</h4>
                        <div>
                            <span class="badge">Qualité {hero_data['quality']}+</span>
                            <span class="badge">Défense {hero_data['defense']}+</span>
                            {'<span class="badge">Coriace {}</span>'.format(hero_data.get('coriace', 0)) if hero_data.get('coriace', 0) > 0 else ''}
                        </div>
                    """

                    if 'base_rules' in hero_data:
                        html_content += f"""
                        <div class="title">Règles spéciales</div>
                        <div>{', '.join(hero_data['base_rules'])}</div>
                        """

                    if 'current_weapon' in hero_data:
                        weapon = hero_data['current_weapon']
                        html_content += f"""
                        <div class="title">Arme équipée</div>
                        <div>
                            {weapon.get('name', 'Arme de base')} | A{weapon.get('attacks', '?')} | PA({weapon.get('armor_piercing', '?')})
                        </div>
                        """

                    html_content += "</div>"

            html_content += "</div>"

    # Afficher les héros indépendants
    if independent_heroes:
        html_content += "<h3>Héros indépendants</h3>"
        for hero in independent_heroes:
            base_rules = hero.get("base_rules", [])
            weapon_rules = []
            mount_rules = []

            if 'current_weapon' in hero and 'special_rules' in hero['current_weapon']:
                weapon_rules = hero['current_weapon']['special_rules']

            if 'mount' in hero and 'special_rules' in hero['mount']:
                mount_rules = hero['mount']['special_rules']

            html_content += f"""
            <div class="army-card">
                <h3>{hero['name']} - {hero['cost']} pts (Héros indépendant)</h3>
                <div>
                    <span class="badge">Qualité {hero['quality']}+</span>
                    <span class="badge">Défense {hero['defense']}+</span>
                    {'<span class="badge">Coriace {}</span>'.format(hero.get('coriace', 0)) if hero.get('coriace', 0) > 0 else ''}
                </div>
            """

            if base_rules:
                html_content += f"""
                <div class="title">Règles spéciales</div>
                <div>{', '.join(base_rules)}</div>
                """

            if 'current_weapon' in hero:
                weapon = hero['current_weapon']
                html_content += f"""
                <div class="title">Arme équipée</div>
                <div>
                    {weapon.get('name', 'Arme de base')} | A{weapon.get('attacks', '?')} | PA({weapon.get('armor_piercing', '?')})
                    {f" | {', '.join(weapon_rules)}" if weapon_rules else ''}
                </div>
                """

            if 'mount' in hero:
                mount = hero['mount']
                html_content += f"""
                <div class="title">Monture</div>
                <div>
                    <strong>{mount['name']}</strong> (+{mount.get('cost', 0)} pts)<br>
                    {', '.join(mount_rules) if mount_rules else 'Aucune règle spéciale'}
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

    components.html(html_content, height=600, scrolling=True)

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

    # Section pour ajouter une unité normale
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

        if unit.get("can_attach_hero", False):
            unit_data["can_attach_hero"] = True

        st.session_state.army_list.append(unit_data)
        st.session_state.army_total_cost += total_cost
        st.rerun()

    # Section pour ajouter un héros indépendant
    st.divider()
    st.subheader("Ajouter un héros indépendant")

    hero_units = [u for u in units if u.get("type", "").lower() == "hero"]
    if hero_units:
        selected_hero = st.selectbox(
            "Sélectionner un héros",
            ["— Aucun —"] + [h["name"] for h in hero_units],
            key="add_hero_select"
        )

        if selected_hero != "— Aucun —":
            hero = next(h for h in hero_units if h["name"] == selected_hero)
            hero_cost = hero["base_cost"]

            st.markdown(f"### 💰 Coût : **{hero_cost} pts**")

            if st.button("➕ Ajouter le héros à l'armée"):
                hero_data = {
                    "name": hero["name"],
                    "cost": hero_cost,
                    "quality": hero["quality"],
                    "defense": hero["defense"],
                    "base_rules": hero.get("special_rules", []),
                    "type": "hero",
                    "current_weapon": hero.get("weapons", [{"name": "Arme non définie", "attacks": "?", "armor_piercing": "?"}])[0]
                }

                # Calcul de la valeur de Coriace pour le héros
                coriace_value = 0
                for rule in hero_data["base_rules"]:
                    match = re.search(r'Coriace \((\d+)\)', rule)
                    if match:
                        coriace_value += int(match.group(1))

                if coriace_value > 0:
                    hero_data["coriace"] = coriace_value

                st.session_state.army_list.append(hero_data)
                st.session_state.army_total_cost += hero_cost
                st.rerun()
    else:
        st.info("Aucun héros disponible dans cette faction")

    # Section pour rattacher un héros à une unité existante
    st.divider()
    st.subheader("Rattacher un héros à une unité existante")

    # Sélection du héros (uniquement les héros indépendants)
    independent_heroes = [u for u in st.session_state.army_list if u.get("type", "").lower() == "hero" and not u.get("attached_to_unit", False)]
    available_heroes = [u for u in units if u.get("type", "").lower() == "hero"]

    # Combiner les héros disponibles et les héros indépendants déjà dans l'armée
    all_available_heroes = []
    for hero in available_heroes:
        # Vérifier si le héros n'est pas déjà dans l'armée (indépendant ou rattaché)
        hero_name = hero["name"]
        hero_in_army = any(u["name"] == hero_name for u in st.session_state.army_list)
        if not hero_in_army:
            all_available_heroes.append(hero)

    for hero in independent_heroes:
        all_available_heroes.append({
            "name": hero["name"],
            "base_cost": hero["cost"],
            "quality": hero["quality"],
            "defense": hero["defense"],
            "special_rules": hero.get("base_rules", []),
            "weapons": hero.get("current_weapon", []),
            "type": "hero"
        })

    if all_available_heroes:
        selected_hero_name = st.selectbox(
            "Sélectionner un héros",
            ["— Aucun —"] + [h["name"] for h in all_available_heroes],
            key="attach_hero_select"
        )

        if selected_hero_name != "— Aucun —":
            hero = next(h for h in all_available_heroes if h["name"] == selected_hero_name)

            # Vérifier si c'est un héros déjà dans l'armée
            hero_in_army = any(u["name"] == hero["name"] for u in independent_heroes)

            # Sélection de l'unité cible
            compatible_units = [u for u in st.session_state.army_list
                              if u.get("can_attach_hero", False)
                              and u.get("type", "").lower() != "hero"]

            if compatible_units:
                target_unit_name = st.selectbox(
                    "Sélectionner l'unité cible",
                    [u["name"] for u in compatible_units],
                    key="attach_target_unit"
                )

                if target_unit_name:
                    target_unit = next(u for u in compatible_units if u["name"] == target_unit_name)

                    if st.button("Rattacher le héros à cette unité"):
                        # Vérifier que l'unité n'a pas déjà un héros rattaché
                        if any(u.get("attached_to_unit") == target_unit["name"] for u in st.session_state.army_list):
                            st.error("Cette unité a déjà un héros rattaché")
                        else:
                            # Si le héros est déjà dans l'armée, le supprimer de la liste
                            if hero_in_army:
                                hero_unit = next(u for u in st.session_state.army_list if u["name"] == hero["name"])
                                st.session_state.army_list.remove(hero_unit)
                                st.session_state.army_total_cost -= hero_unit["cost"]

                            # Créer une nouvelle entrée pour le héros rattaché
                            hero_data = {
                                "name": hero["name"],
                                "cost": hero.get("base_cost", hero.get("cost", 0)),
                                "quality": hero["quality"],
                                "defense": hero["defense"],
                                "base_rules": hero.get("special_rules", []),
                                "type": "hero",
                                "attached_to_unit": target_unit["name"],
                                "current_weapon": hero.get("weapons", [{"name": "Arme non définie", "attacks": "?", "armor_piercing": "?"}])[0]
                            }

                            # Calcul de la valeur de Coriace pour le héros
                            coriace_value = 0
                            for rule in hero_data["base_rules"]:
                                match = re.search(r'Coriace \((\d+)\)', rule)
                                if match:
                                    coriace_value += int(match.group(1))

                            if coriace_value > 0:
                                hero_data["coriace"] = coriace_value

                            st.session_state.army_list.append(hero_data)
                            st.success(f"Héros {hero['name']} rattaché à l'unité {target_unit['name']}!")
                            st.rerun()
            else:
                st.warning("Aucune unité compatible dans votre armée pour rattacher le héros")
    else:
        st.info("Aucun héros disponible à rattacher")

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

    # Regrouper les unités avec leurs héros rattachés
    army_display = []
    for unit in st.session_state.army_list:
        if unit.get("attached_to_unit"):
            continue  # On affichera les héros rattachés avec leurs unités

        army_display.append({
            "type": "unit",
            "data": unit,
            "heroes": []
        })

    # Ajouter les héros rattachés à leurs unités
    for hero in st.session_state.army_list:
        if hero.get("attached_to_unit"):
            unit_name = hero["attached_to_unit"]
            for item in army_display:
                if item["data"]["name"] == unit_name:
                    item["heroes"].append(hero)
                    break

    # Ajouter les héros indépendants
    for unit in st.session_state.army_list:
        if unit.get("type", "").lower() == "hero" and not unit.get("attached_to_unit", False):
            army_display.append({
                "type": "hero",
                "data": unit
            })

    # Affichage des unités et héros
    for i, item in enumerate(army_display):
        if item["type"] == "unit":
            u = item["data"]
            height = 200
            if u.get("mount"):
                height += 40
            if u.get("options"):
                height += 20 * len(u["options"])
            if item["heroes"]:
                height += 60 * len(item["heroes"])

            base_rules = u.get("base_rules", [])
            weapon_rules = []
            option_rules = []
            mount_rules = []

            if 'current_weapon' in u and 'special_rules' in u['current_weapon']:
                weapon_rules = u['current_weapon']['special_rules']

            for opt_group in u.get("options", {}).values():
                if isinstance(opt_group, list):
                    for opt in opt_group:
                        if 'special_rules' in opt:
                            option_rules.extend(opt['special_rules'])
                elif 'special_rules' in opt_group:
                    option_rules.extend(opt_group['special_rules'])

            if 'mount' in u and 'special_rules' in u['mount']:
                mount_rules = u['mount']['special_rules']

            components.html(f"""
            <style>
            .card {{
                border:1px solid #ccc;
                border-radius:8px;
                padding:15px;
                margin-bottom:15px;
                background:#f9f9f9;
            }}
            .hero-card {{
                border:1px solid #e74c3c;
                border-radius:8px;
                padding:15px;
                margin-bottom:15px;
                background:#fff0f0;
                margin-left: 20px;
                margin-top: 10px;
            }}
            .badge {{
                display:inline-block;
                background:#4a89dc;
                color:white;
                padding:6px 12px;
                border-radius:15px;
                margin-right:8px;
                margin-bottom: 5px;
            }}
            .title {{
                font-weight:bold;
                color:#4a89dc;
                margin-top:10px;
            }}
            .valid {{
                border-left: 4px solid #2ecc71;
            }}
            .invalid {{
                border-left: 4px solid #e74c3c;
            }}
            </style>

            <div class="card {'valid' if st.session_state.is_army_valid else 'invalid'}" id="unit_{i}">
                <h4>{u['name']} — {u['cost']} pts</h4>

                <div style="margin-bottom: 10px;">
                    <span class="badge">Qualité {u['quality']}+</span>
                    <span class="badge">Défense {u['defense']}+</span>
                    {'<span class="badge">Coriace {}</span>'.format(u.get('coriace', 0)) if u.get('coriace', 0) > 0 else ''}
                </div>

                {f'''
                <div class="title">Règles spéciales de base</div>
                <div style="margin-left: 15px; margin-bottom: 10px;">
                    {', '.join(base_rules) if base_rules else "Aucune"}
                </div>
                ''' if base_rules else ''}

                {f'''
                <div class="title">Arme équipée</div>
                <div style="margin-left: 15px; margin-bottom: 10px;">
                    {u.get('current_weapon', {{}}).get('name', 'Arme de base')} |
                    A{u.get('current_weapon', {{}}).get('attacks', '?')} |
                    PA({u.get('current_weapon', {{}}).get('armor_piercing', '?')})
                    {f" | {', '.join(weapon_rules)}" if weapon_rules else ''}
                </div>
                ''' if 'current_weapon' in u else ''}

                {f'''
                <div class="title">Options sélectionnées</div>
                <div style="margin-left: 15px; margin-bottom: 10px;">
                    {', '.join([opt['name'] for opt_group in u['options'].values() for opt in (opt_group if isinstance(opt_group, list) else [opt_group])])}
                    {f" | {', '.join(option_rules)}" if option_rules else ''}
                </div>
                ''' if u.get("options") else ''}

                {f'''
                <div class="title">Monture</div>
                <div style="margin-left: 15px; margin-bottom: 10px;">
                    <strong>{u.get('mount', {{}}).get('name', '')}</strong> (+{u.get('mount', {{}}).get('cost', 0)} pts)<br>
                    {', '.join(mount_rules) if mount_rules else 'Aucune règle spéciale'}
                </div>
                ''' if u.get("mount") else ''}
            </div>
            """, height=height)

            # Afficher les héros rattachés à cette unité
            for j, hero in enumerate(item["heroes"]):
                hero_data = hero
                hero_rules = hero_data.get("base_rules", [])
                weapon_rules = []

                if 'current_weapon' in hero_data and 'special_rules' in hero_data['current_weapon']:
                    weapon_rules = hero_data['current_weapon']['special_rules']

                components.html(f"""
                <div class="hero-card" id="hero_{i}_{j}">
                    <h4>⚔️ {hero_data['name']} (Héros rattaché) — {hero_data['cost']} pts</h4>
                    <div>
                        <span class="badge">Qualité {hero_data['quality']}+</span>
                        <span class="badge">Défense {hero_data['defense']}+</span>
                        {'<span class="badge">Coriace {}</span>'.format(hero_data.get('coriace', 0)) if hero_data.get('coriace', 0) > 0 else ''}
                    </div>

                    {f'''
                    <div class="title">Règles spéciales</div>
                    <div style="margin-left: 15px; margin-bottom: 10px;">
                        {', '.join(hero_rules) if hero_rules else "Aucune"}
                    </div>
                    ''' if hero_rules else ''}

                    {f'''
                    <div class="title">Arme équipée</div>
                    <div style="margin-left: 15px; margin-bottom: 10px;">
                        {hero_data.get('current_weapon', {{}}).get('name', 'Arme de base')} |
                        A{hero_data.get('current_weapon', {{}}).get('attacks', '?')} |
                        PA({hero_data.get('current_weapon', {{}}).get('armor_piercing', '?')})
                        {f" | {', '.join(weapon_rules)}" if weapon_rules else ''}
                    </div>
                    ''' if 'current_weapon' in hero_data else ''}
                </div>
                """, height=120)

            if st.button("❌ Supprimer", key=f"del_{i}"):
                st.session_state.army_total_cost -= u["cost"]
                st.session_state.army_list = [unit for unit in st.session_state.army_list if unit["name"] != u["name"] or unit.get("attached_to_unit") != u["name"]]
                st.rerun()

        else:  # Hero indépendant
            u = item["data"]
            height = 180
            if u.get("mount"):
                height += 40

            base_rules = u.get("base_rules", [])
            weapon_rules = []
            mount_rules = []

            if 'current_weapon' in u and 'special_rules' in u['current_weapon']:
                weapon_rules = u['current_weapon']['special_rules']

            if 'mount' in u and 'special_rules' in u['mount']:
                mount_rules = u['mount']['special_rules']

            components.html(f"""
            <div class="card {'valid' if st.session_state.is_army_valid else 'invalid'}" id="hero_{i}">
                <h4>{u['name']} — {u['cost']} pts (Héros indépendant)</h4>

                <div style="margin-bottom: 10px;">
                    <span class="badge">Qualité {u['quality']}+</span>
                    <span class="badge">Défense {u['defense']}+</span>
                    {'<span class="badge">Coriace {}</span>'.format(u.get('coriace', 0)) if u.get('coriace', 0) > 0 else ''}
                </div>

                {f'''
                <div class="title">Règles spéciales</div>
                <div style="margin-left: 15px; margin-bottom: 10px;">
                    {', '.join(base_rules) if base_rules else "Aucune"}
                </div>
                ''' if base_rules else ''}

                {f'''
                <div class="title">Arme équipée</div>
                <div style="margin-left: 15px; margin-bottom: 10px;">
                    {u.get('current_weapon', {{}}).get('name', 'Arme de base')} |
                    A{u.get('current_weapon', {{}}).get('attacks', '?')} |
                    PA({u.get('current_weapon', {{}}).get('armor_piercing', '?')})
                    {f" | {', '.join(weapon_rules)}" if weapon_rules else ''}
                </div>
                ''' if 'current_weapon' in u else ''}

                {f'''
                <div class="title">Monture</div>
                <div style="margin-left: 15px; margin-bottom: 10px;">
                    <strong>{u.get('mount', {{}}).get('name', '')}</strong> (+{u.get('mount', {{}}).get('cost', 0)} pts)<br>
                    {', '.join(mount_rules) if mount_rules else 'Aucune règle spéciale'}
                </div>
                ''' if u.get("mount") else ''}
            </div>
            """, height=height)

            if st.button("❌ Supprimer", key=f"del_hero_{i}"):
                st.session_state.army_total_cost -= u["cost"]
                st.session_state.army_list = [unit for unit in st.session_state.army_list if unit["name"] != u["name"] or unit.get("type", "").lower() != "hero"]
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
            export_to_html()

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
