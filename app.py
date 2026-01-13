import json
import re
from pathlib import Path
from collections import defaultdict
from datetime import datetime
import streamlit as st
import streamlit.components.v1 as components

# =========================================================
# CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="OPR Army Builder FR",
    layout="centered"
)

BASE_DIR = Path(__file__).resolve().parent
FACTIONS_DIR = BASE_DIR / "lists" / "data" / "factions"

GAME_RULES = {
    "Age of Fantasy": {
        "hero_per_points": 375,
        "max_unit_percentage": 35,
        "unit_per_points": 150,
    }
}

# =========================================================
# SESSION STATE INIT
# =========================================================

def init_session_state():
    defaults = {
        "page": "setup",
        "game": None,
        "faction": None,
        "points": 1000,
        "list_name": "",
        "units": [],
        "army_list": [],
        "army_total_cost": 0,
        "is_army_valid": True,
        "validation_errors": [],
        "factions": {},
        "games": [],
        "local_army_lists": []
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session_state()

# =========================================================
# LOCAL STORAGE (JS <-> STREAMLIT)
# =========================================================

def load_lists_from_localstorage():
    components.html(
        """
        <script>
        const data = localStorage.getItem("opr_army_lists_fr");
        const lists = data ? JSON.parse(data) : [];
        window.parent.postMessage(
            { type: "OPR_LOAD_LISTS", payload: lists },
            "*"
        );
        </script>
        """,
        height=0,
    )


def save_lists_to_localstorage(lists):
    components.html(
        f"""
        <script>
        localStorage.setItem(
            "opr_army_lists_fr",
            {json.dumps(lists)}
        );
        </script>
        """,
        height=0,
    )


components.html(
    """
    <script>
    window.addEventListener("message", (event) => {
        if (event.data.type === "OPR_LOAD_LISTS") {
            window.streamlit.setComponentValue(event.data.payload);
        }
    });
    </script>
    """,
    height=0,
)

if st.session_state.get("component_value") is not None:
    st.session_state.local_army_lists = st.session_state.component_value

# =========================================================
# DATA LOADING
# =========================================================

@st.cache_data
def load_factions():
    factions = {}
    games = set()

    if not FACTIONS_DIR.exists():
        st.error(f"Dossier factions introuvable : {FACTIONS_DIR}")
        return {}, []

    for fp in FACTIONS_DIR.glob("*.json"):
        with open(fp, encoding="utf-8") as f:
            data = json.load(f)

        game = data.get("game")
        faction = data.get("faction")
        if not game or not faction:
            continue

        factions.setdefault(game, {})[faction] = data
        games.add(game)

    return factions, sorted(games)

if not st.session_state.factions:
    st.session_state.factions, st.session_state.games = load_factions()

# =========================================================
# UTILITAIRES
# =========================================================

def calculate_coriace_value(unit_data):
    total = 0
    sources = []

    if unit_data.get("base_rules"):
        sources += unit_data["base_rules"]

    for opt in unit_data.get("options", {}).values():
        if isinstance(opt, list):
            for o in opt:
                sources += o.get("special_rules", [])
        elif isinstance(opt, dict):
            sources += opt.get("special_rules", [])

    if unit_data.get("mount"):
        sources += unit_data["mount"].get("special_rules", [])

    for rule in sources:
        match = re.search(r"Coriace\s*\((\d+)\)", rule)
        if match:
            total += int(match.group(1))

    return total


def validate_army(army, rules, total_cost, max_points):
    errors = []

    if total_cost > max_points:
        errors.append("Dépassement de points")

    heroes = sum(1 for u in army if u.get("type") == "Hero")
    max_heroes = max(1, max_points // rules["hero_per_points"])
    if heroes > max_heroes:
        errors.append("Trop de héros")

    return len(errors) == 0, errors

# =========================================================
# PAGE SETUP
# =========================================================

if st.session_state.page == "setup":

    st.title("OPR Army Builder 🇫🇷")

    load_lists_from_localstorage()

    st.subheader("Mes listes sur cet appareil")

    if st.session_state.local_army_lists:
        for i, lst in enumerate(st.session_state.local_army_lists):
            with st.expander(
                f"{lst['name']} — {lst['game']} "
                f"({lst['total_cost']}/{lst['points']} pts)"
            ):
                if st.button("📂 Charger", key=f"load_{i}"):
                    st.session_state.game = lst["game"]
                    st.session_state.faction = lst["faction"]
                    st.session_state.points = lst["points"]
                    st.session_state.list_name = lst["name"]
                    st.session_state.army_list = lst["army_list"]
                    st.session_state.army_total_cost = lst["total_cost"]
                    st.session_state.page = "army"
                    st.rerun()

                if st.button("❌ Supprimer", key=f"del_{i}"):
                    st.session_state.local_army_lists.pop(i)
                    save_lists_to_localstorage(st.session_state.local_army_lists)
                    st.rerun()
    else:
        st.info("Aucune liste sauvegardée.")

    st.divider()
    st.subheader("Créer une nouvelle liste")

    st.session_state.game = st.selectbox("Jeu", st.session_state.games)

    if st.session_state.game:
        factions = list(st.session_state.factions[st.session_state.game].keys())
        st.session_state.faction = st.selectbox("Faction", factions)

    st.session_state.points = st.number_input(
        "Format (points)", 250, step=250, value=1000
    )

    st.session_state.list_name = st.text_input(
        "Nom de la liste", value="Ma liste d'armée"
    )

    if st.button("➡️ Ma liste"):
        data = st.session_state.factions[st.session_state.game][st.session_state.faction]
        st.session_state.units = data["units"]
        st.session_state.page = "army"
        st.rerun()

# =========================================================
# PAGE ARMY
# =========================================================

elif st.session_state.page == "army":

    st.title(st.session_state.list_name)
    st.caption(
        f"{st.session_state.game} — {st.session_state.faction} — "
        f"{st.session_state.army_total_cost}/{st.session_state.points} pts"
    )

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

    cost = unit["base_cost"]

    if st.button("➕ Ajouter"):
        st.session_state.army_list.append({
            "name": unit["name"],
            "cost": cost,
            "quality": unit["quality"],
            "defense": unit["defense"],
            "base_rules": unit.get("special_rules", []),
            "options": {},
            "type": unit.get("type", "Infantry")
        })
        st.session_state.army_total_cost += cost
        st.rerun()

    st.divider()
    st.subheader("Liste de l'armée")

    for i, u in enumerate(st.session_state.army_list):
        coriace = calculate_coriace_value(u)
        st.markdown(
            f"**{u['name']}** — {u['cost']} pts  \n"
            f"Qualité {u['quality']}+ | Défense {u['defense']}+"
            + (f" | Coriace {coriace}" if coriace else "")
        )

        if st.button("❌ Supprimer", key=f"remove_{i}"):
            st.session_state.army_total_cost -= u["cost"]
            st.session_state.army_list.pop(i)
            st.rerun()

    st.divider()

    if st.button("💾 Sauvegarder la liste"):
        data = {
            "name": st.session_state.list_name,
            "game": st.session_state.game,
            "faction": st.session_state.faction,
            "points": st.session_state.points,
            "army_list": st.session_state.army_list,
            "total_cost": st.session_state.army_total_cost,
            "date": datetime.now().isoformat()
        }
        st.session_state.local_army_lists.append(data)
        save_lists_to_localstorage(st.session_state.local_army_lists)
        st.success("Liste sauvegardée dans le navigateur ✔️")
