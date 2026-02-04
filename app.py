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
if "widget_counter" not in st.session_state:
    st.session_state.widget_counter = 0

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
    "Grimdark Future": "assets/games/gf_cover.jpg",
    "Age of Fantasy": "assets/games/aof_cover.jpg",
    "Age of Fantasy Regiments": "assets/games/aofr_cover.jpg",
    "Grimdark Future Firefight": "assets/games/gff_cover.jpg",
    "Age of Fantasy Quest": "assets/games/aofq_cover.jpg",
    "Grimdark Future Squad": "assets/games/gfsq_cover.jpg",
}

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
# HEADER – Identité & Contexte
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
        .stRadio > div {
            display: flex;
            flex-direction: column;
        }
        .stRadio > div > label {
            margin-bottom: 8px;
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

# CSS personnalisé
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
    .unit-card {
        background: #f8f9fa;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 20px;
        border: 1px solid #ddd;
    }
    .hero-badge {
        color: gold;
        font-weight: bold;
    }
    .rule-badge {
        background-color: #e9ecef;
        padding: 2px 6px;
        border-radius: 4px;
        margin-right: 5px;
        font-size: 12px;
    }
</style>
""", unsafe_allow_html=True)

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

def format_unit_option(u):
    name_part = f"{u['name']}"
    if u.get('type') == "hero":
        name_part += " [1]"
    else:
        base_size = u.get('size', 10)
        name_part += f" [{base_size}]"
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
            weapons.append(f"{weapon.get('name', 'Arme')} (A{weapon_details['attacks']}, PA({weapon_details['ap']}))")
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
            details += f" Défense {mount_data['defense']}+"
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

# ======================================================
# EXPORT HTML
# ======================================================
def export_html(army_list, army_name, army_limit):
    def esc(txt):
        return str(txt).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    sorted_army_list = sorted(army_list, key=lambda x: 0 if x.get("type") == "hero" else 1)
    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title>Liste d'Armée OPR - {esc(army_name)}</title>
<style>
:root {{
  --bg-main: #2e2f2b;
  --bg-card: #3a3c36;
  --accent: #9fb39a;
  --text-main: #e6e6e6;
}}
body {{
  background: var(--bg-main);
  color: var(--text-main);
  font-family: "Segoe UI", Roboto, Arial, sans-serif;
  margin: 0;
  padding: 20px;
}}
.unit-card {{
  background: var(--bg-card);
  border: 1px solid #555;
  margin-bottom: 20px;
  padding: 16px;
  border-radius: 8px;
}}
</style>
</head>
<body>
<div style="max-width: 1100px; margin: auto;">
  <h1 style="text-align: center; color: var(--accent); margin-bottom: 20px;">
    {esc(army_name)} - {sum(unit['cost'] for unit in sorted_army_list)}/{army_limit} pts
  </h1>
"""

    for unit in sorted_army_list:
        name = esc(unit.get("name", "Unité"))
        cost = unit.get("cost", 0)
        quality = esc(unit.get("quality", "-"))
        defense = esc(unit.get("defense", "-"))
        coriace = unit.get("coriace")

        unit_size = unit.get("size", 10)
        if unit.get("type", "").lower() == "hero":
            unit_size = 1

        html += f"""
<div class="unit-card">
  <h2 style="margin-top: 0; color: var(--accent);">
    {name} [{unit_size}] - {cost} pts
  </h2>
  <div style="margin-bottom: 10px;">
    <span style="background: #6e7f6a; padding: 4px 8px; border-radius: 4px; margin-right: 6px;">
      Qualité {quality}+
    </span>
    <span style="background: #6e7f6a; padding: 4px 8px; border-radius: 4px;">
      Défense {defense}+
    </span>
"""
        if coriace and coriace > 0:
            html += f"""
    <span style="background: #6e7f6a; padding: 4px 8px; border-radius: 4px;">
      Coriace {coriace}
    </span>
"""
        html += "</div>"

        # Armes
        weapons = unit.get("weapon", [])
        if weapons:
            if not isinstance(weapons, list):
                weapons = [weapons]
            html += "<h3 style='margin-top: 15px;'>Armes équipées :</h3><ul style='margin-top: 5px; padding-left: 20px;'>"
            for w in weapons:
                html += f"<li style='margin-bottom: 5px;'>{esc(w.get('name', '-'))} (A{w.get('attacks', '-')}, PA{w.get('ap', '-')})</li>"
            html += "</ul>"

        # Règles spéciales
        rules = unit.get("rules", [])
        if rules:
            html += f"<div style='margin-top: 15px;'><strong>Règles spéciales :</strong> {', '.join(esc(r) for r in rules)}</div>"

        # Options
        options = unit.get("options", {})
        if options:
            html += "<h3 style='margin-top: 15px;'>Options :</h3><ul style='margin-top: 5px; padding-left: 20px;'>"
            for group_name, opts in options.items():
                if isinstance(opts, list) and opts:
                    html += f"<li style='margin-bottom: 5px;'><strong>{esc(group_name)}:</strong> {', '.join(esc(opt.get('name', '')) for opt in opts)}</li>"
            html += "</ul>"

        # Monture
        mount = unit.get("mount")
        if mount:
            html += f"<h3 style='margin-top: 15px;'>Monture :</h3><p style='margin-top: 5px;'>{esc(mount.get('name', 'Aucune'))}</p>"

        html += "</div>"
    html += "</div></body></html>"
    return html

# ======================================================
# CHARGEMENT DES FACTIONS
# ======================================================
@st.cache_data
def load_factions():
    factions = {}
    games = set()
    for fp in FACTIONS_DIR.glob("*.json"):
        try:
            with open(fp, encoding="utf-8") as f:
                data = json.load(f)
                game = data.get("game")
                faction = data.get("faction")
                if game and faction:
                    if game not in factions:
                        factions[game] = {}
                    factions[game][faction] = data
                    games.add(game)
        except Exception as e:
            st.warning(f"Erreur chargement {fp.name}: {e}")
    return factions, sorted(games) if games else list(GAME_CONFIG.keys())

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
            st.error(f"Trop de copies de l'unité {unit_name}! Maximum autorisé: {max_copies}")
            return False
    return True

def check_unit_max_cost(army_list, army_points, game_config, new_unit_cost=None):
    if not game_config.get("unit_max_cost_ratio"):
        return True
    max_cost = army_points * game_config["unit_max_cost_ratio"]
    for unit in army_list:
        if unit["cost"] > max_cost:
            st.error(f"L'unité {unit['name']} dépasse la limite de coût")
            return False
    if new_unit_cost and new_unit_cost > max_cost:
        st.error(f"Cette unité dépasse la limite de coût")
        return False
    return True

def check_unit_per_points(army_list, army_points, game_config):
    if game_config.get("unit_per_points"):
        max_units = math.floor(army_points / game_config["unit_per_points"])
        if len(army_list) > max_units:
            st.error(f"Trop d'unités! Maximum autorisé: {max_units}")
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
# PAGE 1 – CONFIGURATION
# ======================================================
if st.session_state.page == "setup":
    st.title("OPR Army Forge")

    # IMPORT D'UNE LISTE EXISTANTE
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
                st.session_state.units = factions_by_game[st.session_state.game][st.session_state.faction]["units"]

                st.session_state.page = "army"
                st.success("✅ Liste chargée avec succès")
                st.rerun()
        except Exception as e:
            st.error(f"❌ Erreur lors du chargement : {e}")

    # SÉLECTION DU JEU
    st.divider()
    st.subheader("🎮 Choisis ton jeu")

    factions_by_game, games = load_factions()
    if not games:
        st.error("Aucun jeu trouvé")
        st.stop()

    cols = st.columns(4)
    for i, game_name in enumerate(games):
        col = cols[i % 4]
        card = GAME_CARDS.get(game_name)
        is_selected = st.session_state.get("game") == game_name

        with col:
            with st.container(border=True):
                if card and card.get("image") and card["image"].exists():
                    st.image(str(card["image"]), use_container_width=True)
                else:
                    try:
                        st.image("assets/games/onepagerules_round_128x128.png", use_container_width=True)
                    except:
                        st.warning("Image par défaut non trouvée")

                st.markdown(f"<div style='text-align:center; font-weight:600; margin-top:6px;'>{game_name}</div>", unsafe_allow_html=True)

                if st.button("✔ Sélectionner" if not is_selected else "✅ Sélectionné",
                           key=f"select_game_{game_name}",
                           use_container_width=True,
                           disabled=is_selected):
                    st.session_state.game = game_name
                    st.rerun()

    if "game" not in st.session_state:
        st.info("⬆️ Sélectionne un jeu pour continuer")
        st.stop()

    game = st.session_state.game
    game_config = GAME_CONFIG.get(game, GAME_CONFIG["Age of Fantasy"])

    # PARAMÈTRES DE LISTE
    st.divider()
    st.subheader("⚙️ Paramètres de la liste")

    factions_by_game, _ = load_factions()
    faction = st.selectbox("Faction", factions_by_game[game].keys())

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

    # PASSAGE À LA CONSTRUCTION DE L'ARMÉE
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
# PAGE 2 – CONSTRUCTEUR D'ARMÉE (version corrigée)
# ======================================================
elif st.session_state.page == "army":
    # Initialisation sécurisée
    if "widget_counter" not in st.session_state:
        st.session_state.widget_counter = 0

    # Nettoyage des anciennes clés spécifiques
    if "unit" in locals():
        keys_to_clean = [k for k in st.session_state.keys()
                        if k.startswith("unit_") and unit["name"] in k]
        for k in keys_to_clean:
            del st.session_state[k]

    # Affichage de base
    st.markdown(f"""
    <div style='background: #2e2f2b; padding: 15px; border-radius: 8px; margin-bottom: 20px; color: white;'>
        <h2 style='margin: 0;'>{st.session_state.list_name}</h2>
        <p style='margin: 5px 0;'>{st.session_state.army_cost} / {st.session_state.points} pts</p>
    </div>
    """, unsafe_allow_html=True)

    if st.button("⬅ Retour à la configuration"):
        st.session_state.page = "setup"
        st.rerun()

    # Sélection de l'unité
    unit = st.selectbox(
        "Unité disponible",
        st.session_state.units,
        format_func=format_unit_option,
        key="unit_select"
    )

    # Initialisation des variables
    weapon = unit.get("weapons", [])
    selected_options = {}
    mount = None
    weapon_cost = 0
    mount_cost = 0
    upgrades_cost = 0

    # Traitement des améliorations avec persistance corrigée
    for group_idx, group in enumerate(unit.get("upgrade_groups", [])):
        st.session_state.widget_counter += 1
        unique_key = f"unit_{unit['name']}_{group_idx}"

        st.subheader(group['group'])

        if group["type"] == "weapon":
            # Boutons radio pour les armes (choix unique avec persistance)
            weapon_options = ["Arme de base"]
            for o in group["options"]:
                weapon_details = format_weapon_details(o["weapon"])
                weapon_options.append(f"{o['name']} (+{o['cost']} pts)")

            # Récupération de la sélection précédente
            current_selection = st.session_state.get(f"{unique_key}_weapon", weapon_options[0])

            # Affichage du radio button avec la sélection persistante
            selected_weapon = st.radio(
                "Sélectionnez une arme",
                weapon_options,
                index=weapon_options.index(current_selection) if current_selection in weapon_options else 0,
                key=f"{unique_key}_weapon"
            )

            # Mise à jour de la sélection
            st.session_state[f"{unique_key}_weapon"] = selected_weapon

            if selected_weapon != "Arme de base":
                opt_name = selected_weapon.split(" (+")[0]
                opt = next((o for o in group["options"] if o["name"] == opt_name), None)
                if opt:
                    if unit.get("type") == "hero":
                        weapon = [opt["weapon"]]
                    else:
                        weapon = unit.get("weapons", []) + [opt["weapon"]]
                    weapon_cost += opt["cost"]

        elif group["type"] == "mount":
            # Boutons radio pour les montures avec persistance
            mount_options = ["Aucune monture"]
            mount_map = {}
            for o in group["options"]:
                mount_options.append(f"{o['name']} (+{o['cost']} pts)")
                mount_map[f"{o['name']} (+{o['cost']} pts)"] = o

            current_selection = st.session_state.get(f"{unique_key}_mount", mount_options[0])

            selected_mount = st.radio(
                "Sélectionnez une monture",
                mount_options,
                index=mount_options.index(current_selection) if current_selection in mount_options else 0,
                key=f"{unique_key}_mount"
            )

            st.session_state[f"{unique_key}_mount"] = selected_mount

            if selected_mount != "Aucune monture":
                opt = mount_map.get(selected_mount)
                if opt:
                    mount = opt
                    mount_cost = opt["cost"]

        else:
            # Checkboxes pour les améliorations (choix multiples)
            if unit.get("type") == "hero":
                option_labels = ["Aucune amélioration"]
                option_map = {}
                for o in group["options"]:
                    label = f"{o['name']} (+{o['cost']} pts)"
                    option_labels.append(label)
                    option_map[label] = o

                current_selection = st.session_state.get(f"{unique_key}_hero", option_labels[0])

                selected = st.radio(
                    f"Amélioration – {group['group']}",
                    option_labels,
                    index=option_labels.index(current_selection) if current_selection in option_labels else 0,
                    key=f"{unique_key}_hero"
                )

                st.session_state[f"{unique_key}_hero"] = selected

                if selected != "Aucune amélioration":
                    opt = option_map.get(selected)
                    if opt:
                        selected_options[group['group']] = [opt]
                        upgrades_cost += opt["cost"]
            else:
                for o in group["options"]:
                    option_key = f"{unique_key}_{o['name']}"
                    st.session_state.setdefault(option_key, False)

                    if st.checkbox(
                        f"{o['name']} (+{o['cost']} pts)",
                        value=st.session_state[option_key],
                        key=option_key
                    ):
                        st.session_state[option_key] = True
                        selected_options.setdefault(group["group"], []).append(o)
                        upgrades_cost += o["cost"]
                    else:
                        st.session_state[option_key] = False

    # Doublage des effectifs (uniquement pour les unités non-héros)
    double_size_key = f"unit_double_{unit['name']}"
    if unit.get("type") != "hero":
        double_size = st.checkbox(
            "Unité combinée (doubler les effectifs)",
            value=st.session_state.get(double_size_key, False),
            key=double_size_key
        )
        st.session_state[double_size_key] = double_size
        multiplier = 2 if double_size else 1
    else:
        multiplier = 1

    # Calcul du coût final
    base_cost = unit.get("base_cost", 0)
    core_cost = (base_cost + weapon_cost) * multiplier
    final_cost = core_cost + upgrades_cost + mount_cost

    # Affichage des informations finales
    if unit.get("type") == "hero":
        st.markdown("**Effectif final : [1]** (héros)")
    else:
        st.markdown(f"**Effectif final : [{unit.get('size', 10) * multiplier}]**")

    if st.button("Ajouter à l'armée"):
        try:
            # Création des données de l'unité
            unit_data = {
                "name": unit["name"],
                "type": unit.get("type", "unit"),
                "cost": final_cost,
                "base_cost": base_cost,
                "size": unit.get("size", 10) * multiplier,
                "quality": unit.get("quality", 3),
                "defense": unit.get("defense", 3),
                "rules": unit.get("special_rules", []),
                "weapon": weapon,
                "options": selected_options,
                "mount": mount,
                "game": st.session_state.game
            }

            # Validation et ajout
            test_army = st.session_state.army_list.copy()
            test_army.append(unit_data)
            test_total = st.session_state.army_cost + final_cost

            if test_total > st.session_state.points:
                st.error("Limite de points dépassée!")
            else:
                st.session_state.army_list.append(unit_data)
                st.session_state.army_cost += final_cost
                st.rerun()

        except Exception as e:
            st.error(f"Erreur: {str(e)}")

    # Affichage de la liste de l'armée
    st.divider()
    st.subheader("Liste de l'armée")
    if not st.session_state.army_list:
        st.info("Ajoutez des unités pour commencer")

    for i, u in enumerate(st.session_state.army_list):
        with st.expander(f"{u['name']} ({u['cost']} pts)"):
            st.markdown(f"**Qualité/Défense**: {u['quality']}+/{u['defense']}+")
            if 'weapon' in u and u['weapon']:
                st.markdown("**Armes:**")
                for w in u['weapon']:
                    st.markdown(f"- {w.get('name', 'Arme')} (A{w.get('attacks', '?')}, PA{w.get('ap', '?')})")

            if u.get("options"):
                for group_name, opts in u["options"].items():
                    st.markdown(f"**{group_name}:** {', '.join(o.get('name', '') for o in opts)}")

            if st.button(f"Supprimer {u['name']}", key=f"del_{i}"):
                st.session_state.army_cost -= u["cost"]
                st.session_state.army_list.pop(i)
                st.rerun()

    # Export
    st.divider()
    st.subheader("Exporter l'armée")
    army_data = {
        "name": st.session_state.list_name,
        "game": st.session_state.game,
        "faction": st.session_state.faction,
        "army_list": st.session_state.army_list
    }

    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "Exporter en JSON",
            json.dumps(army_data, indent=2),
            f"{st.session_state.list_name}.json"
        )
    with col2:
        html = export_html(st.session_state.army_list, st.session_state.list_name, st.session_state.points)
        st.download_button(
            "Exporter en HTML",
            html,
            f"{st.session_state.list_name}.html",
            mime="text/html"
        )
