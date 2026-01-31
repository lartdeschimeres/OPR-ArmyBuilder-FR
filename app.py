import json
import streamlit as st
from pathlib import Path
from datetime import datetime
import hashlib
import re
import base64
import math

# ======================================================
# SESSION STATE – valeurs par défaut
# ======================================================
if "page" not in st.session_state:
    st.session_state.page = "setup"

if "army_list" not in st.session_state:
    st.session_state.army_list = []

if "army_cost" not in st.session_state:
    st.session_state.army_cost = 0

# ======================================================
# SIDEBAR – CONTEXTE & NAVIGATION
# ======================================================
with st.sidebar:
    st.title("🛡️ Army Forge")

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

    st.divider()

    st.subheader("🧭 Navigation")

    if st.button("⚙️ Configuration", use_container_width=True):
        st.session_state.page = "setup"
        st.rerun()

    if st.button("🧩 Construction", use_container_width=True):
        st.session_state.page = "army"
        st.rerun()
        
# ======================================================
# CONFIGURATION
# ======================================================
GAME_COVERS = {
    "Age of Fantasy": "assets/games/aof_cover.jpg",
    "Age of Fantasy Quest": "assets/games/aofq_cover.jpg",
    "Age of Fantasy Regiments": "assets/games/aofr_cover.jpg",
    "Grimdark Future": "assets/games/gf_cover.jpg",
    "Grimdark Future Firefight": "assets/games/gff_cover.jpg",
    "Grimdark Future Squad": "assets/games/gfsq_cover.jpg",
}

from pathlib import Path

BASE_DIR = Path(__file__).parent

GAME_CARDS = {
    "Grimdark Future": {
        "image": BASE_DIR / "assets/games/gf_cover.jpg",
        "description": "Escarmouches sci-fi à grande échelle"
    },
    "GF Firefight": {
        "image": BASE_DIR / "assets/games/gff_cover.jpg",
        "description": "Combat tactique en petites escouades"
    },
    "Age of Fantasy": {
        "image": BASE_DIR / "assets/games/aof_cover.jpg",
        "description": "Batailles fantasy"
    },
    "Age of Fantasy Skirmish": {
        "image": BASE_DIR / "assets/games/aofs_cover.jpg",
        "description": "Fantasy en escarmouche"
    },
}

