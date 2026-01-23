import json
import streamlit as st
from pathlib import Path
from datetime import datetime
import hashlib
import re
import base64
import math
import os

# ======================================================
# CONFIGURATION POUR SIMON
# ======================================================
st.set_page_config(
    page_title="OPR Army Forge FR - Simon Joinville Fouquet",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Chemins des fichiers
BASE_DIR = Path(__file__).resolve().parent
FACTIONS_DIR = BASE_DIR / "lists" / "data" / "factions"
FACTIONS_DIR.mkdir(parents=True, exist_ok=True)

# ======================================================
# CONFIGURATION DES JEUX ET LEURS LIMITATIONS
# ======================================================
GAME_CONFIG = {
    "Age of Fantasy": {
        "display_name": "Age of Fantasy",
        "max_points": 10000,
        "min_points": 250,
        "default_points": 1000,
        "point_step": 250,
        "description": "Jeu de bataille dans un univers fantasy médiéval",
        "hero_limit": 375,  # 1 Héros par tranche de 375 pts
        "unit_copy_rule": 750,  # 1+X copies où X=1 pour 750 pts
        "unit_max_cost_ratio": 0.35,  # 35% du total des points
        "unit_per_points": 150  # 1 unité maximum par tranche de 150 pts
    },
    "Grimdark Future": {
        "display_name": "Grimdark Future",
        "max_points": 10000,
        "min_points": 200,
        "default_points": 800,
        "point_step": 200,
        "description": "Jeu de bataille futuriste",
        "hero_limit": 375,  # 1 Héros par tranche de 375 pts
        "unit_copy_rule": 750,  # 1+X copies où X=1 pour 750 pts
        "unit_max_cost_ratio": 0.35,  # 35% du total des points
        "unit_per_points": 150  # 1 unité maximum par tranche de 150 pts
    }
}

# ======================================================
# FONCTION POUR AFFICHER LA BARRE DE PROGRESSION
# ======================================================
def show_points_progress(current_points, max_points):
    """Affiche une barre de progression pour les points avec couleur dynamique"""
    if max_points <= 0:
        progress = 0
    else:
        progress = min(100, (current_points / max_points) * 100)

    remaining_points = max_points - current_points

    # Déterminer la couleur en fonction du pourcentage
    if progress < 70:
        color = "#4CAF50"  # Vert
    elif progress < 90:
        color = "#FFC107"  # Orange
    else:
        color = "#F44336"  # Rouge

    st.markdown(
        f"""
        <div style="width: 100%; margin: 10px 0 20px 0;">
            <div style="background-color: #e0e0e0; border-radius: 4px; height: 20px; margin-bottom: 5px;">
                <div style="width: {progress}%; background-color: {color}; border-radius: 4px; height: 100%; transition: width 0.3s;"></div>
            </div>
            <div style="display: flex; justify-content: space-between; font-size: 0.9em;">
                <span><strong>{current_points}/{max_points} pts</strong> ({int(progress)}%)</span>
                <span><strong>Reste:</strong> {remaining_points} pts</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

# ======================================================
# FONCTIONS POUR LES RÈGLES SPÉCIFIQUES
# ======================================================
def check_army_points(army_list, army_points):
    """Vérifie que le total des points ne dépasse pas la limite choisie"""
    total = sum(unit["cost"] for unit in army_list)
    if total > army_points:
        st.error(f"Limite de points dépassée! Maximum autorisé: {army_points} pts. Total actuel: {total} pts")
        return False
    return True

def check_add_unit_points(current_points, unit_cost, max_points):
    """Vérifie qu'ajouter une unité ne dépasse pas la limite de points"""
    if current_points + unit_cost > max_points:
        remaining = max_points - current_points
        st.error(f"Ajouter cette unité dépasserait votre limite de {max_points} pts. Il vous reste {remaining} pts.")
        return False
    return True

def check_hero_limit(army_list, army_points, game_config):
    """Vérifie la limite de héros"""
    if game_config.get("hero_limit"):
        max_heroes = math.floor(army_points / game_config["hero_limit"])
        hero_count = sum(1 for unit in army_list if unit.get("type") == "hero")

        if hero_count > max_heroes:
            st.error(f"Limite de héros dépassée! Maximum autorisé: {max_heroes} (1 héros par {game_config['hero_limit']} pts)")
            return False
    return True

def check_unit_copy_rule(army_list, army_points, game_config):
    """Vérifie la règle des copies d'unités"""
    if game_config.get("unit_copy_rule"):
        x_value = math.floor(army_points / game_config["unit_copy_rule"])
        max_copies = 1 + x_value

        unit_counts = {}
        for unit in army_list:
            unit_name = unit["name"]
            count_key = unit_name

            if count_key in unit_counts:
                unit_counts[count_key] += 1
            else:
                unit_counts[count_key] = 1

        for unit_name, count in unit_counts.items():
            if count > max_copies:
                st.error(f"Trop de copies de l'unité! Maximum autorisé: {max_copies} (1+{x_value} pour {game_config['unit_copy_rule']} pts)")
                return False
    return True

def check_unit_max_cost(army_list, army_points, game_config, new_unit_cost=None):
    """Vérifie qu'aucune unité ne dépasse le ratio maximum de coût"""
    if not game_config.get("unit_max_cost_ratio"):
        return True

    max_cost = army_points * game_config["unit_max_cost_ratio"]

    for unit in army_list:
        if unit["cost"] > max_cost:
            st.error(f"L'unité {unit['name']} ({unit['cost']} pts) dépasse la limite de {int(max_cost)} pts ({int(game_config['unit_max_cost_ratio']*100)}% du total)")
            return False

    if new_unit_cost and new_unit_cost > max_cost:
        st.error(f"Cette unité ({new_unit_cost} pts) dépasse la limite de {int(max_cost)} pts ({int(game_config['unit_max_cost_ratio']*100)}% du total)")
        return False

    return True

def check_unit_per_points(army_list, army_points, game_config):
    """Vérifie le nombre maximum d'unités par tranche de points"""
    if game_config.get("unit_per_points"):
        max_units = math.floor(army_points / game_config["unit_per_points"])
        if len(army_list) > max_units:
            st.error(f"Trop d'unités! Maximum autorisé: {max_units} (1 unité par {game_config['unit_per_points']} pts)")
            return False
    return True

def validate_army_rules(army_list, army_points, game, new_unit_cost=None):
    """Valide toutes les règles spécifiques au jeu"""
    game_config = GAME_CONFIG.get(game, {})

    if game in GAME_CONFIG:
        # Vérification de la limite de points totale
        total_cost = sum(unit["cost"] for unit in army_list)
        if new_unit_cost:
            total_cost += new_unit_cost

        if total_cost > army_points:
            st.error(f"Limite de points dépassée! Maximum autorisé: {army_points} pts. Total actuel: {total_cost} pts")
            return False

        # Vérification du coût maximum par unité
        max_cost = army_points * game_config["unit_max_cost_ratio"]
        if new_unit_cost and new_unit_cost > max_cost:
            st.error(f"Cette unité ({new_unit_cost} pts) dépasse la limite de {int(max_cost)} pts ({int(game_config['unit_max_cost_ratio']*100)}% du total)")
            return False

        return (check_hero_limit(army_list, army_points, game_config) and
                check_unit_copy_rule(army_list, army_points, game_config) and
                check_unit_max_cost(army_list, army_points, game_config, new_unit_cost) and
                check_unit_per_points(army_list, army_points, game_config))

    return True

# ======================================================
# FONCTIONS UTILITAIRES
# ======================================================
def format_special_rule(rule):
    """Formate les règles spéciales avec parenthèses"""
    if not isinstance(rule, str):
        return str(rule)
    if "(" in rule and ")" in rule:
        return rule
    match = re.search(r"(\D+)(\d+)", rule)
    if match:
        return f"{match.group(1)}({match.group(2)})"
    return rule

def extract_coriace_value(rule):
    """Extrait la valeur numérique de Coriace d'une règle"""
    if not isinstance(rule, str):
        return 0
    match = re.search(r"Coriace\s*\(?(\d+)\)?", rule)
    if match:
        return int(match.group(1))
    return 0

def get_coriace_from_rules(rules):
    """Calcule la Coriace depuis une liste de règles"""
    if not rules or not isinstance(rules, list):
        return 0
    total = 0
    for rule in rules:
        total += extract_coriace_value(rule)
    return total

def get_mount_details(mount):
    """Récupère les détails d'une monture"""
    if not mount:
        return None, 0

    mount_data = mount
    if 'mount' in mount:
        mount_data = mount['mount']

    special_rules = []
    if 'special_rules' in mount_data and isinstance(mount_data['special_rules'], list):
        special_rules = mount_data['special_rules']

    coriace = get_coriace_from_rules(special_rules)
    return special_rules, coriace

def calculate_total_coriace(unit_data, combined=False):
    """Calcule la Coriace totale d'une unité"""
    total = 0

    if 'special_rules' in unit_data:
        total += get_coriace_from_rules(unit_data['special_rules'])

    if 'mount' in unit_data and unit_data['mount']:
        _, mount_coriace = get_mount_details(unit_data['mount'])
        total += mount_coriace

    if 'options' in unit_data:
        for opts in unit_data['options'].values():
            if isinstance(opts, list):
                for opt in opts:
                    if 'special_rules' in opt:
                        total += get_coriace_from_rules(opt['special_rules'])
            elif isinstance(opts, dict) and 'special_rules' in opts:
                total += get_coriace_from_rules(opts['special_rules'])

    if 'weapon' in unit_data and 'special_rules' in unit_data['weapon']:
        total += get_coriace_from_rules(unit_data['weapon']['special_rules'])

    if combined and unit_data.get('type') != "hero":
        base_coriace = get_coriace_from_rules(unit_data.get('special_rules', []))
        total += base_coriace

    return total if total > 0 else None

def format_weapon_details(weapon):
    """Formate les détails d'une arme pour l'affichage"""
    if not weapon:
        return {
            "name": "Arme non spécifiée",
            "attacks": "?",
            "ap": "?",
            "special": []
        }
    return {
        "name": weapon.get('name', 'Arme non nommée'),
        "attacks": weapon.get('attacks', '?'),
        "ap": weapon.get('armor_piercing', '?'),
        "special": weapon.get('special_rules', [])
    }

def format_mount_details(mount):
    """Formate les détails d'une monture pour l'affichage"""
    if not mount:
        return "Aucune monture"

    mount_name = mount.get('name', 'Monture non nommée')
    mount_data = mount
    if 'mount' in mount:
        mount_data = mount['mount']

    details = mount_name

    if 'quality' in mount_data or 'defense' in mount_data:
        details += " ("
        if 'quality' in mount_data:
            details += f"Qua{mount_data['quality']}+"
        if 'defense' in mount_data:
            details += f" Déf{mount_data['defense']}+"
        details += ")"

    if 'special_rules' in mount_data and mount_data['special_rules']:
        details += " | " + ", ".join(mount_data['special_rules'])

    if 'weapons' in mount_data and mount_data['weapons']:
        for weapon in mount_data['weapons']:
            weapon_details = format_weapon_details(weapon)
            details += " | " + f"{weapon.get('name', 'Arme')} (A{weapon_details['attacks']}, PA({weapon_details['ap']})"
            if weapon_details['special']:
                details += ", " + ", ".join(weapon_details['special'])
            details += ")"

    return details

def format_unit_option(u):
    """Formate l'affichage des unités dans la liste déroulante"""
    name_part = f"{u['name']}"

    if u.get('type') == "hero":
        name_part += " [1]"
    else:
        base_size = u.get('size', 10)
        name_part += f" [{base_size}]"

    qua_def = f"Qua {u['quality']}+"

    coriace = get_coriace_from_rules(u.get('special_rules', []))
    if 'mount' in u and u['mount']:
        _, mount_coriace = get_mount_details(u['mount'])
        coriace += mount_coriace

    defense = u.get('defense', '?')
    qua_def_coriace = f"Qua {u['quality']}+ / Déf {defense}"
    if coriace > 0:
        qua_def_coriace += f" / Coriace {coriace}"

    weapons_part = ""
    if 'weapons' in u and u['weapons']:
        weapons = []
        for weapon in u['weapons']:
            weapon_details = format_weapon_details(weapon)
            weapons.append(f"{weapon.get('name', 'Arme')} (A{weapon_details['attacks']}, PA({weapon_details['ap']}){', ' + ', '.join(weapon_details['special']) if weapon_details['special'] else ''})")
        weapons_part = " | ".join(weapons)

    rules_part = ""
    if 'special_rules' in u and u['special_rules']:
        rules_part = ", ".join(u['special_rules'])

    result = f"{name_part} - {qua_def_coriace}"

    if weapons_part:
        result += f" - {weapons_part}"

    if rules_part:
        result += f" - {rules_part}"

    result += f" {u['base_cost']}pts"
    return result

def find_option_by_name(options, name):
    """Trouve une option par son nom de manière sécurisée"""
    try:
        return next((o for o in options if o.get("name") == name), None)
    except Exception:
        return None

# ======================================================
# LOCAL STORAGE
# ======================================================
def ls_get(key):
    """Récupère une valeur du LocalStorage"""
    try:
        unique_key = f"{key}_{hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()[:8]}"
        st.markdown(
            f"""
            <script>
            const value = localStorage.getItem("{key}");
            const input = document.createElement("input");
            input.type = "hidden";
            input.id = "{unique_key}";
            input.value = value || "";
            document.body.appendChild(input);
            </script>
            """,
            unsafe_allow_html=True
        )
        return st.text_input("", key=unique_key, label_visibility="collapsed")
    except Exception as e:
        st.error(f"Erreur LocalStorage: {e}")
        return None

def ls_set(key, value):
    """Stocke une valeur dans le LocalStorage"""
    try:
        if not isinstance(value, str):
            value = json.dumps(value)
        escaped_value = value.replace("'", "\\'").replace('"', '\\"')
        st.markdown(
            f"""
            <script>
            localStorage.setItem("{key}", `{escaped_value}`);
            </script>
            """,
            unsafe_allow_html=True
        )
    except Exception as e:
        st.error(f"Erreur LocalStorage: {e}")

# ======================================================
# FONCTIONS D'AFFICHAGE AVEC ONGLETS
# ======================================================
def show_rules_legend(faction_data):
    """Affiche la légende des règles spéciales"""
    rules_descriptions = faction_data.get('special_rules_descriptions', {})

    with st.expander("📖 Légende des règles spéciales"):
        for rule, description in rules_descriptions.items():
            with st.expander(f"**{rule}**"):
                st.markdown(description)

def show_unit_with_tabs(unit, rules_descriptions):
    """Affiche une unité avec des onglets pour les descriptions des règles"""
    with st.expander(f"{unit['name']} [{unit.get('size', 10)}] ({unit['cost']} pts)"):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown(f"**Qualité:** {unit['quality']}+")
            st.markdown(f"**Défense:** {unit.get('defense', '?')}+")

            if 'rules' in unit and unit['rules']:
                st.markdown("**Règles spéciales:**")
                for rule in unit['rules']:
                    with st.expander(f"📖 {rule}"):
                        description = rules_descriptions.get(rule, "Description non disponible")
                        st.markdown(description)

        with col2:
            if 'weapon' in unit and unit['weapon']:
                weapon = unit['weapon']
                st.markdown(f"**Arme:** {weapon.get('name', 'Arme non nommée')}")
                st.markdown(f"ATK: {weapon.get('attacks', '?')}, PA: {weapon.get('armor_piercing', '?')}")

                if 'special_rules' in weapon and weapon['special_rules']:
                    st.markdown("**Règles spéciales de l'arme:**")
                    for rule in weapon['special_rules']:
                        with st.expander(f"📖 {rule}"):
                            description = rules_descriptions.get(rule, "Description non disponible")
                            st.markdown(description)

# ======================================================
# CHARGEMENT DES FACTIONS
# ======================================================
@st.cache_data
def load_factions():
    """Charge les factions depuis les fichiers JSON"""
    factions = {}
    games = set()

    # Création d'un fichier de faction par défaut si le dossier est vide
    if not list(FACTIONS_DIR.glob("*.json")):
        default_faction = {
            "game": "Age of Fantasy",
            "faction": "Disciples de la Guerre",
            "special_rules_descriptions": {
                "Éclaireur": "Cette unité peut se déplacer à travers les terrains difficiles sans pénalité et ignore les obstacles lors de ses déplacements.",
                "Furieux": "Cette unité relance les dés de 1 lors des tests d'attaque au corps à corps.",
                "Né pour la guerre": "Cette unité peut relancer un dé de 1 lors des tests de moral.",
                "Héros": "Cette unité est un personnage important qui peut inspirer les troupes autour de lui. Les héros ne peuvent pas être combinés.",
                "Coriace(1)": "Cette unité ignore 1 point de dégât par phase.",
                "Magique(1)": "Les armes de cette unité ignorent 1 point de défense grâce à leur nature magique.",
                "Contre-charge": "Cette unité obtient +1 à ses jets de dégât lors d'une charge."
            },
            "units": [
                {
                    "name": "Barbares de la Guerre",
                    "type": "unit",
                    "size": 10,
                    "base_cost": 50,
                    "quality": 3,
                    "defense": 5,
                    "special_rules": ["Éclaireur", "Furieux", "Né pour la guerre"],
                    "weapons": [{
                        "name": "Armes à une main",
                        "attacks": 1,
                        "armor_piercing": 0,
                        "special_rules": []
                    }],
                    "upgrade_groups": [
                        {
                            "group": "Remplacement d'armes",
                            "type": "weapon",
                            "options": [
                                {
                                    "name": "Lance",
                                    "cost": 35,
                                    "weapon": {
                                        "name": "Lance",
                                        "attacks": 1,
                                        "armor_piercing": 0,
                                        "special_rules": ["Contre-charge"]
                                    }
                                },
                                {
                                    "name": "Fléau",
                                    "cost": 20,
                                    "weapon": {
                                        "name": "Fléau",
                                        "attacks": 1,
                                        "armor_piercing": 1,
                                        "special_rules": []
                                    }
                                }
                            ]
                        },
                        {
                            "group": "Améliorations d'unité",
                            "type": "upgrades",
                            "options": [
                                {
                                    "name": "Icône du Ravage",
                                    "cost": 20,
                                    "special_rules": ["Aura de Défense versatile"]
                                },
                                {
                                    "name": "Sergent",
                                    "cost": 5,
                                    "special_rules": []
                                },
                                {
                                    "name": "Bannière",
                                    "cost": 5,
                                    "special_rules": []
                                },
                                {
                                    "name": "Musicien",
                                    "cost": 10,
                                    "special_rules": []
                                }
                            ]
                        }
                    ]
                },
                {
                    "name": "Maître de la Guerre Élu",
                    "type": "hero",
                    "size": 1,
                    "base_cost": 150,
                    "quality": 3,
                    "defense": 5,
                    "special_rules": ["Héros", "Éclaireur", "Furieux"],
                    "weapons": [{
                        "name": "Arme héroïque",
                        "attacks": 2,
                        "armor_piercing": 1,
                        "special_rules": ["Magique(1)"]
                    }]
                }
            ]
        }
        with open(FACTIONS_DIR / "default.json", "w", encoding="utf-8") as f:
            json.dump(default_faction, f, indent=2)

    for fp in FACTIONS_DIR.glob("*.json"):
        try:
            with open(fp, encoding="utf-8") as f:
                data = json.load(f)
                game = data.get("game")
                faction = data.get("faction")
                if game and faction:
                    factions.setdefault(game, {})[faction] = data
                    games.add(game)
        except Exception as e:
            st.warning(f"Erreur chargement {fp.name}: {e}")

    return factions, sorted(games) if games else list(GAME_CONFIG.keys())

# ======================================================
# INITIALISATION
# ======================================================
factions_by_game, games = load_factions()

# Initialisation de la session
if "page" not in st.session_state:
    st.session_state.page = "setup"
    st.session_state.army_list = []
    st.session_state.army_cost = 0
    st.session_state.current_player = "Simon"

# ======================================================
# PAGE 1 – CONFIGURATION
# ======================================================
if st.session_state.page == "setup":
    st.title("OPR Army Forge FR")

    # Affichage des informations sur les jeux disponibles
    st.subheader("Jeux disponibles")
    for game_key, config in GAME_CONFIG.items():
        with st.expander(f"📖 {config['display_name']}"):
            st.markdown(f"""
            **Description**: {config['description']}
            - **Points**: {config['min_points']} à {config['max_points']} (défaut: {config['default_points']})
            """)

            if game_key == "Age of Fantasy":
                st.markdown(f"""
                **Règles spécifiques à Age of Fantasy:**
                - 1 Héros par tranche de {config['hero_limit']} pts d'armée
                - 1+X copies de la même unité (X=1 pour {config['unit_copy_rule']} pts d'armée)
                - Aucune unité ne peut valoir plus de {int(config['unit_max_cost_ratio']*100)}% du total des points
                - 1 unité maximum par tranche de {config['unit_per_points']} pts d'armée
                """)

    # Liste des listes sauvegardées
    st.subheader("Mes listes sauvegardées")

    # Chargement des listes sauvegardées
    saved_lists = ls_get("opr_saved_lists")
    if saved_lists:
        try:
            saved_lists = json.loads(saved_lists)
            if isinstance(saved_lists, list):
                for i, saved_list in enumerate(saved_lists):
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.markdown(f"**{saved_list.get('name', 'Liste sans nom')}**")
                        st.caption(f"{saved_list.get('game', 'Inconnu')} • {saved_list.get('faction', 'Inconnue')} • {saved_list.get('total_cost', 0)}/{saved_list.get('points', 0)} pts")
                    with col2:
                        if st.button(f"Charger", key=f"load_{i}"):
                            st.session_state.game = saved_list["game"]
                            st.session_state.faction = saved_list["faction"]
                            st.session_state.points = saved_list["points"]
                            st.session_state.list_name = saved_list["name"]
                            st.session_state.army_list = saved_list["army_list"]
                            st.session_state.army_cost = saved_list["total_cost"]
                            st.session_state.units = factions_by_game[saved_list["game"]][saved_list["faction"]]["units"]
                            st.session_state.page = "army"
                            st.rerun()
        except Exception as e:
            st.error(f"Erreur chargement listes: {e}")

    if not games:
        st.error("Aucun jeu trouvé")
        st.stop()

    # Sélection du jeu
    game = st.selectbox("Jeu", games)
    game_config = GAME_CONFIG.get(game, GAME_CONFIG["Age of Fantasy"])

    # Sélection de la faction
    if game in factions_by_game and factions_by_game[game]:
        available_factions = list(factions_by_game[game].keys())
        faction = st.selectbox("Faction", available_factions)
    else:
        st.warning("Aucune faction disponible pour ce jeu")
        faction = None

    # Sélection des points
    points = st.number_input(
        "Points",
        min_value=game_config["min_points"],
        max_value=game_config["max_points"],
        value=game_config["default_points"],
        step=game_config["point_step"]
    )

    list_name = st.text_input("Nom de la liste", f"Liste_{datetime.now().strftime('%Y%m%d')}")

    # Import JSON
    uploaded = st.file_uploader("Importer une liste JSON", type=["json"])
    if uploaded:
        try:
            data = json.load(uploaded)
            if not all(key in data for key in ["game", "faction", "army_list", "points"]):
                st.error("Format JSON invalide: les clés 'game', 'faction', 'army_list' et 'points' sont requises")
                st.stop()

            # Vérification que les points de la liste importée ne dépassent pas la limite
            total_cost = data.get("total_cost", sum(u["cost"] for u in data["army_list"]))
            if total_cost > data["points"]:
                st.error(f"La liste importée dépasse sa limite de points ({data['points']} pts). Total actuel: {total_cost} pts")
                st.stop()

            st.session_state.game = data["game"]
            st.session_state.faction = data["faction"]
            st.session_state.points = data["points"]
            st.session_state.list_name = data["name"]
            st.session_state.army_list = data["army_list"]
            st.session_state.army_cost = total_cost
            st.session_state.units = factions_by_game[data["game"]][data["faction"]]["units"]
            st.session_state.page = "army"
            st.rerun()
        except Exception as e:
            st.error(f"Erreur d'import: {str(e)}")

    if st.button("Créer une nouvelle liste"):
        if not faction:
            st.error("Veuillez sélectionner une faction")
        else:
            st.session_state.game = game
            st.session_state.faction = faction
            st.session_state.points = points
            st.session_state.list_name = list_name
            st.session_state.units = factions_by_game[game][faction]["units"]
            st.session_state.army_list = []
            st.session_state.army_cost = 0
            st.session_state.page = "army"
            st.rerun()

# ======================================================
# PAGE 2 – CONSTRUCTEUR D'ARMÉE
# ======================================================
elif st.session_state.page == "army":
    st.title(st.session_state.list_name)
    st.caption(f"{st.session_state.game} • {st.session_state.faction} • {st.session_state.army_cost}/{st.session_state.points} pts")

    # Affichage de la barre de progression des points
    show_points_progress(st.session_state.army_cost, st.session_state.points)

    # Charger les données de faction pour les descriptions des règles
    faction_data = factions_by_game[st.session_state.game][st.session_state.faction]
    rules_descriptions = faction_data.get('special_rules_descriptions', {})

    # Afficher la légende des règles spéciales
    show_rules_legend(faction_data)

    if st.button("⬅ Retour"):
        st.session_state.page = "setup"
        st.rerun()

    # Ajout d'une unité
    st.divider()
    st.subheader("Ajouter une unité")

    # Sélection de l'unité
    unit = st.selectbox(
        "Unité disponible",
        st.session_state.units,
        format_func=format_unit_option,
        index=0,
        key="unit_select"
    )

    # Récupération de la taille de base de l'unité
    base_size = unit.get('size', 10)
    base_cost = unit["base_cost"]

    # Vérification du coût maximum AVANT les améliorations
    max_cost = st.session_state.points * GAME_CONFIG[st.session_state.game]["unit_max_cost_ratio"]
    if base_cost > max_cost:
        st.error(f"Cette unité ({base_cost} pts) dépasse la limite de {int(max_cost)} pts ({int(GAME_CONFIG[st.session_state.game]['unit_max_cost_ratio']*100)}% du total)")
        st.stop()

    # Initialisation
    weapon = unit.get("weapons", [{}])[0]
    selected_options = {}
    mount = None
    weapon_cost = 0
    mount_cost = 0
    upgrades_cost = 0

    # Gestion des unités combinées
    if unit.get("type") == "hero":
        combined = False  # Les héros ne peuvent JAMAIS être combinés
        st.markdown("**Les héros ne peuvent pas être combinés**")
    else:
        combined = st.checkbox("Unité combinée", value=False)

    # Options de l'unité
    for group in unit.get("upgrade_groups", []):
        st.markdown(f"**{group['group']}**")

        if group["type"] == "weapon":
            weapon_options = ["Arme de base"]
            for o in group["options"]:
                weapon_details = format_weapon_details(o["weapon"])
                cost_diff = o["cost"]
                weapon_options.append(f"{o['name']} (A{weapon_details['attacks']}, PA({weapon_details['ap']}){', ' + ', '.join(weapon_details['special']) if weapon_details['special'] else ''}) (+{cost_diff} pts)")

            selected_weapon = st.radio("Arme", weapon_options, key=f"{unit['name']}_weapon")
            if selected_weapon != "Arme de base":
                opt_name = selected_weapon.split(" (")[0]
                opt = next((o for o in group["options"] if o["name"] == opt_name), None)
                if opt:
                    weapon = opt["weapon"]
                    weapon_cost = opt["cost"]

        elif group["type"] == "mount":
            mount_labels = ["Aucune monture"]
            mount_map = {}

            for o in group["options"]:
                mount_details = format_mount_details(o)
                label = f"{mount_details} (+{o['cost']} pts)"
                mount_labels.append(label)
                mount_map[label] = o

            selected_mount = st.radio("Monture", mount_labels, key=f"{unit['name']}_mount")

            if selected_mount != "Aucune monture":
                opt = mount_map[selected_mount]
                mount = opt
                mount_cost = opt["cost"]

        else:  # Améliorations d'unité
            if group["group"] == "Améliorations de rôle":
                option_names = ["Aucune"] + [
                    f"{o['name']} (+{o['cost']} pts)" for o in group["options"]
                ]
                selected = st.radio(group["group"], option_names, key=f"{unit['name']}_{group['group']}")
                if selected != "Aucune":
                    opt_name = selected.split(" (+")[0]
                    opt = next((o for o in group["options"] if o["name"] == opt_name), None)
                    if opt:
                        if group["group"] not in selected_options:
                            selected_options[group["group"]] = []
                        selected_options[group["group"]].append(opt)
                        upgrades_cost += opt["cost"]
            else:
                st.write("Sélectionnez les améliorations (plusieurs choix possibles):")
                for o in group["options"]:
                    if st.checkbox(f"{o['name']} (+{o['cost']} pts)", key=f"{unit['name']}_{group['group']}_{o['name']}"):
                        if group["group"] not in selected_options:
                            selected_options[group["group"]] = []
                        if not any(opt.get("name") == o["name"] for opt in selected_options.get(group["group"], [])):
                            selected_options[group["group"]].append(o)
                            upgrades_cost += o["cost"]

    # Calcul du coût final
    if combined and unit.get("type") != "hero":
        # Pour les unités combinées, on double le coût de base + armes seulement
        final_cost = (base_cost + weapon_cost) * 2 + mount_cost + upgrades_cost
        unit_size = base_size * 2
    else:
        final_cost = base_cost + weapon_cost + mount_cost + upgrades_cost
        unit_size = base_size

    # Vérification du coût maximum par unité
    max_cost = st.session_state.points * GAME_CONFIG[st.session_state.game]["unit_max_cost_ratio"]
    if final_cost > max_cost:
        st.error(f"Cette unité ({final_cost} pts) dépasse la limite de {int(max_cost)} pts ({int(GAME_CONFIG[st.session_state.game]['unit_max_cost_ratio']*100)}% du total)")
        st.stop()

    # Vérification que l'ajout de cette unité ne dépasse pas la limite de points
    if not check_add_unit_points(st.session_state.army_cost, final_cost, st.session_state.points):
        st.stop()

    st.markdown(f"**Coût total: {final_cost} pts**")
    st.markdown(f"**Taille de l'unité: {unit_size} figurines**")

    if st.button("Ajouter à l'armée"):
        try:
            weapon_data = format_weapon_details(weapon)

            # Calcul de la coriace
            total_coriace = 0
            if 'special_rules' in unit and isinstance(unit.get('special_rules'), list):
                total_coriace += get_coriace_from_rules(unit['special_rules'])
            if mount:
                _, mount_coriace = get_mount_details(mount)
                total_coriace += mount_coriace
            if selected_options:
                for opts in selected_options.values():
                    if isinstance(opts, list):
                        for opt in opts:
                            if 'special_rules' in opt and isinstance(opt.get('special_rules'), list):
                                total_coriace += get_coriace_from_rules(opt['special_rules'])
            if 'special_rules' in weapon and isinstance(weapon.get('special_rules'), list):
                total_coriace += get_coriace_from_rules(weapon['special_rules'])
            if combined and unit.get('type') != "hero":
                base_coriace = get_coriace_from_rules(unit.get('special_rules', []))
                total_coriace += base_coriace

            total_coriace = total_coriace if total_coriace > 0 else None

            unit_data = {
                "name": unit["name"],
                "type": unit.get("type", "unit"),
                "cost": final_cost,
                "base_cost": base_cost,
                "size": unit_size,
                "quality": unit["quality"],
                "defense": unit["defense"],
                "rules": [format_special_rule(r) for r in unit.get("special_rules", [])],
                "weapon": weapon_data,
                "options": selected_options,
                "mount": mount,
                "coriace": total_coriace,
                "combined": combined and unit.get("type") != "hero",
            }

            # Vérification finale avant ajout
            test_army = st.session_state.army_list.copy()
            test_army.append(unit_data)
            test_total = st.session_state.army_cost + final_cost

            if test_total > st.session_state.points:
                st.error(f"Ajouter cette unité dépasserait votre limite de {st.session_state.points} pts. Il vous reste {st.session_state.points - st.session_state.army_cost} pts.")
                st.stop()

            # Vérification du coût maximum par unité
            if final_cost > st.session_state.points * GAME_CONFIG[st.session_state.game]["unit_max_cost_ratio"]:
                st.error(f"Cette unité ({final_cost} pts) dépasse la limite de {int(st.session_state.points * GAME_CONFIG[st.session_state.game]['unit_max_cost_ratio'])} pts ({int(GAME_CONFIG[st.session_state.game]['unit_max_cost_ratio']*100)}% du total)")
                st.stop()

            st.session_state.army_list.append(unit_data)
            st.session_state.army_cost += final_cost
            st.rerun()

        except Exception as e:
            st.error(f"Erreur lors de la création de l'unité: {str(e)}")

    # Liste de l'armée
    st.divider()
    st.subheader("Liste de l'armée")

    if not st.session_state.army_list:
        st.info("Ajoutez des unités pour commencer")

    for i, u in enumerate(st.session_state.army_list):
        show_unit_with_tabs(u, rules_descriptions)

        if st.button(f"Supprimer {u['name']}", key=f"del_{i}"):
            st.session_state.army_cost -= u["cost"]
            st.session_state.army_list.pop(i)
            st.rerun()

    # Sauvegarde/Export
    st.divider()
    col1, col2, col3 = st.columns(3)

    army_data = {
        "name": st.session_state.list_name,
        "game": st.session_state.game,
        "faction": st.session_state.faction,
        "points": st.session_state.points,
        "total_cost": st.session_state.army_cost,
        "army_list": st.session_state.army_list,
        "date": datetime.now().isoformat()
    }

    with col1:
        if st.button("Sauvegarder"):
            saved_lists = []
            try:
                existing_lists = ls_get("opr_saved_lists")
                if existing_lists:
                    saved_lists = json.loads(existing_lists)
            except:
                pass

            saved_lists.append(army_data)
            try:
                ls_set("opr_saved_lists", saved_lists)
            except:
                st.warning("La sauvegarde locale n'est pas disponible, mais vous pouvez exporter en JSON.")
            st.success("Liste sauvegardée!")

    with col2:
        st.download_button(
            "Exporter en JSON",
            json.dumps(army_data, indent=2, ensure_ascii=False),
            file_name=f"{st.session_state.list_name}.json",
            mime="application/json"
        )

    with col3:
        # EXPORT HTML avec barre de progression
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Liste OPR - {army_data['name']}</title>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 20px;
            color: #333;
        }}
        .army-title {{
            text-align: center;
            margin-bottom: 20px;
            color: #2c3e50;
        }}
        .army-info {{
            text-align: center;
            margin-bottom: 30px;
            color: #666;
        }}
        .unit-container {{
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 20px;
            padding: 20px;
            page-break-inside: avoid;
        }}
        .unit-header {{
            font-size: 1.5em;
            font-weight: bold;
            margin-bottom: 10px;
            color: #2c3e50;
            border-bottom: 1px solid #eee;
            padding-bottom: 10px;
        }}
        .hero-badge {{
            background-color: gold;
            color: black;
            padding: 2px 8px;
            border-radius: 10px;
            margin-left: 10px;
            font-weight: bold;
            font-size: 0.9em;
        }}
        .unit-stats {{
            display: flex;
            margin-bottom: 15px;
        }}
        .stat-badge {{
            background-color: #3498db;
            color: white;
            padding: 8px 12px;
            border-radius: 4px;
            margin-right: 10px;
            font-weight: bold;
            text-align: center;
            min-width: 80px;
        }}
        .stat-value {{
            font-size: 1.2em;
        }}
        .stat-label {{
            font-size: 0.8em;
            display: block;
            margin-bottom: 3px;
        }}
        .section-title {{
            font-weight: bold;
            margin: 15px 0 10px 0;
            color: #2c3e50;
            border-bottom: 1px solid #eee;
            padding-bottom: 5px;
        }}
        .weapon-table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 15px;
        }}
        .weapon-table th {{
            background-color: #f8f9fa;
            text-align: left;
            padding: 8px;
            border-bottom: 1px solid #ddd;
        }}
        .weapon-table td {{
            padding: 8px;
            border-bottom: 1px solid #eee;
        }}
        .rules-list {{
            margin: 10px 0;
        }}
        .special-rules {{
            font-style: italic;
            color: #555;
            margin-bottom: 15px;
        }}
        .unit-cost {{
            float: right;
            background-color: #3498db;
            color: white;
            padding: 5px 10px;
            border-radius: 4px;
            font-weight: bold;
        }}
        .progress-container {{
            width: 100%;
            background-color: #e0e0e0;
            border-radius: 4px;
            margin-bottom: 10px;
        }}
        .progress-bar {{
            height: 20px;
            border-radius: 4px;
            text-align: center;
            line-height: 20px;
            color: white;
        }}
        @media print {{
            .unit-container {{
                page-break-inside: avoid;
            }}
        }}
    </style>
