import json
import streamlit as st
from pathlib import Path
from datetime import datetime
import hashlib
import re
import base64
import math

# ======================================================
# SESSION STATE – Initialisation
# ======================================================
if "page" not in st.session_state:
    st.session_state.page = "setup"
if "army_list" not in st.session_state:
    st.session_state.army_list = []
if "army_cost" not in st.session_state:
    st.session_state.army_cost = 0
if "widget_counter" not in st.session_state:
    st.session_state.widget_counter = 0  # Compteur pour les clés uniques

# ======================================================
# SIDEBAR – CONTEXTE & NAVIGATION (inchangé)
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
# CONFIGURATION DES JEUX (inchangée)
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
# FONCTIONS UTILITAIRES (inchangées)
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

# ======================================================
# EXPORT HTML (inchangé)
# ======================================================
def export_html(army_list, army_name, army_limit):
    def esc(txt):
        return str(txt).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    sorted_army_list = sorted(army_list, key=lambda x: 0 if x.get("type") == "hero" else 1)
    html = f"""<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"><title>Liste d'Armée OPR - {esc(army_name)}</title><style>:root{{--bg-main: #2e2f2b;--bg-card: #3a3c36;--accent: #9fb39a;--text-main: #e6e6e6;}}body{{background: var(--bg-main);color: var(--text-main);font-family: "Segoe UI", Roboto, Arial, sans-serif;margin: 0;padding: 20px;}}.unit-card{{background: var(--bg-card);border: 1px solid #555;margin-bottom: 20px;padding: 16px;border-radius: 8px;}}</style></head><body><div style="max-width: 1100px; margin: auto;"><h1 style="text-align: center; color: #9fb39a; margin-bottom: 20px;">{esc(army_name)} - {sum(unit['cost'] for unit in sorted_army_list)}/{army_limit} pts</h1>"""
    for unit in sorted_army_list:
        name = esc(unit.get("name", "Unité"))
        cost = unit.get("cost", 0)
        quality = esc(unit.get("quality", "-"))
        defense = esc(unit.get("defense", "-"))
        coriace = unit.get("coriace")
        unit_size = unit.get("size", 10)
        if unit.get("type", "").lower() == "hero":
            unit_size = 1
        html += f"""<div class="unit-card"><h2 style="margin-top: 0; color: #9fb39a;">{name} [{unit_size}] - {cost} pts</h2><div style="margin-bottom: 10px;">"""
        if coriace and coriace > 0:
            html += f"""<span style="background: #6e7f6a; padding: 4px 8px; border-radius: 4px; margin-right: 6px;">Coriace {coriace}</span>"""
        html += f"""<span style="background: #6e7f6a; padding: 4px 8px; border-radius: 4px; margin-right: 6px;">Qualité {quality}+</span><span style="background: #6e7f6a; padding: 4px 8px; border-radius: 4px;">Défense {defense}+</span></div>"""
        weapons = unit.get("weapon", [])
        if weapons:
            if not isinstance(weapons, list):
                weapons = [weapons]
            html += "<h3 style='margin-top: 15px;'>Armes équipées :</h3><ul style='margin-top: 5px; padding-left: 20px;'>"
            for w in weapons:
                html += f"<li style='margin-bottom: 5px;'>{esc(w.get('name', '-'))} (A{w.get('attacks', '-')}, PA{w.get('ap', '-')})</li>"
            html += "</ul>"
        rules = unit.get("rules", [])
        if rules:
            html += f"<div style='margin-top: 15px;'><strong>Règles spéciales :</strong> {', '.join(esc(r) for r in rules)}</div>"
        options = unit.get("options", {})
        if options:
            html += "<h3 style='margin-top: 15px;'>Options :</h3><ul style='margin-top: 5px; padding-left: 20px;'>"
            for group_name, opts in options.items():
                if isinstance(opts, list) and opts:
                    html += f"<li style='margin-bottom: 5px;'><strong>{esc(group_name)}:</strong> {', '.join(esc(opt.get('name', '')) for opt in opts)}</li>"
            html += "</ul>"
        mount = unit.get("mount")
        if mount:
            html += f"<h3 style='margin-top: 15px;'>Monture :</h3><p style='margin-top: 5px;'>{esc(mount.get('name', 'Aucune'))}</p>"
        html += "</div>"
    html += "</div></body></html>"
    return html

