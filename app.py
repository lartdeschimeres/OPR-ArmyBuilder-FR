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
    page_title="OPR Army Builder FR",
    layout="wide",
    initial_sidebar_state="collapsed"
)

BASE_DIR = Path(__file__).resolve().parent
FACTIONS_DIR = BASE_DIR / "lists" / "data" / "factions"
FACTIONS_DIR.mkdir(parents=True, exist_ok=True)

# ======================================================
# OUTILS RÈGLES
# ======================================================
def format_special_rule(rule):
    if not isinstance(rule, str):
        return str(rule)
    if "(" in rule:
        return rule
    m = re.search(r"(.*?)(\d+)", rule)
    return f"{m.group(1)}({m.group(2)})" if m else rule

def extract_coriace_value(rule):
    if not isinstance(rule, str):
        return 0
    m = re.search(r"Coriace\s*\(?(\d+)\)?", rule)
    return int(m.group(1)) if m else 0

def calculate_coriace_from_rules(rules):
    return sum(extract_coriace_value(r) for r in rules or [])

# ======================================================
# 🔧 CORRECTION UNIQUE ICI
# ======================================================
def calculate_total_coriace(unit_data, combined=False):
    total = 0

    # Règles de base (héros compris)
    total += calculate_coriace_from_rules(unit_data.get("special_rules", []))

    # Monture (structure : opt["mount"])
    mount_opt = unit_data.get("mount")
    if mount_opt and isinstance(mount_opt, dict):
        mount_data = mount_opt.get("mount")
        if mount_data:
            total += calculate_coriace_from_rules(mount_data.get("special_rules", []))

    # Options
    for opts in unit_data.get("options", {}).values():
        for opt in opts:
            total += calculate_coriace_from_rules(opt.get("special_rules", []))

    # Arme
    weapon = unit_data.get("weapon")
    if weapon:
        total += calculate_coriace_from_rules(weapon.get("special_rules", []))

    # Unité combinée (pas héros)
    if combined and unit_data.get("type", "").lower() != "hero":
        total += calculate_coriace_from_rules(unit_data.get("special_rules", []))

    return total if total > 0 else None

# ======================================================
# LOCAL STORAGE
# ======================================================
def ls_get(key):
    uid = f"{key}_{hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]}"
    components.html(
        f"""
        <script>
        const v = localStorage.getItem("{key}") || "";
        const i = document.createElement("input");
        i.type="hidden"; i.id="{uid}"; i.value=v;
        document.body.appendChild(i);
        </script>
        """,
        height=0
    )
    return st.text_input("", key=uid, label_visibility="collapsed")

def ls_set(key, value):
    components.html(
        f"<script>localStorage.setItem('{key}', `{json.dumps(value, ensure_ascii=False)}`);</script>",
        height=0
    )

# ======================================================
# CHARGEMENT DES FACTIONS
# ======================================================
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

# ======================================================
# ÉTAT
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

    saved = ls_get("opr_lists")
    if saved:
        lists = json.loads(saved)
        for i, l in enumerate(lists):
            if st.button(f"📂 {l['name']} ({l['total_cost']} pts)", key=f"load{i}"):
                st.session_state.update(l)
                st.session_state.page = "army"
                st.rerun()

    game = st.selectbox("Jeu", games)
    faction = st.selectbox("Faction", factions_by_game[game].keys())
    points = st.number_input("Points", 250, 5000, 1000, 250)
    name = st.text_input("Nom de la liste")

    if st.button("Créer"):
        st.session_state.update({
            "game": game,
            "faction": faction,
            "points": points,
            "list_name": name,
            "army_list": [],
            "army_cost": 0,
            "units": factions_by_game[game][faction]["units"]
        })
        st.session_state.page = "army"
        st.rerun()

# ======================================================
# PAGE ARMÉE
# ======================================================
else:
    st.title(st.session_state.list_name)
    st.caption(f"{st.session_state.army_cost}/{st.session_state.points} pts")

    unit = st.selectbox(
        "Ajouter une unité",
        st.session_state.units,
        format_func=lambda u: f"{u['name']} ({u['base_cost']} pts)"
    )

    cost = unit["base_cost"]
    weapon = unit["weapons"][0]
    options, mount = {}, None
    combined = False

    if unit["type"].lower() != "hero":
        combined = st.checkbox("Unité combinée")
        if combined:
            cost *= 2

    for g in unit.get("upgrade_groups", []):
        st.subheader(g["group"])

        if g["type"] == "weapon":
            choice = st.radio("Arme", ["Base"] + [o["name"] for o in g["options"]])
            if choice != "Base":
                opt = next(o for o in g["options"] if o["name"] == choice)
                weapon = opt["weapon"]
                cost += opt["cost"]

        elif g["type"] == "mount":
            choice = st.radio("Monture", ["Aucune"] + [o["name"] for o in g["options"]])
            if choice != "Aucune":
                mount = next(o for o in g["options"] if o["name"] == choice)
                cost += mount["cost"]

        else:
            sel = []
            for o in g["options"]:
                if st.checkbox(o["name"]):
                    sel.append(o)
                    cost += o["cost"]
            if sel:
                options[g["group"]] = sel

    coriace = calculate_total_coriace({
        "special_rules": unit.get("special_rules", []),
        "mount": mount,
        "options": options,
        "weapon": weapon,
        "type": unit["type"]
    }, combined)

    st.markdown(f"**Coût : {cost} pts**")

    if st.button("Ajouter à l'armée"):
        st.session_state.army_list.append({
            "name": unit["name"],
            "cost": cost,
            "quality": unit["quality"],
            "defense": unit["defense"],
            "special_rules": unit.get("special_rules", []),
            "weapon": weapon,
            "options": options,
            "mount": mount,
            "coriace": coriace,
            "type": unit["type"],
            "combined": combined
        })
        st.session_state.army_cost += cost
        st.rerun()

    st.divider()
    for i, u in enumerate(st.session_state.army_list):
        st.subheader(f"{u['name']} – {u['cost']} pts")
        st.write(f"Qua {u['quality']}+ / Déf {u['defense']}+")
        if u.get("coriace"):
            st.success(f"Coriace {u['coriace']}")

        if st.button("❌ Supprimer", key=f"del{i}"):
            st.session_state.army_cost -= u["cost"]
            st.session_state.army_list.pop(i)
            st.rerun()

    if st.button("💾 Sauvegarder"):
        saved = json.loads(ls_get("opr_lists") or "[]")
        saved.append({
            "name": st.session_state.list_name,
            "game": st.session_state.game,
            "faction": st.session_state.faction,
            "points": st.session_state.points,
            "total_cost": st.session_state.army_cost,
            "army_list": st.session_state.army_list
        })
        ls_set("opr_lists", saved)
        st.success("Liste sauvegardée")
