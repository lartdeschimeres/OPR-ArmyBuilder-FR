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
# CSS - MODIFIÉ POUR CORRESPONDRE AU STYLE QUE VOUS AIMEZ
# ======================================================
st.markdown(
    """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {background: transparent;}

    .stApp {
        background: #f5f5f5;
        color: #333333;
    }

    section[data-testid="stSidebar"] {
        background: #e9ecef;
        border-right: 1px solid #dee2e6;
    }

    h1, h2, h3 {
        color: #2c3e50;
        letter-spacing: 0.04em;
    }

    .card {
        background: #ffffff;
        border: 2px solid #3498db;
        border-radius: 8px;
        padding: 1.2rem;
        transition: all 0.2s ease;
        cursor: pointer;
        box-shadow: 0 0 10px rgba(52, 152, 219, 0.2);
    }

    .card:hover {
        border-color: #2980b9;
        box-shadow: 0 0 20px rgba(52, 152, 219, 0.4);
        transform: translateY(-2px);
    }

    .badge {
        display: inline-block;
        padding: 0.25rem 0.6rem;
        border-radius: 4px;
        background: #3498db;
        color: white;
        font-size: 0.75rem;
        margin-bottom: 0.5rem;
        font-weight: bold;
    }

    button[kind="primary"] {
        background: linear-gradient(135deg, #3498db, #2980b9) !important;
        color: white !important;
        font-weight: bold;
        border-radius: 6px;
        padding: 0.6rem 1rem;
        border: none;
    }

    .rule-item, .spell-item {
        font-size: 14px;
        margin-bottom: 5px;
        display: flex;
        align-items: center;
    }
    .rule-name, .spell-name {
        font-weight: bold;
        color: #bb86fc;
        margin-right: 10px;
    }
    .rule-description, .spell-description {
        color: #ccc;
    }

    /* NOUVEAUX STYLES POUR L'EXPORT HTML */
    .stat-badge {
        background: #6e7f6a;
        color: #000;
        padding: 5px 10px;
        border-radius: 4px;
        font-weight: bold;
        font-size: 12px;
        margin-right: 8px;
        margin-bottom: 8px;
        display: inline-block;
    }

    .tough-badge {
        background: #f87171;
        color: #000;
        padding: 5px 10px;
        border-radius: 4px;
        font-weight: bold;
        font-size: 12px;
        margin-right: 8px;
        margin-bottom: 8px;
        display: inline-block;
    }

    .rule-tag {
        background: #4b4d46;
        color: #e5e7eb;
        padding: 3px 6px;
        border-radius: 3px;
        font-size: 11px;
        margin-right: 5px;
        margin-bottom: 5px;
        display: inline-block;
    }

    .weapon-table {
        width: 100%;
        border-collapse: collapse;
        margin: 10px 0;
        font-size: 12px;
    }

    .weapon-table th, .weapon-table td {
        border: 1px solid #4b4d46;
        padding: 6px;
        text-align: left;
    }

    .weapon-table th {
        background: #1f201d;
        color: #e5e7eb;
    }

    .stats-grid {
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 8px;
        background: #2e2f2b;
        padding: 12px;
        border-radius: 6px;
        text-align: center;
        font-size: 12px;
        margin-bottom: 15px;
    }

    .stat-item {
        padding: 5px;
    }

    .stat-label {
        color: #9ca3af;
        font-size: 10px;
        text-transform: uppercase;
        margin-bottom: 3px;
    }

    .stat-value {
        font-weight: bold;
        font-size: 16px;
        color: #e5e7eb;
    }

    .tough-value {
        color: #f87171 !important;
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
        return str(txt).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def format_weapon(weapon):
        """Formate une arme pour l'affichage"""
        if not weapon:
            return "Arme non spécifiée"

        range_text = weapon.get('range', '-')
        if range_text == "-" or range_text is None:
            range_text = "Mêlée"

        attacks = weapon.get('attacks', '-')
        ap = weapon.get('armor_piercing', '-')
        special = ", ".join(weapon.get('special_rules', [])) if weapon.get('special_rules') else ""

        result = f"{range_text} | A{attacks}"

        if ap not in ("-", 0, "0", None):
            result += f" | PA({ap})"

        if special:
            result += f" | {special}"

        return result

    def get_special_rules(unit):
        """Extraire et formater les règles spéciales"""
        rules = []

        # Règles spéciales de base
        if "special_rules" in unit:
            for rule in unit["special_rules"]:
                if isinstance(rule, dict):
                    rules.append(f'{rule.get("name", "")}')
                elif isinstance(rule, str):
                    # Exclure les règles de Coriace qui sont déjà affichées dans les stats
                    if "Coriace" not in rule or "Monture" in rule:
                        rules.append(rule)

        # Règles spéciales des améliorations
        if "options" in unit:
            for group_name, opts in unit["options"].items():
                if isinstance(opts, list):
                    for opt in opts:
                        if "special_rules" in opt:
                            rules.extend(opt["special_rules"])

        # Règles spéciales de la monture (sans la Coriace qui est déjà comptée)
        if "mount" in unit and unit["mount"]:
            mount_data = unit["mount"].get("mount", {})
            if "special_rules" in mount_data:
                for rule in mount_data["special_rules"]:
                    if not rule.startswith(("Griffes", "Sabots")) and "Coriace" not in rule:
                        rules.append(rule)

        return list(set(rules))  # Supprimer les doublons

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
  --bg-dark: #f8f9fa;          /* Fond clair pour PDF */
  --bg-card: #ffffff;          /* Cartes blanches */
  --bg-header: #e9ecef;        /* En-têtes clairs */
  --accent: #3498db;           /* Bleu plus foncé */
  --accent-dark: #2980b9;
  --text-main: #212529;        /* Noir pour meilleur contraste */
  --text-muted: #6c757d;       /* Gris plus foncé */
  --border: #dee2e6;           /* Bordures claires */
  --cost-color: #ff6b6b;       /* Rouge pour les coûts */
  --tough-color: #e74c3c;
  --hero-color: #f39c12;
  --unit-color: #3498db;
  --highlight: #8e44ad;
}}