# ======================================================
# CHARGEMENT DES FACTIONS (inchangé)
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
# INITIALISATION SESSION STATE (inchangée)
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
# PAGE 1 – CONFIGURATION (inchangée)
# ======================================================
if st.session_state.page == "setup":
    st.title("OPR Army Forge")
    # ... (ton code existant pour la page de setup)
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
# PAGE 2 – CONSTRUCTEUR D'ARMÉE (UNIQUEMENT cette partie modifiée)
# ======================================================
elif st.session_state.page == "army":
    st.markdown(
        f"""
        <div style="background: #2e2f2b; padding: 15px; border-radius: 8px; margin-bottom: 20px; color: white;">
            <h2 style="margin: 0;">{st.session_state.list_name}</h2>
            <p style="margin: 5px 0;">{st.session_state.army_cost} / {st.session_state.points} pts</p>
        </div>
        """,
        unsafe_allow_html=True
    )

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

    # Boucle des groupes d'améliorations (UNIQUEMENT cette partie modifiée)
    for group in unit.get("upgrade_groups", []):
        st.session_state.widget_counter += 1
        unique_key = f"{unit['name']}_{st.session_state.widget_counter}"

        st.markdown(f"**{group['group']}**")

        if group["type"] == "weapon":
            # Boutons radio pour les armes (choix unique - Cavaliers Barbares)
            weapon_options = ["Arme de base"]
            for o in group["options"]:
                weapon_details = format_weapon_details(o["weapon"])
                weapon_options.append(
                    f"{o['name']} (A{weapon_details['attacks']}, PA({weapon_details['ap']})"
                    f"{', ' + ', '.join(weapon_details['special']) if weapon_details['special'] else ''}) "
                    f"(+{o['cost']} pts)"
                )
            if f"{unique_key}_weapon" not in st.session_state:
                st.session_state[f"{unique_key}_weapon"] = weapon_options[0]
            selected_weapon = st.radio(
                "Arme",
                weapon_options,
                key=f"{unique_key}_weapon",
                index=weapon_options.index(st.session_state[f"{unique_key}_weapon"])
            )
            st.session_state[f"{unique_key}_weapon"] = selected_weapon
            if selected_weapon != weapon_options[0]:
                opt_name = selected_weapon.split(" (")[0]
                opt = next((o for o in group["options"] if o["name"] == opt_name), None)
                if opt:
                    if unit.get("type", "").lower() == "hero":
                        weapon = [opt["weapon"]]  # Remplacement total pour les héros
                    else:
                        weapon = unit.get("weapons", []) + [opt["weapon"]]  # Ajout pour les unités
                    weapon_cost += opt["cost"]

        elif group["type"] == "mount":
            # Boutons radio pour les montures (inchangé)
            mount_labels = ["Aucune monture"]
            mount_map = {}
            for o in group["options"]:
                mount_details = format_mount_details(o)
                label = f"{mount_details} (+{o['cost']} pts)"
                mount_labels.append(label)
                mount_map[label] = o
            if f"{unique_key}_mount" not in st.session_state:
                st.session_state[f"{unique_key}_mount"] = mount_labels[0]
            selected_mount = st.radio(
                "Monture",
                mount_labels,
                key=f"{unique_key}_mount",
                index=mount_labels.index(st.session_state[f"{unique_key}_mount"])
            )
            st.session_state[f"{unique_key}_mount"] = selected_mount
            if selected_mount != mount_labels[0]:
                mount = mount_map[selected_mount.split(" (+")[0]]
                mount_cost += mount["cost"]

        else:
            # Checkboxes pour les améliorations (choix multiples - inchangé)
            if unit.get("type", "").lower() == "hero":
                option_labels = ["Aucune amélioration"]
                option_map = {}
                for o in group["options"]:
                    option_labels.append(f"{o['name']} (+{o['cost']} pts)")
                    option_map[f"{o['name']} (+{o['cost']} pts)"] = o
                if f"{unique_key}_hero" not in st.session_state:
                    st.session_state[f"{unique_key}_hero"] = option_labels[0]
                selected = st.radio(
                    f"Amélioration – {group['group']}",
                    option_labels,
                    key=f"{unique_key}_hero",
                    index=option_labels.index(st.session_state[f"{unique_key}_hero"])
                )
                st.session_state[f"{unique_key}_hero"] = selected
                if selected != option_labels[0]:
                    opt = option_map[selected]
                    selected_options[group['group']] = [opt]
                    upgrades_cost += opt["cost"]
            else:
                st.write("Améliorations (choix multiples):")
                for o in group["options"]:
                    option_key = f"{unique_key}_{o['name']}"
                    if option_key not in st.session_state:
                        st.session_state[option_key] = False
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

    # Doublage des effectifs (UNIQUEMENT pour les unités, PAS pour les héros)
    if unit.get("type") != "hero":
        double_size = st.checkbox(
            "Unité combinée (doubler les effectifs)",
            value=False,
            key=f"{unique_key}_double"
        )
        multiplier = 2 if double_size else 1
    else:
        double_size = False
        multiplier = 1

    # ... (reste du code inchangé : calcul des coûts, ajout à l'armée, etc.)
