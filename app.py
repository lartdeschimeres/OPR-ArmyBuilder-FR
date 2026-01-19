import json
import streamlit as st
from pathlib import Path
from datetime import datetime
import streamlit.components.v1 as components
import hashlib
import re

# ======================================================
# CONFIGURATION POUR SIMON
# ======================================================
st.set_page_config(
    page_title="OPR Army Builder FR - Simon Joinville Fouquet",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Chemins des fichiers
BASE_DIR = Path(__file__).resolve().parent
FACTIONS_DIR = BASE_DIR / "lists" / "data" / "factions"
FACTIONS_DIR.mkdir(parents=True, exist_ok=True)

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

def calculate_coriace_from_rules(rules):
    if not rules or not isinstance(rules, list):
        return 0
    return sum(extract_coriace_value(r) for r in rules)

def calculate_total_coriace(unit_data, combined=False):
    """
    CORRECTION :
    La Coriace de la monture est lue depuis
    unit_data["mount"]["mount"]["special_rules"]
    conformément au JSON.
    """
    total = 0

    # 1. Règles de base
    total += calculate_coriace_from_rules(
        unit_data.get("special_rules", [])
    )

    # 2. Monture (CORRECTION ICI)
    mount = unit_data.get("mount")
    if isinstance(mount, dict):
        if "mount" in mount and isinstance(mount["mount"], dict):
            total += calculate_coriace_from_rules(
                mount["mount"].get("special_rules", [])
            )
        else:
            total += calculate_coriace_from_rules(
                mount.get("special_rules", [])
            )

    # 3. Options
    for opts in unit_data.get("options", {}).values():
        if isinstance(opts, list):
            for opt in opts:
                total += calculate_coriace_from_rules(
                    opt.get("special_rules", [])
                )

    # 4. Arme
    total += calculate_coriace_from_rules(
        unit_data.get("weapon", {}).get("special_rules", [])
    )

    # 5. Unité combinée (pas pour héros)
    if combined and unit_data.get("type", "").lower() != "hero":
        total += calculate_coriace_from_rules(
            unit_data.get("special_rules", [])
        )

    return total if total > 0 else None

# ======================================================
# LOCAL STORAGE
# ======================================================
def ls_get(key):
    try:
        unique_key = f"{key}_{hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()[:8]}"
        components.html(
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
            height=0
        )
        return st.text_input("", key=unique_key, label_visibility="collapsed")
    except Exception:
        return None

def ls_set(key, value):
    if not isinstance(value, str):
        value = json.dumps(value)
    components.html(
        f"""
        <script>
        localStorage.setItem("{key}", `{value}`);
        </script>
        """,
        height=0
    )

# ======================================================
# CHARGEMENT DES FACTIONS
# ======================================================
@st.cache_data
def load_factions():
    factions = {}
    games = set()

    for fp in FACTIONS_DIR.glob("*.json"):
        with open(fp, encoding="utf-8") as f:
            data = json.load(f)
            factions.setdefault(data["game"], {})[data["faction"]] = data
            games.add(data["game"])

    return factions, sorted(games)

# ======================================================
# INITIALISATION
# ======================================================
factions_by_game, games = load_factions()

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
    list_name = st.text_input("Nom de la liste")

    if st.button("Créer une nouvelle liste"):
        st.session_state.game = game
        st.session_state.faction = faction
        st.session_state.points = points
        st.session_state.list_name = list_name
        st.session_state.units = factions_by_game[game][faction]["units"]
        st.session_state.page = "army"
        st.rerun()

# ======================================================
# PAGE ARMY
# ======================================================
else:
    st.title(st.session_state.list_name)
    st.caption(f"{st.session_state.game} • {st.session_state.faction}")

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
        if group["type"] == "mount":
            names = ["Aucune"] + [o["name"] for o in group["options"]]
            choice = st.radio("Monture", names)
            if choice != "Aucune":
                opt = next(o for o in group["options"] if o["name"] == choice)
                mount = opt
                cost += opt["cost"]

    total_coriace = calculate_total_coriace({
        "special_rules": unit.get("special_rules", []),
        "weapon": weapon,
        "options": selected_options,
        "mount": mount,
        "type": unit.get("type", "")
    })

    st.markdown(f"**Coût : {cost} pts**")

    if st.button("Ajouter"):
        st.session_state.army_list.append({
            "name": unit["name"],
            "cost": cost,
            "quality": unit["quality"],
            "defense": unit["defense"],
            "rules": unit
