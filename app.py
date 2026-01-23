import json
import streamlit as st
from pathlib import Path
from datetime import datetime
import hashlib
import re
import copy
import math

# ======================================================
# CONFIGURATION POUR SIMON JOINVILLE FOUQUET
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
# CONFIGURATION DES JEUX
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
    }
}

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

def format_weapon_details(weapon):
    """Formate les détails d'une arme avec toutes ses caractéristiques"""
    if not weapon:
        return {
            "name": "Arme non spécifiée",
            "attacks": 1,
            "ap": 0,
            "special": [],
            "formatted": "Arme non spécifiée (ATK: 1, PA: 0)"
        }

    weapon_details = {
        "name": weapon.get('name', 'Arme non nommée'),
        "attacks": weapon.get('attacks', 1),
        "ap": weapon.get('armor_piercing', 0),
        "special": weapon.get('special_rules', []),
    }

    # Formatage complet des caractéristiques
    details = f"{weapon_details['name']} (ATK: {weapon_details['attacks']}, PA: {weapon_details['ap']})"
    if weapon_details['special']:
        details += ", " + ", ".join(weapon_details['special'])

    weapon_details['formatted'] = details
    return weapon_details

def format_mount_details(mount):
    """Formate les détails d'une monture"""
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
            details += f" | {weapon_details['formatted']}"

    return details

def format_unit_option(u):
    """Formate l'affichage des unités DISPONIBLES dans la liste déroulante"""
    name_part = f"{u['name']}"
    name_part += " [1]" if u.get('type') == "hero" else f" [{u.get('size', 10)}]"

    qua_def = f"Qualité: {u['quality']}+ | Défense: {u.get('defense', '?')}"

    # Règles spéciales
    rules_part = ""
    if 'special_rules' in u and u['special_rules']:
        rules_part = "<br><strong>Règles spéciales:</strong> " + ", ".join(u['special_rules'])

    # Arme avec toutes ses caractéristiques
    weapons_part = ""
    if 'weapons' in u and u['weapons']:
        weapons = []
        for weapon in u['weapons']:
            weapon_details = format_weapon_details(weapon)
            weapons.append(weapon_details['formatted'])
        weapons_part = "<br><strong>Arme:</strong> " + " | ".join(weapons)

    return f"""
    <div style="border: 1px solid #ddd; padding: 10px; margin-bottom: 10px; border-radius: 5px;">
        <div style="display: flex; justify-content: space-between;">
            <h4 style="margin: 0;">{name_part}</h4>
            <span style="background-color: #3498db; color: white; padding: 2px 6px; border-radius: 3px;">
                {u.get('base_cost', '?')} pts
            </span>
        </div>
        <div style="margin-top: 5px;">
            <strong>{qua_def}</strong>
            {rules_part}
            {weapons_part}
        </div>
    </div>
    """

def format_unit_display(u):
    """Formate l'affichage des unités DÉJÀ AJOUTÉES comme dans votre capture"""
    name_part = f"{u['name']} [{u.get('size', 10)}]"

    # Qualité/Défense
    qua_def = f"Qualité: {u['quality']}+ | Défense: {u.get('defense', '?')}+"

    # Règles spéciales
    rules_part = ""
    if 'rules' in u and u['rules']:
        rules_part = f"""
        <div style='margin: 5px 0;'>
            <strong>Règles spéciales:</strong> {', '.join(u['rules'])}
        </div>
        """

    # Arme avec toutes ses caractéristiques
    weapon_part = ""
    if 'weapon' in u and u['weapon']:
        weapon_details = format_weapon_details(u['weapon'])
        weapon_part = f"""
        <div style='margin: 5px 0;'>
            <strong>Arme:</strong> {weapon_details['formatted']}
        </div>
        """

    # Monture
    mount_part = ""
    if 'mount' in u and u['mount']:
        mount_details = format_mount_details(u['mount'])
        mount_part = f"""
        <div style='margin: 5px 0;'>
            <strong>Monture:</strong> {mount_details}
        </div>
        """

    # Options/Améliorations
    options_part = ""
    if 'options' in u and u['options']:
        for group_name, opts in u['options'].items():
            if isinstance(opts, list) and opts:
                options_part += f"""
                <div style='margin: 5px 0;'>
                    <strong>{group_name}:</strong> {', '.join(opt.get('name', '') for opt in opts)}
                </div>
                """

    # Coût
    cost_part = f"""
    <div style='float:right; background-color: #3498db; color: white;
                padding: 2px 6px; border-radius: 3px;'>
        {u.get('cost', '?')} pts
    </div>
    """

    return f"""
    <div style='border: 1px solid #ddd; padding: 10px; margin-bottom: 10px; border-radius: 5px;'>
        <div style='display: flex; justify-content: space-between;'>
            <h4 style='margin: 0;'>{name_part}</h4>
            {cost_part}
        </div>
        <div style='margin-top: 5px;'>
            <div style='margin: 5px 0;'>{qua_def}</div>
            {rules_part}
            {weapon_part}
            {mount_part}
            {options_part}
        </div>
    </div>
    """

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

