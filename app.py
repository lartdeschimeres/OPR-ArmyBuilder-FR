import json
import streamlit as st
from pathlib import Path
from datetime import datetime
import re
import math

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
        "Age of Fantasy Regiments": {
        "image": BASE_DIR / "assets/games/aofr_cover.jpg",
        "description": "Fantasy en régiment"
    },
}

st.set_page_config(
    page_title="OPR Army Forge FR",
    layout="wide",
    initial_sidebar_state="collapsed"
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

# ======================================================
# CONFIGURATION DES JEUX
# ======================================================
GAME_CONFIG = {
    "Age of Fantasy": {
        "max_points": 10000,
        "min_points": 250,
        "default_points": 1000,
        "hero_limit": 375,  # 1 héros par 375pts
        "unit_copy_rule": 750,
        "unit_max_cost_ratio": 0.35,  # 35% du total
        "unit_per_points": 150
    },
    "Grimdark Future": {
        "max_points": 10000,
        "min_points": 250,
        "default_points": 1000,
        "hero_limit": 375,
        "unit_copy_rule": 750,
        "unit_max_cost_ratio": 0.35,
        "unit_per_points": 150
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
def format_weapon_details(weapon):
    if not weapon:
        return {"name": "Arme non spécifiée", "attacks": "?", "ap": "?", "special": []}
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
        name_part += f" [{u.get('size', 10)}]"
    qua_def = f"Qua {u['quality']}+ / Déf {u.get('defense', '?')}"
    result = f"{name_part} - {qua_def} {u['base_cost']}pts"
    return result

# ======================================================
# EXPORT HTML
# ======================================================
def export_html(army_list, army_name, army_limit):
    def esc(txt):
        return str(txt).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # Trier la liste pour afficher les héros en premier
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
  page-break-inside: avoid;
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

.rules div {{
  margin-bottom: 6px;
  color: var(--text-main);
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
        weapons = unit.get("weapon", [])
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
            # Pour les héros, n'afficher que l'arme de remplacement si elle existe
            if unit.get("type", "").lower() == "hero":
                # Trouver l'arme de remplacement (si elle existe)
                replacement_weapon = None
                for w in weapons:
                    if w.get("name") != "Arme de base" and w.get("name") != "Arme à une main lourde":
                        replacement_weapon = w
                        break

                # Si une arme de remplacement existe, n'afficher que celle-ci
                if replacement_weapon:
                    w = replacement_weapon
                    html += f"""
<tr>
  <td>{esc(w.get('name', '-'))}</td>
  <td>{esc(w.get('range', '-'))}</td>
  <td>{esc(w.get('attacks', '-'))}</td>
  <td>{esc(w.get('ap', '-'))}</td>
  <td>{esc(", ".join(w.get('special', [])) if w.get('special') else '-')}</td>
</tr>
"""
                else:
                    # Sinon, afficher toutes les armes de base
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
            else:
                # Pour les unités normales, afficher toutes les armes
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
            html += "<div>" + ", ".join(f"<span style='font-size: 12px;'>{esc(r)}</span>" for r in rules) + "</div>"
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

    # ---- SORTS DE LA FACTION (en dehors des unités, en une seule colonne) ----
    if 'faction' in st.session_state:
        faction_data = factions_by_game.get(st.session_state.game, {}).get(st.session_state.faction, {})
        if 'spells' in faction_data:
            spells = faction_data['spells']
            if spells:
                html += """
                <div style="margin-top: 40px;">
                    <h3 style="text-align: center; color: var(--accent); border-top: 1px solid var(--border); padding-top: 10px; margin-bottom: 15px;">
                        Sorts de la faction
                    </h3>
                    <div style="display: flex; flex-direction: column; font-size: 12px; margin-bottom: 20px; max-width: 100%;">
                        <div style="flex: 1; padding: 0 10px; width: 100%;">
                """

                # Utilise directement les clés du dictionnaire `spells` sans trier
                spell_names = spells.keys()

                # Afficher chaque sort en une seule colonne, dans l'ordre du JSON
                for spell_name in spell_names:
                    spell_info = spells[spell_name]
                    cost = spell_info.get('cost', '?')
                    description = spell_info.get('description', '')
                    html += f"""
                    <div style="margin-bottom: 12px; line-height: 1.4; width: 100%;">
                        <strong>{esc(spell_name)} [{cost}]</strong>: {esc(description)}
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
</html>"""
    return html

# ======================================================
# CHARGEMENT DES FACTIONS
# ======================================================
@st.cache_data
def load_factions():
    factions = {}
    games = set()
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
                    factions[game][faction] = data
                    games.add(game)
        except Exception as e:
            st.warning(f"Erreur chargement {fp.name}: {e}")
    return factions, sorted(games) if games else list(GAME_CONFIG.keys())

# ======================================================
# PAGE 1 – CONFIGURATION
# ======================================================
if st.session_state.page == "setup":
    st.title("OPR Army Forge - Configuration")

    factions_by_game, games = load_factions()
    if not games:
        st.error("Aucun jeu trouvé")
        st.stop()

    game = st.selectbox("Jeu", games)
    faction = st.selectbox("Faction", factions_by_game[game].keys())
    points = st.number_input("Points", min_value=250, max_value=10000, value=1000)
    list_name = st.text_input("Nom de la liste", f"Liste_{datetime.now().strftime('%Y%m%d')}")

    if st.button("Construire l'armée"):
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
    st.title(f"{st.session_state.list_name} - {st.session_state.army_cost}/{st.session_state.points} pts")

    if st.button("Retour à la configuration"):
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

    # Initialisation de la structure de sélection pour cette unité
    unit_key = f"unit_{unit['name']}"
    if unit_key not in st.session_state.unit_selections:
        st.session_state.unit_selections[unit_key] = {}

    # Traitement des améliorations
    for group_idx, group in enumerate(unit.get("upgrade_groups", [])):
        group_key = f"group_{group_idx}"
        st.subheader(group['group'])

        if group["type"] == "weapon":
            # Boutons radio pour les armes (choix unique)
            weapon_options = ["Arme de base"]
            for o in group["options"]:
                weapon_details = format_weapon_details(o["weapon"])
                weapon_options.append(f"{o['name']} (+{o['cost']} pts)")

            current_selection = st.session_state.unit_selections[unit_key].get(group_key, weapon_options[0])
            selected_weapon = st.radio(
                "Sélectionnez une arme",
                weapon_options,
                index=weapon_options.index(current_selection) if current_selection in weapon_options else 0,
                key=f"{unit_key}_{group_key}_weapon"
            )

            st.session_state.unit_selections[unit_key][group_key] = selected_weapon

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
            # Boutons radio pour les montures
            mount_options = ["Aucune monture"]
            mount_map = {}
            for o in group["options"]:
                mount_options.append(f"{o['name']} (+{o['cost']} pts)")
                mount_map[f"{o['name']} (+{o['cost']} pts)"] = o

            current_selection = st.session_state.unit_selections[unit_key].get(group_key, mount_options[0])
            selected_mount = st.radio(
                "Sélectionnez une monture",
                mount_options,
                index=mount_options.index(current_selection) if current_selection in mount_options else 0,
                key=f"{unit_key}_{group_key}_mount"
            )

            st.session_state.unit_selections[unit_key][group_key] = selected_mount

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

                current_selection = st.session_state.unit_selections[unit_key].get(group_key, option_labels[0])
                selected = st.radio(
                    f"Amélioration – {group['group']}",
                    option_labels,
                    index=option_labels.index(current_selection) if current_selection in option_labels else 0,
                    key=f"{unit_key}_{group_key}_hero"
                )

                st.session_state.unit_selections[unit_key][group_key] = selected

                if selected != "Aucune amélioration":
                    opt = option_map.get(selected)
                    if opt:
                        selected_options[group['group']] = [opt]
                        upgrades_cost += opt["cost"]
            else:
                for o in group["options"]:
                    option_key = f"{o['name']}"
                    if option_key not in st.session_state.unit_selections[unit_key]:
                        st.session_state.unit_selections[unit_key][option_key] = False

                    if st.checkbox(
                        f"{o['name']} (+{o['cost']} pts)",
                        value=st.session_state.unit_selections[unit_key][option_key],
                        key=f"{unit_key}_{group_key}_{option_key}"
                    ):
                        st.session_state.unit_selections[unit_key][option_key] = True
                        selected_options.setdefault(group["group"], []).append(o)
                        upgrades_cost += o["cost"]
                    else:
                        st.session_state.unit_selections[unit_key][option_key] = False

    # Doublage des effectifs (UNIQUEMENT pour les unités non-héros)
    if unit.get("type") != "hero":
        double_size = st.checkbox("Unité combinée (doubler les effectifs)")
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
            unit_data = {
                "name": unit["name"],
                "type": unit.get("type", "unit"),
                "cost": final_cost,
                "base_cost": base_cost,
                "size": unit.get("size", 10) * multiplier if unit.get("type") != "hero" else 1,
                "quality": unit.get("quality", 3),
                "defense": unit.get("defense", 3),
                "rules": unit.get("special_rules", []),
                "weapon": weapon,
                "options": selected_options,
                "mount": mount,
                "game": st.session_state.game
            }

            # Validation des règles
            test_army = st.session_state.army_list.copy()
            test_army.append(unit_data)
            test_total = st.session_state.army_cost + final_cost

            if test_total > st.session_state.points:
                st.error(f"Limite de points dépassée! ({st.session_state.points} pts max)")
            elif not validate_army_rules(test_army, st.session_state.points, st.session_state.game):
                pass  # Les erreurs sont déjà affichées par les fonctions de validation
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
            json.dumps(army_data, indent=2, ensure_ascii=False),
            f"{st.session_state.list_name}.json"
        )
    with col2:
        html = f"""<!DOCTYPE html>
<html>
<head>
<style>
body {{ background: #2e2f2b; color: #e6e6e6; font-family: Arial; }}
.unit {{ background: #3a3c36; padding: 15px; margin-bottom: 20px; border-radius: 5px; }}
</style>
</head>
<body>
<h1>{st.session_state.list_name}</h1>
"""
        for unit in st.session_state.army_list:
            html += f"""
<div class="unit">
<h2>{unit['name']} [{unit['size']}] - {unit['cost']} pts</h2>
<p>Qualité {unit['quality']}+ / Défense {unit['defense']}+</p>
"""
            if 'weapon' in unit and unit['weapon']:
                html += "<h3>Armes:</h3><ul>"
                for w in unit['weapon']:
                    html += f"<li>{w.get('name', 'Arme')} (A{w.get('attacks', '?')}, PA{w.get('ap', '?')})</li>"
                html += "</ul>"
            html += "</div>"
        html += "</body></html>"

        st.download_button(
            "Exporter en HTML",
            html,
            f"{st.session_state.list_name}.html",
            mime="text/html"
        )
