import json
import streamlit as st
from pathlib import Path
from datetime import datetime
import streamlit.components.v1 as components
import hashlib
import re

# ======================================================
# CONFIGURATION
# ======================================================
st.set_page_config(
    page_title="OPR Army Builder FR - Simon Joinville Fouquet",
    layout="wide",
    initial_sidebar_state="collapsed"
)

BASE_DIR = Path(__file__).resolve().parent
FACTIONS_DIR = BASE_DIR / "lists" / "data" / "factions"
FACTIONS_DIR.mkdir(parents=True, exist_ok=True)

# ======================================================
# OUTILS
# ======================================================
def format_special_rule(rule):
    if not isinstance(rule, str):
        return str(rule)
    if "(" in rule:
        return rule
    match = re.search(r"(.+?)\s*(\d+)$", rule)
    if match:
        return f"{match.group(1)}({match.group(2)})"
    return rule

def extract_coriace_value(rule):
    if not isinstance(rule, str):
        return 0
    match = re.search(r"Coriace\s*\(?(\d+)\)?", rule)
    return int(match.group(1)) if match else 0

def calculate_coriace_from_rules(rules):
    return sum(extract_coriace_value(r) for r in rules if isinstance(r, str))

# ✅ CORRECTION UNIQUE ICI
def calculate_total_coriace(unit_data, combined=False):
    total = 0

    # 1. Règles de base
    total += calculate_coriace_from_rules(unit_data.get("special_rules", []))

    # 2. Monture (JSON OPR : mount → mount → special_rules)
    mount = unit_data.get("mount")
    if mount:
        if isinstance(mount, dict) and "mount" in mount:
            total += calculate_coriace_from_rules(
                mount["mount"].get("special_rules", [])
            )
        elif "special_rules" in mount:
            total += calculate_coriace_from_rules(mount["special_rules"])

    # 3. Options
    for opts in unit_data.get("options", {}).values():
        if isinstance(opts, list):
            for opt in opts:
                total += calculate_coriace_from_rules(opt.get("special_rules", []))

    # 4. Arme
    weapon = unit_data.get("weapon")
    if weapon:
        total += calculate_coriace_from_rules(weapon.get("special_rules", []))

    return total if total > 0 else None

# ======================================================
# LOCAL STORAGE
# ======================================================
def ls_get(key):
    try:
        uid = hashlib.md5(key.encode()).hexdigest()
        components.html(
            f"""
            <script>
            const v = localStorage.getItem("{key}") || "";
            const i = document.createElement("input");
            i.type = "hidden";
            i.id = "{uid}";
            i.value = v;
            document.body.appendChild(i);
            </script>
            """,
            height=0
        )
        return st.text_input("", key=uid, label_visibility="collapsed")
    except Exception:
        return None

def ls_set(key, value):
    if not isinstance(value, str):
        value = json.dumps(value, ensure_ascii=False)
    components.html(
        f"""
        <script>
        localStorage.setItem("{key}", `{value}`);
        </script>
        """,
        height=0
    )

# ======================================================
# CHARGEMENT FACTIONS
# ======================================================
@st.cache_data
def load_factions():
    factions = {}
    games = set()
    for fp in FACTIONS_DIR.glob("*.json"):
        with open(fp, encoding="utf-8") as f:
            data = json.load(f)
            game = data.get("game")
            faction = data.get("faction")
            if game and faction:
                factions.setdefault(game, {})[faction] = data
                games.add(game)
    return factions, sorted(games)

factions_by_game, games = load_factions()

# ======================================================
# SESSION
# ======================================================
if "page" not in st.session_state:
    st.session_state.page = "setup"
    st.session_state.army_list = []
    st.session_state.army_cost = 0

# ======================================================
# PAGE SETUP
# ======================================================
if st.session_state.page == "setup":
    st.title("OPR Army Builder 🇫🇷")

    game = st.selectbox("Jeu", games)
    faction = st.selectbox("Faction", factions_by_game[game].keys())
    points = st.number_input("Points", 250, 5000, 1000, 250)
    name = st.text_input("Nom de la liste", "Nouvelle Liste")

    if st.button("Créer la liste"):
        st.session_state.game = game
        st.session_state.faction = faction
        st.session_state.points = points
        st.session_state.list_name = name
        st.session_state.units = factions_by_game[game][faction]["units"]
        st.session_state.army_list = []
        st.session_state.army_cost = 0
        st.session_state.page = "army"
        st.rerun()

# ======================================================
# PAGE ARMÉE
# ======================================================
elif st.session_state.page == "army":
    st.title(st.session_state.list_name)
    st.caption(
        f"{st.session_state.game} • {st.session_state.faction} • "
        f"{st.session_state.army_cost}/{st.session_state.points} pts"
    )

    unit = st.selectbox(
        "Ajouter une unité",
        st.session_state.units,
        format_func=lambda u: f"{u['name']} ({u['base_cost']} pts)"
    )

    cost = unit["base_cost"]
    weapon = unit.get("weapons", [{}])[0]
    selected_options = {}
    mount = None

    for group in unit.get("upgrade_groups", []):
        st.markdown(f"**{group['group']}**")

        if group["type"] == "weapon":
            choice = st.radio(
                "Arme",
                ["Base"] + [o["name"] for o in group["options"]],
                key=f"{unit['name']}_weapon"
            )
            if choice != "Base":
                opt = next(o for o in group["options"] if o["name"] == choice)
                weapon = opt["weapon"]
                cost += opt["cost"]

        elif group["type"] == "mount":
            choice = st.radio(
                "Monture",
                ["Aucune"] + [o["name"] for o in group["options"]],
                key=f"{unit['name']}_mount"
            )
            if choice != "Aucune":
                mount = next(o for o in group["options"] if o["name"] == choice)
                cost += moun