@media screen {{
  body {{
    background: var(--bg-dark);
    color: var(--text-main);
    font-family: 'Inter', sans-serif;
    margin: 0;
    padding: 20px;
    line-height: 1.5;
  }}
}}

@media print {{
  body {{
    background: white !important;
    color: black !important;
    font-family: 'Inter', Arial, sans-serif;
    margin: 0;
    padding: 20px;
    line-height: 1.6;
    font-size: 12pt;  /* Taille de police augmentée pour PDF */
  }}

  .unit-card, .army-summary {{
    background: white !important;
    border: 1px solid #ccc !important;
    page-break-inside: avoid;
    box-shadow: none !important;
  }}

  .stat-value {{
    font-size: 14pt !important;  /* Taille augmentée pour les stats */
    font-weight: bold !important;
  }}

  .rule-tag {{
    background: #f0f0f0 !important;
    color: black !important;
    border: 1px solid #ddd !important;
    padding: 4px 8px !important;
    margin: 2px !important;
  }}

  .weapon-stats {{
    font-size: 11pt !important;
  }}

  .rule-name, .spell-name {{
    color: #2c3e50 !important;
    font-weight: bold !important;
  }}

  h3, .unit-name {{
    color: #2c3e50 !important;
    font-size: 14pt !important;
  }}

  .section-title {{
    font-size: 12pt !important;
    font-weight: bold !important;
    margin: 12px 0 6px 0 !important;
  }}
}}

.army {{
  max-width: 800px;
  margin: 0 auto;
}}

.army-title {{
  text-align: center;
  font-size: 18pt;  /* Taille augmentée */
  font-weight: 700;
  margin-bottom: 15px;
  color: var(--accent);
  border-bottom: 2px solid var(--border);
  padding-bottom: 8px;
}}

.unit-card {{
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 8px;
  margin-bottom: 20px;
  padding: 16px;
  position: relative;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}}

.unit-header {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}}

.unit-name {{
  font-size: 16pt;  /* Taille augmentée */
  font-weight: 600;
  color: var(--text-main);
  margin: 0;
}}

.unit-cost {{
  font-family: monospace;
  font-size: 16pt;  /* Taille augmentée */
  font-weight: bold;
  color: var(--cost-color);
}}

