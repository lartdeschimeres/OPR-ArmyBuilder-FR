import json
import streamlit as st
import re
from pathlib import Path
from copy import deepcopy

st.set_page_config(page_title="OPR Army Forge FR", layout="wide")

# ==================================================
# PATHS
# ==================================================

BASE_DIR = Path(__file__).resolve().parent
FACTIONS_DIR = BASE_DIR / "lists" / "data" / "factions"

# ==================================================
# SESSION STATE
# ==================================================

if "page" not in st.session_state:
    st.session_state.page = "setup"

if "army" not in st.session_state:
    st.session_state.army = []

if "faction_data" not in st.session_state:
    st.session_state.faction_data = None

if "list_name" not in st.session_state:
    st.session_state.list_name = ""

if "points_limit" not in st.session_state:
    st.session_state.points_limit = 2000


# ==================================================
# UTILITAIRES
# ==================================================

def extract_coriace(rules):
    total = 0
    for r in rules:
        m = re.search(r"Coriace\s*\(?\+?(\d+)\)?", r)
        if m:
            total += int(m.group(1))
    return total


def load_factions():
    factions = []
    for fp in FACTIONS_DIR.glob("*.json"):
        with open(fp, encoding="utf-8") as f:
            factions.append(json.load(f))
    return factions


# ==================================================
# PAGE 1 – CONFIGURATION
# ==================================================

if st.session_state.page == "setup":
    st.title("⚙️ Création de la liste")

    if not FACTIONS_DIR.exists():
        st.error(f"Dossier introuvable : {FACTIONS_DIR}")
        st.stop()

    factions = load_factions()

    games = sorted(set(f["game"] for f in factions))
    selected_game = st.selectbox("Jeu", games)

    available_factions = [f for f in factions if f["game"] == selected_game]
    faction_names = [f["faction"] for f in available_factions]

    selected_faction_name = st.selectbox("Faction", faction_names)
    selected_faction = next(f for f in available_factions if f["faction"] == selected_faction_name)

    st.session_state.list_name = st.text_input("Nom de la liste", st.session_state.list_name)
    st.session_state.points_limit = st.number_input(
        "Limite de points",
        min_value=250,
        step=250,
        value=st.session_state.points_limit
    )

    if st.button("➡️ Créer / Continuer"):
        st.session_state.faction_data = selected_faction
        st.session_state.page = "army"
        st.rerun()


# ==================================================
# PAGE 2 – MA LISTE
# ==================================================

if st.session_state.page == "army":
    faction = st.session_state.faction_data
    units = faction["units"]

    st.title(f"📜 {st.session_state.list_name or 'Ma liste'}")
    st.caption(
        f"{faction['game']} | {faction['faction']} | "
        f"{st.session_state.points_limit} pts"
    )

    if st.button("⬅️ Retour configuration"):
        st.session_state.page = "setup"
        st.rerun()

    col_left, col_right = st.columns([1, 2])

    # --------------------------------------------------
    # AJOUT D’UNITÉ
    # --------------------------------------------------

    with col_left:
        st.header("Ajouter une unité")

        unit_names = [u["name"] for u in units]
        selected_name = st.selectbox("Unité", unit_names)
        base_unit = next(u for u in units if u["name"] == selected_name)
        unit = deepcopy(base_unit)

        total_cost = unit["base_cost"]
        final_rules = list(unit.get("special_rules", []))
        selected_options = {}
        selected_mount = None

        st.subheader("Options")

        for group in unit.get("upgrade_groups", []):
            options = ["Aucune"] + [o["name"] for o in group["options"]]
            choice = st.selectbox(group["group"], options, key=f"{unit['name']}_{group['group']}")

            if choice != "Aucune":
                opt = next(o for o in group["options"] if o["name"] == choice)
                total_cost += opt.get("cost", 0)

                if group["type"] == "mount":
                    selected_mount = opt
                else:
                    selected_options[group["group"]] = opt

                if "special_rules" in opt:
                    final_rules.extend(opt["special_rules"])

        if st.button("➕ Ajouter à l'armée"):
            st.session_state.army.append({
                "profile": unit,
                "rules": final_rules,
                "options": selected_options,
                "mount": selected_mount,
                "cost": total_cost
            })
            st.rerun()

    # --------------------------------------------------
    # LISTE DE L’ARMÉE
    # --------------------------------------------------

    with col_right:
        st.header("Unités")

        if not st.session_state.army:
            st.info("Aucune unité ajoutée.")
        else:
            for i, u in enumerate(st.session_state.army):
                profile = u["profile"]

                with st.container(border=True):
                    cols = st.columns([3, 1])

                    with cols[0]:
                        st.subheader(profile["name"])

                        q, d, c = st.columns(3)
                        q.metric("Qualité", f"{profile['quality']}+")
                        d.metric("Défense", f"{profile['defense']}+")

                        coriace_total = extract_coriace(u["rules"])
                        c.metric("Coriace total", coriace_total)

                        st.markdown("**Règles spéciales**")
                        st.caption(", ".join(sorted(set(u["rules"]))))

                        if u["options"]:
                            st.markdown("**Options sélectionnées**")
                            st.caption(", ".join(opt["name"] for opt in u["options"].values()))

                        if u["mount"]:
                            st.markdown("**Monture**")
                            st.caption(
                                f"{u['mount']['name']} — "
                                + ", ".join(u['mount'].get("special_rules", []))
                            )

                    with cols[1]:
                        st.metric("Coût", u["cost"])
                        if st.button("🗑 Supprimer", key=f"del_{i}"):
                            st.session_state.army.pop(i)
                            st.rerun()