st.set_page_config(
    page_title="OPR Army Forge FR",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ======================================================
# HEADER – Identité & Contexte (UX ArmyForge ++)
# ======================================================
with st.container():
    st.markdown("""
    <style>
        .af-header {
            background: linear-gradient(90deg, #1e1e1e, #2b2b2b);
            padding: 16px 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            color: #f0f0f0;
        }
        .af-title {
            font-size: 22px;
            font-weight: 700;
        }
        .af-sub {
            font-size: 14px;
            opacity: 0.9;
        }
        .af-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 10px;
        }
        .af-actions button {
            margin-right: 8px;
        }
    </style>
    """, unsafe_allow_html=True)

    game = st.session_state.get("game", "—")
    faction = st.session_state.get("faction", "—")
    list_name = st.session_state.get("list_name", "Liste sans nom")
    total = st.session_state.get("army_cost", 0)
    limit = st.session_state.get("points", 0)

    st.markdown(f"""
    <div class="af-header">
        <div class="af-row">
            <div>
                <div class="af-title">🛡 OPR Army Forge</div>
                <div class="af-sub">🎲 {game} &nbsp;&nbsp;|&nbsp;&nbsp; 🏴‍☠️ {faction}</div>
            </div>
            <div class="af-sub">
                📋 <b>{list_name}</b><br>
                📊 <b>{total}</b> / {limit} pts
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# CSS personnalisé pour les expanders et l'interface
st.markdown("""
<style>
    .stExpander > details > summary {
        background-color: #e9ecef;
        padding: 8px 12px;
        border-radius: 4px;
        font-weight: bold;
        color: #2c3e50;
    }
    .stExpander > details > div {
        padding: 10px 12px;
        background-color: #f8f9fa;
        border-radius: 0 0 4px 4px;
    }
    .army-header {
        margin-bottom: 16px;
        padding-bottom: 8px;
        border-bottom: 1px solid #444;
    }
    .army-title {
        font-size: 22px;
        font-weight: bold;
        letter-spacing: 1px;
    }
    .army-meta {
        font-size: 12px;
        color: #bbb;
    }
</style>
""", unsafe_allow_html=True)

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
        "min_points": 250,
        "default_points": 1000,
        "point_step": 250,
        "description": "Jeu de bataille futuriste",
        "hero_limit": 375,
        "unit_copy_rule": 750,
        "unit_max_cost_ratio": 0.35,
        "unit_per_points": 150
    }
}

# ======================================================
# FONCTIONS POUR LES RÈGLES SPÉCIFIQUES
# ======================================================
def check_hero_limit(army_list, army_points, game_config):
    if game_config.get("hero_limit"):
        max_heroes = math.floor(army_points / game_config["hero_limit"])
        hero_count = sum(1 for unit in army_list if unit.get("type", "").lower() == "hero")
        if hero_count > max_heroes:
            st.error(f"Limite de héros dépassée! Maximum autorisé: {max_heroes} (1 héros par {game_config['hero_limit']} pts)")
            return False
    return True

def check_unit_copy_rule(army_list, army_points, game_config):
    if not game_config.get("unit_copy_rule"):
        return True

    x_value = math.floor(army_points / game_config["unit_copy_rule"])
    max_copies = 1 + x_value

    unit_counts = {}

    for unit in army_list:
        name = unit["name"]
        unit_counts[name] = unit_counts.get(name, 0) + 1

    for unit_name, count in unit_counts.items():
        if count > max_copies:
            st.error(
                f"Trop de copies de l'unité {unit_name}! "
                f"Maximum autorisé: {max_copies} "
                f"(1+{x_value} pour {game_config['unit_copy_rule']} pts)"
            )
            return False

    return True

def check_unit_max_cost(army_list, army_points, game_config, new_unit_cost=None):
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
    if game_config.get("unit_per_points"):
        max_units = math.floor(army_points / game_config["unit_per_points"])
        if len(army_list) > max_units:
            st.error(f"Trop d'unités! Maximum autorisé: {max_units} (1 unité par {game_config['unit_per_points']} pts)")
            return False
    return True

def validate_army_rules(army_list, army_points, game, new_unit_cost=None):
    game_config = GAME_CONFIG.get(game, {})
    if game in GAME_CONFIG:
        return (check_hero_limit(army_list, army_points, game_config) and
                check_unit_copy_rule(army_list, army_points, game_config) and
                check_unit_max_cost(army_list, army_points, game_config, new_unit_cost) and
                check_unit_per_points(army_list, army_points, game_config))
    return True

# ======================================================
# FONCTIONS UTILITAIRES
# ======================================================
def format_special_rule(rule):
    if not isinstance(rule, str):
        return str(rule)
    if "(" in rule and ")" in rule:
        return rule
    match = re.search(r"(\D+)(\d+)", rule)
    if match:
        return f"{match.group(1)}({match.group(2)})"
    return rule

def extract_coriace_value(rule):
    if not isinstance(rule, str):
        return 0
    match = re.search(r"Coriace\s*\(?(\d+)\)?", rule)
    if match:
        return int(match.group(1))
    return 0

def get_coriace_from_rules(rules):
    if not rules or not isinstance(rules, list):
        return 0
    total = 0
    for rule in rules:
        total += extract_coriace_value(rule)
    return total

def get_mount_details(mount):
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

def format_weapon_details(weapon):
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
    name_part = f"{u['name']}"
    if u.get('type') == "hero":
        name_part += " [1]"  # Les héros ont toujours un effectif de 1
    else:
        base_size = u.get('size', 10)
        name_part += f" [{base_size}]"  # Les unités ont leur effectif de base
    qua_def = f"Qua {u['quality']}+ / Déf {u.get('defense', '?')}"
    coriace = get_coriace_from_rules(u.get('special_rules', []))
    if 'mount' in u and u['mount']:
        _, mount_coriace = get_mount_details(u['mount'])
        coriace += mount_coriace
    if coriace > 0:
        qua_def += f" / Coriace {coriace}"
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
    result = f"{name_part} - {qua_def}"
    if weapons_part:
        result += f" - {weapons_part}"
    if rules_part:
        result += f" - {rules_part}"
    result += f" {u['base_cost']}pts"
    return result

def find_option_by_name(options, name):
    try:
        return next((o for o in options if o.get("name") == name), None)
    except Exception:
        return None

def display_faction_rules(faction_data):
    if not faction_data or 'special_rules_descriptions' not in faction_data:
        return
    st.subheader("📜 Règles Spéciales de la Faction")
    rules_descriptions = faction_data['special_rules_descriptions']
    if not rules_descriptions:
        st.info("Cette faction n'a pas de règles spéciales spécifiques.")
        return
    for rule_name, description in rules_descriptions.items():
        with st.expander(f"**{rule_name}**", expanded=False):
            st.markdown(f"{description}")

# ======================================================
# EXPORT HTML
# ======================================================
def export_html(army_list, army_name, army_limit):
    def esc(txt):
        return str(txt).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # Trier la liste pour afficher les héros en premier
    sorted_army_list = sorted(army_list, key=lambda x: 0 if x.get("type") == "hero" else 1)

    html = f"""
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title>Liste d'Armée OPR - {esc(army_name)}</title>
<style>
:root {{
  --bg-main: #2e2f2b;
  --bg-card: #3a3c36;
  --bg-header: #1f201d;
  --accent: #9fb39a;
  --accent-soft: #6e7f6a;
  --text-main: #e6e6e6;
  --text-muted: #b0b0b0;
  --border: #555;
}}
body {{
  background: var(--bg-main);
  color: var(--text-main);
  font-family: "Segoe UI", Roboto, Arial, sans-serif;
  margin: 0;
  padding: 20px;
}}

.army {{
  max-width: 1100px;
  margin: auto;
}}

.army-title {{
  text-align: center;
  font-size: 24px;
  font-weight: bold;
  margin-bottom: 20px;
  color: var(--accent);
  border-bottom: 1px solid var(--border);
  padding-bottom: 10px;
}}

.unit-card {{
  background: var(--bg-card);
  border: 1px solid var(--border);
  margin-bottom: 40px;
  padding: 16px;
  page-break-inside: avoid;  /* Évite la coupure d'une unité sur plusieurs pages */
}}

.unit-header {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: var(--bg-header);
  padding: 10px 14px;
  margin: -16px -16px 12px -16px;
}}

.unit-header h2 {{
  margin: 0;
  font-size: 18px;
  color: var(--accent);
}}

.cost {{
  font-weight: bold;
}}

.stats {{
  margin-bottom: 10px;
}}

.stats span {{
  display: inline-block;
  background: var(--accent-soft);
  color: #000;
  padding: 4px 8px;
  margin-right: 6px;
  font-size: 12px;
  font-weight: bold;
}}

table {{
  width: 100%;
  border-collapse: collapse;
  margin-top: 10px;
  font-size: 12px;
  border: 1px solid var(--border);
}}

th, td {{
  border: 1px solid var(--border);
  padding: 6px;
  text-align: left;
}}

th {{
  background: var(--bg-header);
  color: var(--text-main);
}}

.rules {{
  margin-top: 10px;
  font-size: 12px;
}}

.rules span {{
  display: inline-block;
  margin-right: 8px;
  color: var(--accent);
}}

.section-title {{
  font-weight: bold;
  margin-top: 10px;
  margin-bottom: 5px;
  color: var(--text-main);
}}

.special-rules-title {{
  font-size: 18px;
  font-weight: bold;
  margin-top: 40px;
  margin-bottom: 15px;
  color: var(--accent);
  text-align: center;
  border-top: 1px solid var(--border);
  padding-top: 10px;
}}

.special-rules-container {{
  display: flex;
  flex-wrap: wrap;
  font-size: 12px;
  margin-bottom: 20px;
}}

.special-rules-column {{
  flex: 1;
  padding: 0 10px;
}}

.special-rules-column div {{
  margin-bottom: 8px;
}}
</style>
</head>
<body>
<div class="army">
  <!-- Titre de la liste -->
  <div class="army-title">
    {esc(army_name)} - {sum(unit['cost'] for unit in sorted_army_list)}/{army_limit} pts - {st.session_state.game}
  </div>
"""

    for unit in sorted_army_list:
        name = esc(unit.get("name", "Unité"))
        cost = unit.get("cost", 0)
        quality = esc(unit.get("quality", "-"))
        defense = esc(unit.get("defense", "-"))
        coriace = unit.get("coriace")

        # Détermine l'effectif à afficher
        unit_size = unit.get("size", 10)
        if unit.get("type", "").lower() == "hero":
            unit_size = 1  # Les héros ont toujours un effectif de 1

        html += f"""
<section class="unit-card">
  <div class="unit-header">
    <h2>{name} [{unit_size}]</h2>
    <span class="cost">{cost} pts</span>
  </div>

  <div class="stats">
    <span>Qualité {quality}+</span>
    <span>Défense {defense}+</span>
"""

        if coriace and coriace > 0:
            html += f"<span>Coriace {coriace}</span>"

        html += "</div>"

        # ---- ARMES ----
        weapons = unit.get("weapon")
        if weapons:
            if not isinstance(weapons, list):
                weapons = [weapons]

            html += '<div class="section-title">Armes équipées :</div>'
            html += """
<table>
<thead>
<tr>
  <th>Arme</th><th>Port</th><th>Att</th><th>PA</th><th>Règles spéciales</th>
</tr>
</thead>
<tbody>
"""
            for w in weapons:
                html += f"""
<tr>
  <td>{esc(w.get('name', '-'))}</td>
  <td>{esc(w.get('range', '-'))}</td>
  <td>{esc(w.get('attacks', '-'))}</td>
  <td>{esc(w.get('ap', '-'))}</td>
  <td>{esc(", ".join(w.get('special', [])) if w.get('special') else '-')}</td>
</tr>
"""
            html += "</tbody></table>"

        # ---- RÈGLES SPÉCIALES ----
        rules = unit.get("rules", [])
        if rules:
            html += '<div class="section-title">Règles spéciales :</div>'
            html += "<div class='rules'>"
            for r in rules:
                html += f"<span>{esc(r)}</span>"
            html += "</div>"

        # ---- OPTIONS ----
        options = unit.get("options", {})
        if options:
            html += '<div class="section-title">Options :</div>'
            for group_name, opts in options.items():
                if isinstance(opts, list) and opts:
                    html += f"<div><strong>{esc(group_name)} :</strong> "
                    for opt in opts:
                        html += f"{esc(opt.get('name', ''))}, "
                    html += "</div>"

        # ---- MONTURE (pour les héros) ----
        mount = unit.get("mount")
        if mount:
            mount_name = esc(mount.get("name", "Monture non nommée"))
            mount_data = mount
            if 'mount' in mount:
                mount_data = mount['mount']

            html += '<div class="section-title">Monture :</div>'
            html += f"<div><strong>{mount_name}</strong>"

            if 'quality' in mount_data or 'defense' in mount_data:
                html += " ("
                if 'quality' in mount_data:
                    html += f"Qualité {mount_data['quality']}+"
                if 'defense' in mount_data:
                    html += f" Défense {mount_data['defense']}+"
                html += ")"

            if 'special_rules' in mount_data and mount_data['special_rules']:
                html += " | " + ", ".join(mount_data['special_rules'])

            if 'weapons' in mount_data and mount_data['weapons']:
                for weapon in mount_data['weapons']:
                    weapon_details = format_weapon_details(weapon)
                    html += f" | {weapon.get('name', 'Arme')} (Att{weapon_details['attacks']}, PA({weapon_details['ap']})"
                    if weapon_details['special']:
                        html += ", " + ", ".join(weapon_details['special'])
                    html += ")"

            html += "</div>"

        html += "</section>"

    # ---- RÈGLES SPÉCIALES DE L'ARMÉE (en deux colonnes) ----
    if sorted_army_list and 'faction' in st.session_state:
        faction_data = factions_by_game.get(st.session_state.game, {}).get(st.session_state.faction, {})
        if 'special_rules_descriptions' in faction_data:
            faction_rules = faction_data['special_rules_descriptions']
            all_rules = sorted(faction_rules.keys())

            if all_rules:
                html += """
                <div style="margin-top: 40px;">
                    <h3 style="text-align: center; color: var(--accent); border-top: 1px solid var(--border); padding-top: 10px; margin-bottom: 15px;">
                        Légende des règles spéciales de la faction
                    </h3>
                    <div style="display: flex; flex-wrap: wrap;">
                        <div style="flex: 1; min-width: 300px; padding-right: 15px;">
                """

                # Diviser les règles en deux colonnes de longueur égale
                half = len(all_rules) // 2
                if len(all_rules) % 2 != 0:
                    half += 1  # Ajouter une règle à la première colonne si le nombre est impair

                # Première colonne
                for rule in all_rules[:half]:
                    html += f"""
                    <div style="margin-bottom: 8px; font-size: 12px;">
                        <strong>{esc(rule)}:</strong> {esc(faction_rules[rule])}
                    </div>
                    """

                html += """
                        </div>
                        <div style="flex: 1; min-width: 300px; padding-left: 15px;">
                """

                # Deuxième colonne
                for rule in all_rules[half:]:
                    html += f"""
                    <div style="margin-bottom: 8px; font-size: 12px;">
                        <strong>{esc(rule)}:</strong> {esc(faction_rules[rule])}
                    </div>
                    """

                html += """
                        </div>
                    </div>
                </div>
                """

    html += """
</div>
</body>
</html>
"""
    return html

# ======================================================
# CHARGEMENT DES FACTIONS
# ======================================================
@st.cache_data
def load_factions():
    factions = {}
    games = set()
    if not list(FACTIONS_DIR.glob("*.json")):
        default_faction = {
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
# INITIALISATION SESSION STATE
# ======================================================
if "game" not in st.session_state:
    st.session_state.game = "Grimdark Future"
if "faction" not in st.session_state:
    st.session_state.faction = None
if "points" not in st.session_state:
    st.session_state.points = GAME_CONFIG["Grimdark Future"]["default_points"]
if "army_list" not in st.session_state:
    st.session_state.army_list = []

# ======================================================
# FONCTION POUR LA BARRE DE PROGRESSION
# ======================================================
def show_points_progress(current_points, max_points):
    ratio = min(current_points / max_points, 1.0)
    st.progress(ratio)
    st.markdown(f"**{current_points}/{max_points} pts**")

# ======================================================
# INITIALISATION
# ======================================================
factions_by_game, games = load_factions()
if "list_name" not in st.session_state:
    st.session_state.list_name = "Liste sans nom"
if "page" not in st.session_state:
    st.session_state.page = "setup"
    st.session_state.army_list = []
    st.session_state.army_cost = 0
    st.session_state.current_player = "Simon Joinville Fouquet"

# ======================================================
# PAGE 1 – CONFIGURATION
# ======================================================
if st.session_state.page == "setup":
    st.title("OPR Army Forge")

    # ======================================================
    # IMPORT D'UNE LISTE EXISTANTE
    # ======================================================
    st.divider()
    st.subheader("🔄 Recharger une liste JSON")

    uploaded = st.file_uploader(
        "Importer une liste exportée",
        type=["json"],
        key="import_json"
    )

    if uploaded is not None:
        try:
            data = json.load(uploaded)

            required_keys = {"game", "faction", "army_list", "points"}
            if not required_keys.issubset(data.keys()):
                st.error("❌ Fichier JSON invalide ou incomplet")
            else:
                st.session_state.game = data["game"]
                st.session_state.faction = data["faction"]
                st.session_state.points = data["points"]
                st.session_state.list_name = data.get("name", "Liste importée")
                st.session_state.army_list = data["army_list"]
                st.session_state.army_cost = data.get("total_cost", 0)

                factions_by_game, _ = load_factions()
                st.session_state.units = factions_by_game[
                    st.session_state.game
                ][
                    st.session_state.faction
                ]["units"]

                st.session_state.page = "army"
                st.success("✅ Liste chargée avec succès")
                st.rerun()

        except Exception as e:
            st.error(f"❌ Erreur lors du chargement : {e}")

    # ======================================================
    # SÉLECTION DU JEU (CARTES VISUELLES)
    # ======================================================
    st.divider()
    st.subheader("🎮 Choisis ton jeu")

    if not games:
        st.error("Aucun jeu trouvé")
        st.stop()

    # Grille 4 colonnes → 8 jeux = 2 lignes
    cols = st.columns(4)

    for i, game_name in enumerate(games):
        col = cols[i % 4]
        card = GAME_CARDS.get(game_name)
        is_selected = st.session_state.get("game") == game_name

        with col:
            with st.container(border=True):
                # Image du jeu
                if card and card.get("image") and card["image"].exists():
                    st.image(
                        str(card["image"]),
                        use_container_width=True
                    )
                else:
                    st.image(
                        "assets/games/onepagerules_round_128x128.png",
                        use_container_width=True
                    )

                # Nom du jeu
                st.markdown(
                    f"<div style='text-align:center; font-weight:600; margin-top:6px;'>"
                    f"{game_name}</div>",
                    unsafe_allow_html=True
                )

                # Bouton de sélection
                if st.button(
                    "✔ Sélectionner" if not is_selected else "✅ Sélectionné",
                    key=f"select_game_{game_name}",
                    use_container_width=True,
                    disabled=is_selected
                ):
                    st.session_state.game = game_name
                    st.rerun()

    # Jeu non sélectionné → on bloque la suite
    if "game" not in st.session_state:
        st.info("⬆️ Sélectionne un jeu pour continuer")
        st.stop()

    game = st.session_state.game
    game_config = GAME_CONFIG.get(game, GAME_CONFIG["Age of Fantasy"])

    # ======================================================
    # PARAMÈTRES DE LISTE
    # ======================================================
    st.divider()
    st.subheader("⚙️ Paramètres de la liste")

    factions_by_game, _ = load_factions()

    faction = st.selectbox(
        "Faction",
        factions_by_game[game].keys()
    )

    points = st.number_input(
        "Points",
        min_value=game_config["min_points"],
        max_value=game_config["max_points"],
        value=game_config["default_points"],
        step=game_config["point_step"]
    )

    list_name = st.text_input(
        "Nom de la liste",
        f"Liste_{datetime.now().strftime('%Y%m%d')}"
    )

    # ======================================================
    # PASSAGE À LA CONSTRUCTION DE L'ARMÉE
    # ======================================================
    st.divider()
    st.markdown("### 🚀 Étape suivante")
    st.info("Tu pourras ajouter, modifier et exporter ton armée à l’étape suivante.")

    if st.button("➡️ Construire l’armée", use_container_width=True):
        st.session_state.game = game
        st.session_state.faction = faction
        st.session_state.points = points
        st.session_state.list_name = list_name
        st.session_state.units = factions_by_game[game][faction]["units"]
        st.session_state.army_list = st.session_state.get("army_list", [])
        st.session_state.army_cost = st.session_state.get("army_cost", 0)
        st.session_state.page = "army"
        st.rerun()
        
# ======================================================
# PAGE 2 – CONSTRUCTEUR D'ARMÉE
# ======================================================
elif st.session_state.page == "army":
    st.markdown(
        f"""
        <div class="army-header">
            <div class="army-title">{st.session_state.list_name}</div>
            <div class="army-meta">
              {st.session_state.army_cost} / {st.session_state.points} pts
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    if st.button("⬅ Retour à la page Configuration"):
        st.session_state.page = "setup"
        st.rerun()
    st.title(st.session_state.list_name)
    st.caption(f"{st.session_state.game} • {st.session_state.faction} • {st.session_state.army_cost}/{st.session_state.points} pts")
    game_config = GAME_CONFIG.get(st.session_state.game, GAME_CONFIG["Age of Fantasy"])
    faction_data = factions_by_game[st.session_state.game][st.session_state.faction]
    display_faction_rules(faction_data)
    if not validate_army_rules(st.session_state.army_list, st.session_state.points, st.session_state.game):
        st.warning("⚠️ Certaines règles spécifiques ne sont pas respectées. Voir les messages d'erreur ci-dessus.")
    st.divider()
    st.subheader("Points d'armée")
    show_points_progress(st.session_state.army_cost, st.session_state.points)
    st.divider()
    st.subheader("Ajouter une unité")
    unit = st.selectbox(
        "Unité disponible",
        st.session_state.units,
        format_func=format_unit_option,
        index=0,
        key="unit_select"
    )
    for k in list(st.session_state.keys()):
        if k.startswith("combined_"):
            del st.session_state[k]
    base_size = unit.get('size', 10)
    base_cost = unit["base_cost"]
    max_cost = st.session_state.points * game_config["unit_max_cost_ratio"]
    if unit["base_cost"] > max_cost:
        st.error(f"Cette unité ({unit['base_cost']} pts) dépasse la limite de {int(max_cost)} pts ({int(game_config['unit_max_cost_ratio']*100)}% du total)")
        st.stop()
    weapon = unit.get("weapons", [{}])[0]
    selected_options = {}
    mount = None
    weapon_cost = 0
    mount_cost = 0
    upgrades_cost = 0
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
        
        else:
            is_hero = unit.get("type", "").lower() == "hero"

            if is_hero:
                option_labels = ["Aucune amélioration"]
                option_map = {}
    
                for o in group["options"]:
                    label = f"{o['name']} (+{o['cost']} pts)"
                    option_labels.append(label)
                    option_map[label] = o

                selected = st.radio(
                    f"Amélioration – {group['group']}",
                    option_labels,
                    key=f"{unit['name']}_{group['group']}_hero"
                )

                if selected != "Aucune amélioration":
                    opt = option_map[selected]
                    selected_options[group['group']] = [opt]
                    upgrades_cost += opt["cost"]

            else:
                st.write("Sélectionnez les améliorations (plusieurs choix possibles):")
                for o in group["options"]:
                    if st.checkbox(
                        f"{o['name']} (+{o['cost']} pts)",
                        key=f"{unit['name']}_{group['group']}_{o['name']}"
                    ):
                        selected_options.setdefault(group["group"], []).append(o)
                        upgrades_cost += o["cost"]
        
# Doublage des effectifs (UNIQUEMENT pour les unités, PAS pour les héros)
    if unit.get("type") != "hero":
        double_size = st.checkbox(
            "Unité combinée (doubler les effectifs)",
            value=False,
            key=f"double_{unit['name']}"
        )
        multiplier = 2 if double_size else 1
    else:
        double_size = False
        multiplier = 1


    # Calcul du coût final (en tenant compte du doublage uniquement pour les unités)
    core_cost = (base_cost + weapon_cost) * multiplier
    final_cost = core_cost + upgrades_cost + mount_cost
    unit_size = base_size * multiplier

    if unit.get("type", "").lower() == "hero":
        st.markdown("**Effectif final : [1]** (héros)")
    else:
        label = "combinée" if double_size else "standard"
        st.markdown(f"**Effectif final : [{unit_size}]** ({label})")

    if st.button("Ajouter à l'armée"):
        try:
            weapon_data = format_weapon_details(weapon)
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
            total_coriace = total_coriace if total_coriace > 0 else None
            unit_data = {
                "name": unit["name"],
                "type": unit.get("type", "unit"),
                "cost": final_cost,
                "base_cost": base_cost,
                "size": unit_size,
                "is_combined": double_size if unit.get("type") != "hero" else False,
                "quality": unit["quality"],
                "defense": unit["defense"],
                "rules": [format_special_rule(r) for r in unit.get("special_rules", []) if "Coriace(0)" not in r],
                "weapon": weapon_data,
                "options": selected_options,
                "mount": mount,
                "coriace": total_coriace,
                "game": st.session_state.game
            }
            test_army = st.session_state.army_list.copy()
            test_army.append(unit_data)
            test_total = st.session_state.army_cost + final_cost
            if test_total > st.session_state.points:
                st.error(f"⚠️ La limite de points ({st.session_state.points}) est dépassée! Ajout annulé.")
                if st.button("Annuler la dernière action"):
                    st.session_state.army_list = st.session_state.army_list[:-1]
                    st.session_state.army_cost -= final_cost
                    st.rerun()
            elif not validate_army_rules(test_army, st.session_state.points, st.session_state.game, final_cost):
                st.error("Cette unité ne peut pas être ajoutée car elle violerait les règles du jeu.")
            else:
                st.session_state.army_list.append(unit_data)
                st.session_state.army_cost += final_cost
                st.rerun()
        except Exception as e:
            st.error(f"Erreur lors de la création de l'unité: {str(e)}")
    st.divider()
    st.subheader("Liste de l'armée")
    if not st.session_state.army_list:
        st.info("Ajoutez des unités pour commencer")
    for i, u in enumerate(st.session_state.army_list):
        with st.container():
            qua_def_coriace = f"Qua {u['quality']}+ / Déf {u['defense']}+"
            if u.get("coriace"):
                qua_def_coriace += f" / Coriace {u['coriace']}"
            unit_header = f"### {u['name']} [{u.get('size', 1) if u.get('type') != 'hero' else 1}] ({u['cost']} pts) | {qua_def_coriace}"
            if u.get("type") == "hero":
                unit_header += " | 🌟 Héros"
            st.markdown(unit_header)
            if u.get("rules"):
                rules_text = ", ".join(u["rules"])
                st.markdown(f"**Règles spéciales:** {rules_text}")
            if 'weapon' in u and u['weapon']:
                weapon_details = format_weapon_details(u['weapon'])
                st.markdown(f"**Arme:** {weapon_details['name']} (A{weapon_details['attacks']}, PA({weapon_details['ap']}){', ' + ', '.join(weapon_details['special']) if weapon_details['special'] else ''})")
            if u.get("options"):
                for group_name, opts in u["options"].items():
                    if isinstance(opts, list) and opts:
                        st.markdown(f"**{group_name}:**")
                        for opt in opts:
                            st.markdown(f"• {opt.get('name', '')}")
            if u.get("mount"):
                 mount_details = format_mount_details(u["mount"])
                 st.markdown(f"**Monture:** {mount_details}")
            if st.button(f"Supprimer {u['name']}", key=f"del_{i}"):
                st.session_state.army_cost -= u["cost"]
                st.session_state.army_list.pop(i)
                st.rerun()
    army_name = st.session_state.get("list_name", "Liste sans nom")
    army = st.session_state.get("army_list", [])
    army_limit = st.session_state.get("points", 0)
    army_data = {
        "name": army_name,
        "game": st.session_state.get("game", "Grimdark Future"),
        "faction": st.session_state.faction,
        "points": army_limit,
        "total_cost": st.session_state.army_cost,
        "army_list": army
    }
    html_export = export_html(
        army_list=army,
        army_name=army_name,
        army_limit=army_limit
    )        
    
    json_data = json.dumps(army_data, indent=2, ensure_ascii=False)
    st.divider()
    
    st.divider()
    st.subheader("📤 Exporter l’armée")

    col_json, col_html = st.columns(2)

    with col_json:
        st.download_button(
            label="📄 Exporter en JSON (fichier téléchargeable)",
            data=json.dumps(army_data, indent=2, ensure_ascii=False),
            file_name=f"{st.session_state.list_name or 'army'}_opr.json",
            mime="application/json",
            use_container_width=True
        )

    with col_html:
        st.download_button(
            label="🌐 Exporter en HTML (fiche imprimable)",
            data=html_export,
            file_name=f"{st.session_state.list_name or 'army'}.html",
            mime="text/html",
            use_container_width=True
        )