.stats-grid {{
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 8px;
  background: var(--bg-header);
  padding: 12px;
  border-radius: 6px;
  text-align: center;
  font-size: 11pt;  /* Taille augmentée */
  margin: 12px 0;
}}

.stat-value {{
  font-weight: bold;
  font-size: 14pt;  /* Taille augmentée */
  color: var(--text-main);
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
  font-weight: 600;
  color: var(--text-main);
  font-size: 11pt;  /* Taille légèrement augmentée */
}}

.rule-tag {{
  background: var(--bg-header);
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 10pt;  /* Taille légèrement augmentée */
  color: var(--text-main);
  margin: 2px;
  display: inline-block;
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

.summary-cost {{
  font-family: monospace;
  font-size: 18pt;  /* Taille augmentée */
  font-weight: bold;
  color: var(--cost-color);
}}

.faction-rules, .spells-section {{
  margin: 30px 0;
  border-top: 2px solid var(--border);
  padding-top: 15px;
}}

.rule-item, .spell-item {{
  margin-bottom: 12px;
  font-size: 11pt;  /* Taille augmentée */
  line-height: 1.5;
}}

.rule-name, .spell-name {{
  font-weight: bold;
  color: var(--accent);
  display: block;  /* Pour une meilleure mise en page */
  margin-bottom: 2px;
}}

.rule-description, .spell-description {{
  color: var(--text-main);
  display: block;
  margin-bottom: 8px;
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
        name = esc(unit.get("name", "Unité"))
        cost = unit.get("cost", 0)
        quality = esc(unit.get("quality", "-"))
        defense = esc(unit.get("defense", "-"))
        unit_type = unit.get("type", "unit")
        unit_size = unit.get("size", 10)

        if unit_type.lower() == "hero":
            unit_size = 1

        # Calcul de la valeur de Coriace
        tough_value = unit.get("coriace", 0)

        # Récupération des armes
        base_weapons = unit.get("weapon", [])
        if not isinstance(base_weapons, list):
            base_weapons = [base_weapons]

        # Récupération des améliorations
        weapon_upgrades = unit.get("weapon_upgrades", [])
        options = unit.get("options", {})
        mount = unit.get("mount", None)

        # Récupération des règles spéciales
        special_rules = get_special_rules(unit)

        html += f'''
<div class="unit-card">
  <div class="unit-header">
    <div>
      <h3 class="unit-name">
        {name}
        <span style="font-size: 12px; color: var(--text-muted); margin-left: 8px;">[{unit_size}]</span>
      </h3>
      <div class="unit-type">
        {"⭐" if unit_type == "hero" else "🛡️"} {unit_type}
        {" | Taille: " + str(unit_size) if unit_type != "hero" else ""}
      </div>
    </div>
    <div class="unit-cost">{cost} pts</div>
  </div>

  <div class="stats-grid">
    <div class="stat-item">
      <div class="stat-label">Qualité</div>
      <div class="stat-value">{quality}+</div>
    </div>
    <div class="stat-item">
      <div class="stat-label">Défense</div>
      <div class="stat-value">{defense}+</div>
    </div>
'''

        # Affichage de la Coriace
        if tough_value > 0:
            html += f'''
    <div class="stat-item">
      <div class="stat-label">Coriace</div>
      <div class="stat-value tough-value">{tough_value}</div>
    </div>
'''

        html += f'''
    <div class="stat-item">
      <div class="stat-label">Coût Base</div>
      <div class="stat-value">{cost} pts</div>
    </div>
    <div class="stat-item">
      <div class="stat-label">Taille</div>
      <div class="stat-value">{unit_size}</div>
    </div>
  </div>
'''

        # Armes de base
        if base_weapons:
            html += '''
  <div class="section-title">Armes:</div>
  <div class="weapon-list">
'''
            for weapon in base_weapons:
                if weapon:
                    html += f'''
    <div class="weapon-item">
      <div class="weapon-name">{esc(weapon.get('name', 'Arme'))}</div>
      <div class="weapon-stats">{format_weapon(weapon)}</div>
    </div>
'''
            html += '''
  </div>
'''

        # Améliorations d'arme
        if weapon_upgrades:
            html += '''
  <div class="section-title">Améliorations d'arme:</div>
  <div class="weapon-list">
'''
            for weapon in weapon_upgrades:
                if weapon:
                    html += f'''
    <div class="weapon-item">
      <div class="weapon-name">{esc(weapon.get('name', 'Amélioration'))}</div>
      <div class="weapon-stats">{format_weapon(weapon)}</div>
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
            for rule in sorted(special_rules):
                html += f'<span class="rule-tag">{esc(rule)}</span>'
            html += '''
    </div>
  </div>
'''

        # Améliorations d'unité
        if options:
            html += '''
  <div class="upgrades-section">
    <div class="rules-title">Améliorations sélectionnées:</div>
'''
            for group_name, opts in options.items():
                if isinstance(opts, list) and opts:
                    for opt in opts:
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

        # Monture
        if mount:
            mount_data = mount.get("mount", {})
            mount_name = esc(mount.get("name", "Monture"))
            mount_weapons = mount_data.get("weapon", [])

            html += f'''
    <div class="mount-section" style="background: rgba(150, 150, 150, 0.1); border: 1px solid rgba(150, 150, 150, 0.3);">
        <div class="mount-title">
          <span>🐴</span>
          <span style="color: var(--text-main);">{mount_name}</span>
        </div>
'''

            # Caractéristiques de la monture
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

            # Armes de la monture
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

        html += '''
</div>
'''

    # Légende des règles spéciales de la faction
    if sorted_army_list and hasattr(st.session_state, 'faction_special_rules') and st.session_state.faction_special_rules:
        faction_rules = st.session_state.faction_special_rules
        all_rules = [rule for rule in faction_rules if isinstance(rule, dict)]

        if all_rules:
            html += '''
<div class="faction-rules">
  <h3 style="text-align: center; color: var(--accent); border-top: 1px solid var(--border); padding-top: 10px; margin-bottom: 15px;">
    Légende des règles spéciales de la faction
  </h3>
  <div style="display: flex; flex-wrap: wrap;">
'''

            half = len(all_rules) // 2
            if len(all_rules) % 2 != 0:
                half += 1

            html += '<div class="rule-column" style="flex: 1; min-width: 300px; padding-right: 15px;">'
            for rule in all_rules[:half]:
                if isinstance(rule, dict):
                    html += f'''
    <div class="rule-item">
      <div class="rule-name">{esc(rule.get('name', ''))}:</div>
      <div class="rule-description">{esc(rule.get('description', ''))}</div>
    </div>
'''
            html += '</div>'

            html += '<div class="rule-column" style="flex: 1; min-width: 300px; padding-left: 15px;">'
            for rule in all_rules[half:]:
                if isinstance(rule, dict):
                    html += f'''
    <div class="rule-item">
      <div class="rule-name">{esc(rule.get('name', ''))}:</div>
      <div class="rule-description">{esc(rule.get('description', ''))}</div>
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
  <h3 style="text-align: center; color: var(--accent); border-top: 1px solid var(--border); padding-top: 10px; margin-bottom: 15px;">
    Légende des sorts de la faction
  </h3>
  <div style="display: flex; flex-wrap: wrap;">
    <div style="flex: 1; min-width: 100%;">
'''
            for spell in all_spells:
                if isinstance(spell, dict):
                    html += f'''
      <div class="spell-item" style="margin-bottom: 12px;">
        <div>
          <span class="spell-name">{esc(spell.get('name', ''))}</span>
          <span class="spell-cost"> ({spell.get('details', {}).get('cost', '?')})</span>
        </div>
        <div class="rule-description">{esc(spell.get('details', {}).get('description', ''))}</div>
      </div>
'''
            html += '''
    </div>
  </div>
</div>
'''

    html += '''
<div style="text-align: center; margin-top: 20px; font-size: 12px; color: var(--text-muted);">
  Généré par OPR ArmyBuilder FR
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
        # Essayer d'abord le chemin principal (Memory #8)
        FACTIONS_DIR = Path(__file__).resolve().parent / "frontend" / "public" / "factions"
        if not FACTIONS_DIR.exists():
            # Chemin alternatif si le premier n'existe pas
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

    # CSS pour les boutons de filtre
    st.markdown(
        """
        <style>
        .filter-container {
            margin-bottom: 20px;
        }
        .filter-button {
            margin-bottom: 10px;
        }
        .filter-button .stButton>button {
            background-color: #f0f2f6;
            color: #333;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 8px;
            font-weight: 500;
            width: 100%;
            height: 100%;
        }
        .filter-button .stButton>button:hover {
            background-color: #e9ecef;
            border-color: #ced4da;
        }
        .filter-button.active .stButton>button {
            background-color: #3498db !important;
            color: white !important;
            border-color: #2980b9 !important;
        }
        .unit-count {
            font-size: 0.9em;
            color: #6c757d;
            margin-bottom: 10px;
            text-align: center;
        }
        .unit-selector {
            margin-top: 15px;
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

    # Créer une grille de boutons de filtre
    cols = st.columns(len(filter_categories))
    for i, (category, _) in enumerate(filter_categories.items()):
        with cols[i]:
            # Déterminer si ce filtre est actif
            button_class = "active" if st.session_state.unit_filter == category else ""

            # Créer le bouton avec la classe CSS appropriée
            st.markdown(f"<div class='filter-button {button_class}'>", unsafe_allow_html=True)
            if st.button(category, key=f"filter_{category}"):
                st.session_state.unit_filter = category
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
    <div class='unit-count'>
        {len(filtered_units)} unités {st.session_state.unit_filter.lower()} disponibles |
        Total: {len(st.session_state.units)} unités
    </div>
    """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # Sélection de l'unité (uniquement parmi les unités filtrées)
    if filtered_units:
        st.markdown("<div class='unit-selector'>", unsafe_allow_html=True)
        unit = st.selectbox(
            "Unité disponible",
            filtered_units,
            format_func=format_unit_option,
            key="unit_select",
        )
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.warning(f"Aucune unité {st.session_state.unit_filter.lower()} disponible.")
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

        # ARMES
        if group.get("type") == "weapon":
            choices = []
            base_weapons = unit.get("weapon", [])
            if isinstance(base_weapons, list) and base_weapons:
                for weapon in base_weapons:
                    choices.append(format_weapon_option(weapon))
            elif isinstance(base_weapons, dict):
                choices.append(format_weapon_option(base_weapons))
            else:
                choices.append("Aucune arme de base")

            opt_map = {}
            for o in group.get("options", []):
                weapon = o.get("weapon", {})
                label = format_weapon_option(weapon, o['cost'])
                choices.append(label)
                opt_map[label] = o

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
                        weapons = [opt["weapon"]] if unit.get("type") == "hero" else [opt["weapon"]]
                        break

        # RÔLES
        elif group.get("type") == "role" and unit.get("type") == "hero":
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
                "Rôle du héros",
                choices,
                index=choices.index(current) if current in choices else 0,
                key=f"{unit_key}_{g_key}_role",
            )

            st.session_state.unit_selections[unit_key][g_key] = choice

            if choice != "Aucun rôle":
                for opt_label, opt in opt_map.items():
                    if opt_label == choice:
                        upgrades_cost += opt["cost"]
                        selected_options[group.get("group", "Rôle")] = [opt]
                        break

        # AMÉLIORATIONS D'ARME
        elif group.get("type") == "weapon_upgrades":
            choices = ["Aucune amélioration d'arme"]
            opt_map = {}

            for o in group.get("options", []):
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
                weapon_upgrades.append(opt["weapon"])

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

    # BOUTON D'AJOUT D'UNITÉ
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
            if st.session_state.unit_selections.get(unit_key, {}).get(group_key):
                selected_option = st.session_state.unit_selections[unit_key][group_key]
                if selected_option not in [format_weapon_option(unit.get("weapon", [{}])[0])] and selected_option != "Aucune monture" and selected_option != "Aucun rôle":
                    for opt in group.get("options", []):
                        weapon = opt.get("weapon", {})
                        if f"{format_weapon_option(weapon)} (+{opt['cost']} pts)" == selected_option and "special_rules" in opt:
                            all_special_rules.extend(opt["special_rules"])

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
