import json
import streamlit as st
from pathlib import Path
from datetime import datetime
import re
import math

st.set_page_config(
    page_title="OPR ArmyBuilder FR",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ======================================================
# FONCTIONS UTILITAIRES POUR LES NOUVEAUX TYPES D'AMÉLIORATIONS
# ======================================================
def calculate_max_count(unit, count_rule):
    """Calcule le nombre maximum d'améliorations possibles"""
    if not count_rule or not isinstance(count_rule, dict):
        return 1  # Valeur par défaut

    rule_type = count_rule.get("type", "fixed")
    value = count_rule.get("value", 1)

    if rule_type == "fixed":
        return value
    elif rule_type == "size_based":
        return unit.get("size", 1) * value
    elif rule_type == "quality_based":
        return unit.get("quality", 3) * value
    elif rule_type == "defense_based":
        return unit.get("defense", 3) * value
    elif rule_type == "percentage":
        return math.ceil(unit.get("size", 1) * (value / 100))
    else:
        return value

def format_count_options(option, unit, current_count=0):
    """Formate les options de compteur pour une amélioration"""
    max_count = calculate_max_count(unit, option.get("max_count", {"type": "fixed", "value": 1}))
    min_count = option.get("min_count", 0)
    cost_per_unit = option.get("cost_per_unit", option.get("cost", 0))

    # Limiter le max_count à la taille de l'unité si c'est une amélioration par figurine
    if option.get("weapon") or option.get("special_rules"):
        max_count = min(max_count, unit.get("size", 1))

    # Créer les options de 0 à max_count
    choices = []
    for count in range(min_count, max_count + 1):
        total_cost = count * cost_per_unit
        label = f"{count} × {option['name']} (+{total_cost} pts)"
        choices.append({
            "label": label,
            "count": count,
            "cost": total_cost,
            "option": option
        })

    return choices, max_count

# ======================================================
# CSS
# ======================================================
st.markdown(
    """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {background: transparent;}

    /* Fond général plus contrasté */
    .stApp {
        background: #e9ecef;
        color: #212529;
    }

    /* Sidebar plus visible */
    section[data-testid="stSidebar"] {
        background: #dee2e6;
        border-right: 1px solid #adb5bd;
        box-shadow: 2px 0 5px rgba(0,0,0,0.1);
    }

    /* Titres plus visibles */
    h1, h2, h3 {
        color: #202c45;
        letter-spacing: 0.04em;
        font-weight: 600;
    }

    /* Style amélioré pour les selectbox */
    .stSelectbox, .stNumberInput, .stTextInput {
        background-color: white;
        border-radius: 6px;
        border: 1px solid #ced4da;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        transition: all 0.2s ease;
    }

    /* Styles pour les améliorations variables */
    .variable-upgrade {
        margin-bottom: 15px;
        padding: 10px;
        background: rgba(240, 248, 255, 0.3);
        border-radius: 6px;
        border-left: 3px solid #3498db;
    }

    .upgrade-counter {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin: 5px 0;
    }

    .upgrade-summary {
        background: #f0f8ff;
        padding: 8px;
        border-radius: 4px;
        margin: 10px 0;
        font-weight: bold;
    }

    /* Style pour les remplacements d'armes */
    .weapon-replacement {
        background: rgba(255, 235, 205, 0.3);
        padding: 8px;
        border-radius: 4px;
        margin: 8px 0;
        border-left: 3px solid #ff8c00;
    }

    .weapon-replacement .removed {
        color: #dc3545;
        text-decoration: line-through;
    }

    .weapon-replacement .added {
        color: #28a745;
        font-weight: bold;
    }

    /* Rest of your existing CSS */
    .stSelectbox:hover, .stNumberInput:hover, .stTextInput:hover {
        border-color: #3498db;
        box-shadow: 0 0 0 3px rgba(52, 152, 219, 0.2);
    }

    .stSelectbox > div, .stNumberInput > div, .stTextInput > div {
        border-radius: 6px !important;
    }

    .stSelectbox label, .stNumberInput label, .stTextInput label {
        color: #2c3e50;
        font-weight: 500;
        margin-bottom: 0.3rem;
    }

    button[kind="primary"] {
        background: linear-gradient(135deg, #2980b9, #1e5aa8) !important;
        color: white !important;
        font-weight: bold;
        border-radius: 6px;
        padding: 0.6rem 1rem;
        border: none;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        transition: all 0.2s ease;
    }

    button[kind="primary"]:hover {
        background: linear-gradient(135deg, #1e5aa8, #194b8d) !important;
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        transform: translateY(-1px);
    }

    /* Style pour les badges */
    .badge {
        display: inline-block;
        padding: 0.35rem 0.75rem;
        border-radius: 4px;
        background: #2980b9;
        color: white;
        font-size: 0.8rem;
        margin-bottom: 0.75rem;
        font-weight: 600;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }

    /* Style pour les cartes */
    .card {
        background: #ffffff;
        border: 2px solid #2980b9;
        border-radius: 8px;
        padding: 1.2rem;
        transition: all 0.2s ease;
        cursor: pointer;
        box-shadow: 0 2px 8px rgba(41, 128, 185, 0.2);
    }

    .card:hover {
        border-color: #1e5aa8;
        box-shadow: 0 4px 16px rgba(41, 128, 185, 0.3);
        transform: translateY(-2px);
    }

    /* Style pour les éléments de formulaire */
    .stButton>button {
        background-color: #f8f9fa;
        border: 1px solid #ced4da;
        border-radius: 6px;
        padding: 0.5rem 1rem;
        color: #212529;
        font-weight: 500;
        transition: all 0.2s ease;
    }

    .stButton>button:hover {
        background-color: #e9ecef;
        border-color: #3498db;
        color: #2980b9;
    }

    /* Style pour les colonnes */
    .stColumn {
        padding: 0.5rem;
    }

    /* Style pour les diviseurs */
    .stDivider {
        margin: 1.5rem 0;
        border-top: 1px solid #adb5bd;
    }

    /* Style pour les messages d'erreur */
    .stAlert {
        border-radius: 6px;
        padding: 0.75rem 1.25rem;
    }

    /* Style pour la progression */
    .stProgress > div > div > div {
        background-color: #2980b9 !important;
    }

    /* Style pour les éléments de sélection */
    .stSelectbox div[role="button"] {
        background-color: white !important;
        border: 1px solid #ced4da !important;
        border-radius: 6px !important;
    }

    /* Style pour les éléments focus */
    .stSelectbox div[role="button"]:focus,
    .stNumberInput input:focus,
    .stTextInput input:focus {
        border-color: #3498db !important;
        box-shadow: 0 0 0 3px rgba(52, 152, 219, 0.2) !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

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
# CONFIGURATION DES JEUX OPR (EXTENSIBLE)
# ======================================================
GAME_CONFIG = {
    "Age of Fantasy": {
        "min_points": 250,
        "max_points": 10000,
        "default_points": 1000,
        "hero_limit": 375,
        "unit_copy_rule": 750,
        "unit_max_cost_ratio": 0.35,
        "unit_per_points": 150
    },
    "Age of Fantasy: Regiments": {
        "min_points": 500,
        "max_points": 20000,
        "default_points": 2000,
        "hero_limit": 500,
        "unit_copy_rule": 1000,
        "unit_max_cost_ratio": 0.4,
        "unit_per_points": 200
    },
    "Grimdark Future": {
        "min_points": 250,
        "max_points": 10000,
        "default_points": 1000,
        "hero_limit": 375,
        "unit_copy_rule": 750,
        "unit_max_cost_ratio": 0.35,
        "unit_per_points": 150
    },
    "Grimdark Future: Firefight": {
        "min_points": 150,
        "max_points": 1000,
        "default_points": 300,
        "hero_limit": 300,
        "unit_copy_rule": 300,
        "unit_max_cost_ratio": 0.6,
        "unit_per_points": 100
    },
    "Age of Fantasy: Skirmish": {
        "min_points": 150,
        "max_points": 1000,
        "default_points": 300,
        "hero_limit": 300,
        "unit_copy_rule": 300,
        "unit_max_cost_ratio": 0.6,
        "unit_per_points": 100
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

    # Récupération des armes de base
    weapons = u.get('weapon', [])
    weapon_profiles = []
    if isinstance(weapons, list):
        for weapon in weapons:
            if isinstance(weapon, dict):
                attacks = weapon.get('attacks', '?')
                ap = weapon.get('armor_piercing', '?')
                weapon_profiles.append(f"A{attacks}/PA{ap}")
    elif isinstance(weapons, dict):
        attacks = weapons.get('attacks', '?')
        ap = weapons.get('armor_piercing', '?')
        weapon_profiles.append(f"A{attacks}/PA{ap}")

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

def format_weapon_option(weapon):
    """Formate le nom de l'arme avec son profil pour remplacer 'Arme de base'"""
    if not weapon or not isinstance(weapon, dict):
        return "Aucune arme"

    name = weapon.get('name', 'Arme')
    attacks = weapon.get('attacks', '?')
    ap = weapon.get('armor_piercing', '?')
    range_text = weapon.get('range', 'Mêlée')

    return f"{name} (A{attacks}/PA{ap}/{range_text})"

# ======================================================
# EXPORT HTML - VERSION CORRIGÉE
# ======================================================
def export_html(army_list, army_name, army_limit):
    def esc(txt):
        return str(txt).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

    def format_weapon(weapon):
        """Formate une arme pour l'affichage avec ses règles spéciales"""
        if not weapon:
            return "Aucune arme"

        range_text = weapon.get('range', '-')
        attacks = weapon.get('attacks', '-')
        ap = weapon.get('armor_piercing', '-')
        special_rules = weapon.get('special_rules', [])

        if range_text == "-" or range_text is None or range_text.lower() == "mêlée":
            range_text = "Mêlée"

        result = f"{range_text} | A{attacks}"

        if ap not in ("-", 0, "0", None):
            result += f" | PA{ap}"

        if special_rules:
            result += f" | {', '.join(special_rules)}"

        return result

    def get_special_rules(unit):
        """Extraire toutes les règles spéciales de l'unité SAUF celles des armes"""
        rules = set()

        # 1. Règles spéciales de base de l'unité
        if "special_rules" in unit:
            for rule in unit["special_rules"]:
                if isinstance(rule, str):
                    rules.add(rule)

        # 2. Règles spéciales des améliorations (y compris rôles)
        if "options" in unit:
            for group_name, opts in unit["options"].items():
                if isinstance(opts, list):
                    for opt in opts:
                        if "special_rules" in opt:
                            for rule in opt["special_rules"]:
                                if isinstance(rule, str):
                                    rules.add(rule)

        # 3. Règles spéciales de la monture
        if "mount" in unit and unit.get("mount"):
            mount_data = unit["mount"].get("mount", {})
            if "special_rules" in mount_data:
                for rule in mount_data["special_rules"]:
                    if isinstance(rule, str):
                        rules.add(rule)

        return sorted(rules, key=lambda x: x.lower().replace('é', 'e').replace('è', 'e'))

    def get_french_type(unit):
        """Retourne le type français basé sur unit_detail"""
        if unit.get('type') == 'hero':
            return 'Héros'
        unit_detail = unit.get('unit_detail', 'unit')
        type_mapping = {
            'hero': 'Héros',
            'named_hero': 'Héros nommé',
            'unit': 'Unité de base',
            'light_vehicle': 'Véhicule léger',
            'vehicle': 'Véhicule/Monstre',
            'titan': 'Titan'
        }
        return type_mapping.get(unit_detail, 'Unité')

    # Trier la liste pour afficher les héros en premier
    sorted_army_list = sorted(army_list, key=lambda x: 0 if x.get("type") == "hero" else 1)

    html = f"""
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title>Liste d'Armée OPR - {esc(army_name)}</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root {{
  --bg-dark: #f8f9fa;
  --bg-card: #ffffff;
  --bg-header: #e9ecef;
  --accent: #3498db;
  --text-main: #212529;
  --text-muted: #6c757d;
  --border: #dee2e6;
  --cost-color: #ff6b6b;
  --tough-color: #e74c3c;
}}

body {{
  background: var(--bg-dark);
  color: var(--text-main);
  font-family: 'Inter', sans-serif;
  margin: 0;
  padding: 20px;
  line-height: 1.5;
}}

.army {{
  max-width: 800px;
  margin: 0 auto;
}}

.army-title {{
  text-align: center;
  font-size: 24px;
  font-weight: 700;
  margin-bottom: 20px;
  color: var(--accent);
  border-bottom: 1px solid var(--border);
  padding-bottom: 10px;
}}

.army-summary {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: var(--bg-card);
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
  padding: 16px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}}

.unit-header {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}}

.unit-name {{
  font-size: 18px;
  font-weight: 600;
  color: var(--text-main);
  margin: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}}

.unit-cost {{
  font-family: monospace;
  font-size: 18px;
  font-weight: bold;
  color: var(--cost-color);
}}

.unit-type {{
  font-size: 14px;
  color: var(--text-muted);
  margin-top: 4px;
}}

.stats-grid {{
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  background: var(--bg-header);
  padding: 12px;
  border-radius: 6px;
  text-align: center;
  font-size: 12px;
  margin: 12px 0;
}}

.stat-item {{
  padding: 5px;
  display: flex;
  flex-direction: column;
  align-items: center;
}}

.stat-label {{
  color: var(--text-muted);
  font-size: 10px;
  text-transform: uppercase;
  margin-bottom: 3px;
  display: flex;
  align-items: center;
  gap: 5px;
}}

.stat-value {{
  font-weight: bold;
  font-size: 16px;
  color: var(--text-main);
}}

.tough-value {{
  color: var(--tough-color) !important;
  font-weight: bold;
  font-size: 18px;
}}

.section-title {{
  font-weight: 600;
  margin: 15px 0 8px 0;
  color: var(--text-main);
  font-size: 14px;
}}

.weapon-item {{
  background: var(--bg-header);
  padding: 8px;
  border-radius: 4px;
  margin-bottom: 6px;
  display: flex;
  justify-content: space-between;
}}

.weapon-name {{
  font-weight: 500;
  color: var(--text-main);
  flex: 1;
}}

.weapon-stats {{
  text-align: right;
  white-space: nowrap;
  flex: 1;
}}

.rules-section {{
  margin: 12px 0;
}}

.rules-title {{
  font-weight: 600;
  margin-bottom: 6px;
  color: #3498db;
  font-size: 14px;
}}

.rules-list {{
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}}

.rule-tag {{
  background: var(--bg-header);
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 11px;
  color: var(--text-main);
}}

.summary-cost {{
  font-family: monospace;
  font-size: 24px;
  font-weight: bold;
  color: var(--cost-color);
}}

.role-section {{
  background: rgba(240, 248, 255, 0.3);
  padding: 10px;
  border-radius: 6px;
  margin: 10px 0;
  border-left: 3px solid #3498db;
}}

.role-title {{
  font-weight: 600;
  color: #3498db;
  margin-bottom: 5px;
  font-size: 14px;
}}

@media print {{
  body {{
    background: white;
    color: black;
  }}
  .unit-card, .army-summary {{
    background: white;
    border: 1px solid #ccc;
    page-break-inside: avoid;
  }}
}}
</style>
</head>
<body>
<div class="army">
  <!-- Titre de la liste -->
  <div class="army-title">
    {esc(army_name)} - {sum(unit['cost'] for unit in sorted_army_list)}/{army_limit} pts
  </div>

  <!-- Résumé de l'armée -->
  <div class="army-summary">
    <div style="font-size: 14px; color: var(--text-main);">
      <span style="color: var(--text-muted);">Nombre d'unités:</span>
      <strong style="margin-left: 8px; font-size: 18px;">{len(sorted_army_list)}</strong>
    </div>
    <div class="summary-cost">
      {sum(unit['cost'] for unit in sorted_army_list)}/{army_limit} pts
    </div>
  </div>
"""

    for unit in sorted_army_list:
        # Initialisation sécurisée de toutes les variables
        name = esc(unit.get("name", "Unité"))
        cost = unit.get("cost", 0)
        quality = esc(unit.get("quality", "-"))
        defense = esc(unit.get("defense", "-"))
        unit_type_french = get_french_type(unit)
        unit_size = unit.get("size", 10)

        if unit.get("type") == "hero":
            unit_size = 1

        # Calcul de la valeur de Coriace
        tough_value = unit.get("coriace", 0)

        # Récupération sécurisée des données
        weapons = unit.get("weapon", [])
        if not isinstance(weapons, list):
            weapons = [weapons]

        special_rules = get_special_rules(unit)
        unit_options = unit.get("options", {})
        mount = unit.get("mount", None)

        html += f'''
<div class="unit-card">
  <div class="unit-header">
    <div>
      <h3 class="unit-name">
        {name}
        <span style="font-size: 12px; color: var(--text-muted); margin-left: 8px;">[{unit_size}]</span>
      </h3>
      <div class="unit-type">
        {"★" if unit.get("type") == "hero" else "🛡️"} {unit_type_french}
      </div>
    </div>
    <div class="unit-cost">{cost} pts</div>
  </div>

  <div class="stats-grid">
    <div class="stat-item">
      <div class="stat-label"><span>⚔️</span> Qualité</div>
      <div class="stat-value">{quality}+</div>
    </div>
    <div class="stat-item">
      <div class="stat-label"><span>🛡️</span> Défense</div>
      <div class="stat-value">{defense}+</div>
    </div>
    <div class="stat-item">
      <div class="stat-label"><span>❤️</span> Coriace</div>
      <div class="stat-value tough-value">{tough_value if tough_value > 0 else "-"}</div>
    </div>
  </div>
'''

        # Armes
        if weapons:
            html += '<div class="section-title">Armes:</div>'
            for weapon in weapons:
                if weapon and isinstance(weapon, dict):
                    html += f'''
    <div class="weapon-item">
      <div class="weapon-name">{esc(weapon.get('name', 'Arme'))}</div>
      <div class="weapon-stats">{format_weapon(weapon)}</div>
    </div>
'''

        # Rôles
        if unit_options:
            for group_name, opts in unit_options.items():
                if isinstance(opts, list) and opts:
                    for opt in opts:
                        if isinstance(opt, dict) and "weapon" in opt:
                            role_name = opt.get("name", "Rôle")
                            role_weapons = opt.get("weapon", [])
                            role_special_rules = opt.get("special_rules", [])

                            html += f'''
    <div class="role-section">
      <div class="role-title">Rôle: {esc(role_name)}</div>
'''

                            # Armes du rôle
                            if role_weapons:
                                if isinstance(role_weapons, list):
                                    for weapon in role_weapons:
                                        if isinstance(weapon, dict):
                                            html += f'''
        <div class="weapon-item" style="margin-left: 15px;">
          <div class="weapon-name">{esc(weapon.get('name', 'Arme du rôle'))}</div>
          <div class="weapon-stats">{format_weapon(weapon)}</div>
        </div>
'''
                                else:
                                    html += f'''
        <div class="weapon-item" style="margin-left: 15px;">
          <div class="weapon-name">{esc(role_weapons.get('name', 'Arme du rôle'))}</div>
          <div class="weapon-stats">{format_weapon(role_weapons)}</div>
        </div>
'''

                            # Règles spéciales du rôle (hors armes)
                            role_rules_to_show = []
                            for rule in role_special_rules:
                                if isinstance(rule, str):
                                    is_weapon_rule = False
                                    if "weapon" in opt:
                                        role_weapons = opt.get("weapon", [])
                                        if isinstance(role_weapons, list):
                                            for weapon in role_weapons:
                                                if isinstance(weapon, dict) and "special_rules" in weapon:
                                                    if rule in weapon["special_rules"]:
                                                        is_weapon_rule = True
                                                        break
                                        elif isinstance(role_weapons, dict) and "special_rules" in role_weapons:
                                            if rule in role_weapons["special_rules"]:
                                                is_weapon_rule = True

                                    if not is_weapon_rule:
                                        role_rules_to_show.append(rule)

                            if role_rules_to_show:
                                html += '''
      <div style="margin-left: 15px; margin-top: 5px;">
        <div style="font-weight: 600; color: #3498db; font-size: 12px;">Règles spéciales:</div>
        <div style="display: flex; flex-wrap: wrap; gap: 4px; margin-top: 3px;">
'''
                                for rule in role_rules_to_show:
                                    html += f'<span class="rule-tag">{esc(rule)}</span>'
                                html += '''
        </div>
      </div>
'''
                            html += '''
    </div>
'''

        # Section des améliorations sélectionnées
        if unit_options and isinstance(unit_options, dict) and unit_options:
            html += '''
  <div class="upgrades-section">
    <div class="rules-title">Améliorations sélectionnées:</div>
'''
            for group_name, opts in unit_options.items():
                if isinstance(opts, list) and opts:
                    for opt in opts:
                        if isinstance(opt, dict):
                            # Cas spécial pour les améliorations par figurine
                            if "total_cost" in opt:
                                html += f'''
    <div class="upgrade-item">
      <div class="upgrade-name">
        {esc(opt.get("name", ""))} × {opt.get("count", 1)}
        <span style="color: var(--cost-color); font-weight: bold; margin-left: 10px;">
          {opt.get("total_cost", 0)} pts
        </span>
      </div>
'''
                                if 'special_rules' in opt and opt['special_rules']:
                                    html += f'<div style="font-size: 10px; color: var(--text-muted);">({", ".join(opt["special_rules"])})</div>'
                                html += '''
    </div>
'''

                            # Cas spécial pour les remplacements conditionnels
                            elif "replaces" in opt:
                                html += f'''
    <div class="upgrade-item">
      <div class="upgrade-name">
        {esc(opt.get("name", ""))}
        <span style="color: var(--cost-color); font-weight: bold; margin-left: 10px;">
          +{opt.get("cost", 0)} pts
        </span>
      </div>
'''
                                if 'replaces' in opt and opt['replaces']:
                                    html += f'''
      <div style="font-size: 10px; color: var(--text-muted); margin-top: 2px;">
        Remplace: {", ".join(opt["replaces"])}
      </div>
'''
                                if 'weapon' in opt and isinstance(opt['weapon'], dict):
                                    html += f'''
      <div style="font-size: 10px; color: var(--text-muted); margin-top: 2px;">
        Nouvelle arme: {esc(opt["weapon"].get("name", ""))}
      </div>
'''
                                html += '''
    </div>
'''

                            # Cas spécial pour les améliorations variables
                            elif "count" in opt and "cost_per_unit" in opt:
                                html += f'''
    <div class="upgrade-item">
      <div class="upgrade-name">
        {esc(opt.get("name", ""))} × {opt.get("count", 0)}
        <span style="color: var(--cost-color); font-weight: bold; margin-left: 10px;">
          {opt.get("total_cost", 0)} pts
        </span>
      </div>
'''
                                if 'special_rules' in opt and opt['special_rules']:
                                    html += f'<div style="font-size: 10px; color: var(--text-muted);">({", ".join(opt["special_rules"])})</div>'
                                if 'weapon' in opt and opt['weapon']:
                                    weapon = opt['weapon']
                                    if isinstance(weapon, dict):
                                        html += f'<div style="font-size: 10px; color: var(--text-muted);">Arme: {esc(weapon.get("name", ""))}</div>'
                                html += '''
    </div>
'''

                            # Améliorations normales
                            else:
                                html += f'''
    <div class="upgrade-item">
      <div class="upgrade-name">{esc(opt.get("name", ""))}</div>
'''
                                if 'special_rules' in opt and opt['special_rules']:
                                    html += f'<div style="font-size: 10px; color: var(--text-muted);">({", ".join(opt["special_rules"])})</div>'
                                html += '''
    </div>
'''
            html += '''
  </div>
'''

        # Règles spéciales
        if special_rules:
            html += '''
  <div class="rules-section">
    <div class="rules-title">Règles spéciales:</div>
    <div class="rules-list">
'''
            for rule in special_rules:
                html += f'<span class="rule-tag">{esc(rule)}</span>'
            html += '''
    </div>
  </div>
'''

        # Monture
        if mount:
            mount_data = mount.get("mount", {})
            mount_name = esc(mount.get("name", "Monture"))
            mount_weapons = mount_data.get("weapon", [])

            html += f'''
    <div class="role-section" style="background: rgba(150, 150, 150, 0.1); border: 1px solid rgba(150, 150, 150, 0.3);">
        <div class="role-title">
          <span>🐴</span>
          <span style="color: var(--text-main);">{mount_name}</span>
        </div>
'''

            stats_parts = []
            if 'quality' in mount_data:
                stats_parts.append(f"Qualité {mount_data['quality']}+")
            if 'defense' in mount_data:
                stats_parts.append(f"Défense {mount_data['defense']}+")
            if stats_parts:
                html += f'''
    <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 8px;">
      {', '.join(stats_parts)}
    </div>
'''

            if mount_weapons:
                html += '''
    <div style="margin-top: 8px;">
      <div style="font-weight: 600; margin-bottom: 4px; color: var(--text-main);">Armes:</div>
      <div class="weapon-list">
'''
                for weapon in mount_weapons:
                    if weapon:
                        html += f'''
        <div class="weapon-item">
          <div class="weapon-name">{esc(weapon.get('name', 'Arme'))}</div>
          <div class="weapon-stats">{format_weapon(weapon)}</div>
        </div>
'''
                html += '''
      </div>
    </div>
'''

            html += '''
  </div>
'''

        html += '</div>'

    # Légende des règles spéciales de la faction
    if sorted_army_list and hasattr(st.session_state, 'faction_special_rules') and st.session_state.faction_special_rules:
        faction_rules = st.session_state.faction_special_rules
        all_rules = [rule for rule in faction_rules if isinstance(rule, dict)]

        if all_rules:
            html += '''
<div class="faction-rules">
  <h3 style="text-align: center; color: #3498db; border-top: 1px solid var(--border); padding-top: 10px; margin-bottom: 15px;">
    Légende des règles spéciales de la faction
  </h3>
  <div style="display: flex; flex-wrap: wrap;">
'''

            half = len(all_rules) // 2
            if len(all_rules) % 2 != 0:
                half += 1

            html += '<div style="flex: 1; min-width: 300px; padding-right: 15px;">'
            for rule in sorted(all_rules[:half], key=lambda x: x.get('name', '').lower().replace('é', 'e').replace('è', 'e')):
                if isinstance(rule, dict):
                    html += f'''
    <div style="margin-bottom: 10px;">
      <div style="color: #3498db; font-weight: bold;">{esc(rule.get('name', ''))}:</div>
      <div style="font-size: 14px; color: var(--text-main);">{esc(rule.get('description', ''))}</div>
    </div>
'''
            html += '</div>'

            html += '<div style="flex: 1; min-width: 300px; padding-left: 15px;">'
            for rule in sorted(all_rules[half:], key=lambda x: x.get('name', '').lower().replace('é', 'e').replace('è', 'e')):
                if isinstance(rule, dict):
                    html += f'''
    <div style="margin-bottom: 10px;">
      <div style="color: #3498db; font-weight: bold;">{esc(rule.get('name', ''))}:</div>
      <div style="font-size: 14px; color: var(--text-main);">{esc(rule.get('description', ''))}</div>
    </div>
'''
            html += '</div>'

            html += '''
  </div>
</div>
'''

    # Légende des sorts de la faction
    if sorted_army_list and hasattr(st.session_state, 'faction_spells') and st.session_state.faction_spells:
        spells = st.session_state.faction_spells
        all_spells = [{"name": name, "details": details} for name, details in spells.items() if isinstance(details, dict)]

        if all_spells:
            html += '''
<div class="spells-section">
  <h3 style="text-align: center; color: #3498db; border-top: 1px solid var(--border); padding-top: 10px; margin-bottom: 15px;">
    Légende des sorts de la faction
  </h3>
  <div style="display: flex; flex-wrap: wrap;">
    <div style="flex: 1; min-width: 100%;">
'''
            for spell in sorted(all_spells, key=lambda x: x['name'].lower().replace('é', 'e').replace('è', 'e')):
                if isinstance(spell, dict):
                    html += f'''
      <div style="margin-bottom: 12px; padding: 8px; background: rgba(240, 248, 255, 0.2); border-radius: 4px;">
        <div>
          <span style="color: #3498db; font-weight: bold; font-size: 16px;">{esc(spell.get('name', ''))}</span>
          <span style="color: var(--text-muted); margin-left: 8px;">({spell.get('details', {}).get('cost', '?')} pts)</span>
        </div>
        <div style="font-size: 14px; color: var(--text-main); margin-top: 4px;">{esc(spell.get('details', {}).get('description', ''))}</div>
      </div>
'''
            html += '''
    </div>
  </div>
</div>
'''

    html += '''
<div style="text-align: center; margin-top: 30px; font-size: 12px; color: var(--text-muted);">
  Généré par OPR ArmyBuilder FR - {datetime.now().strftime('%d/%m/%Y %H:%M')}
</div>
</div>
</body>
</html>
'''
    return html

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

                        # Ajout des valeurs par défaut pour upgrade_types si non présent
                        if "upgrade_types" not in data:
                            data["upgrade_types"] = {
                                "unit_improvements": "checkbox",
                                "hero_improvements": "radio",
                                "weapon_upgrades": "radio",
                                "roles": "radio"
                            }

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
# PAGE 1 – CONFIGURATION AVEC IMAGES DE FOND LOCALES (version finale)
# ======================================================
if st.session_state.page == "setup":
    # Définition des images pour chaque jeu + image par défaut
    game_images = {
        "Age of Fantasy": "assets/games/aof_cover.jpg",
        "Age of Fantasy Regiments": "assets/games/aofr_cover.jpg",
        "Grimdark Future": "assets/games/gf_cover.jpg",
        "Grimdark Future Firefight": "assets/games/gff_cover.jpg",
        "Age of Fantasy Skirmish": "assets/games/aofs_cover.jpg",
        "__default__": "https://i.imgur.com/DEFAULT_IMAGE.jpg"  # Image par défaut distante
    }

    # Vérification et sélection de l'image actuelle
    current_game = st.session_state.get("game", "__default__")

    # Détermination de l'URL de l'image avec conversion pour Streamlit
    if current_game in game_images and current_game != "__default__":
        image_path = game_images[current_game]
        try:
            if Path(image_path).exists():
                # Méthode alternative pour les images locales dans Streamlit
                from pathlib import Path
                import base64

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

    # CSS pour l'image de fond avec fondu
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

    # Conteneur avec l'image de fond
    st.markdown('<div class="game-bg"><div class="content">', unsafe_allow_html=True)

    st.markdown("## 🛡️ OPR ArmyBuilder FR")
    st.markdown(
        "<p class='muted'>Construisez, équilibrez et façonnez vos armées pour "
        "Age of Fantasy et Grimdark Future.</p>",
        unsafe_allow_html=True
    )

    st.markdown("</div></div>", unsafe_allow_html=True)
    st.markdown("---")

    # Solution pour le rafraîchissement
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

        # Mise à jour de l'état et rafraîchissement
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
        st.markdown(
            "<p class='muted'>Prêt à forger votre armée ?</p>",
            unsafe_allow_html=True
        )

        can_build = all([game, faction, points > 0, list_name.strip() != ""])

        if st.button(
            "🔥 Construire l'armée",
            use_container_width=True,
            type="primary",
            disabled=not can_build
        ):
            st.session_state.game = game
            st.session_state.faction = faction
            st.session_state.points = points
            st.session_state.list_name = list_name

            # Charger les données de la faction sélectionnée
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
# FONCTIONS UTILITAIRES POUR LA PAGE 2 (corrigées)
# ======================================================
def format_weapon_profile(weapon):
    """Formate le profil complet d'une arme avec portée avant Aa"""
    if not weapon or not isinstance(weapon, dict):
        return "Aucune arme"

    name = weapon.get('name', 'Arme')
    attacks = weapon.get('attacks', '?')
    ap = weapon.get('armor_piercing', '?')
    range_text = weapon.get('range', 'Mêlée')
    special_rules = weapon.get('special_rules', [])

    profile = f"{range_text} A{attacks}/PA{ap}"
    if special_rules:
        profile += f" ({', '.join(special_rules)})"

    return f"{name} {profile}"

def format_weapon_option(weapon, cost=0):
    """Formate l'option d'arme pour la sélection"""
    if not weapon or not isinstance(weapon, dict):
        return "Aucune arme"

    profile = format_weapon_profile(weapon)
    if cost > 0:
        profile += f" (+{cost} pts)"

    return profile

def format_mount_option(mount):
    """Formate l'option de monture avec les noms réels des armes"""
    if not mount or not isinstance(mount, dict):
        return "Aucune monture"

    name = mount.get('name', 'Monture')
    cost = mount.get('cost', 0)
    mount_data = mount.get('mount', {})
    weapons = mount_data.get('weapon', [])
    special_rules = mount_data.get('special_rules', [])
    coriace = mount_data.get('coriace_bonus', 0)

    stats = []

    # 1. Armes avec leurs noms réels
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
        stats.extend(weapon_profiles)  # On utilise extend pour ajouter chaque arme séparément

    # 2. Coriace si présent
    if coriace > 0:
        stats.append(f"Coriace+{coriace}")

    # 3. Règles spéciales
    if special_rules:
        rules_text = ", ".join([r for r in special_rules if not r.startswith(("Griffes", "Sabots"))])
        if rules_text:
            stats.append(rules_text)

    label = f"{name}"
    if stats:
        label += f" ({', '.join(stats)})"
    label += f" (+{cost} pts)"

    return label

def format_unit_option(u):
    """Formate l'option d'unité avec tous les détails"""
    name_part = f"{u['name']}"
    if u.get('type') == "hero":
        name_part += " [1]"
    else:
        name_part += f" [{u.get('size', 10)}]"

    # Récupération des armes de base
    weapons = u.get('weapon', [])
    weapon_profiles = []
    if isinstance(weapons, list):
        for weapon in weapons:
            if isinstance(weapon, dict):
                profile = format_weapon_profile(weapon)
                weapon_profiles.append(profile)
    elif isinstance(weapons, dict):
        profile = format_weapon_profile(weapons)
        weapon_profiles.append(profile)

    weapon_text = ", ".join(weapon_profiles) if weapon_profiles else "Aucune"

    # Récupération des règles spéciales
    special_rules = u.get('special_rules', [])
    rules_text = []
    if isinstance(special_rules, list):
        for rule in special_rules:
            if isinstance(rule, str):
                if not rule.startswith(("Griffes", "Sabots")) and "Coriace" not in rule:
                    rules_text.append(rule)
            elif isinstance(rule, dict):
                rules_text.append(rule.get('name', ''))

    rules_text = ", ".join(rules_text) if rules_text else "Aucune"

    qua_def = f"Déf {u.get('defense', '?')}+"
    cost = f"{u.get('base_cost', 0)}pts"

    return f"{name_part} | {qua_def} | {weapon_text} | {rules_text} | {cost}"

# ======================================================
# PAGE 2 – CONSTRUCTEUR D'ARMÉE (version complète avec filtres)
# ======================================================
if st.session_state.page == "army":
    # Vérification renforcée des données requises
    required_keys = ["game", "faction", "points", "list_name", "units", "faction_special_rules", "faction_spells"]
    if not all(key in st.session_state for key in required_keys):
        st.error("Configuration incomplète. Veuillez retourner à la page de configuration.")
        if st.button("Retour à la configuration"):
            st.session_state.page = "setup"
            st.rerun()
        st.stop()

    # Vérification que les unités sont bien chargées
    if not st.session_state.units:
        st.error("Aucune unité disponible pour cette faction. Veuillez choisir une autre faction.")
        if st.button("Retour à la configuration"):
            st.session_state.page = "setup"
            st.rerun()
        st.stop()

    st.session_state.setdefault("list_name", "Nouvelle Armée")
    st.session_state.setdefault("army_cost", 0)
    st.session_state.setdefault("army_list", [])
    st.session_state.setdefault("unit_selections", {})
    st.session_state.setdefault("unit_filter", "Tous")  # Filtre par défaut

    st.title(f"{st.session_state.list_name} - {st.session_state.army_cost}/{st.session_state.points} pts")

    if st.button("⬅️ Retour à la configuration"):
        st.session_state.page = "setup"
        st.rerun()

    st.divider()
    st.subheader("📤 Export/Import de la liste")

    # Section pour les boutons d'export/import
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
            use_container_width=True
        )

    with colE2:
        html_data = export_html(st.session_state.army_list, st.session_state.list_name, st.session_state.points)
        st.download_button(
            "🌐 Export HTML",
            data=html_data,
            file_name=f"{st.session_state.list_name}.html",
            mime="text/html",
            use_container_width=True
        )

    with colE3:
        uploaded_file = st.file_uploader(
            "📥 Importer une liste d'armée",
            type=["json"],
            label_visibility="collapsed",
            accept_multiple_files=False
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

    # Affichage des points
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

    # Progression de l'armée
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

    # Règles spéciales et sorts
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

    # Liste de l'armée
    st.subheader("Liste de l'Armée")
    if not st.session_state.army_list:
        st.markdown("Aucune unité ajoutée pour le moment.")
    else:
        for i, unit_data in enumerate(st.session_state.army_list):
            with st.expander(f"{unit_data['name']} - {unit_data['cost']} pts", expanded=False):
                st.markdown(f"**Type :** {unit_data['type']}")
                st.markdown(f"**Taille :** {unit_data.get('size', '?')}")
                st.markdown(f"**Qualité :** {unit_data.get('quality', '?')}+")
                st.markdown(f"**Défense :** {unit_data.get('defense', '?')}+")

                if "coriace" in unit_data:
                    st.markdown(f"**Coriace :** {unit_data.get('coriace', '?')}")

                if st.button(f"Supprimer {unit_data['name']}", key=f"delete_{i}"):
                    st.session_state.army_cost -= unit_data['cost']
                    st.session_state.army_list.pop(i)
                    st.rerun()

    st.divider()

    # CSS pour les boutons de filtre avec mise en évidence simple
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

        /* Style pour le filtre actif - simple et efficace */
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

    # Système de filtres par catégorie
    st.markdown("<div class='filter-container'>", unsafe_allow_html=True)
    st.subheader("Filtres par type d'unité")

    # Définir les catégories et leurs types associés
    filter_categories = {
        "Tous": None,
        "Héros": ["hero"],
        "Héros nommés": ["named_hero"],
        "Unités de base": ["unit"],
        "Véhicules légers / Petits monstres": ["light_vehicle"],
        "Véhicules / Monstres": ["vehicle"],
        "Titans": ["titan"]
    }

    # Créer les boutons de filtre
    for category in filter_categories.keys():
        # Créer un bouton Streamlit normal
        btn = st.button(
            category,
            key=f"filter_{category}",
            use_container_width=True
        )

        # Si le bouton est cliqué, mettre à jour le filtre
        if btn:
            st.session_state.unit_filter = category
            st.rerun()

    # Appliquer le style actif après les boutons
    st.markdown(
        f"""
        <script>
        // Appliquer le style actif au bouton correspondant
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

    # Filtrer les unités selon le filtre sélectionné
    filtered_units = []
    if st.session_state.unit_filter == "Tous":
        filtered_units = st.session_state.units
    else:
        relevant_types = filter_categories[st.session_state.unit_filter]
        filtered_units = [
            unit for unit in st.session_state.units
            if unit.get('unit_detail') in relevant_types
        ]

    # Afficher le nombre d'unités disponibles
    st.markdown(f"""
    <div style='text-align: center; margin: 10px 0; color: #6c757d; font-size: 0.9em;'>
        {len(filtered_units)} unités disponibles (filtre: {st.session_state.unit_filter})
    </div>
    """, unsafe_allow_html=True)

    # Sélection de l'unité
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

    # Suite du code existant pour les améliorations
    unit_key = f"unit_{unit['name']}"
    st.session_state.unit_selections.setdefault(unit_key, {})

    weapons = list(unit.get("weapon", []))
    selected_options = {}
    mount = None
    weapon_cost = 0
    mount_cost = 0
    upgrades_cost = 0
    weapon_upgrades = []

    # Configuration des améliorations
    for g_idx, group in enumerate(unit.get("upgrade_groups", [])):
        g_key = f"group_{g_idx}"
        st.subheader(group.get("group", "Améliorations"))

        # ARMES (existantes)
        if group.get("type") == "weapon":
            choices = []
            base_weapons = unit.get("weapon", [])
        
            # Ajouter les armes de base comme première option
            if isinstance(base_weapons, list) and base_weapons:
                # Créer un label pour les armes de base
                base_weapons_labels = []
                for weapon in base_weapons:
                    base_weapons_labels.append(weapon.get('name', 'Arme'))
        
                if len(base_weapons_labels) == 1:
                    choices.append(format_weapon_option(base_weapons[0]))
                else:
                    choices.append(" et ".join(base_weapons_labels))
            elif isinstance(base_weapons, dict):
                choices.append(format_weapon_option(base_weapons))
        
            # Ajouter les options de remplacement
            opt_map = {}
            for o in group.get("options", []):
                weapon = o.get("weapon", {})
                if isinstance(weapon, list):
                    # Cas spécial pour les armes combinées
                    weapon_names = [w.get('name', 'Arme') for w in weapon]
                    label = " et ".join(weapon_names) + f" (+{o['cost']} pts)"
                else:
                    label = format_weapon_option(weapon, o['cost'])
                choices.append(label)
                opt_map[label] = o
        
            # Si on a des choix à afficher
            if choices:
                current = st.session_state.unit_selections[unit_key].get(g_key, choices[0] if choices else "Aucune arme")
                choice = st.radio(
                    "Sélection de l'arme",
                    choices,
                    index=choices.index(current) if current in choices else 0,
                    key=f"{unit_key}_{g_key}_weapon",
                )
        
                st.session_state.unit_selections[unit_key][g_key] = choice
        
                # Gérer le choix de l'utilisateur
                if choice != choices[0]:
                    for opt_label, opt in opt_map.items():
                        if opt_label == choice:
                            weapon_cost += opt["cost"]
        
                            # Si c'est une arme simple
                            if not isinstance(opt["weapon"], list):
                                weapons = [opt["weapon"]]
                            # Si c'est une arme combinée
                            else:
                                weapons = opt["weapon"]
        
                            # Vérifier si on doit remplacer une arme spécifique
                            if "replaces" in opt:
                                # Filtrer les armes de base pour enlever celles à remplacer
                                weapons = [
                                    w for w in base_weapons
                                    if w.get('name') not in opt["replaces"]
                                ] + weapons
                            break

        # RÔLES - MODIFICATION MINIMALE POUR L'AFFICHAGE EN COLONNE DES TITANS
        elif group.get("type") == "role":
            choices = []
            opt_map = {}
        
            # Pour les titans, on n'affiche pas "Aucun rôle" et on prend le premier rôle par défaut
            if unit.get("unit_detail") == "titan":
                # On commence directement avec les options disponibles
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
        
                # Sélection par défaut : premier rôle (index 0)
                default_choice = choices[0] if choices else ""
                current = st.session_state.unit_selections[unit_key].get(g_key, default_choice)
        
                # Affichage en colonne (sans horizontal=True)
                choice = st.radio(
                    group.get("group", "Rôle"),
                    choices,
                    index=choices.index(current) if current in choices else 0,
                    key=f"{unit_key}_{g_key}_role"
                    # Pas de horizontal=True pour afficher en colonne
                )
        
            # Pour les héros normaux, on garde le comportement classique
            else:
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
        
            # Le reste de la logique reste identique pour les deux cas
            for opt_label, opt in opt_map.items():
                if opt_label == choice:
                    upgrades_cost += opt.get("cost", 0)
                    selected_options[group.get("group", "Rôle")] = [opt]
        
                    # Ajouter les armes du rôle à la liste des armes principales
                    if "weapon" in opt:
                        role_weapons = opt.get("weapon", [])
                        if isinstance(role_weapons, list):
                            weapons.extend(role_weapons)
                        elif isinstance(role_weapons, dict):
                            weapons.append(role_weapons)
                    break      
        
        # AMÉLIORATIONS D'ARME - SECTION CORRIGÉE
        elif group.get("type") == "weapon_upgrades":
            choices = ["Aucune amélioration d'arme"]
            opt_map = {}
        
            for o in group.get("options", []):
                weapon = o.get("weapon", {})
                if isinstance(weapon, dict):
                    # Formatage complet avec toutes les caractéristiques
                    name = weapon.get('name', 'Arme')
                    attacks = weapon.get('attacks', '?')
                    ap = weapon.get('armor_piercing', '?')
                    range_text = weapon.get('range', 'Mêlée')
                    special_rules = weapon.get('special_rules', [])
        
                    # Construction du label avec toutes les infos
                    profile = f"{name} ({range_text}, A{attacks}"
                    if ap not in ("-", 0, "0", None):
                        profile += f"/PA{ap}"
                    profile += ")"
        
                    if special_rules:
                        profile += f" [{', '.join(special_rules)}]"
        
                    label = f"{profile} (+{o['cost']} pts)"
                else:
                    label = f"{o['name']} (+{o['cost']} pts)"
        
                choices.append(label)
                opt_map[label] = o
        
            current = st.session_state.unit_selections[unit_key].get(g_key, choices[0])
            choice = st.radio(
                "Amélioration d'arme",
                choices,
                index=choices.index(current) if current in choices else 0,
                key=f"{unit_key}_{g_key}_weapon_upgrade",
            )
        
            st.session_state.unit_selections[unit_key][g_key] = choice
        
            if choice != "Aucune amélioration d'arme":
                opt = opt_map[choice]
                upgrades_cost += opt["cost"]
        
                # Ajouter l'arme d'amélioration à la liste des armes principales
                if "weapon" in opt:
                    weapon_upgrades.append(opt["weapon"])
                    # Ajouter aussi à la liste des armes principales pour l'affichage
                    if isinstance(opt["weapon"], dict):
                        weapons.append(opt["weapon"])
                    elif isinstance(opt["weapon"], list):
                        weapons.extend(opt["weapon"])

        # AMÉLIORATIONS PAR FIGURINE (weapon_count - version améliorée)
        elif group.get("type") == "weapon_count":
            st.subheader(group.get("group", "Améliorations par figurine"))

            # Récupérer la taille de l'unité
            unit_size = unit.get("size", 10)
            if unit.get("type") == "hero":
                unit_size = 1

            # Préparer les options
            choices = ["Aucune amélioration"]
            opt_map = {}

            for o in group.get("options", []):
                weapon = o.get("weapon", {})
                cost = o.get("cost", 0)
                label = f"{o['name']} (+{cost} pts/figurine, total: {cost * unit_size} pts)"
                choices.append(label)
                opt_map[label] = o

            # Sélection de l'amélioration
            current = st.session_state.unit_selections[unit_key].get(g_key, choices[0])
            choice = st.radio(
                "Amélioration par figurine",
                choices,
                index=choices.index(current) if current in choices else 0,
                key=f"{unit_key}_{g_key}_weapon_count"
            )

            st.session_state.unit_selections[unit_key][g_key] = choice

            # Si une amélioration est sélectionnée
            if choice != choices[0]:
                for opt_label, opt in opt_map.items():
                    if opt_label == choice:
                        # Calcul du coût total
                        total_cost = opt["cost"] * unit_size
                        upgrades_cost += total_cost

                        # Ajouter un compteur visible
                        st.markdown(f"""
                        <div style='margin: 10px 0; padding: 8px; background: #f8f9fa; border-radius: 4px;'>
                            <strong>{opt['name']}</strong> × {unit_size} figurines =
                            <strong style='color: #e74c3c;'>{total_cost} pts</strong>
                        </div>
                        """, unsafe_allow_html=True)

                        # Ajouter l'arme à la liste des armes
                        if "weapon" in opt:
                            if isinstance(opt["weapon"], dict):
                                weapons.append(opt["weapon"])
                            elif isinstance(opt["weapon"], list):
                                weapons.extend(opt["weapon"])

                        # Stocker l'information pour l'export
                        selected_options[group.get("group", "Améliorations")] = [
                            {
                                "name": opt["name"],
                                "cost": opt["cost"],
                                "total_cost": total_cost,
                                "count": unit_size,
                                "weapon": opt.get("weapon")
                            }
                        ]
                        break

        # REMPLACEMENT D'ARME CONDITIONNEL (nouveau)
        elif group.get("type") == "conditional_weapon":
            st.subheader(group.get("group", "Remplacement d'arme conditionnel"))

            # Récupérer les armes de base de l'unité
            base_weapons = unit.get("weapon", [])
            if not isinstance(base_weapons, list):
                base_weapons = [base_weapons]

            # Créer une liste des noms d'armes de base pour l'affichage
            weapon_names = [w.get('name', 'Arme') for w in base_weapons if isinstance(w, dict)]

            # Préparer les options disponibles en fonction des armes actuelles
            choices = ["Aucun remplacement"]
            opt_map = {}
            available_options = []

            # Filtrer les options en fonction des armes disponibles
            for o in group.get("options", []):
                replaces = o.get("replaces", [])
                weapon = o.get("weapon", {})

                # Si l'option ne remplace rien (ajout pur) ou remplace une arme disponible
                if not replaces or any(weapon_name in replaces for weapon_name in weapon_names):
                    label = f"{o['name']} (+{o['cost']} pts)"

                    # Ajouter des détails sur ce qui est remplacé
                    if replaces:
                        label += f" (remplace: {', '.join(replaces)})"
                    else:
                        label += " (ajout)"

                    choices.append(label)
                    opt_map[label] = o
                    available_options.append(o)

            # Si aucune option n'est disponible
            if len(choices) == 1:
                st.warning("Aucun remplacement d'arme disponible avec les armes actuelles")
            else:
                current = st.session_state.unit_selections[unit_key].get(g_key, choices[0])
                choice = st.radio(
                    "Choix de remplacement",
                    choices,
                    index=choices.index(current) if current in choices else 0,
                    key=f"{unit_key}_{g_key}_conditional_weapon"
                )

                st.session_state.unit_selections[unit_key][g_key] = choice

                # Si un remplacement est sélectionné
                if choice != choices[0]:
                    selected_option = opt_map[choice]
                    upgrades_cost += selected_option["cost"]

                    # Récupérer les armes actuelles
                    current_weapons = weapons.copy()

                    # Appliquer le remplacement
                    if "replaces" in selected_option:
                        # Retirer les armes à remplacer
                        replaces = selected_option["replaces"]
                        current_weapons = [w for w in current_weapons
                                        if w.get('name') not in replaces]

                    # Ajouter la nouvelle arme
                    if "weapon" in selected_option:
                        new_weapon = selected_option["weapon"]
                        if isinstance(new_weapon, dict):
                            current_weapons.append(new_weapon)
                        elif isinstance(new_weapon, list):
                            current_weapons.extend(new_weapon)

                    # Mettre à jour la liste des armes
                    weapons[:] = current_weapons

                    # Stocker l'information pour l'export
                    selected_options[group.get("group", "Remplacements")] = [selected_option]

        # AMÉLIORATIONS VARIABLES (variable_weapon_count - nouveau)
        elif group.get("type") == "variable_weapon_count":
            st.subheader(group.get("group", "Améliorations variables"))

            # Récupérer les améliorations sélectionnées précédemment
            current_selection = st.session_state.unit_selections[unit_key].get(g_key, {})

            # Pour chaque option d'amélioration
            for opt_idx, option in enumerate(group.get("options", [])):
                st.subheader(f"Option: {option['name']}", divider="gray50")

                # Calculer les options de compteur disponibles
                choices, max_count = format_count_options(option, unit,
                                                          current_selection.get(str(opt_idx), 0))

                # Créer un slider pour sélectionner le nombre
                if choices:
                    labels = [c["label"] for c in choices]
                    current_value = current_selection.get(str(opt_idx), 0)

                    # Trouver l'index du choix actuel
                    try:
                        current_index = next(i for i, c in enumerate(choices)
                                           if c["count"] == current_value)
                    except StopIteration:
                        current_index = 0

                    # Sélecteur du nombre d'améliorations
                    selected = st.select_slider(
                        f"Nombre de {option['name']} (max: {max_count})",
                        options=labels,
                        value=labels[current_index],
                        key=f"{unit_key}_{g_key}_{opt_idx}"
                    )

                    # Mettre à jour la sélection
                    selected_choice = next(c for c in choices if c["label"] == selected)
                    current_selection[str(opt_idx)] = selected_choice["count"]

                    # Mettre à jour le coût total
                    upgrades_cost += selected_choice["cost"]

                    # Stocker les informations pour l'export
                    if selected_choice["count"] > 0:
                        if group.get("group", "Améliorations") not in selected_options:
                            selected_options[group.get("group", "Améliorations")] = []

                        selected_options[group.get("group", "Améliorations")].append({
                            "name": option["name"],
                            "count": selected_choice["count"],
                            "cost_per_unit": option.get("cost_per_unit", option.get("cost", 0)),
                            "total_cost": selected_choice["cost"],
                            "weapon": option.get("weapon"),
                            "special_rules": option.get("special_rules", [])
                        })

            # Mettre à jour les sélections
            st.session_state.unit_selections[unit_key][g_key] = current_selection

            # Afficher un résumé des améliorations sélectionnées
            if current_selection:
                total_items = sum(current_selection.values())
                total_cost = sum(c["cost"] for c in choices
                                if c["count"] == current_selection.get(str(choices.index(c)), 0))

                st.markdown(f"""
                <div style='margin: 10px 0; padding: 8px; background: #f0f8ff; border-radius: 4px;'>
                    <strong>Total:</strong> {total_items} amélioration(s) pour
                    <strong style='color: #e74c3c;'>{total_cost} pts</strong>
                </div>
                """, unsafe_allow_html=True)
        
        # MONTURE
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

        # OPTIONS NORMALES
        else:
            for o in group.get("options", []):
                opt_key = f"{unit_key}_{g_key}_{o['name']}"
                checked = st.checkbox(
                    f"{o['name']} (+{o['cost']} pts)",
                    value=st.session_state.unit_selections[unit_key].get(opt_key, False),
                    key=opt_key,
                )
                st.session_state.unit_selections[unit_key][opt_key] = checked
                if checked:
                    upgrades_cost += o["cost"]
                    selected_options.setdefault(group.get("group", "Options"), []).append(o)

    # Option unité combinée
    multiplier = 1
    if unit.get("type") != "hero" and unit.get("size", 1) > 1:
        if st.checkbox("Unité combinée"):
            multiplier = 2

    base_cost = unit.get("base_cost", 0)
    final_cost = (base_cost + weapon_cost + upgrades_cost) * multiplier + mount_cost

    st.subheader("Coût de l'unité sélectionnée")
    st.markdown(f"**Coût total :** {final_cost} pts")
    st.divider()

    # BOUTON D'AJOUT D'UNITÉ (modifié pour gérer les nouveaux types)
    if st.button("➕ Ajouter à l'armée"):
        if st.session_state.army_cost + final_cost > st.session_state.points:
            st.error(f"⛔ Dépassement du format : {st.session_state.army_cost + final_cost} / {st.session_state.points} pts")
            st.stop()

        # Calcul de la Coriace
        coriace_total = unit.get("coriace", 0)
        if mount and "mount" in mount:
            coriace_total += mount["mount"].get("coriace_bonus", 0)

        # Préparation des règles spéciales
        all_special_rules = unit.get("special_rules", []).copy()

        # Règles spéciales des améliorations
        for group in unit.get("upgrade_groups", []):
            group_key = f"group_{unit.get('upgrade_groups', []).index(group)}"
            selection = st.session_state.unit_selections[unit_key].get(group_key)

            if selection:
                # Gestion des améliorations variables
                if isinstance(selection, dict):
                    for opt_idx, count in selection.items():
                        if count > 0:
                            opt = group.get("options", [])[int(opt_idx)]
                            if "special_rules" in opt:
                                all_special_rules.extend(opt["special_rules"] * count)

                            # Ajouter les armes si elles existent
                            if "weapon" in opt and opt["weapon"]:
                                weapon = opt["weapon"]
                                if isinstance(weapon, dict):
                                    for _ in range(count):
                                        weapons.append(weapon.copy())
                                elif isinstance(weapon, list):
                                    for w in weapon:
                                        for _ in range(count):
                                            weapons.append(w.copy())

                # Gestion des autres types d'améliorations
                elif isinstance(selection, str) and selection != choices[0]:
                    for opt in group.get("options", []):
                        if f"{format_weapon_option(opt.get('weapon', {}))} (+{opt['cost']} pts)" == selection:
                            if "special_rules" in opt:
                                all_special_rules.extend(opt["special_rules"])
                            break

        # Règles spéciales de la monture
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
            "weapon": weapons,
            "weapon_upgrades": weapon_upgrades,
            "options": selected_options,
            "mount": mount,
            "special_rules": all_special_rules,
            "coriace": coriace_total
        }

        # Ajout d'une mention pour la monture si elle apporte de la Coriace
        if mount and "coriace_bonus" in mount.get("mount", {}):
            mount_name = mount.get("name", "Monture")
            mount_bonus = mount.get("mount", {}).get("coriace_bonus", 0)
            if mount_bonus > 0:
                unit_data["special_rules"].append(f"{mount_name} (Coriace +{mount_bonus})")

        if validate_army_rules(st.session_state.army_list + [unit_data], st.session_state.points, st.session_state.game):
            st.session_state.army_list.append(unit_data)
            st.session_state.army_cost += final_cost
            st.rerun()
