# ===========================
# IMPORTS
# ===========================
import json
import streamlit as st
from pathlib import Path
from datetime import datetime
import streamlit.components.v1 as components
import hashlib
import re

# ===========================
# CONFIGURATION
# ===========================
st.set_page_config(
    page_title="OPR Army Builder FR - Simon Joinville Fouquet",
    layout="wide",
    initial_sidebar_state="collapsed"
)

BASE_DIR = Path(__file__).resolve().parent
FACTIONS_DIR = BASE_DIR / "lists" / "data" / "factions"
FACTIONS_DIR.mkdir(parents=True, exist_ok=True)

# ===========================
# FONCTIONS UTILITAIRES
# ===========================
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
    return int(match.group(1)) if match else 0

def get_coriace_from_rules(rules):
    if not rules or not isinstance(rules, list):
        return 0
    return sum(extract_coriace_value(r) for r in rules)

def get_mount_details(mount):
    if not mount:
        return None, 0
    mount_data = mount.get("mount", mount)
    rules = mount_data.get("special_rules", [])
    return rules, get_coriace_from_rules(rules)

def calculate_total_coriace(unit):
    total = get_coriace_from_rules(unit.get("special_rules", []))
    if unit.get("mount"):
        _, mc = get_mount_details(unit["mount"])
        total += mc
    for opts in unit.get("options", {}).values():
        for o in opts:
            total += get_coriace_from_rules(o.get("special_rules", []))
    total += get_coriace_from_rules(unit.get("weapon", {}).get("special_rules", []))
    return total or None

def format_weapon_details(w):
    return f"A{w.get('attacks','?')}, AP({w.get('armor_piercing','?')})" + (
        ", " + ", ".join(w["special_rules"]) if w.get("special_rules") else ""
    )

def format_mount_details(m):
    if not m:
        return "Aucune monture"
    md = m.get("mount", m)
    txt = m.get("name", "")
    if md.get("special_rules"):
        txt += " | " + ", ".join(md["special_rules"])
    return txt

# ===========================
# CHARGEMENT FACTIONS
# ===========================
@st.cache_data
def load_factions():
    factions, games = {}, set()
    for fp in FACTIONS_DIR.glob("*.json"):
        with open(fp, encoding="utf-8") as f:
            data = json.load(f)
            factions.setdefault(data["game"], {})[data["faction"]] = data
            games.add(data["game"])
    return factions, sorted(games)

factions_by_game, games = load_factions()

# ===========================
# SESSION
# ===========================
if "page" not in st.session_state:
    st.session_state.page = "setup"
    st.session_state.army_list = []
    st.session_state.army_cost = 0

# ===========================
# PAGE SETUP
# ===========================
if st.session_state.page == "setup":
    st.title("OPR Army Builder FR")
    game = st.selectbox("Jeu", games)
    faction = st.selectbox("Faction", factions_by_game[game])
    points = st.number_input("Points", 250, 5000, 1000, 250)
    name = st.text_input("Nom de la liste", "Nouvelle Liste")

    if st.button("Créer"):
        st.session_state.update({
            "page": "army",
            "game": game,
            "faction": faction,
            "points": points,
            "list_name": name,
            "units": factions_by_game[game][faction]["units"],
            "army_list": [],
            "army_cost": 0
        })
        st.rerun()

# ===========================
# PAGE ARMY
# ===========================
else:
    st.title(st.session_state.list_name)
    st.caption(f"{st.session_state.army_cost}/{st.session_state.points} pts")

    unit = st.selectbox("Unité", st.session_state.units, format_func=lambda u: u["name"])

    base_cost = unit["base_cost"]
    weapon = unit.get("weapons", [{}])[0]
    weapon_cost = 0
    mount = None
    mount_cost = 0
    options = {}
    upgrades_cost = 0

    for g in unit.get("upgrade_groups", []):
        if g["type"] == "weapon":
            sel = st.radio("Weapon", ["Base"] + [o["name"] for o in g["options"]])
            for o in g["options"]:
                if o["name"] == sel:
                    weapon = o["weapon"]
                    weapon_cost = o["cost"]

    cost = base_cost + weapon_cost + mount_cost + upgrades_cost

    coriace = calculate_total_coriace({
        "special_rules": unit.get("special_rules", []),
        "weapon": weapon,
        "mount": mount,
        "options": options
    })

    if st.button("Ajouter"):
        st.session_state.army_list.append({
            "name": unit["name"],
            "cost": cost,
            "quality": unit["quality"],
            "defense": unit["defense"],
            "rules": unit.get("special_rules", []),
            "weapon": weapon,
            "weapons": unit.get("weapons", []),
            "options": options,
            "mount": mount,
            "coriace": coriace
        })
        st.session_state.army_cost += cost
        st.rerun()

    # ===========================
    # EXPORT HTML FICHE (MODIFIÉ UNIQUEMENT ICI)
    # ===========================
    html = "<html><body>"

    for u in st.session_state.army_list:
        rows = ""

        # ==== CORRECTION UNIQUE ====
        if u.get("weapon"):
            w = u["weapon"]
            rows += f"""
            <tr>
                <td>{w.get('name','')}</td>
                <td>-</td>
                <td>A{w.get('attacks','')}</td>
                <td>{w.get('armor_piercing','')}</td>
                <td>{", ".join(w.get("special_rules",[]))}</td>
            </tr>
            """
        else:
            for w in u.get("weapons", []):
                rows += f"""
                <tr>
                    <td>{w.get('name','')}</td>
                    <td>-</td>
                    <td>A{w.get('attacks','')}</td>
                    <td>{w.get('armor_piercing','')}</td>
                    <td>{", ".join(w.get("special_rules",[]))}</td>
                </tr>
                """

        html += f"""
        <h2>{u['name']} ({u['cost']} pts)</h2>
        <table border="1">
            <tr><th>Name</th><th>RNG</th><th>ATK</th><th>AP</th><th>SPE</th></tr>
            {rows}
        </table>
        """

    html += "</body></html>"

    st.download_button("Export Fiches Unités", html, "fiches.html", "text/html")