</head>
<body>
    <h1 class="army-title">Liste d'armée OPR - {army_data['name']}</h1>
    <div class="army-info">
        <strong>Jeu:</strong> {army_data['game']} |
        <strong>Faction:</strong> {army_data['faction']} |
        <strong>Points:</strong> {army_data['total_cost']}/{army_data['points']} pts
    </div>

    <div class="progress-container">
        <div class="progress-bar" style="width: {min(100, int((army_data['total_cost']/army_data['points'])*100))}%; background-color: {'#4CAF50' if (army_data['total_cost']/army_data['points']) < 0.7 else '#FFC107' if (army_data['total_cost']/army_data['points']) < 0.9 else '#F44336'}">
            {min(100, int((army_data['total_cost']/army_data['points'])*100))}% ({army_data['total_cost']}/{army_data['points']} pts)
        </div>
    </div>
"""

        # Charger les descriptions des règles spéciales depuis le fichier de faction
        factions, _ = load_factions()
        faction_data = factions.get(army_data['game'], {}).get(army_data['faction'], {})
        rules_descriptions = faction_data.get('special_rules_descriptions', {})

        html_content += """
        <div class="section-title">Légende des règles spéciales</div>
        <div class="rules-legend">
        """

        # Ajouter une légende des règles spéciales utilisées dans cette armée
        used_rules = set()
        for unit in army_data['army_list']:
            if 'rules' in unit:
                used_rules.update(unit['rules'])
            if 'weapon' in unit and 'special_rules' in unit['weapon']:
                used_rules.update(unit['weapon']['special_rules'])

        # Ajouter les règles spéciales utilisées dans cette armée
        if used_rules:
            html_content += "<ul>"
            for rule in sorted(used_rules):
                description = rules_descriptions.get(rule, "Description non disponible")
                html_content += f"<li><strong>{rule}:</strong> {description}</li>"
            html_content += "</ul>"
        else:
            html_content += "<p>Aucune règle spéciale dans cette armée.</p>"

        html_content += """
        </div>
        """

        for unit in army_data['army_list']:
            rules = unit.get('rules', [])
            special_rules = ", ".join(rules) if rules else "Aucune"

            weapon_info = unit.get('weapon', {})
            if not isinstance(weapon_info, dict):
                weapon_info = {
                    "name": "Arme non spécifiée",
                    "attacks": "?",
                    "ap": "?",
                    "special": []
                }

            # Affichage du nom avec la taille FINAL de l'unité
            unit_name = f"{unit['name']} [{unit.get('size', 10)}]"
            unit_name = str(unit_name).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

            weapon_name = str(weapon_info['name']).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            weapon_attacks = str(weapon_info['attacks']).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            weapon_ap = str(weapon_info['ap']).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            weapon_special = ', '.join(weapon_info['special']) if weapon_info['special'] else '-'
            weapon_special = str(weapon_special).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

            # Badge héros si applicable
            hero_badge = ""
            if unit.get('type') == "hero":
                hero_badge = '<span class="hero-badge">HÉROS</span>'

            html_content += f"""
        <div class="unit-container">
            <div class="unit-header">
                {unit_name}
                {hero_badge}
                <span class="unit-cost">{unit['cost']} pts</span>
            </div>

            <div class="unit-stats">
                <div class="stat-badge">
                    <div class="stat-label">Qualité</div>
                    <div class="stat-value">{unit['quality']}+</div>
                </div>
                <div class="stat-badge">
                    <div class="stat-label">Défense</div>
                    <div class="stat-value">{unit.get('defense', '?')}+</div>
                </div>
