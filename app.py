import json
import streamlit as st
from pathlib import Path
from datetime import datetime
import re
import math
import base64

st.set_page_config(
    page_title="OPR ArmyBuilder FR",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ======================================================
# CSS
# ======================================================
st.markdown("""
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {background: transparent;}
.stApp {background: #e9ecef; color: #212529;}
section[data-testid="stSidebar"] {background: #dee2e6; border-right: 1px solid #adb5bd; box-shadow: 2px 0 5px rgba(0,0,0,0.1);}
h1, h2, h3 {color: #202c45; letter-spacing: 0.04em; font-weight: 600;}
.stSelectbox, .stNumberInput, .stTextInput {background-color: white; border-radius: 6px; border: 1px solid #ced4da; box-shadow: 0 2px 4px rgba(0,0,0,0.05); transition: all 0.2s ease;}
.stSelectbox:hover, .stNumberInput:hover, .stTextInput:hover {border-color: #3498db; box-shadow: 0 0 0 3px rgba(52, 152, 219, 0.2);}
.stSelectbox > div, .stNumberInput > div, .stTextInput > div {border-radius: 6px !important;}
.stSelectbox label, .stNumberInput label, .stTextInput label {color: #2c3e50; font-weight: 500; margin-bottom: 0.3rem;}
button[kind="primary"] {background: linear-gradient(135deg, #2980b9, #1e5aa8) !important; color: white !important; font-weight: bold; border-radius: 6px; padding: 0.6rem 1rem; border: none; box-shadow: 0 2px 4px rgba(0,0,0,0.1); transition: all 0.2s ease;}
button[kind="primary"]:hover {background: linear-gradient(135deg, #1e5aa8, #194b8d) !important; box-shadow: 0 4px 8px rgba(0,0,0,0.15); transform: translateY(-1px);}
.badge {display: inline-block; padding: 0.35rem 0.75rem; border-radius: 4px; background: #2980b9; color: white; font-size: 0.8rem; margin-bottom: 0.75rem; font-weight: 600; box-shadow: 0 1px 2px rgba(0,0,0,0.1);}
.card {background: #ffffff; border: 2px solid #2980b9; border-radius: 8px; padding: 1.2rem; transition: all 0.2s ease; cursor: pointer; box-shadow: 0 2px 8px rgba(41, 128, 185, 0.2);}
.card:hover {border-color: #1e5aa8; box-shadow: 0 4px 16px rgba(41, 128, 185, 0.3); transform: translateY(-2px);}
.stButton>button {background-color: #f8f9fa; border: 1px solid #ced4da; border-radius: 6px; padding: 0.5rem 1rem; color: #212529; font-weight: 500; transition: all 0.2s ease;}
.stButton>button:hover {background-color: #e9ecef; border-color: #3498db; color: #2980b9;}
.stColumn {padding: 0.5rem;}
.stDivider {margin: 1.5rem 0; border-top: 1px solid #adb5bd;}
.stAlert {border-radius: 6px; padding: 0.75rem 1.25rem;}
.stProgress > div > div > div {background-color: #2980b9 !important;}
.stSelectbox div[role="button"] {background-color: white !important; border: 1px solid #ced4da !important; border-radius: 6px !important;}
.stSelectbox div[role="button"]:focus, .stNumberInput input:focus, .stTextInput input:focus {border-color: #3498db !important; box-shadow: 0 0 0 3px rgba(52, 152, 219, 0.2) !important;}
</style>
""", unsafe_allow_html=True)

# ======================================================
# SIDEBAR – CONTEXTE & NAVIGATION MODIFIÉE (version corrigée)
# ======================================================
with st.sidebar:
    st.markdown("<div style='height:1px;'></div>", unsafe_allow_html=True)

with st.sidebar:
    st.title("🛡️ OPR ArmyBuilder FR")

    st.subheader("📋 Armée")

    game = st.session_state.get("game", "—")
    faction = st.session_state.get("faction", "—")
    points = st.session_state.get("points", 0)
    army_cost = st.session_state.get("army_cost", 0)

    st.markdown(f"**Jeu :** {game}")
    st.markdown(f"**Faction :** {faction}")
    st.markdown(f"**Format :** {points} pts")

    if points > 0:
        st.progress(min(army_cost / points, 1.0))
        st.markdown(f"**Coût :** {army_cost} / {points} pts")

        if army_cost > points:
            st.error("⚠️ Dépassement de points")

        # NOUVELLES INFORMATIONS AJOUTÉES (version corrigée)
        if st.session_state.page == "army" and hasattr(st.session_state, 'army_list') and 'game' in st.session_state:
            # Utilisation des valeurs par défaut de GAME_CONFIG
            units_cap = math.floor(points / 150)  # Valeur par défaut de unit_per_points
            heroes_cap = math.floor(points / 375)  # Valeur par défaut de hero_limit

            units_now = len([u for u in st.session_state.army_list if u.get("type") != "hero"])
            heroes_now = len([u for u in st.session_state.army_list if u.get("type") == "hero"])

            st.markdown(f"**Unités :** {units_now} / {units_cap}")
            st.markdown(f"**Héros :** {heroes_now} / {heroes_cap}")

    st.divider()

# ======================================================
# INITIALISATION
# ======================================================
if "page" not in st.session_state:
    st.session_state.page = "setup"
if "army_list" not in st.session_state:
    st.session_state.army_list = []
if "army_cost" not in st.session_state:
    st.session_state.army_cost = 0
if "unit_selections" not in st.session_state:
    st.session_state.unit_selections = {}
if "game" not in st.session_state:
    st.session_state.game = None
if "faction" not in st.session_state:
    st.session_state.faction = None
if "points" not in st.session_state:
    st.session_state.points = 0
if "list_name" not in st.session_state:
    st.session_state.list_name = ""
if "units" not in st.session_state:
    st.session_state.units = []
if "faction_special_rules" not in st.session_state:
    st.session_state.faction_special_rules = []
if "faction_spells" not in st.session_state:
    st.session_state.faction_spells = {}

# ======================================================
# CONFIGURATION DES JEUX OPR (EXTENSIBLE)
# ======================================================
GAME_CONFIG = {
    "Age of Fantasy": {
        "min_points": 250, "max_points": 10000, "default_points": 1000,
        "hero_limit": 375, "unit_copy_rule": 750, "unit_max_cost_ratio": 0.35, "unit_per_points": 150
    },
    "Age of Fantasy: Regiments": {
        "min_points": 500, "max_points": 20000, "default_points": 2000,
        "hero_limit": 500, "unit_copy_rule": 1000, "unit_max_cost_ratio": 0.4, "unit_per_points": 200
    },
    "Grimdark Future": {
        "min_points": 250, "max_points": 10000, "default_points": 1000,
        "hero_limit": 375, "unit_copy_rule": 750, "unit_max_cost_ratio": 0.35, "unit_per_points": 150
    },
    "Grimdark Future: Firefight": {
        "min_points": 150, "max_points": 1000, "default_points": 300,
        "hero_limit": 300, "unit_copy_rule": 300, "unit_max_cost_ratio": 0.6, "unit_per_points": 100
    },
    "Age of Fantasy: Skirmish": {
        "min_points": 150, "max_points": 1000, "default_points": 300,
        "hero_limit": 300, "unit_copy_rule": 300, "unit_max_cost_ratio": 0.6, "unit_per_points": 100
    }
}

# ======================================================
# FONCTIONS DE VALIDATION
# ======================================================
def check_hero_limit(army_list, army_points, game_config):
    max_heroes = math.floor(army_points / game_config["hero_limit"])
    hero_count = sum(1 for unit in army_list if unit.get("type") == "hero")
    if hero_count > max_heroes:
        st.error(f"Limite de héros dépassée! Max: {max_heroes} (1 héros/{game_config['hero_limit']} pts)")
        return False
    return True

def check_unit_max_cost(army_list, army_points, game_config, new_unit_cost=None):
    max_cost = army_points * game_config["unit_max_cost_ratio"]
    for unit in army_list:
        if unit["cost"] > max_cost:
            st.error(f"Unité {unit['name']} dépasse {int(max_cost)} pts (35% du total)")
            return False
    if new_unit_cost and new_unit_cost > max_cost:
        st.error(f"Cette unité dépasse {int(max_cost)} pts (35% du total)")
        return False
    return True

def check_unit_copy_rule(army_list, army_points, game_config):
    x_value = math.floor(army_points / game_config["unit_copy_rule"])
    max_copies = 1 + x_value
    unit_counts = {}
    for unit in army_list:
        name = unit["name"]
        unit_counts[name] = unit_counts.get(name, 0) + 1
    for unit_name, count in unit_counts.items():
        if count > max_copies:
            st.error(f"Trop de copies de {unit_name}! Max: {max_copies}")
            return False
    return True

def validate_army_rules(army_list, army_points, game):
    game_config = GAME_CONFIG.get(game, {})
    return (check_hero_limit(army_list, army_points, game_config) and
            check_unit_max_cost(army_list, army_points, game_config) and
            check_unit_copy_rule(army_list, army_points, game_config))

def check_weapon_conditions(unit_key, requires):
    if not requires:
        return True

    current_weapons = []
    for selection in st.session_state.unit_selections.get(unit_key, {}).values():
        if isinstance(selection, dict) and "weapon" in selection:
            weapon = selection["weapon"]
            if isinstance(weapon, dict):
                current_weapons.append(weapon)
            elif isinstance(weapon, list):
                current_weapons.extend(weapon)
        elif isinstance(selection, str) and selection != "Aucune amélioration" and selection != "Aucune arme":
            weapon_name = selection.split(" (")[0]
            current_weapons.append({"name": weapon_name})

    for req in requires:
        if not any(w.get("name") == req or req in w.get("tags", []) for w in current_weapons):
            return False
    return True

# ======================================================
# FONCTIONS UTILITAIRES
# ======================================================
def format_unit_option(u):
    """Formate l'option d'unité avec plus de détails"""
    name_part = f"{u['name']}"
    if u.get('type') == "hero":
        name_part += " [1]"
    else:
        name_part += f" [{u.get('size', 10)}]"

    # Récupération des armes de base avec leur profil complet
    weapons = u.get('weapon', [])
    weapon_profiles = []
    if isinstance(weapons, list) and weapons:
        for weapon in weapons:
            if isinstance(weapon, dict):
                weapon_name = weapon.get('name', 'Arme')
                attacks = weapon.get('attacks', '?')
                ap = weapon.get('armor_piercing', '?')
                range_text = weapon.get('range', 'Mêlée')
                special_rules = weapon.get('special_rules', [])

                # Formatage du profil complet
                profile = f"{weapon_name} (A{attacks}/PA{ap}/{range_text}"
                if special_rules:
                    profile += f", {', '.join(special_rules)})"
                else:
                    profile += ")"

                weapon_profiles.append(profile)
    elif isinstance(weapons, dict):
        weapon_name = weapons.get('name', 'Arme')
        attacks = weapons.get('attacks', '?')
        ap = weapons.get('armor_piercing', '?')
        range_text = weapons.get('range', 'Mêlée')
        special_rules = weapons.get('special_rules', [])

        profile = f"{weapon_name} (A{attacks}/PA{ap}/{range_text}"
        if special_rules:
            profile += f", {', '.join(special_rules)})"
        else:
            profile += ")"

        weapon_profiles.append(profile)

    weapon_text = ", ".join(weapon_profiles) if weapon_profiles else "Aucune"

    # Récupération des règles spéciales
    special_rules = u.get('special_rules', [])
    rules_text = []
    if isinstance(special_rules, list):
        for rule in special_rules:
            if isinstance(rule, str):
                rules_text.append(rule)
            elif isinstance(rule, dict):
                rules_text.append(rule.get('name', ''))

    rules_text = ", ".join(rules_text) if rules_text else "Aucune"

    # Construction du texte final
    qua_def = f"Déf {u.get('defense', '?')}+"
    cost = f"{u.get('base_cost', 0)}pts"

    return f"{name_part} | {qua_def} | {weapon_text} | {rules_text} | {cost}"
def format_weapon_option(weapon, cost=0):
    if not weapon or not isinstance(weapon, dict):
        return "Aucune arme"

    name = weapon.get('name', 'Arme')
    attacks = weapon.get('attacks', '?')
    ap = weapon.get('armor_piercing', '?')
    range_text = weapon.get('range', 'Mêlée')

    profile = f"{name} (A{attacks}/PA{ap}/{range_text})"
    if cost > 0:
        profile += f" (+{cost} pts)"

    return profile

def format_weapon(weapon):
    if not weapon:
        return "Aucune arme"

    range_text = weapon.get('range', '-')
    attacks = weapon.get('attacks', '-')
    ap = weapon.get('armor_piercing', '-')
    special_rules = weapon.get('special_rules', [])

    if isinstance(range_text, (int, float)):
        range_text = str(range_text) + '"'
    elif range_text == "-" or range_text is None or str(range_text).lower() == "mêlée":
        range_text = "Mêlée"

    result = f"<table><tr><th>RNG</th><th>ATK</th><th>AP</th><th>SPE</th></tr><tr>"
    result += f"<td>{range_text}</td><td>{attacks}</td><td>{ap}</td>"

    if special_rules:
        result += f"<td>{', '.join(special_rules)}</td>"
    else:
        result += "<td>-</td>"

    result += "</tr></table>"
    return result

def format_mount_option(mount):
    if not mount or not isinstance(mount, dict):
        return "Aucune monture"

    name = mount.get('name', 'Monture')
    cost = mount.get('cost', 0)
    mount_data = mount.get('mount', {})
    weapons = mount_data.get('weapon', [])
    special_rules = mount_data.get('special_rules', [])
    coriace = mount_data.get('coriace_bonus', 0)

    stats = []
    weapon_profiles = []
    if isinstance(weapons, list) and weapons:
        for weapon in weapons:
            if isinstance(weapon, dict):
                weapon_name = weapon.get('name', 'Arme')
                attacks = weapon.get('attacks', '?')
                ap = weapon.get('armor_piercing', '?')
                special = ", ".join(weapon.get('special_rules', [])) if weapon.get('special_rules') else ""
                profile = f"{weapon_name} A{attacks}/PA{ap}"
                if special:
                    profile += f" ({special})"
                weapon_profiles.append(profile)
    elif isinstance(weapons, dict):
        weapon_name = weapons.get('name', 'Arme')
        attacks = weapons.get('attacks', '?')
        ap = weapons.get('armor_piercing', '?')
        special = ", ".join(weapons.get('special_rules', [])) if weapons.get('special_rules') else ""
        profile = f"{weapon_name} A{attacks}/PA{ap}"
        if special:
            profile += f" ({special})"
        weapon_profiles.append(profile)

    if weapon_profiles:
        stats.extend(weapon_profiles)

    if coriace > 0:
        stats.append(f"Coriace+{coriace}")

    if special_rules:
        rules_text = ", ".join([r for r in special_rules if not r.startswith(("Griffes", "Sabots"))])
        if rules_text:
            stats.append(rules_text)

    label = f"{name}"
    if stats:
        label += f" ({', '.join(stats)})"
    label += f" (+{cost} pts)"

    return label

# ======================================================
# EXPORT HTML
# ======================================================
def export_html(army_list, army_name, army_limit):
    def esc(txt):
        if txt is None:
            return ""
        return str(txt).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

    def get_unit_type_priority(unit):
        """Détermine la priorité d'affichage des unités"""
        unit_type = unit.get('type', 'unit')
        unit_detail = unit.get('unit_detail', 'unit')

        if unit_type == "hero" or unit_detail == "named_hero":
            return 1
        elif unit_detail == "unit":
            return 2
        elif unit_detail == "light_vehicle":
            return 3
        elif unit_detail == "vehicle":
            return 4
        elif unit_detail == "titan":
            return 5
        return 6

    def get_french_type(unit):
        """Retourne le type français basé sur unit_detail"""
        unit_type = unit.get('type', 'unit')
        unit_detail = unit.get('unit_detail', 'unit')

        if unit_type == "hero":
            return "Héros"
        elif unit_detail == "titan":
            return "Titan"
        elif unit_detail == "named_hero":
            return "Héros nommé"
        elif unit_detail == "light_vehicle":
            return "Véhicule léger"
        elif unit_detail == "vehicle":
            return "Véhicule/Monstre"
        return "Unité de base"

    def get_icon_for_unit(unit):
        """Retourne l'icône appropriée pour le type d'unité"""
        if unit.get("type") == "hero":
            return "★"
        elif unit.get("unit_detail") == "titan":
            return "🤖"
        return "🛡️"

    def format_unit_option(u):
        """Formate l'option d'unité avec les statistiques complètes"""
        name_part = f"{u['name']}"

        # Ajout des statistiques de base
        qua_def = f"Qual {u.get('quality', '?')}+ | Déf {u.get('defense', '?')}+"
        if 'coriace' in u and u['coriace'] > 0:
            qua_def += f" | Coriace {u.get('coriace', '?')}"
        qua_def += f" | Taille {u.get('size', '?')}"

        # Récupération des armes principales
        weapons = []
        if "weapon" in u:
            if isinstance(u["weapon"], list):
                for weapon in u["weapon"]:
                    if isinstance(weapon, dict):
                        weapon_name = weapon.get('name', 'Arme')
                        attacks = weapon.get('attacks', '?')
                        ap = weapon.get('armor_piercing', '?')
                        range_text = weapon.get('range', 'Mêlée')
                        if range_text == "Mêlée" or range_text == "mêlée":
                            range_text = "Mêlée"
                        elif isinstance(range_text, (int, float)):
                            range_text = f'{range_text}"'
                        weapons.append(f"{weapon_name} (A{attacks}/PA{ap}/{range_text})")
            elif isinstance(u["weapon"], dict):
                weapon_name = u["weapon"].get('name', 'Arme')
                attacks = u["weapon"].get('attacks', '?')
                ap = u["weapon"].get('armor_piercing', '?')
                range_text = u["weapon"].get('range', 'Mêlée')
                if range_text == "Mêlée" or range_text == "mêlée":
                    range_text = "Mêlée"
                elif isinstance(range_text, (int, float)):
                    range_text = f'{range_text}"'
                weapons.append(f"{weapon_name} (A{attacks}/PA{ap}/{range_text})")

        weapon_text = ", ".join(weapons) if weapons else "Aucune arme"

        # Récupération des règles spéciales
        special_rules = []
        if "special_rules" in u and isinstance(u["special_rules"], list):
            special_rules = [r for r in u["special_rules"] if isinstance(r, str)]

        rules_text = ", ".join(special_rules) if special_rules else "Aucune"

        # Coût
        cost = f"{u.get('cost', 0)}pts"

        return f"{name_part} | {qua_def} | {weapon_text} | {rules_text} | {cost}"

    def get_roles(unit):
        """Récupère les rôles sélectionnés pour les héros/titans"""
        roles = []

        if "options" in unit and isinstance(unit["options"], dict):
            for group_name, options in unit["options"].items():
                if isinstance(options, list):
                    for opt in options:
                        if isinstance(opt, dict) and opt.get("type") == "role":
                            roles.append(opt)
                elif isinstance(options, dict) and options.get("type") == "role":
                    roles.append(options)

        if "upgrade_groups" in unit and isinstance(unit.get("upgrade_groups"), list):
            for group in unit["upgrade_groups"]:
                if isinstance(group, dict) and group.get("type") == "role" and "options" in group:
                    for opt in group["options"]:
                        if isinstance(opt, dict):
                            roles.append(opt)

        return roles

    def get_role_rules(unit):
        """Récupère les règles des rôles comme des armes"""
        role_rules = []
        roles = get_roles(unit)
        for role in roles:
            if "special_rules" in role and isinstance(role["special_rules"], list):
                for rule in role["special_rules"]:
                    if isinstance(rule, str):
                        role_name = role.get("name", "Rôle")
                        # Format: "Lanceur de sorts (2) (Seigneur Éternel)"
                        if "(" in rule and ")" in rule:
                            rule_name_part = rule.split("(")[0].strip()
                            rule_count = rule.split("(")[1].split(")")[0]
                            role_rules.append({
                                "name": f"{rule_name_part} ({rule_count}) ({role_name})",
                                "range": "-",
                                "attacks": "-",
                                "armor_piercing": "-",
                                "special_rules": [],
                                "_role_rule": True,
                                "_role_name": role_name
                            })
                        else:
                            role_rules.append({
                                "name": f"{rule} ({role_name})",
                                "range": "-",
                                "attacks": "-",
                                "armor_piercing": "-",
                                "special_rules": [],
                                "_role_rule": True,
                                "_role_name": role_name
                            })
        return role_rules

    def collect_weapons(unit):
        """Collecte toutes les armes de l'unité, y compris les règles de rôle et les améliorations"""
        weapons = []

        # Règles de rôle comme armes
        role_rules = get_role_rules(unit)
        weapons.extend(role_rules)

        # Armes de base
        if "weapon" in unit:
            base_weapons = unit["weapon"]
            if isinstance(base_weapons, list):
                for weapon in base_weapons:
                    if isinstance(weapon, dict):
                        # Ajouter la portée par défaut si manquante
                        weapon_copy = weapon.copy()
                        if "range" not in weapon_copy:
                            weapon_copy["range"] = "Mêlée"
                        weapons.append(weapon_copy)
            elif isinstance(base_weapons, dict):
                # Ajouter la portée par défaut si manquante
                weapon_copy = base_weapons.copy()
                if "range" not in weapon_copy:
                    weapon_copy["range"] = "Mêlée"
                weapons.append(weapon_copy)

        # Armes des options (y compris améliorations)
        if "options" in unit and isinstance(unit["options"], dict):
            for group_name, group in unit["options"].items():
                if isinstance(group, list):
                    for opt in group:
                        if isinstance(opt, dict):
                            # Armes de remplacement
                            if "weapon" in opt:
                                weapon = opt["weapon"]
                                if isinstance(weapon, list):
                                    for w in weapon:
                                        if isinstance(w, dict):
                                            w_copy = w.copy()
                                            # Ajouter la portée si manquante
                                            if "range" not in w_copy:
                                                w_copy["range"] = "Mêlée"
                                            # Ajouter le compteur si présent
                                            if "_count" in opt:
                                                w_copy["_count"] = opt["_count"]
                                            if opt.get("type") == "variable_weapon_count":
                                                w_copy["_count"] = opt.get("count", 1)
                                            # Marquer comme amélioration si c'est un remplacement
                                            if opt.get("replaces"):
                                                w_copy["_replaces"] = opt["replaces"]
                                                w_copy["_upgraded"] = True
                                            weapons.append(w_copy)
                                else:
                                    if isinstance(weapon, dict):
                                        w_copy = weapon.copy()
                                        # Ajouter la portée si manquante
                                        if "range" not in w_copy:
                                            w_copy["range"] = "Mêlée"
                                        # Ajouter le compteur si présent
                                        if "_count" in opt:
                                            w_copy["_count"] = opt["_count"]
                                        if opt.get("type") == "variable_weapon_count":
                                            w_copy["_count"] = opt.get("count", 1)
                                        # Marquer comme amélioration si c'est un remplacement
                                        if opt.get("replaces"):
                                            w_copy["_replaces"] = opt["replaces"]
                                            w_copy["_upgraded"] = True
                                        weapons.append(w_copy)

                            # Améliorations d'arme (ex: Javelot des Tempêtes)
                            if opt.get("type") == "conditional_weapon" and "weapon" in opt:
                                weapon = opt["weapon"]
                                if isinstance(weapon, list):
                                    for w in weapon:
                                        if isinstance(w, dict):
                                            w_copy = w.copy()
                                            # Ajouter la portée si manquante
                                            if "range" not in w_copy:
                                                w_copy["range"] = "Mêlée"
                                            # Ajouter le compteur si présent
                                            if "count" in opt:
                                                w_copy["_count"] = opt["count"]
                                            w_copy["_upgraded"] = True
                                            weapons.append(w_copy)
                                else:
                                    if isinstance(weapon, dict):
                                        w_copy = weapon.copy()
                                        # Ajouter la portée si manquante
                                        if "range" not in w_copy:
                                            w_copy["range"] = "Mêlée"
                                        # Ajouter le compteur si présent
                                        if "count" in opt:
                                            w_copy["_count"] = opt["count"]
                                        w_copy["_upgraded"] = True
                                        weapons.append(w_copy)

                elif isinstance(group, dict) and "weapon" in group:
                    weapon = group["weapon"]
                    if isinstance(weapon, list):
                        for w in weapon:
                            if isinstance(w, dict):
                                w_copy = w.copy()
                                if "range" not in w_copy:
                                    w_copy["range"] = "Mêlée"
                                weapons.append(w_copy)
                    else:
                        if isinstance(weapon, dict):
                            w_copy = weapon.copy()
                            if "range" not in w_copy:
                                w_copy["range"] = "Mêlée"
                            weapons.append(w_copy)

        # Armes de monture (mais ne seront pas affichées dans la section monture)
        if "mount" in unit and unit.get("mount"):
            mount = unit["mount"]
            if isinstance(mount, dict) and "mount" in mount:
                mount_data = mount["mount"]
                if isinstance(mount_data, dict) and "weapon" in mount_data:
                    mount_weapons = mount_data["weapon"]
                    if isinstance(mount_weapons, list):
                        for w in mount_weapons:
                            if isinstance(w, dict):
                                w_copy = w.copy()
                                if "range" not in w_copy:
                                    w_copy["range"] = "Mêlée"
                                w_copy["_mount_weapon"] = True
                                weapons.append(w_copy)
                    else:
                        if isinstance(mount_weapons, dict):
                            w_copy = mount_weapons.copy()
                            if "range" not in w_copy:
                                w_copy["range"] = "Mêlée"
                            w_copy["_mount_weapon"] = True
                            weapons.append(w_copy)

        return weapons

    def group_weapons(weapons):
        """Regroupe les armes identiques et gère les comptages"""
        weapon_map = {}

        for w in weapons:
            if not isinstance(w, dict):
                continue

            # Ajouter la portée par défaut si manquante
            if "range" not in w:
                w = w.copy()
                w["range"] = "Mêlée"

            name = w.get("name", "Arme")
            rng = w.get("range", "Mêlée")
            att = w.get("attacks", "-")
            ap = w.get("armor_piercing", "-")
            rules = tuple(sorted(w.get("special_rules", [])))

            # Pour les règles de rôle, on veut les garder séparées
            is_role_rule = w.get("_role_rule", False)
            if is_role_rule:
                key = (name, rng, att, ap, rules, True)
            else:
                key = (name, rng, att, ap, rules, False)

            if key not in weapon_map:
                weapon_map[key] = dict(w)
                weapon_map[key]["count"] = w.get("_count", 1)
            else:
                weapon_map[key]["count"] += w.get("_count", 1)

        grouped = list(weapon_map.values())
        return grouped

    def get_rules(unit):
        """Récupère toutes les règles spéciales (sans les règles de rôle)"""
        rules = set()

        if "special_rules" in unit and isinstance(unit["special_rules"], list):
            for r in unit["special_rules"]:
                if isinstance(r, str):
                    rules.add(r)

        if "options" in unit and isinstance(unit["options"], dict):
            for group in unit["options"].values():
                if isinstance(group, list):
                    for opt in group:
                        if isinstance(opt, dict) and "special_rules" in opt:
                            for r in opt["special_rules"]:
                                if isinstance(r, str):
                                    rules.add(r)
                elif isinstance(group, dict) and "special_rules" in group:
                    for r in group["special_rules"]:
                        if isinstance(r, str):
                            rules.add(r)

        if "mount" in unit and unit.get("mount"):
            mount = unit["mount"]
            if isinstance(mount, dict) and "mount" in mount:
                mount_data = mount["mount"]
                if isinstance(mount_data, dict) and "special_rules" in mount_data:
                    for r in mount_data["special_rules"]:
                        if isinstance(r, str) and not r.startswith(("Griffes", "Sabots")):
                            rules.add(r)

        return sorted(rules)

    def get_upgrades(unit):
        """Récupère les améliorations de l'unité"""
        upgrades = []
        if "options" in unit and isinstance(unit["options"], dict):
            for group in unit["options"].values():
                if isinstance(group, list):
                    for opt in group:
                        if isinstance(opt, dict) and opt.get("type") == "upgrade":
                            upgrades.append(opt)
                elif isinstance(group, dict) and group.get("type") == "upgrade":
                    upgrades.append(group)
        return upgrades

    # Trier les unités selon vos critères
    sorted_units = sorted(army_list, key=lambda u: get_unit_type_priority(u))

    # Génération du HTML
    html_content = f"""
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title>Liste d'Armée OPR - {esc(army_name)}</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root {{
  --bg-page: #ffffff;
  --bg-card: #ffffff;
  --bg-header: #f8f9fa;
  --bg-section: #f8f9fa;
  --accent: #3498db;
  --accent-light: #e3f2fd;
  --text-main: #212529;
  --text-muted: #6c757d;
  --border: #dee2e6;
  --border-dark: #adb5bd;
  --cost-color: #e74c3c;
  --tough-color: #e74c3c;
  --rule-bg: #e9ecef;
  --weapon-bg: #f8f9fa;
  --role-bg: #e3f2fd;
  --upgrade-bg: #e8f5e9;
  --mount-bg: #f3e5f5;
  --stat-badge: #e9ecef;
  --table-header: #f8f9fa;
  --table-row: #ffffff;
}}

body {{
  background: var(--bg-page);
  color: var(--text-main);
  font-family: 'Inter', sans-serif;
  margin: 0;
  padding: 20px;
  line-height: 1.5;
}}

.army {{
  max-width: 1000px;
  margin: 0 auto;
}}

.army-title {{
  text-align: center;
  font-size: 28px;
  font-weight: 700;
  margin-bottom: 20px;
  color: var(--text-main);
  border-bottom: 2px solid var(--accent);
  padding-bottom: 10px;
}}

.army-summary {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: var(--bg-header);
  padding: 16px;
  border-radius: 8px;
  margin: 20px 0;
  border: 1px solid var(--border);
}}

.unit-card {{
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 8px;
  margin-bottom: 20px;
  padding: 0;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  page-break-inside: avoid;
}}

.unit-header {{
  padding: 16px;
  background: var(--bg-header);
  border-bottom: 1px solid var(--border);
  border-radius: 8px 8px 0 0;
}}

.unit-name-container {{
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 8px;
}}

.unit-name {{
  font-size: 20px;
  font-weight: 600;
  color: var(--text-main);
  margin: 0;
}}

.unit-cost {{
  font-family: monospace;
  font-size: 18px;
  font-weight: bold;
  color: var(--cost-color);
}}

.unit-stats {{
  display: flex;
  gap: 12px;
  background: var(--bg-header);
  padding: 12px;
  margin: 0 16px 16px;
  border-radius: 6px;
  justify-content: center;
  flex-wrap: wrap;
}}

.stat-badge {{
  background: var(--stat-badge);
  color: var(--text-main);
  padding: 8px 12px;
  border-radius: 20px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 100px;
  justify-content: center;
  border: 1px solid var(--border);
}}

.stat-value {{
  font-weight: bold;
  font-size: 16px;
}}

.stat-label {{
  font-size: 12px;
  color: var(--text-muted);
}}

.section {{
  padding: 0 16px 16px;
}}

.section-title {{
  font-weight: 600;
  margin: 16px 0 8px;
  color: var(--text-main);
  font-size: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
  border-bottom: 1px solid var(--border);
  padding-bottom: 4px;
}}

.weapon-table {{
  width: 100%;
  border-collapse: collapse;
  margin: 0 0 16px;
  background: var(--weapon-bg);
  border-radius: 6px;
  overflow: hidden;
  border: 1px solid var(--border);
}}

.weapon-table th {{
  background: var(--table-header);
  color: var(--text-main);
  padding: 10px 12px;
  text-align: left;
  font-weight: 600;
  border-bottom: 1px solid var(--border);
  border-right: 1px solid var(--border);
}}

.weapon-table th:last-child {{
  border-right: none;
}}

.weapon-table td {{
  padding: 10px 12px;
  border-bottom: 1px solid var(--border);
  border-right: 1px solid var(--border);
  vertical-align: top;
}}

.weapon-table td:last-child {{
  border-right: none;
}}

.weapon-table tr:last-child td {{
  border-bottom: none;
}}

.weapon-table tr:nth-child(even) {{
  background: var(--table-row);
}}

.weapon-name {{
  font-weight: 500;
  color: var(--text-main);
}}

.weapon-stats {{
  color: var(--text-muted);
}}

.role-rule {{
  font-weight: 600;
  color: var(--accent);
}}

.upgrade-section {{
  background: var(--upgrade-bg);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 16px;
  margin: 16px 0;
}}

.mount-section {{
  background: var(--mount-bg);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 16px;
  margin: 16px 0;
}}

.rules-section {{
  margin: 16px 0;
}}

.rules-title {{
  font-weight: 600;
  margin-bottom: 8px;
  color: var(--text-main);
  display: flex;
  align-items: center;
  gap: 8px;
}}

.rule-tag {{
  background: var(--rule-bg);
  padding: 6px 12px;
  border-radius: 4px;
  font-size: 13px;
  color: var(--text-main);
  border: 1px solid var(--border);
  margin-right: 8px;
  margin-bottom: 8px;
  display: inline-block;
}}

.faction-rules, .faction-spells {{
  margin-top: 40px;
  padding: 20px;
  background: var(--bg-card);
  border-radius: 8px;
  border: 1px solid var(--border);
}}

.rule-item, .spell-item {{
  margin-bottom: 15px;
  padding-bottom: 15px;
  border-bottom: 1px solid var(--border);
}}

.rule-name, .spell-name {{
  color: var(--accent);
  font-weight: 600;
  margin-bottom: 5px;
}}

.summary-cost {{
  font-family: monospace;
  font-size: 24px;
  font-weight: bold;
  color: var(--cost-color);
}}

@media print {{
  body {{
    background: white;
    color: black;
  }}
  .unit-card {{
    background: white;
    border: 1px solid #ddd;
    page-break-inside: avoid;
    box-shadow: none;
  }}
  .stat-badge {{
    background: #f8f9fa;
    color: black;
    border: 1px solid #ddd;
  }}
  .weapon-table th {{
    background: #f8f9fa;
    color: black;
  }}
}}
</style>
</head>
<body>
<div class="army">
  <!-- Titre de la liste -->
  <div class="army-title">
    {esc(army_name)} - {sum(unit['cost'] for unit in sorted_units)}/{army_limit} pts
  </div>

  <!-- Résumé de l'armée -->
  <div class="army-summary">
    <div style="font-size: 14px; color: var(--text-main);">
      <span style="color: var(--text-muted);">Nombre d'unités:</span>
      <strong style="margin-left: 8px; font-size: 18px;">{len(sorted_units)}</strong>
    </div>
    <div class="summary-cost">
      {sum(unit['cost'] for unit in sorted_units)}/{army_limit} pts
    </div>
  </div>
"""

    for unit in sorted_units:
        if not isinstance(unit, dict):
            continue

        name = esc(unit.get("name", "Unité"))
        cost = unit.get("cost", 0)
        quality = esc(unit.get("quality", "-"))
        defense = esc(unit.get("defense", "-"))
        size = unit.get("size", 10)
        coriace = unit.get("coriace", 0)

        html_content += f'''
<div class="unit-card">
  <div class="unit-header">
    <div class="unit-name-container">
      <div class="unit-name">
        {name}
      </div>
      <div class="unit-cost">{cost} pts</div>
    </div>

    <!-- Profil de l'unité avec badges -->
    <div class="unit-stats">
      <div class="stat-badge">
        <span class="stat-label">QUAL</span>
        <span class="stat-value">{quality}+</span>
      </div>
      <div class="stat-badge">
        <span class="stat-label">DÉF</span>
        <span class="stat-value">{defense}+</span>
      </div>
      <div class="stat-badge">
        <span class="stat-label">CORIACE</span>
        <span class="stat-value">{coriace if coriace > 0 else '-'}</span>
      </div>
      <div class="stat-badge">
        <span class="stat-label">TAILLE</span>
        <span class="stat-value">{size}</span>
      </div>
    </div>

    <div class="section">
        <!-- Tableau des armes avec portées complètes -->
        <div class="section-title">⚔️ Armes</div>
        <table class="weapon-table">
          <thead>
            <tr>
              <th>Nom</th>
              <th>Portée</th>
              <th>ATQ</th>
              <th>PA</th>
              <th>Spéciaux</th>
            </tr>
          </thead>
          <tbody>
'''

        try:
            # Armes et règles de rôle de l'unité
            weapons = collect_weapons(unit)
            final_weapons = group_weapons(weapons)

            for w in final_weapons:
                name = esc(w.get("name", "Arme"))
                count = w.get("count", 1)
                name_display = name

                # Gestion des comptages pour les sliders
                if "_count" in w and w["_count"] > 1:
                    name_display = f"{name} ({w['_count']})"

                # Style différent pour les règles de rôle
                is_role_rule = w.get("_role_rule", False)
                if is_role_rule:
                    name_display = f'<span class="role-rule">{name_display}</span>'

                # Portée complète (toujours affichée)
                rng = w.get("range", "Mêlée")
                if rng == "-" or rng == "mêlée" or str(rng).lower() == "mêlée":
                    rng = "Mêlée"
                elif isinstance(rng, (int, float)):
                    rng = f'{rng}"'
                else:
                    rng = f'{rng}"' if not rng.endswith('"') else rng

                att = w.get("attacks", "-")
                ap = w.get("armor_piercing", "-")
                rules = ", ".join(w.get("special_rules", []))
                rules_display = rules if rules else "-"

                html_content += f"""
            <tr>
              <td class="weapon-name">{name_display}</td>
              <td class="weapon-stats">{rng}</td>
              <td class="weapon-stats">{att}</td>
              <td class="weapon-stats">{ap}</td>
              <td class="weapon-stats">{rules_display}</td>
            </tr>
"""
        except Exception as e:
            html_content += f"""
            <tr>
              <td colspan="5" style="color: red;">Erreur de chargement des armes: {str(e)}</td>
            </tr>
"""

        html_content += '''
          </tbody>
        </table>

        <!-- Règles spéciales (sans les règles de rôle) -->
        <div class="rules-section">
          <div class="rules-title">📜 Règles spéciales</div>
          <div style="margin-bottom: 12px;">
'''
        try:
            rules = get_rules(unit)
            if rules:
                html_content += ' '.join(f'<span class="rule-tag">{esc(r)}</span>' for r in rules)
            else:
                html_content += '<span class="rule-tag">Aucune</span>'
        except Exception as e:
            html_content += f'<span class="rule-tag" style="color: red;">Erreur: {str(e)}</span>'

        html_content += '''
          </div>
        </div>
'''

        # Section Améliorations
        try:
            upgrades = get_upgrades(unit)
            if upgrades:
                html_content += '''
        <div class="upgrade-section">
          <div class="section-title">⬆️ Améliorations</div>
          <div style="margin-left: 8px;">
'''
                for upgrade in upgrades:
                    upgrade_name = esc(upgrade.get("name", "Amélioration"))
                    upgrade_cost = upgrade.get("cost", 0)
                    upgrade_rules = ", ".join(upgrade.get("special_rules", []))

                    html_content += f'''
            <div style="margin-bottom: 8px;">
              <strong>{upgrade_name}</strong>{' (+' + str(upgrade_cost) + ' pts)' if upgrade_cost > 0 else ''}
'''
                    if upgrade_rules:
                        html_content += f'''
              <div style="font-size: 13px; color: var(--text-muted); margin-top: 2px;">{upgrade_rules}</div>
'''
                    html_content += '''
            </div>
'''
                html_content += '''
          </div>
        </div>
'''
        except Exception as e:
            html_content += f'''
        <div class="upgrade-section">
          <div style="color: red; padding: 8px;">Erreur de chargement des améliorations: {str(e)}</div>
        </div>
'''

        # Section Monture (sans les armes)
        try:
            if "mount" in unit and unit.get("mount"):
                mount = unit["mount"]
                if isinstance(mount, dict) and "mount" in mount:
                    mount_data = mount["mount"]
                    mount_name = esc(mount.get("name", "Monture"))
                    mount_cost = mount.get("cost", 0)

                    html_content += f'''
        <div class="mount-section">
          <div class="section-title">🐴 {mount_name}</div>
          <div style="margin: 0 8px 8px;">
            +{mount_cost} pts
'''

                    # Règles spéciales de la monture (sans les armes)
                    mount_rules = []
                    if isinstance(mount_data, dict) and "special_rules" in mount_data:
                        mount_rules = [r for r in mount_data["special_rules"] if not r.startswith(("Griffes", "Sabots", "Coriace"))]

                    if mount_rules:
                        html_content += '''
            <div style="margin-top: 12px;">
              <div style="font-weight: 600; color: var(--text-main); margin-bottom: 8px;">Règles spéciales:</div>
              <div>
'''
                        html_content += ' '.join(f'<span class="rule-tag">{esc(r)}</span>' for r in mount_rules)
                        html_content += '''
              </div>
            </div>
'''

                    html_content += '''
          </div>
        </div>
'''
        except Exception as e:
            html_content += f'''
        <div class="mount-section">
          <div style="color: red; padding: 8px;">Erreur de chargement de la monture: {str(e)}</div>
        </div>
'''

        html_content += '''
    </div>
</div>
'''

    # Légende des règles spéciales de la faction
    try:
        if hasattr(st.session_state, 'faction_special_rules') and st.session_state.faction_special_rules:
            faction_rules = st.session_state.faction_special_rules
            all_rules = [rule for rule in faction_rules if isinstance(rule, dict)]

            if all_rules:
                html_content += '''
<div class="faction-rules">
  <h3 style="text-align: center; color: var(--accent); border-bottom: 2px solid var(--accent); padding-bottom: 10px; margin-bottom: 20px;">
    📜 Légende des règles spéciales de la faction
  </h3>
  <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, fr)); gap: 20px;">
'''
                for rule in sorted(all_rules, key=lambda x: x.get('name', '').lower().replace('é', 'e').replace('è', 'e')):
                    if isinstance(rule, dict):
                        html_content += f'''
    <div class="rule-item">
      <div class="rule-name">{esc(rule.get('name', ''))}</div>
      <div style="font-size: 14px; color: var(--text-main); line-height: 1.4;">{esc(rule.get('description', ''))}</div>
    </div>
'''
                html_content += '''
  </div>
</div>
'''
    except Exception as e:
        html_content += f'''
<div style="margin-top: 20px; padding: 10px; color: red; border: 1px solid #ffcccc; background: #ffebee; border-radius: 4px;">
  Erreur de chargement des règles de faction: {str(e)}
</div>
'''

    html_content += '''
<div style="text-align: center; margin-top: 30px; font-size: 12px; color: var(--text-muted);">
  Généré par OPR ArmyBuilder FR - {datetime.now().strftime('%d/%m/%Y %H:%M')}
</div>
</div>
</body>
</html>
'''

    return html_content

# ======================================================
# CHARGEMENT DES FACTIONS
# ======================================================
@st.cache_data
def load_factions():
    factions = {}
    games = set()
    try:
        FACTIONS_DIR = Path(__file__).resolve().parent / "frontend" / "public" / "factions"
        if not FACTIONS_DIR.exists():
            FACTIONS_DIR = Path(__file__).resolve().parent / "lists" / "data" / "factions"

        for fp in FACTIONS_DIR.glob("*.json"):
            try:
                with open(fp, encoding="utf-8") as f:
                    data = json.load(f)
                    game = data.get("game")
                    faction = data.get("faction")
                    if game and faction:
                        if game not in factions:
                            factions[game] = {}
                        if "faction_special_rules" not in data:
                            data["faction_special_rules"] = []
                        if "spells" not in data:
                            data["spells"] = {}
                        if "units" not in data:
                            data["units"] = []
                        factions[game][faction] = data
                        games.add(game)
            except Exception as e:
                st.warning(f"Erreur chargement {fp.name}: {e}")
                continue
    except Exception as e:
        st.error(f"Erreur lors du chargement des factions: {str(e)}")
        return {}, []

    return factions, sorted(games) if games else list(GAME_CONFIG.keys())

# ======================================================
# PAGE 1 – CONFIGURATION AVEC IMAGES DE FOND LOCALES
# ======================================================
if st.session_state.page == "setup":
    game_images = {
        "Age of Fantasy": "assets/games/aof_cover.jpg",
        "Age of Fantasy Regiments": "assets/games/aofr_cover.jpg",
        "Grimdark Future": "assets/games/gf_cover.jpg",
        "Grimdark Future Firefight": "assets/games/gff_cover.jpg",
        "Age of Fantasy Skirmish": "assets/games/aofs_cover.jpg",
        "__default__": "https://i.imgur.com/DEFAULT_IMAGE.jpg"
    }

    current_game = st.session_state.get("game", "__default__")

    if current_game in game_images and current_game != "__default__":
        image_path = game_images[current_game]
        try:
            if Path(image_path).exists():
                with open(image_path, "rb") as f:
                    img_data = f.read()
                img_base64 = base64.b64encode(img_data).decode("utf-8")
                image_url = f"data:image/jpeg;base64,{img_base64}"
            else:
                image_url = game_images["__default__"]
        except:
            image_url = game_images["__default__"]
    else:
        image_url = game_images["__default__"]

    st.markdown(
        f"""
        <style>
        .game-bg {{
            background: linear-gradient(to bottom,
                rgba(0,0,0,0.7) 0%,
                rgba(0,0,0,0.3) 50%,
                rgba(0,0,0,0) 100%),
                url('{image_url}');
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            padding: 2rem;
            border-radius: 10px;
            margin-bottom: 2rem;
            position: relative;
            min-height: 200px;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .game-bg::before {{
            content: "";
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: linear-gradient(to bottom,
                rgba(0,0,0,0.6) 0%,
                rgba(0,0,0,0) 100%);
            border-radius: 10px;
        }}
        .game-bg .content {{
            position: relative;
            z-index: 1;
            width: 100%;
            text-align: center;
        }}
        .game-bg h2 {{
            color: white;
            text-shadow: 1px 1px 3px rgba(0,0,0,0.8);
            margin-bottom: 0.5rem;
        }}
        .game-bg p {{
            color: rgba(255,255,255,0.9);
            text-shadow: 1px 1px 2px rgba(0,0,0,0.7);
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown('<div class="game-bg"><div class="content">', unsafe_allow_html=True)
    st.markdown("## 🛡️ OPR ArmyBuilder FR")
    st.markdown("<p class='muted'>Construisez, équilibrez et façonnez vos armées pour Age of Fantasy et Grimdark Future.</p>", unsafe_allow_html=True)
    st.markdown("</div></div>", unsafe_allow_html=True)
    st.markdown("---")

    factions_by_game, games = load_factions()
    if not games:
        st.error("Aucun jeu trouvé")
        st.stop()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("<span class='badge'>Jeu</span>", unsafe_allow_html=True)
        game = st.selectbox(
            "Choisissez un système",
            games,
            index=games.index(st.session_state.get("game")) if st.session_state.get("game") in games else 0,
            label_visibility="collapsed"
        )

        if 'game' not in st.session_state or game != st.session_state.game:
            st.session_state.game = game
            st.rerun()

    with col2:
        st.markdown("<span class='badge'>Faction</span>", unsafe_allow_html=True)
        faction_options = list(factions_by_game.get(game, {}).keys())
        if not faction_options:
            st.error("Aucune faction disponible pour ce jeu")
            st.stop()

        faction = st.selectbox(
            "Faction",
            faction_options,
            index=0,
            label_visibility="collapsed"
        )

    with col3:
        st.markdown("<span class='badge'>Format</span>", unsafe_allow_html=True)
        game_cfg = GAME_CONFIG.get(game, {})
        points = st.number_input(
            "Points",
            min_value=game_cfg.get("min_points", 250),
            max_value=game_cfg.get("max_points", 10000),
            value=game_cfg.get("default_points", 1000),
            step=250,
            label_visibility="collapsed"
        )

    st.markdown("")

    colA, colB = st.columns([2, 1])

    with colA:
        st.markdown("<span class='badge'>Nom de la liste</span>", unsafe_allow_html=True)
        list_name = st.text_input(
            "Nom de la liste",
            value=st.session_state.get(
                "list_name",
                f"Liste_{datetime.now().strftime('%Y%m%d')}"
            ),
            label_visibility="collapsed"
        )

    with colB:
        st.markdown("<span class='badge'>Action</span>", unsafe_allow_html=True)
        st.markdown("<p class='muted'>Prêt à forger votre armée ?</p>", unsafe_allow_html=True)

        can_build = all([game, faction, points > 0, list_name.strip() != ""])

        if st.button(
            "🔥 Construire l'armée",
            use_container_width=True,
            type="primary",
            disabled=not can_build,
            key="build_army"
        ):
            st.session_state.game = game
            st.session_state.faction = faction
            st.session_state.points = points
            st.session_state.list_name = list_name

            faction_data = factions_by_game[game][faction]
            st.session_state.units = faction_data.get("units", [])
            st.session_state.faction_special_rules = faction_data.get("faction_special_rules", [])
            st.session_state.faction_spells = faction_data.get("spells", {})

            st.session_state.army_list = []
            st.session_state.army_cost = 0
            st.session_state.unit_selections = {}

            st.session_state.page = "army"
            st.rerun()

# ======================================================
# PAGE 2 – CONSTRUCTEUR D'ARMÉE
# ======================================================
if st.session_state.page == "army":
    required_keys = ["game", "faction", "points", "list_name", "units", "faction_special_rules", "faction_spells"]
    if not all(key in st.session_state for key in required_keys):
        st.error("Configuration incomplète. Veuillez retourner à la page de configuration.")
        if st.button("Retour à la configuration", key="back_to_setup_1"):
            st.session_state.page = "setup"
            st.rerun()
        st.stop()

    if not st.session_state.units:
        st.error("Aucune unité disponible pour cette faction. Veuillez choisir une autre faction.")
        if st.button("Retour à la configuration", key="back_to_setup_2"):
            st.session_state.page = "setup"
            st.rerun()
        st.stop()

    st.session_state.setdefault("list_name", "Nouvelle Armée")
    st.session_state.setdefault("army_cost", 0)
    st.session_state.setdefault("army_list", [])
    st.session_state.setdefault("unit_selections", {})
    st.session_state.setdefault("unit_filter", "Tous")

    st.title(f"{st.session_state.list_name} - {st.session_state.army_cost}/{st.session_state.points} pts")

    if st.button("⬅️ Retour à la configuration", key="back_to_setup_3"):
        st.session_state.page = "setup"
        st.rerun()

    st.divider()
    st.subheader("📤 Export/Import de la liste")

    colE1, colE2, colE3 = st.columns(3)

    with colE1:
        json_data = json.dumps({
            "game": st.session_state.game,
            "faction": st.session_state.faction,
            "points": st.session_state.points,
            "list_name": st.session_state.list_name,
            "army_list": st.session_state.army_list,
            "army_cost": st.session_state.army_cost
        }, indent=2, ensure_ascii=False)
        st.download_button(
            "📄 Export JSON",
            data=json_data,
            file_name=f"{st.session_state.list_name}.json",
            mime="application/json",
            use_container_width=True,
            key="export_json"
        )

    with colE2:
        html_data = export_html(st.session_state.army_list, st.session_state.list_name, st.session_state.points)
        st.download_button(
            "🌐 Export HTML",
            data=html_data,
            file_name=f"{st.session_state.list_name}.html",
            mime="text/html",
            use_container_width=True,
            key="export_html"
        )

    with colE3:
        uploaded_file = st.file_uploader(
            "📥 Importer une liste d'armée",
            type=["json"],
            label_visibility="collapsed",
            accept_multiple_files=False,
            key="import_file"
        )

        if uploaded_file is not None:
            try:
                imported_data = json.loads(uploaded_file.getvalue().decode("utf-8"))

                if not isinstance(imported_data, dict) or "army_list" not in imported_data:
                    st.error("Fichier JSON invalide. Veuillez importer un fichier valide.")
                    st.stop()

                st.session_state.list_name = imported_data.get("list_name", st.session_state.list_name)
                st.session_state.army_list = imported_data["army_list"]
                st.session_state.army_cost = imported_data.get("army_cost", sum(u["cost"] for u in imported_data["army_list"]))

                st.success(f"Liste importée avec succès! ({len(imported_data['army_list'])} unités)")
                st.rerun()
            except Exception as e:
                st.error(f"Erreur lors de l'import: {str(e)}")

    st.subheader("📊 Points de l'Armée")
    points_used = st.session_state.army_cost
    points_total = st.session_state.points
    progress_ratio = min(points_used / points_total, 1.0) if points_total > 0 else 0

    st.progress(progress_ratio)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Points utilisés :** {points_used} pts")
    with col2:
        st.markdown(f"**Points totaux :** {points_total} pts")

    if points_used > points_total:
        st.error("⚠️ Dépassement du total de points autorisé")

    st.divider()

    game_cfg = GAME_CONFIG.get(st.session_state.game, {})
    col1, col2, col3 = st.columns(3)

    with col1:
        units_cap = math.floor(st.session_state.points / game_cfg.get("unit_per_points", 150))
        units_now = len([u for u in st.session_state.army_list if u.get("type") != "hero"])
        st.progress(min(units_now / max(units_cap, 1), 1.0))
        st.caption(f"Unités : {units_now} / {units_cap}")

    with col2:
        heroes_cap = math.floor(st.session_state.points / game_cfg.get("hero_limit", 375))
        heroes_now = len([u for u in st.session_state.army_list if u.get("type") == "hero"])
        st.progress(min(heroes_now / max(heroes_cap, 1), 1.0))
        st.caption(f"Héros : {heroes_now} / {heroes_cap}")

    with col3:
        copy_cap = 1 + math.floor(st.session_state.points / game_cfg.get("unit_copy_rule", 750))
        st.progress(min(copy_cap / 5, 1.0))
        st.caption(f"Copies max : {copy_cap} / unité")

    st.divider()

    if hasattr(st.session_state, 'faction_special_rules') and st.session_state.faction_special_rules:
        with st.expander("📜 Règles spéciales de la faction", expanded=False):
            for rule in st.session_state.faction_special_rules:
                if isinstance(rule, dict):
                    st.markdown(f"**{rule.get('name', 'Règle sans nom')}**: {rule.get('description', '')}")
                else:
                    st.markdown(f"- {rule}")

    if hasattr(st.session_state, 'faction_spells') and st.session_state.faction_spells:
        with st.expander("✨ Sorts de la faction", expanded=False):
            for spell_name, spell_details in st.session_state.faction_spells.items():
                if isinstance(spell_details, dict):
                    st.markdown(f"**{spell_name}** ({spell_details.get('cost', '?')} pts): {spell_details.get('description', '')}")

    # Liste de l'Armée
    st.subheader("Liste de l'Armée")
    if not st.session_state.army_list:
        st.markdown("Aucune unité ajoutée pour le moment.")
    else:
        for i, unit_data in enumerate(st.session_state.army_list):
            with st.expander(f"{unit_data['name']} - {unit_data['cost']} pts", expanded=False):
                # Première ligne : Infos de base
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.markdown(f"**Type :** {unit_data.get('type', 'unit')}")
                with col2:
                    st.markdown(f"**Qualité :** {unit_data.get('quality', '?')}+")
                with col3:
                    st.markdown(f"**Défense :** {unit_data.get('defense', '?')}+")
                with col4:
                    coriace = unit_data.get("coriace", 0)
                    st.markdown(f"**Coriace :** {coriace if coriace > 0 else '-'}")
                    st.markdown(f"**Taille :** {unit_data.get('size', '?')}")
    
                # Deuxième ligne : Armes
                weapons = unit_data.get("weapon", [])
                if weapons:
                    st.markdown("---")
                    st.markdown("**Armes :**")
                    if isinstance(weapons, list):
                        for weapon in weapons:
                            if isinstance(weapon, dict):
                                range_text = weapon.get('range', '-')
                                attacks = weapon.get('attacks', '-')
                                ap = weapon.get('armor_piercing', '-')
                                special_rules = weapon.get('special_rules', [])
    
                                if isinstance(range_text, (int, float)):
                                    range_text = f'{range_text}"'
                                elif range_text == "Mêlée":
                                    range_text = "Mêlée"
    
                                rules_text = ", ".join(special_rules) if special_rules else "-"
    
                                st.markdown(f"- {weapon.get('name', 'Arme')} | {range_text} | A{attacks} | PA{ap} | {rules_text}")
                    elif isinstance(weapons, dict):
                        range_text = weapons.get('range', '-')
                        attacks = weapons.get('attacks', '-')
                        ap = weapons.get('armor_piercing', '-')
                        special_rules = weapons.get('special_rules', [])
    
                        if isinstance(range_text, (int, float)):
                            range_text = f'{range_text}"'
                        elif range_text == "Mêlée":
                            range_text = "Mêlée"
    
                        rules_text = ", ".join(special_rules) if special_rules else "-"
    
                        st.markdown(f"- {weapons.get('name', 'Arme')} | {range_text} | A{attacks} | PA{ap} | {rules_text}")
    
                # Monture si présente
                if "mount" in unit_data and unit_data["mount"]:
                    mount = unit_data["mount"]
                    mount_name = mount.get("name", "Monture")
                    mount_data = mount.get("mount", {})
    
                    st.markdown("---")
                    st.markdown(f"**Monture :** {mount_name}")
    
                    if "weapon" in mount_data:
                        mount_weapons = mount_data["weapon"]
                        st.markdown("**Armes de la monture :**")
                        if isinstance(mount_weapons, list):
                            for weapon in mount_weapons:
                                if isinstance(weapon, dict):
                                    range_text = weapon.get('range', '-')
                                    attacks = weapon.get('attacks', '-')
                                    ap = weapon.get('armor_piercing', '-')
                                    special_rules = weapon.get('special_rules', [])
    
                                    if isinstance(range_text, (int, float)):
                                        range_text = f'{range_text}"'
                                    elif range_text == "Mêlée":
                                        range_text = "Mêlée"
    
                                    rules_text = ", ".join(special_rules) if special_rules else "-"
    
                                    st.markdown(f"- {weapon.get('name', 'Arme')} | {range_text} | A{attacks} | PA{ap} | {rules_text}")
    
                if st.button(f"Supprimer {unit_data['name']}", key=f"delete_unit_{i}"):
                    st.session_state.army_cost -= unit_data['cost']
                    st.session_state.army_list.pop(i)
                    st.rerun()

    st.divider()

    st.markdown(
        """
        <style>
        .filter-container {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin: 20px 0;
        }
        .filter-button {
            padding: 8px 15px;
            border-radius: 6px;
            border: 1px solid #ddd;
            background-color: #f8f9fa;
            color: #495057;
            font-weight: 500;
            text-align: center;
            cursor: pointer;
            transition: all 0.2s;
        }
        .filter-button:hover {
            background-color: #e9ecef;
        }
        .filter-button.active {
            background-color: #3498db;
            color: white;
            font-weight: 600;
        }
        @media (max-width: 768px) {
            .filter-container {
                flex-direction: column;
            }
            .filter-button {
                width: 100%;
            }
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown("<div class='filter-container'>", unsafe_allow_html=True)
    st.subheader("Filtres par type d'unité")

    filter_categories = {
        "Tous": None,
        "Héros": ["hero"],
        "Héros nommés": ["named_hero"],
        "Unités de base": ["unit"],
        "Véhicules légers / Petits monstres": ["light_vehicle"],
        "Véhicules / Monstres": ["vehicle"],
        "Titans": ["titan"]
    }

    for category in filter_categories.keys():
        btn = st.button(
            category,
            key=f"filter_{category}",
            use_container_width=True
        )

        if btn:
            st.session_state.unit_filter = category
            st.rerun()

    st.markdown(
        f"""
        <script>
        document.querySelectorAll('button').forEach(btn => {{
            if (btn.textContent === '{st.session_state.unit_filter}') {{
                btn.style.backgroundColor = '#3498db';
                btn.style.color = 'white';
                btn.style.fontWeight = '600';
                btn.style.borderColor = '#2980b9';
            }}
        }});
        </script>
        """,
        unsafe_allow_html=True
    )

    st.markdown("</div>", unsafe_allow_html=True)

    filtered_units = []
    if st.session_state.unit_filter == "Tous":
        filtered_units = st.session_state.units
    else:
        relevant_types = filter_categories[st.session_state.unit_filter]
        filtered_units = [
            unit for unit in st.session_state.units
            if unit.get('unit_detail') in relevant_types
        ]

    st.markdown(f"""
    <div style='text-align: center; margin: 10px 0; color: #6c757d; font-size: 0.9em;'>
        {len(filtered_units)} unités disponibles (filtre: {st.session_state.unit_filter})
    </div>
    """, unsafe_allow_html=True)

    if filtered_units:
        unit = st.selectbox(
            "Unité disponible",
            filtered_units,
            format_func=format_unit_option,
            key="unit_select",
        )
    else:
        st.warning(f"Aucune unité disponible pour le filtre '{st.session_state.unit_filter}'.")
        st.stop()

    if not unit:
        st.error("Aucune unité sélectionnée.")
        st.stop()

    if "upgrade_groups" not in unit:
        unit["upgrade_groups"] = []

    unit_key = f"unit_{unit['name']}"
    st.session_state.unit_selections.setdefault(unit_key, {})

    # Initialisation des variables
    weapons = list(unit.get("weapon", []))
    selected_options = {}
    mount = None
    weapon_cost = 0
    mount_cost = 0
    upgrades_cost = 0

    # Configuration des améliorations
    for g_idx, group in enumerate(unit.get("upgrade_groups", [])):
        g_key = f"group_{g_idx}"

        # Vérifier si le groupe a des options valides
        has_valid_options = False
        if group.get("type") == "weapon":
            has_valid_options = len(group.get("options", [])) > 0
        elif group.get("type") == "role":
            has_valid_options = len(group.get("options", [])) > 0
        elif group.get("type") == "variable_weapon_count":
            has_valid_options = len(group.get("options", [])) > 0
        elif group.get("type") == "conditional_weapon":
            has_valid_options = len([o for o in group.get("options", [])
                                    if not o.get("requires", []) or check_weapon_conditions(unit_key, o.get("requires", []))]) > 0
        elif group.get("type") == "upgrades":
            has_valid_options = len(group.get("options", [])) > 0
        elif group.get("type") == "mount":
            has_valid_options = len(group.get("options", [])) > 0

        if not has_valid_options:
            continue

        st.subheader(group.get("group", "Améliorations"))

        # =============================================
        # ARMES STANDARD (remplacement complet)
        # =============================================
        if group.get("type") == "weapon":
            choices = []
            base_weapons = unit.get("weapon", [])

            if isinstance(base_weapons, list) and base_weapons:
                base_weapons_labels = []
                for weapon in base_weapons:
                    base_weapons_labels.append(weapon.get('name', 'Arme'))

                if len(base_weapons_labels) == 1:
                    choices.append(format_weapon_option(base_weapons[0]))
                else:
                    choices.append(" et ".join(base_weapons_labels))
            elif isinstance(base_weapons, dict):
                choices.append(format_weapon_option(base_weapons))

            opt_map = {}
            for o in group.get("options", []):
                weapon = o.get("weapon", {})
                if isinstance(weapon, list):
                    weapon_names = [w.get('name', 'Arme') for w in weapon]
                    label = " et ".join(weapon_names) + f" (+{o['cost']} pts)"
                else:
                    label = format_weapon_option(weapon, o['cost'])
                choices.append(label)
                opt_map[label] = o

            if choices:
                current = st.session_state.unit_selections[unit_key].get(g_key, choices[0] if choices else "Aucune arme")
                choice = st.radio(
                    "Sélection de l'arme",
                    choices,
                    index=choices.index(current) if current in choices else 0,
                    key=f"{unit_key}_{g_key}_weapon",
                )

                st.session_state.unit_selections[unit_key][g_key] = choice

                if choice != choices[0]:
                    for opt_label, opt in opt_map.items():
                        if opt_label == choice:
                            weapon_cost += opt["cost"]
                            if not isinstance(opt["weapon"], list):
                                weapons = [opt["weapon"]]
                            else:
                                weapons = opt["weapon"]
                            break

        # =============================================
        # AMÉLIORATIONS D'ARME INDIVIDUELLES (remplacement d'une seule arme)
        # =============================================
        elif group.get("type") == "conditional_weapon":
            available_options = []
            for opt in group.get("options", []):
                requires = opt.get("requires", [])
                if not requires or check_weapon_conditions(unit_key, requires):
                    available_options.append(opt)

            if not available_options:
                st.markdown(f"""
                <div style='color: #999; font-size: 0.9em; margin-bottom: 15px;'>
                    {group.get("description", "")} <em>(Non disponible)</em>
                </div>
                """, unsafe_allow_html=True)
            else:
                choices = ["Aucune amélioration"]
                opt_map = {}

                for o in available_options:
                    weapon = o.get("weapon", {})
                    label = f"{o.get('name', 'Amélioration')} (+{o.get('cost', 0)} pts)"
                    choices.append(label)
                    opt_map[label] = o

                current = st.session_state.unit_selections[unit_key].get(g_key, choices[0])
                choice = st.radio(
                    group.get("description", "Sélectionnez une amélioration"),
                    choices,
                    index=choices.index(current) if current in choices else 0,
                    key=f"{unit_key}_{g_key}_conditional"
                )

                st.session_state.unit_selections[unit_key][g_key] = choice

                if choice != choices[0]:
                    opt = opt_map[choice]
                    upgrades_cost += opt.get("cost", 0)

                    # Trouver et remplacer l'arme
                    if "replaces" in opt and "weapon" in opt:
                        # Trouver l'arme à remplacer
                        weapons_to_replace = []
                        for weapon in weapons:
                            if weapon.get("name") in opt.get("replaces", []):
                                weapons_to_replace.append(weapon)

                        if weapons_to_replace:
                            weapons.remove(weapons_to_replace[0])

                        # Ajouter la nouvelle arme
                        new_weapon = opt.get("weapon", {})
                        if isinstance(new_weapon, dict):
                            new_weapon = new_weapon.copy()
                            new_weapon["_upgraded"] = True
                            weapons.append(new_weapon)
                        elif isinstance(new_weapon, list):
                            for w in new_weapon:
                                w = w.copy()
                                w["_upgraded"] = True
                                weapons.append(w)

        # =============================================
        # AMÉLIORATIONS D'ARME A NOMBRE VARIABLE (slider)
        # =============================================
        elif group.get("type") == "variable_weapon_count":
            st.markdown(f"""
            <div style='margin-bottom: 10px; color: #6c757d;'>
                {group.get("description", "")}
            </div>
            """, unsafe_allow_html=True)

            # Conserver les armes de base
            base_weapons = unit.get("weapon", [])
            if isinstance(base_weapons, list):
                base_weapons = base_weapons.copy()
            elif isinstance(base_weapons, dict):
                base_weapons = [base_weapons]

            # Pour chaque option d'amélioration
            for opt_idx, option in enumerate(group.get("options", [])):
                st.markdown(f"""
                <div style='margin-top: 15px; margin-bottom: 10px;'>
                  <h4 style='color: #3498db;'>{option['name']}</h4>
                </div>
                """, unsafe_allow_html=True)

                requires = option.get("requires", [])
                if requires and not check_weapon_conditions(unit_key, requires):
                    st.markdown(f"""
                    <div style='color: #999; font-size: 0.9em; margin-bottom: 15px;'>
                        {option['name']} <em>(Non disponible - nécessite {', '.join(requires)})</em>
                    </div>
                    """, unsafe_allow_html=True)
                    continue

                max_count = unit.get("size", 1)
                if "max_count" in option:
                    max_count = min(option["max_count"].get("value", max_count), unit.get("size", 1))

                min_count = option.get("min_count", 0)

                count = st.slider(
                    f"Nombre de {option['name']} (max: {max_count})",
                    min_value=min_count,
                    max_value=max_count,
                    value=min_count,
                    key=f"{unit_key}_{g_key}_count_{opt_idx}"
                )

                total_cost = count * option["cost"]
                upgrades_cost += total_cost

                st.markdown(f"""
                <div style='margin: 10px 0; padding: 8px; background: #f8f9fa; border-radius: 4px;'>
                    <strong>{option['name']}</strong> × {count} =
                    <strong style='color: #e74c3c;'>{total_cost} pts</strong>
                </div>
                """, unsafe_allow_html=True)

                if count > 0:
                    # Conserver toutes les armes de base
                    final_weapons = base_weapons.copy()

                    # Ajouter les nouvelles armes avec le nombre d'exemplaires
                    new_weapon = option["weapon"]
                    if isinstance(new_weapon, dict):
                        new_weapon = new_weapon.copy()
                        new_weapon["_count"] = count
                        new_weapon["_replaces"] = option.get("replaces", [])
                        new_weapon["_upgraded"] = True
                        final_weapons.append(new_weapon)
                    elif isinstance(new_weapon, list):
                        for w in new_weapon:
                            w = w.copy()
                            w["_count"] = count
                            w["_replaces"] = option.get("replaces", [])
                            w["_upgraded"] = True
                            final_weapons.append(w)

                    # Mettre à jour les armes de l'unité
                    weapons = final_weapons

        # =============================================
        # RÔLES (pour héros et titans)
        # =============================================
        elif group.get("type") == "role":
            choices = ["Aucun rôle"]
            opt_map = {}

            for o in group.get("options", []):
                role_name = o.get('name', 'Rôle')
                cost = o.get('cost', 0)
                special_rules = o.get('special_rules', [])

                label = f"{role_name}"
                if special_rules:
                    rules_text = ", ".join(special_rules)
                    label += f" | {rules_text}"
                label += f" (+{cost} pts)"

                choices.append(label)
                opt_map[label] = o

            current = st.session_state.unit_selections[unit_key].get(g_key, choices[0])
            choice = st.radio(
                group.get("group", "Rôle"),
                choices,
                index=choices.index(current) if current in choices else 0,
                key=f"{unit_key}_{g_key}_role",
                horizontal=True if len(choices) <= 4 else False
            )

            st.session_state.unit_selections[unit_key][g_key] = choice

            if choice != choices[0]:
                opt = opt_map[choice]
                upgrades_cost += opt.get("cost", 0)
                selected_options[group.get("group", "Rôle")] = [opt]

                if "weapon" in opt:
                    role_weapons = opt.get("weapon", [])
                    if isinstance(role_weapons, list):
                        weapons.extend(role_weapons)
                    elif isinstance(role_weapons, dict):
                        weapons.append(role_weapons)

        # =============================================
        # AMÉLIORATIONS D'UNITÉ
        # =============================================
        elif group.get("type") == "upgrades":
            for o_idx, o in enumerate(group.get("options", [])):
                opt_key = f"{unit_key}_{g_key}_{o['name']}_{o_idx}"
                checked = st.checkbox(
                    f"{o['name']} (+{o['cost']} pts)",
                    value=st.session_state.unit_selections[unit_key].get(opt_key, False),
                    key=opt_key,
                )
                st.session_state.unit_selections[unit_key][opt_key] = checked
                if checked:
                    upgrades_cost += o["cost"]
                    selected_options.setdefault(group.get("group", "Options"), []).append(o)

        # =============================================
        # MONTURE
        # =============================================
        elif group.get("type") == "mount":
            choices = ["Aucune monture"]
            opt_map = {}

            for o in group.get("options", []):
                label = format_mount_option(o)
                choices.append(label)
                opt_map[label] = o

            current = st.session_state.unit_selections[unit_key].get(g_key, choices[0])
            choice = st.radio(
                "Monture",
                choices,
                index=choices.index(current) if current in choices else 0,
                key=f"{unit_key}_{g_key}_mount",
            )

            st.session_state.unit_selections[unit_key][g_key] = choice

            if choice != "Aucune monture":
                mount = opt_map[choice]
                mount_cost = mount["cost"]

    # Calcul du coût final
    multiplier = 1
    if unit.get("type") != "hero" and unit.get("size", 1) > 1:
        if st.checkbox("Unité combinée", key=f"{unit_key}_combined"):
            multiplier = 2

    base_cost = unit.get("base_cost", 0)
    final_cost = (base_cost + weapon_cost) * multiplier + upgrades_cost + mount_cost

    st.subheader("Coût de l'unité sélectionnée")
    st.markdown(f"**Coût total :** {final_cost} pts")
    st.divider()

    if st.button("➕ Ajouter à l'armée", key=f"{unit_key}_add_to_army"):
        if st.session_state.army_cost + final_cost > st.session_state.points:
            st.error(f"⛔ Dépassement du format : {st.session_state.army_cost + final_cost} / {st.session_state.points} pts")
            st.stop()

        # Préparation des règles spéciales
        coriace_total = unit.get("coriace", 0)
        if mount and "mount" in mount:
            coriace_total += mount["mount"].get("coriace_bonus", 0)

        all_special_rules = unit.get("special_rules", []).copy()

        # Ajouter les règles spéciales des options sélectionnées
        for group in unit.get("upgrade_groups", []):
            group_key = f"group_{unit.get('upgrade_groups', []).index(group)}"
            selected_option = st.session_state.unit_selections[unit_key].get(group_key, "")
            if selected_option and selected_option != "Aucune amélioration" and selected_option != "Aucun rôle":
                for opt in group.get("options", []):
                    if "special_rules" in opt and f"{opt.get('name')}" in selected_option:
                        all_special_rules.extend(opt["special_rules"])

        if mount:
            mount_data = mount.get("mount", {})
            if "special_rules" in mount_data:
                for rule in mount_data["special_rules"]:
                    if not rule.startswith(("Griffes", "Sabots")) and "Coriace" not in rule:
                        all_special_rules.append(rule)

        # Création de l'unité
        unit_data = {
            "name": unit["name"],
            "type": unit.get("type", "unit"),
            "cost": final_cost,
            "size": unit.get("size", 10) * multiplier if unit.get("type") != "hero" else 1,
            "quality": unit.get("quality"),
            "defense": unit.get("defense"),
            "weapon": weapons,  # Toutes les armes (y compris améliorations) sont ici
            "options": selected_options,
            "mount": mount,
            "special_rules": list(set(all_special_rules)),  # Supprimer les doublons
            "coriace": coriace_total
        }

        if validate_army_rules(st.session_state.army_list + [unit_data], st.session_state.points, st.session_state.game):
            st.session_state.army_list.append(unit_data)
            st.session_state.army_cost += final_cost
            st.rerun()