def validate_army_rules(army_list, army_points, game):
    """Valide toutes les règles spécifiques au jeu"""
    game_config = GAME_CONFIG.get(game, {})
    errors = []

    if game in GAME_CONFIG:
        total_cost = sum(unit["cost"] for unit in army_list)
        if total_cost > army_points:
            errors.append(f"Limite de points dépassée! Maximum autorisé: {army_points} pts. Total actuel: {total_cost} pts")

    return len(errors) == 0, errors

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
# FONCTION POUR GÉNÉRER L'EXPORT HTML (AMÉLIORÉE)
# ======================================================
def generate_html_export(army_data, factions_by_game):
    """Génère un export HTML qui correspond exactement à vos captures d'écran"""
    faction_data = factions_by_game[army_data['game']][army_data['faction']]
    rules_descriptions = faction_data.get('special_rules_descriptions', {})

    # Collecter toutes les règles spéciales utilisées
    used_rules = set()
    for unit in army_data['army_list']:
        if 'rules' in unit:
            used_rules.update(unit['rules'])
        if 'weapon' in unit and 'special_rules' in unit['weapon']:
            used_rules.update(unit['weapon']['special_rules'])
        if 'mount' in unit and unit['mount']:
            mount_data = unit['mount']['mount'] if 'mount' in unit['mount'] else unit['mount']
            if 'special_rules' in mount_data:
                used_rules.update(mount_data['special_rules'])

    # Générer la légende des règles
    rules_legend = ""
    if used_rules:
        rules_legend = """
        <div style="background-color: #f8f9fa; padding: 15px; border-radius: 6px; margin: 20px 0;">
            <h3 style="margin-top: 0;">Légende des règles spéciales</h3>
            <table style="width: 100%; border-collapse: collapse;">
        """
        for rule in sorted(used_rules):
            description = rules_descriptions.get(rule, "Description non disponible")
            rules_legend += f"""
            <tr>
                <td style="padding: 5px; border-bottom: 1px solid #eee; width: 30%;"><strong>{rule}</strong></td>
                <td style="padding: 5px; border-bottom: 1px solid #eee;">{description}</td>
            </tr>
            """
        rules_legend += "</table></div>"

    # Générer les unités avec le format exact de votre capture
    units_html = ""
    for unit in army_data['army_list']:
        # Qualité/Défense
        qua_def = f"Qualité: {unit['quality']}+ | Défense: {unit.get('defense', '?')}+"

        # Règles spéciales
        rules_list = ""
        if 'rules' in unit and unit['rules']:
            rules_list = f"""
            <div style="margin: 5px 0;">
                <strong>Règles spéciales:</strong> {', '.join(unit['rules'])}
            </div>
            """

        # Arme avec toutes ses caractéristiques
        weapon_html = ""
        if 'weapon' in unit and unit['weapon']:
            weapon_details = format_weapon_details(unit['weapon'])
            weapon_html = f"""
            <div style="margin: 5px 0;">
                <strong>Arme:</strong> {weapon_details['formatted']}
            </div>
            """

        # Monture
        mount_html = ""
        if 'mount' in unit and unit['mount']:
            mount_details = format_mount_details(unit['mount'])
            mount_html = f"""
            <div style="margin: 5px 0;">
                <strong>Monture:</strong> {mount_details}
            </div>
            """

        # Options/Améliorations
        options_html = ""
        if 'options' in unit and unit['options']:
            for group_name, opts in unit['options'].items():
                if isinstance(opts, list) and opts:
                    options_html += f"""
                    <div style="margin: 5px 0;">
                        <strong>{group_name}:</strong> {', '.join(opt.get('name', '') for opt in opts)}
                    </div>
                    """

        units_html += f"""
        <div style="background-color: white; border: 1px solid #ddd; border-radius: 6px;
                    padding: 15px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <div style="display: flex; justify-content: space-between; align-items: center;
                        margin-bottom: 10px; border-bottom: 1px solid #eee; padding-bottom: 5px;">
                <h3 style="margin: 0; color: #2c3e50;">{unit['name']} [{unit.get('size', 10)}]</h3>
                <div style="background-color: #3498db; color: white; padding: 3px 8px;
                            border-radius: 4px; font-weight: bold;">{unit['cost']} pts</div>
            </div>

            <div style="margin-top: 5px;">
                <div style="margin: 5px 0;">{qua_def}</div>
                {rules_list}
                {weapon_html}
                {mount_html}
                {options_html}
            </div>
        </div>
        """

    html_content = f"""
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Liste d'armée OPR - {army_data['name']}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }}
        .army-header {{
            text-align: center;
            margin-bottom: 30px;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
        }}
        .army-title {{
            color: #2c3e50;
            margin-bottom: 5px;
        }}
        .army-info {{
            color: #666;
            font-size: 0.9em;
        }}
        .progress-container {{
            width: 100%;
            background-color: #e0e0e0;
            border-radius: 4px;
            margin: 20px 0;
            height: 20px;
        }}
        .progress-bar {{
            height: 100%;
            border-radius: 4px;
            text-align: right;
            padding-right: 10px;
            color: white;
            font-size: 0.8em;
            line-height: 20px;
        }}
        @media print {{
            .unit-container {{
                page-break-inside: avoid;
            }}
        }}
    </style>
</head>
<body>
    <div class="army-header">
        <h1 class="army-title">Liste d'armée OPR - {army_data['name']}</h1>
        <div class="army-info">
            {army_data['game']} • {army_data['faction']} • {army_data['total_cost']}/{army_data['points']} pts
        </div>
    </div>

    <div class="progress-container">
        <div class="progress-bar" style="width: {min(100, (army_data['total_cost']/army_data['points'])*100)}%;
                                              background-color: {'#2E7D32' if army_data['total_cost'] == army_data['points'] else '#4CAF50' if (army_data['total_cost']/army_data['points']) < 0.9 else '#FFC107' if (army_data['total_cost']/army_data['points']) < 1 else '#F44336'}">
            {min(100, int((army_data['total_cost']/army_data['points'])*100))}% ({army_data['total_cost']}/{army_data['points']} pts)
        </div>
    </div>

    {rules_legend}

    <h2 style="color: #2c3e50; border-bottom: 1px solid #eee; padding-bottom: 5px;">Composition de l'armée</h2>
    {units_html}
</body>
</html>
"""
    return html_content