"""

            if unit.get('coriace'):
                html_content += f"""
                <div class="stat-badge">
                    <div class="stat-label">Coriace</div>
                    <div class="stat-value">{unit['coriace']}</div>
                </div>
"""

            html_content += """
            </div>
"""

            if rules:
                html_content += f'<div class="special-rules"><strong>Règles spéciales:</strong> {special_rules.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")}</div>'

            html_content += f"""
            <div class="section-title">Arme</div>
            <table class="weapon-table">
                <thead>
                    <tr>
                        <th>Nom</th>
                        <th>PORT</th>
                        <th>ATK</th>
                        <th>PA</th>
                        <th>SPE</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>{weapon_name}</td>
                        <td>-</td>
                        <td>{weapon_attacks}</td>
                        <td>{weapon_ap}</td>
                        <td>{weapon_special}</td>
                    </tr>
                </tbody>
            </table>
"""

            if 'options' in unit and unit['options']:
                for group_name, opts in unit['options'].items():
                    if isinstance(opts, list) and opts:
                        group_name_clean = str(group_name).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                        html_content += f'<div class="section-title">{group_name_clean}:</div>'
                        for opt in opts:
                            opt_name = str(opt.get("name", "")).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                            html_content += f'<div>• {opt_name}</div>'

            if 'mount' in unit and unit['mount']:
                mount_details = format_mount_details(unit["mount"])
                mount_details_clean = str(mount_details).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                html_content += f'<div class="section-title">Monture</div><p>{mount_details_clean}</p>'

            html_content += "</div>"

        html_content += """
    </body>
</html>
"""

        st.download_button(
            "Exporter en HTML",
            html_content,
            file_name=f"{st.session_state.list_name}.html",
            mime="text/html"
        )
