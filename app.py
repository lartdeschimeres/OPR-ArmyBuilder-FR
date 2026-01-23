import json
import streamlit as st
from pathlib import Path
from datetime import datetime
import hashlib
import re
import copy
import math

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
        "hero_limit": 375,
        "unit_copy_rule": 750,
        "unit_max_cost_ratio": 0.35,
        "unit_per_points": 150
    },
    "Grimdark Future": {
        "display_name": "Grimdark Future",
        "max_points": 10000,
        "min_points": 200,
        "default_points": 800,
        "point_step": 200,
        "description": "Jeu de bataille futuriste",
        "hero_limit": 375,
        "unit_copy_rule": 750,
        "unit_max_cost_ratio": 0.35,
        "unit_per_points": 150
    }
}

# ======================================================
# FONCTION POUR AFFICHER LA BARRE DE PROGRESSION
# ======================================================
def show_points_progress(current_points, max_points):
    """Affiche une barre de progression pour les points"""
    if max_points <= 0:
        progress = 0
    else:
        progress = min(100, (current_points / max_points) * 100)

    remaining_points = max_points - current_points

    if progress < 70:
        color = "#4CAF50"
    elif progress < 90:
        color = "#FFC107"
    elif progress < 100:
        color = "#F44336"
    else:
        color = "#2E7D32"

    st.markdown(
        f"""
        <div style="width: 100%; margin: 10px 0 20px 0;">
            <div style="background-color: #e0e0e0; border-radius: 4px; height: 20px; margin-bottom: 5px;">
                <div style="width: {progress}%; background-color: {color}; border-radius: 4px; height: 100%;"></div>
            </div>
            <div style="display: flex; justify-content: space-between; font-size: 0.9em;">
                <span><strong>{current_points}/{max_points} pts</strong> ({int(progress)}%)</span>
                <span><strong>Reste:</strong> {remaining_points} pts</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    if current_points == max_points:
        st.success("✅ Liste valide! Vous avez atteint exactement votre limite de points.")

# ======================================================
# FONCTIONS POUR LES RÈGLES SPÉCIFIQUES
# ======================================================
def check_army_points(army_list, army_points):
    """Vérifie que le total des points ne dépasse pas la limite"""
    total = sum(unit["cost"] for unit in army_list)
    if total > army_points:
        return False, f"Limite de points dépassée! Maximum autorisé: {army_points} pts. Total actuel: {total} pts"
    return True, ""

def check_hero_limit(army_list, army_points, game_config):
    """Vérifie la limite de héros"""
    if game_config.get("hero_limit"):
        max_heroes = math.floor(army_points / game_config["hero_limit"])
        hero_count = sum(1 for unit in army_list if unit.get("type") == "hero")

        if hero_count > max_heroes:
            return False, f"Limite de héros dépassée! Maximum autorisé: {max_heroes} (1 héros par {game_config['hero_limit']} pts)"
    return True, ""

def check_unit_copy_rule(army_list, army_points, game_config):
    """Vérifie la règle des copies d'unités"""
    if game_config.get("unit_copy_rule"):
        x_value = math.floor(army_points / game_config["unit_copy_rule"])
        max_copies = 1 + x_value

        unit_counts = {}
        for unit in army_list:
            unit_name = unit["name"]
            unit_counts[unit_name] = unit_counts.get(unit_name, 0) + 1

        for unit_name, count in unit_counts.items():
            if count > max_copies:
                return False, f"Trop de copies de l'unité! Maximum autorisé: {max_copies} (1+{x_value} pour {game_config['unit_copy_rule']} pts)"
    return True, ""

def check_unit_max_cost(unit_cost, army_points, game_config):
    """Vérifie qu'une unité ne dépasse pas le ratio maximum de coût"""
    if game_config.get("unit_max_cost_ratio"):
        max_cost = army_points * game_config["unit_max_cost_ratio"]
        if unit_cost > max_cost:
            return False, f"Cette unité ({unit_cost} pts) dépasse la limite de {int(max_cost)} pts ({int(game_config['unit_max_cost_ratio']*100)}% du total)"
    return True, ""

def check_unit_per_points(army_list, army_points, game_config):
    """Vérifie le nombre maximum d'unités par tranche de points"""
    if game_config.get("unit_per_points"):
        max_units = math.floor(army_points / game_config["unit_per_points"])
        if len(army_list) > max_units:
            return False, f"Trop d'unités! Maximum autorisé: {max_units} (1 unité par {game_config['unit_per_points']} pts)"
    return True, ""

def validate_army_rules(army_list, army_points, game):
    """Valide toutes les règles spécifiques au jeu"""
    game_config = GAME_CONFIG.get(game, {})
    errors = []

    if game in GAME_CONFIG:
        total_cost = sum(unit["cost"] for unit in army_list)
        if total_cost > army_points:
            errors.append(f"Limite de points dépassée! Maximum autorisé: {army_points} pts. Total actuel: {total_cost} pts")

        valid, msg = check_hero_limit(army_list, army_points, game_config)
        if not valid: errors.append(msg)

        valid, msg = check_unit_copy_rule(army_list, army_points, game_config)
        if not valid: errors.append(msg)

        valid, msg = check_unit_per_points(army_list, army_points, game_config)
        if not valid: errors.append(msg)

    return len(errors) == 0, errors

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
    return sum(extract_coriace_value(rule) for rule in rules)

def get_mount_details(mount):
    """Récupère les détails d'une monture"""
    if not mount:
        return None, 0
    mount_data = mount['mount'] if 'mount' in mount else mount
    special_rules = mount_data.get('special_rules', [])
    return special_rules, get_coriace_from_rules(special_rules)

def format_weapon_details(weapon):
    """Formate les détails d'une arme pour l'affichage"""
    if not weapon:
        return {"name": "Arme non spécifiée", "attacks": "?", "ap": "?", "special": []}
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

    mount_data = mount['mount'] if 'mount' in mount else mount
    details = mount_data.get('name', 'Monture non nommée')

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
            details += f" | {weapon.get('name', 'Arme')} (A{weapon_details['attacks']}, PA({weapon_details['ap']})"
            if weapon_details['special']:
                details += ", " + ", ".join(weapon_details['special'])
            details += ")"

    return details

def format_unit_option(u):
    """Formate l'affichage des unités dans la liste déroulante"""
    name_part = f"{u['name']}"
    name_part += " [1]" if u.get('type') == "hero" else f" [{u.get('size', 10)}]"

    coriace = get_coriace_from_rules(u.get('special_rules', []))
    if 'mount' in u and u['mount']:
        _, mount_coriace = get_mount_details(u['mount'])
        coriace += mount_coriace

    qua_def_coriace = f"Qua {u['quality']}+ / Déf {u.get('defense', '?')}"
    if coriace > 0:
        qua_def_coriace += f" / Coriace {coriace}"

    weapons_part = ""
    if 'weapons' in u and u['weapons']:
        weapons = []
        for weapon in u['weapons']:
            weapon_details = format_weapon_details(weapon)
            weapons.append(f"{weapon.get('name', 'Arme')} (A{weapon_details['attacks']}, PA({weapon_details['ap']}){', ' + ', '.join(weapon_details['special']) if weapon_details['special'] else ''})")
        weapons_part = " | ".join(weapons)

    rules_part = ", ".join(u['special_rules']) if 'special_rules' in u and u['special_rules'] else ""

    result = f"{name_part} - {qua_def_coriace}"
    if weapons_part:
        result += f" - {weapons_part}"
    if rules_part:
        result += f" - {rules_part}"
    result += f" {u['base_cost']}pts"

    return result

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
    except Exception:
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
    except Exception:
        pass

# ======================================================
# CHARGEMENT DES FACTIONS
# ======================================================
@st.cache_data
def load_factions():
    """Charge les factions depuis les fichiers JSON"""
    factions = {}
    games = set()

    # Factions par défaut
    default_factions = {
        "Age of Fantasy": {
            "Disciples de la Guerre": {
                "game": "Age of Fantasy",
                "faction": "Disciples de la Guerre",
                "special_rules_descriptions": {
                    "Éclaireur": "Déplacement facilité en terrain difficile.",
                    "Furieux": "Relance les 1 en attaque.",
                    "Né pour la guerre": "Relance les 1 en test de moral.",
                    "Héros": "Personnage inspirant.",
                    "Coriace(1)": "Ignore 1 point de dégât par phase.",
                    "Magique(1)": "Ignore 1 point de défense.",
                    "Contre-charge": "+1 aux jets de dégât lors d'une charge."
                },
                "units": [
                    {
                        "name": "Troupe d'infanterie",
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
                                        "cost": 5,
                                        "weapon": {
                                            "name": "Lance",
                                            "attacks": 1,
                                            "armor_piercing": 0,
                                            "special_rules": ["Contre-charge"]
                                        }
                                    }
                                ]
                            },
                            {
                                "group": "Améliorations d'unité",
                                "type": "upgrades",
                                "options": [
                                    {
                                        "name": "Maître Sorcier",
                                        "cost": 60,
                                        "special_rules": ["Lanceur de sorts (3)"]
                                    }
                                ]
                            },
                            {
                                "group": "Montures",
                                "type": "mount",
                                "options": [
                                    {
                                        "name": "Cheval",
                                        "cost": 15,
                                        "mount": {
                                            "name": "Cheval",
                                            "quality": 3,
                                            "defense": 3,
                                            "special_rules": []
                                        }
                                    },
                                    {
                                        "name": "Manticore",
                                        "cost": 155,
                                        "mount": {
                                            "name": "Manticore",
                                            "quality": 4,
                                            "defense": 4,
                                            "special_rules": ["Volant", "Effrayant(1)", "Coriace(6)"],
                                            "weapons": [
                                                {
                                                    "name": "Griffes perforantes",
                                                    "attacks": 6,
                                                    "armor_piercing": 1,
                                                    "special_rules": ["Perforant"]
                                                }
                                            ]
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        }
    }

    # Charger les factions depuis les fichiers
    files_loaded = 0
    if FACTIONS_DIR.exists():
        for fp in FACTIONS_DIR.glob("*.json"):
            try:
                with open(fp, encoding="utf-8") as f:
                    data = json.load(f)
                    game = data.get("game")
                    faction = data.get("faction")

                    if game and faction:
                        if game not in factions:
                            factions[game] = {}
                            games.add(game)

                        factions[game][faction] = data
                        files_loaded += 1
                        st.info(f"Faction chargée: {faction} ({game}) depuis {fp.name}")

            except Exception as e:
                st.warning(f"Erreur chargement {fp.name}: {e}")

    if files_loaded > 0:
        st.info(f"Chargé {files_loaded} factions depuis les fichiers")
    else:
        st.warning("Aucun fichier de faction valide trouvé. Utilisation des factions par défaut.")
        factions = default_factions
        games = set(factions.keys())

    if "Age of Fantasy" not in factions or not factions["Age of Fantasy"]:
        if "Age of Fantasy" not in factions:
            factions["Age of Fantasy"] = {}
        factions["Age of Fantasy"].update(default_factions["Age of Fantasy"])
        games.add("Age of Fantasy")

    return factions, sorted(games) if games else ["Age of Fantasy"]

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
    st.session_state.history = []
    st.session_state.undo_disabled = True

# ======================================================
# PAGE 1 – CONFIGURATION
# ======================================================
if st.session_state.page == "setup":
    st.title("OPR Army Forge FR")

    # Affichage des jeux disponibles
    st.subheader("Jeux disponibles")
    for game_key, config in GAME_CONFIG.items():
        with st.expander(f"📖 {config['display_name']}"):
            st.markdown(f"**Description**: {config['description']}")
            st.markdown(f"- **Points**: {config['min_points']} à {config['max_points']} (défaut: {config['default_points']})")

    # Liste des listes sauvegardées
    st.subheader("Mes listes sauvegardées")
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
                            st.session_state.history = []
                            st.session_state.undo_disabled = True
                            st.rerun()
        except Exception as e:
            st.error(f"Erreur chargement listes: {e}")

    # Sélection du jeu
    game = st.selectbox("Jeu", games)
    game_config = GAME_CONFIG.get(game, GAME_CONFIG["Age of Fantasy"])

    # Sélection de la faction
    if game in factions_by_game and factions_by_game[game]:
        available_factions = list(factions_by_game[game].keys())
        faction = st.selectbox("Faction", available_factions)
    else:
        st.error(f"Aucune faction disponible pour {game}")
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
                st.error("Format JSON invalide")
                st.stop()

            total_cost = data.get("total_cost", sum(u["cost"] for u in data["army_list"]))
            if total_cost > data["points"]:
                st.error(f"Limite de points dépassée ({total_cost}/{data['points']})")
                st.stop()

            st.session_state.game = data["game"]
            st.session_state.faction = data["faction"]
            st.session_state.points = data["points"]
            st.session_state.list_name = data["name"]
            st.session_state.army_list = data["army_list"]
            st.session_state.army_cost = total_cost
            st.session_state.units = factions_by_game[data["game"]][data["faction"]]["units"]
            st.session_state.page = "army"
            st.session_state.history = []
            st.session_state.undo_disabled = True
            st.rerun()
        except Exception as e:
            st.error(f"Erreur d'import: {str(e)}")

    if st.button("Créer une nouvelle liste") and faction:
        st.session_state.game = game
        st.session_state.faction = faction
        st.session_state.points = points
        st.session_state.list_name = list_name
        st.session_state.units = factions_by_game[game][faction]["units"]
        st.session_state.army_list = []
        st.session_state.army_cost = 0
        st.session_state.history = []
        st.session_state.undo_disabled = True
        st.session_state.page = "army"
        st.rerun()

# ======================================================
# PAGE 2 – CONSTRUCTEUR D'ARMÉE
# ======================================================
elif st.session_state.page == "army":
    st.title(st.session_state.list_name)
    st.caption(f"{st.session_state.game} • {st.session_state.faction} • {st.session_state.army_cost}/{st.session_state.points} pts")

    # Affichage de la barre de progression
    show_points_progress(st.session_state.army_cost, st.session_state.points)

    # Charger les données de faction
    faction_data = factions_by_game[st.session_state.game][st.session_state.faction]
    rules_descriptions = faction_data.get('special_rules_descriptions', {})

    # Boutons de contrôle
    col_undo, col_reset, col_spacer = st.columns([1, 1, 2])
    with col_undo:
        if st.button("↩ Annuler la dernière action", disabled=st.session_state.undo_disabled):
            if st.session_state.history:
                previous_state = st.session_state.history.pop()
                st.session_state.army_list = copy.deepcopy(previous_state["army_list"])
                st.session_state.army_cost = previous_state["army_cost"]

                if not st.session_state.history:
                    st.session_state.undo_disabled = True

                st.rerun()

    with col_reset:
        if st.button("🗑 Réinitialiser la liste", key="reset_list"):
            st.session_state.army_list = []
            st.session_state.army_cost = 0
            st.session_state.history = []
            st.session_state.undo_disabled = True
            st.rerun()

    if st.button("⬅ Retour"):
        st.session_state.page = "setup"
        st.rerun()

    # Ajout d'une unité
    st.divider()
    st.subheader("Ajouter une unité")

    unit = st.selectbox(
        "Unité disponible",
        st.session_state.units,
        format_func=format_unit_option,
        index=0,
        key="unit_select"
    )

    base_size = unit.get('size', 10)
    base_cost = unit["base_cost"]

    weapon = unit.get("weapons", [{}])[0]
    selected_options = {}
    mount = None
    weapon_cost = 0
    mount_cost = 0
    upgrades_cost = 0

    if unit.get("type") == "hero":
        combined = False
        st.markdown("**Les héros ne peuvent pas être combinés**")
    else:
        combined = st.checkbox("Unité combinée", value=False)

    # Gestion des améliorations
    for group in unit.get("upgrade_groups", []):
        st.markdown(f"**{group['group']}**")

        if group["type"] == "weapon":
            weapon_options = ["Arme de base"]
            for o in group["options"]:
                weapon_details = format_weapon_details(o["weapon"])
                cost_diff = o["cost"]
                weapon_options.append(f"{o['name']} (+{cost_diff} pts)")

            selected_weapon = st.radio("Arme", weapon_options, key=f"{unit['name']}_weapon")
            if selected_weapon != "Arme de base":
                opt_name = selected_weapon.split(" (+")[0]
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

            if selected_mount != "Aucune monture" and selected_mount in mount_map:
                mount = mount_map[selected_mount]
                mount_cost = mount["cost"]
            else:
                mount = None
                mount_cost = 0

        else:  # Améliorations d'unité
            st.write("Sélectionnez les améliorations:")
            for o in group["options"]:
                if st.checkbox(f"{o['name']} (+{o['cost']} pts)", key=f"{unit['name']}_{group['group']}_{o['name']}"):
                    if group["group"] not in selected_options:
                        selected_options[group["group"]] = []
                    selected_options[group["group"]] = [o]
                    upgrades_cost = o["cost"]

    if combined and unit.get("type") != "hero":
        final_cost = (base_cost + weapon_cost) * 2 + mount_cost + upgrades_cost
        unit_size = base_size * 2
    else:
        final_cost = base_cost + weapon_cost + mount_cost + upgrades_cost
        unit_size = base_size

    st.markdown(f"**Coût total: {final_cost} pts**")
    st.markdown(f"**Taille de l'unité: {unit_size} figurines**")

    if st.button("Ajouter à l'armée"):
        try:
            # Sauvegarder l'état actuel avant l'ajout
            st.session_state.history.append({
                "army_list": copy.deepcopy(st.session_state.army_list),
                "army_cost": st.session_state.army_cost
            })
            st.session_state.undo_disabled = False

            weapon_data = format_weapon_details(weapon)
            total_coriace = calculate_total_coriace({
                "special_rules": unit.get('special_rules', []),
                "mount": mount,
                "options": selected_options,
                "weapon": weapon,
                "type": unit.get('type'),
                "combined": combined
            })

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

            # Ajouter temporairement l'unité pour vérifier les règles
            test_army = copy.deepcopy(st.session_state.army_list)
            test_army.append(unit_data)
            test_cost = st.session_state.army_cost + final_cost

            # Vérifier les règles APRES l'ajout
            valid, errors = validate_army_rules(test_army, st.session_state.points, st.session_state.game)

            if not valid:
                for error in errors:
                    st.error(error)
                # Ne pas ajouter l'unité si les règles ne sont pas respectées
                st.stop()

            # Si tout est valide, ajouter l'unité
            st.session_state.army_list.append(unit_data)
            st.session_state.army_cost += final_cost
            st.rerun()

        except Exception as e:
            st.error(f"Erreur: {str(e)}")

    # Liste de l'armée
    st.divider()
    st.subheader("Liste de l'armée")

    if not st.session_state.army_list:
        st.info("Ajoutez des unités pour commencer")

    for i, u in enumerate(st.session_state.army_list):
        with st.expander(f"{u['name']} [{u.get('size', 10)}] ({u['cost']} pts)"):
            col1, col2 = st.columns(2)

            with col1:
                st.markdown(f"**Qualité:** {u['quality']}+")
                st.markdown(f"**Défense:** {u.get('defense', '?')}+")

                if 'rules' in u and u['rules']:
                    st.markdown("**Règles spéciales:**")
                    for rule in u['rules']:
                        st.markdown(f"- {rule}")

            with col2:
                if 'weapon' in u and u['weapon']:
                    weapon = u['weapon']
                    st.markdown(f"**Arme:** {weapon.get('name', 'Arme non nommée')}")
                    st.markdown(f"ATK: {weapon.get('attacks', '?')}, PA: {weapon.get('armor_piercing', '?')}")

            if st.button(f"Supprimer {u['name']}", key=f"del_{i}"):
                # Sauvegarder l'état avant suppression
                st.session_state.history.append({
                    "army_list": copy.deepcopy(st.session_state.army_list),
                    "army_cost": st.session_state.army_cost
                })
                st.session_state.undo_disabled = False

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
            ls_set("opr_saved_lists", saved_lists)
            st.success("Liste sauvegardée!")

    with col2:
        st.download_button(
            "Exporter en JSON",
            json.dumps(army_data, indent=2, ensure_ascii=False),
            file_name=f"{st.session_state.list_name}.json",
            mime="application/json"
        )

    with col3:
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Liste OPR - {army_data['name']}</title>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .unit {{ margin-bottom: 20px; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
        .progress {{ width: 100%; background-color: #e0e0e0; border-radius: 4px; margin: 10px 0; }}
        .progress-bar {{ height: 20px; border-radius: 4px; }}
    </style>
</head>
<body>
    <h1>Liste d'armée: {army_data['name']}</h1>
    <p>{army_data['game']} • {army_data['faction']} • {army_data['total_cost']}/{army_data['points']} pts</p>

    <div class="progress">
        <div class="progress-bar" style="width: {min(100, int((army_data['total_cost']/army_data['points'])*100))}%; background-color: {'#4CAF50' if (army_data['total_cost']/army_data['points']) < 0.9 else '#2E7D32'}"></div>
    </div>
"""

        for unit in army_data['army_list']:
            rules = ", ".join(unit.get('rules', [])) if unit.get('rules') else "Aucune"
            weapon_name = unit.get('weapon', {}).get('name', 'Arme non spécifiée') if 'weapon' in unit else 'Aucune'

            html_content += f"""
    <div class="unit">
        <h3>{unit['name']} [{unit.get('size', 10)}] ({unit['cost']} pts)</h3>
        <p>Qualité: {unit['quality']}+ | Défense: {unit.get('defense', '?')}+ | {rules}</p>
        <p>Arme: {weapon_name}</p>
    </div>
"""

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