# ======================================================
# CHARGEMENT DES FACTIONS
# ======================================================
@st.cache_data
def load_factions():
    """Charge les factions avec des données corrigées"""
    factions = {}
    games = set()

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
                    "Contre-charge": "+1 aux jets de dégât lors d'une charge.",
                    "Attaque venimeuse": "Les blessures infligées par cette unité ne peuvent pas être régénérées.",
                    "Perforant": "Ignore 1 point de défense supplémentaire.",
                    "Volant": "Peut voler par-dessus les obstacles et les unités.",
                    "Effrayant(1)": "Les unités ennemies à 6\" doivent passer un test de moral ou reculer de 3\".",
                    "Lanceur de sorts (3)": "Peut lancer 3 sorts par tour."
                },
                "units": [
                    {
                        "name": "Maître de la Guerre Élu",
                        "type": "hero",
                        "size": 1,
                        "base_cost": 150,
                        "quality": 3,
                        "defense": 5,
                        "special_rules": ["Héros", "Éclaireur", "Furieux", "Né pour la guerre"],
                        "weapons": [{
                            "name": "Grande arme lourde",
                            "attacks": 4,
                            "armor_piercing": 0,
                            "special_rules": []
                        }],
                        "upgrade_groups": [
                            {
                                "group": "Montures",
                                "type": "mount",
                                "options": [
                                    {
                                        "name": "Dragon du Ravage",
                                        "cost": 155,
                                        "mount": {
                                            "name": "Dragon du Ravage",
                                            "quality": 4,
                                            "defense": 4,
                                            "special_rules": ["Volant", "Effrayant(1)", "Coriace(6)"],
                                            "weapons": [
                                                {
                                                    "name": "Griffes et crocs",
                                                    "attacks": 6,
                                                    "armor_piercing": 1,
                                                    "special_rules": ["Perforant"]
                                                },
                                                {
                                                    "name": "Souffle de feu",
                                                    "attacks": 1,
                                                    "armor_piercing": 0,
                                                    "special_rules": ["Attaque de souffle"]
                                                }
                                            ]
                                        }
                                    }
                                ]
                            },
                            {
                                "group": "Améliorations de rôle",
                                "type": "upgrades",
                                "options": [
                                    {
                                        "name": "Porteur de la bannière de l'armée",
                                        "cost": 60,
                                        "special_rules": ["Effrayant(3)"]
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        }
    }

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
    st.session_state.current_player = "Simon Joinville Fouquet"
    st.session_state.history = []
    st.session_state.undo_disabled = True

# ======================================================
# PAGE 1 – CONFIGURATION
# ======================================================
if st.session_state.page == "setup":
    st.title("OPR Army Forge FR")

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

    # Chargement des listes sauvegardées
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

    # Boutons de contrôle
    col_undo, col_reset = st.columns([1, 1])
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
        if st.button("🗑 Réinitialiser la liste"):
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

    # Sélection de l'unité
    unit = st.selectbox(
        "Unité disponible",
        st.session_state.units,
        format_func=format_unit_option,
        index=0,
        key="unit_select"
    )

    base_size = unit.get('size', 10)
    base_cost = unit["base_cost"]

    # Gestion des options
    weapon = unit.get("weapons", [{}])[0]
    selected_options = {}
    mount = None
    weapon_cost = 0
    mount_cost = 0
    upgrades_cost = 0

    # Gestion spécifique pour les héros (pas d'unité combinée)
    if unit.get("type") == "hero":
        st.markdown("**Les héros ne peuvent pas être combinés**")
        combined = False
    else:
        combined = st.checkbox("Unité combinée", value=False)

    # Gestion des améliorations
    for group in unit.get("upgrade_groups", []):
        st.markdown(f"**{group['group']}**")

        if group["type"] == "weapon":
            weapon_options = ["Arme de base"]
            for o in group["options"]:
                weapon_details = format_weapon_details(o["weapon"])
                weapon_options.append(f"{weapon_details['formatted']} (+{o['cost']} pts)")

            selected_weapon = st.radio(
                "Arme",
                weapon_options,
                key=f"{unit['name']}_weapon"
            )
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

            selected_mount = st.radio(
                "Monture",
                mount_labels,
                key=f"{unit['name']}_mount"
            )
            if selected_mount != "Aucune monture" and selected_mount in mount_map:
                mount = mount_map[selected_mount]
                mount_cost = mount["cost"]

        else:  # Améliorations d'unité (radio boutons pour un seul choix)
            options = ["Aucune"] + [f"{o['name']} (+{o['cost']} pts)" for o in group["options"]]
            selected_option = st.radio(
                group["group"],
                options,
                key=f"{unit['name']}_{group['group']}"
            )
            if selected_option != "Aucune":
                opt_name = selected_option.split(" (+")[0]
                opt = next((o for o in group["options"] if o["name"] == opt_name), None)
                if opt:
                    if group["group"] not in selected_options:
                        selected_options[group["group"]] = []
                    selected_options[group["group"]] = [opt]
                    upgrades_cost = opt["cost"]

    # Calcul du coût final
    if combined and unit.get("type") != "hero":
        final_cost = (base_cost + weapon_cost) * 2 + mount_cost + upgrades_cost
        unit_size = base_size * 2
    else:
        final_cost = base_cost + weapon_cost + mount_cost + upgrades_cost
        unit_size = base_size

    st.markdown(f"**Coût total: {final_cost} pts**")
    st.markdown(f"**Taille de l'unité: {unit_size} figurines**")

    if st.button("Ajouter à l'armée"):
        # Sauvegarder l'état actuel avant l'ajout
        st.session_state.history.append({
            "army_list": copy.deepcopy(st.session_state.army_list),
            "army_cost": st.session_state.army_cost
        })
        st.session_state.undo_disabled = False

        weapon_data = format_weapon_details(weapon)

        unit_data = {
            "name": unit["name"],
            "type": unit.get("type", "unit"),
            "cost": final_cost,
            "base_cost": base_cost,
            "size": unit_size,
            "quality": unit["quality"],
            "defense": unit["defense"],
            "rules": unit.get("special_rules", []),
            "weapon": weapon_data,
            "options": selected_options,
            "mount": mount
        }

        # Ajouter temporairement l'unité pour vérifier les règles
        test_army = copy.deepcopy(st.session_state.army_list)
        test_army.append(unit_data)
        test_cost = st.session_state.army_cost + final_cost

        # Vérifier les règles
        valid, errors = validate_army_rules(test_army, st.session_state.points, st.session_state.game)

        if not valid:
            for error in errors:
                st.error(error)
            st.stop()

        # Si tout est valide, ajouter l'unité
        st.session_state.army_list.append(unit_data)
        st.session_state.army_cost += final_cost
        st.rerun()

    # Liste de l'armée
    st.divider()
    st.subheader("Liste de l'armée")

    if not st.session_state.army_list:
        st.info("Ajoutez des unités pour commencer")

    for i, u in enumerate(st.session_state.army_list):
        st.markdown(format_unit_display(u), unsafe_allow_html=True)

        if st.button(f"Supprimer {u['name']}", key=f"del_{i}"):
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
        html_content = generate_html_export(army_data, factions_by_game)
        st.download_button(
            "Exporter en HTML",
            html_content,
            file_name=f"{st.session_state.list_name}.html",
            mime="text/html"
        )
