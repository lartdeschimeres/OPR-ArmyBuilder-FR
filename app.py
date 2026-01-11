import json
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components

# -------------------------------------------------
# CONFIG
# -------------------------------------------------
st.set_page_config(page_title="OPR Army Builder FR", layout="centered")
BASE_DIR = Path(__file__).resolve().parent
FACTIONS_DIR = BASE_DIR / "lists" / "data" / "factions"

# -------------------------------------------------
# SESSION STATE INIT
# -------------------------------------------------
if "page" not in st.session_state:
    st.session_state.page = "setup"

for key, default in {
    "game": None,
    "faction": None,
    "points": 1000,
    "list_name": "",
    "army_list": [],
    "army_total_cost": 0
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# -------------------------------------------------
# CHARGEMENT DES FACTIONS
# -------------------------------------------------
faction_files = list(FACTIONS_DIR.glob("*.json"))
factions = []

for fp in faction_files:
    with open(fp, encoding="utf-8") as f:
        data = json.load(f)
        factions.append({
            "name": data["faction"],
            "game": data["game"],
            "file": fp
        })

games = sorted(set(f["game"] for f in factions))

# =================================================
# PAGE 1 — CONFIGURATION DE LA LISTE
# =================================================
if st.session_state.page == "setup":

    st.title("OPR Army Builder 🇫🇷")
    st.subheader("Créer une nouvelle liste")

    st.session_state.game = st.selectbox(
        "Jeu",
        games,
        index=games.index(st.session_state.game) if st.session_state.game else 0
    )

    available_factions = [
        f for f in factions if f["game"] == st.session_state.game
    ]

    faction_names = [f["name"] for f in available_factions]

    st.session_state.faction = st.selectbox(
        "Faction",
        faction_names,
        index=faction_names.index(st.session_state.faction)
        if st.session_state.faction in faction_names else 0
    )

    st.session_state.points = st.number_input(
        "Format de la partie (points)",
        min_value=250,
        step=250,
        value=st.session_state.points
    )

    st.session_state.list_name = st.text_input(
        "Nom de la liste",
        value=st.session_state.list_name
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("💾 Sauvegarder la configuration"):
            st.success("Configuration sauvegardée")

    with col2:
        if st.button("➡️ Ma liste"):
            st.session_state.page = "army"
            st.rerun()

# =================================================
# PAGE 2 — COMPOSITION DE L’ARMÉE
# =================================================
if st.session_state.page == "army":

    st.title(st.session_state.list_name or "Ma liste d'armée")
    st.caption(
        f"{st.session_state.game} — {st.session_state.faction} — "
        f"{st.session_state.army_total_cost}/{st.session_state.points} pts"
    )

    if st.button("⬅️ Retour configuration"):
        st.session_state.page = "setup"
        st.rerun()

    # ---------------------------------------------
    # CHARGER LA FACTION
    # ---------------------------------------------
    faction_file = next(
        f["file"] for f in factions
        if f["name"] == st.session_state.faction
    )

    with open(faction_file, encoding="utf-8") as f:
        faction = json.load(f)

    units = faction.get("units", [])

    st.divider()
    st.subheader("Ajouter une unité")

    unit = st.selectbox(
        "Unité",
        units,
        format_func=lambda u: f"{u['name']} ({u['base_cost']} pts)",
    )

    total_cost = unit["base_cost"]
    base_rules = unit.get("special_rules", [])
    options_selected = {}
    mount_selected = None

    # ---------------------------------------------
    # OPTIONS
    # ---------------------------------------------
    for group in unit.get("upgrade_groups", []):
        choice = st.selectbox(
            group["group"],
            ["— Aucun —"] + [o["name"] for o in group["options"]],
            key=f"{unit['name']}_{group['group']}"
        )

        if choice != "— Aucun —":
            opt = next(o for o in group["options"] if o["name"] == choice)
            total_cost += opt.get("cost", 0)

            if group["type"] == "mount":
                mount_selected = opt
            else:
                options_selected[group["group"]] = opt

    st.markdown(f"### 💰 Coût : **{total_cost} pts**")

    if st.button("➕ Ajouter à l'armée"):
        st.session_state.army_list.append({
            "name": unit["name"],
            "cost": total_cost,
            "quality": unit["quality"],
            "defense": unit["defense"],
            "base_rules": base_rules,
            "options": options_selected,
            "mount": mount_selected
        })
        st.session_state.army_total_cost += total_cost
        st.rerun()

    # ---------------------------------------------
    # LISTE DE L’ARMÉE
    # ---------------------------------------------
    st.divider()
    st.subheader("Liste de l'armée")

    for i, u in enumerate(st.session_state.army_list):

        components.html(f"""
        <style>
        .card {{
            border:1px solid #ccc;
            border-radius:10px;
            padding:15px;
            margin-bottom:15px;
            background:#f9f9f9;
        }}
        .badge {{
            display:inline-block;
            background:#4a89dc;
            color:white;
            padding:6px 12px;
            border-radius:15px;
            margin-right:8px;
        }}
        .title {{
            font-weight:bold;
            color:#4a89dc;
            margin-top:10px;
        }}
        </style>

        <div class="card">
            <h4>{u['name']} — {u['cost']} pts</h4>

            <div>
                <span class="badge">Qualité {u['quality']}+</span>
                <span class="badge">Défense {u['defense']}+</span>
            </div>

            <div class="title">Règles spéciales</div>
            <div>{", ".join(u["base_rules"])}</div>

            {(
                "<div class='title'>Options sélectionnées</div><div>" +
                ", ".join(o["name"] for o in u["options"].values()) +
                "</div>"
            ) if u["options"] else ""}

            {(
                "<div class='title'>Monture</div><div><strong>" +
                u["mount"]["name"] +
                "</strong><br>" +
                ", ".join(u["mount"].get("special_rules", [])) +
                "</div>"
            ) if u["mount"] else ""}
        </div>
        """, height=260)

        if st.button("❌ Supprimer", key=f"del_{i}"):
            st.session_state.army_total_cost -= u["cost"]
            st.session_state.army_list.pop(i)
            st.rerun()

    st.progress(
        st.session_state.army_total_cost / st.session_state.points
        if st.session_state.points else 0
    )
