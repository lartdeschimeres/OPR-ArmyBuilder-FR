import json
import re
from pathlib import Path
import streamlit as st

# -------------------------------------------------
# CONFIG
# -------------------------------------------------
st.set_page_config(page_title="OPR Army Builder FR", layout="centered")

BASE_DIR = Path(__file__).resolve().parent
FACTIONS_DIR = BASE_DIR / "lists" / "data" / "factions"

# -------------------------------------------------
# OUTILS
# -------------------------------------------------
def extract_coriace(rules):
    value = 0
    for r in rules:
        if isinstance(r, str):
            m = re.search(r"Coriace\s*\((\d+)\)", r)
            if m:
                value += int(m.group(1))
    return value

def calculate_coriace(unit):
    total = extract_coriace(unit.get("base_rules", []))

    for opt in unit.get("options", {}).values():
        if isinstance(opt, list):
            for o in opt:
                total += extract_coriace(o.get("special_rules", []))
        elif isinstance(opt, dict):
            total += extract_coriace(opt.get("special_rules", []))

    if unit.get("mount"):
        total += extract_coriace(unit["mount"].get("special_rules", []))

    return total

# -------------------------------------------------
# SESSION INIT
# -------------------------------------------------
if "page" not in st.session_state:
    st.session_state.page = "setup"
if "army_list" not in st.session_state:
    st.session_state.army_list = []
if "army_total_cost" not in st.session_state:
    st.session_state.army_total_cost = 0

# -------------------------------------------------
# CHARGEMENT FACTIONS
# -------------------------------------------------
@st.cache_data
def load_factions():
    factions = {}
    games = set()

    for fp in FACTIONS_DIR.glob("*.json"):
        with open(fp, encoding="utf-8") as f:
            data = json.load(f)
            game = data["game"]
            factions.setdefault(game, {})
            factions[game][data["faction"]] = data
            games.add(game)

    return factions, sorted(games)

factions, games = load_factions()

# =================================================
# PAGE SETUP
# =================================================
if st.session_state.page == "setup":
    st.title("OPR Army Builder 🇫🇷")

    game = st.selectbox("Jeu", games)
    faction = st.selectbox("Faction", factions[game].keys())
    points = st.number_input("Format de la partie (pts)", 250, 5000, 1000, step=250)
    list_name = st.text_input("Nom de la liste", "Ma liste")

    if st.button("➡️ Ma liste"):
        st.session_state.game = game
        st.session_state.faction = faction
        st.session_state.points = points
        st.session_state.list_name = list_name
        st.session_state.units = factions[game][faction]["units"]
        st.session_state.page = "army"
        st.rerun()

# =================================================
# PAGE ARMY
# =================================================
elif st.session_state.page == "army":
    st.title(st.session_state.list_name)
    st.caption(f"{st.session_state.game} — {st.session_state.faction}")

    if st.button("⬅️ Retour"):
        st.session_state.page = "setup"
        st.rerun()

    st.divider()
    st.subheader("Ajouter une unité")

    unit = st.selectbox(
        "Unité",
        st.session_state.units,
        format_func=lambda u: f"{u['name']} ({u['base_cost']} pts)"
    )

    total_cost = unit["base_cost"]
    base_rules = list(unit.get("special_rules", []))
    options_selected = {}
    current_weapon = unit.get("weapons", [{}])[0].copy()
    mount_selected = None

    # -----------------------------
    # OPTIONS
    # -----------------------------
    for group in unit.get("upgrade_groups", []):
        st.markdown(f"### {group['group']}")

        # Rôle (radio)
        if "rôle" in group["group"].lower():
            choice = st.radio(
                group["group"],
                ["— Aucun —"] + [o["name"] for o in group["options"]],
                key=f"{unit['name']}_{group['group']}"
            )
            if choice != "— Aucun —":
                opt = next(o for o in group["options"] if o["name"] == choice)
                total_cost += opt["cost"]
                options_selected[group["group"]] = opt

        # Arme
        elif group.get("type") == "weapon":
            choice = st.radio(
                group["group"],
                ["— Arme de base —"] + [o["name"] for o in group["options"]],
                key=f"{unit['name']}_{group['group']}"
            )
            if choice != "— Arme de base —":
                opt = next(o for o in group["options"] if o["name"] == choice)
                total_cost += opt["cost"]
                current_weapon = opt["weapon"].copy()
                current_weapon["name"] = opt["name"]

        # Monture
        elif group.get("type") == "mount":
            choice = st.radio(
                group["group"],
                ["— Aucune —"] + [o["name"] for o in group["options"]],
                key=f"{unit['name']}_{group['group']}"
            )
            if choice != "— Aucune —":
                opt = next(o for o in group["options"] if o["name"] == choice)
                total_cost += opt["cost"]
                mount_selected = opt

        # Options multiples
        elif group.get("type") == "multiple":
            selected = []
            for opt in group["options"]:
                if st.checkbox(f"{opt['name']} (+{opt['cost']} pts)"):
                    total_cost += opt["cost"]
                    selected.append(opt)
            if selected:
                options_selected[group["group"]] = selected

    coriace = calculate_coriace({
        "base_rules": base_rules,
        "options": options_selected,
        "mount": mount_selected
    })

    st.markdown(f"### 💰 Coût : **{total_cost} pts**")
    if coriace:
        st.markdown(f"**Coriace totale : {coriace}**")

    if st.button("➕ Ajouter à l'armée"):
        st.session_state.army_list.append({
            "name": unit["name"],
            "cost": total_cost,
            "quality": unit["quality"],
            "defense": unit["defense"],
            "base_rules": base_rules,
            "options": options_selected,
            "current_weapon": current_weapon,
            "mount": mount_selected
        })
        st.session_state.army_total_cost += total_cost
        st.rerun()

    # =================================================
    # LISTE D’ARMÉE
    # =================================================
    st.divider()
    st.subheader("Liste de l’armée")

    for i, u in enumerate(st.session_state.army_list):
        coriace = calculate_coriace(u)

        st.markdown(f"""
        **{u['name']}** — {u['cost']} pts  
        Qualité {u['quality']}+ | Défense {u['defense']}+ {"| Coriace "+str(coriace) if coriace else ""}
        """)

        if u.get("base_rules"):
            st.caption("Règles spéciales : " + ", ".join(u["base_rules"]))

        if u.get("current_weapon"):
            w = u["current_weapon"]
            st.caption(f"Arme : {w.get('name')} | A{w.get('attacks')} | PA({w.get('armor_piercing')})")

        if u.get("options"):
            st.caption("Options : " + ", ".join(
                o["name"] if isinstance(o, dict) else opt["name"]
                for g in u["options"].values()
                for opt in (g if isinstance(g, list) else [g])
            ))

        if u.get("mount"):
            st.caption("Monture : " + u["mount"]["name"])

        if st.button("❌ Supprimer", key=f"del_{i}"):
            st.session_state.army_total_cost -= u["cost"]
            st.session_state.army_list.pop(i)
            st.rerun()

    st.markdown(f"### Total : **{st.session_state.army_total_cost} / {st.session_state.points} pts**")
