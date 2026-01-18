import json
import re
from pathlib import Path
from datetime import datetime
import hashlib
import streamlit as st
import streamlit.components.v1 as components

# ======================================================
# CONFIGURATION STREAMLIT
# ======================================================

st.set_page_config(
    page_title="OPR Army Builder FR",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ======================================================
# LOCAL STORAGE (STABLE)
# ======================================================

def localstorage_get(key):
    components.html(
        f"""
        <script>
        const val = localStorage.getItem("{key}");
        const input = document.createElement("input");
        input.type = "hidden";
        input.id = "{key}";
        input.value = val ?? "";
        document.body.appendChild(input);
        </script>
        """,
        height=0
    )
    return st.session_state.get(key)

def localstorage_set(key, value):
    components.html(
        f"""
        <script>
        localStorage.setItem("{key}", `{json.dumps(value, ensure_ascii=False)}`);
        </script>
        """,
        height=0
    )

# ======================================================
# CORIACE
# ======================================================

def extract_coriace(rules):
    total = 0
    for r in rules or []:
        m = re.search(r"Coriace\s*\(?(\d+)\)?", r)
        if m:
            total += int(m.group(1))
    return total

def calculate_total_coriace(unit):
    total = extract_coriace(unit.get("base_rules", []))
    for opts in unit.get("options", {}).values():
        for o in opts if isinstance(opts, list) else [opts]:
            total += extract_coriace(o.get("special_rules", []))
    if unit.get("mount"):
        total += extract_coriace(unit["mount"].get("special_rules", []))
    return total if total > 0 else None

# ======================================================
# CHARGEMENT DES FACTIONS (POINT CRITIQUE)
# ======================================================

BASE_DIR = Path(__file__).resolve().parent
FACTIONS_DIR = BASE_DIR / "lists" / "data" / "factions"

if not FACTIONS_DIR.exists():
    st.error(f"❌ Dossier factions introuvable : {FACTIONS_DIR}")
    st.stop()

@st.cache_data
def load_factions():
    factions = {}
    games = set()

    for file in FACTIONS_DIR.glob("*.json"):
        try:
            with open(file, encoding="utf-8") as f:
                data = json.load(f)
                game = data.get("game")
                faction = data.get("faction")
                if game and faction:
                    factions.setdefault(game, {})[faction] = data
                    games.add(game)
        except Exception as e:
            st.warning(f"Erreur chargement {file.name} : {e}")

    return factions, sorted(games)

# ======================================================
# MAIN
# ======================================================

def main():

    if "page" not in st.session_state:
        st.session_state.page = "setup"
        st.session_state.player = "Simon"
        st.session_state.army_list = []
        st.session_state.army_cost = 0

    factions, games = load_factions()

    # ==================================================
    # PAGE SETUP
    # ==================================================

    if st.session_state.page == "setup":
        st.title("OPR Army Builder 🇫🇷")

        game = st.selectbox("Jeu", games)
        faction = st.selectbox("Faction", list(factions[game].keys()))

        points = st.number_input("Points", 250, 5000, 1000, 250)
        name = st.text_input("Nom de la liste", f"Liste_{datetime.now().strftime('%Y%m%d')}")

        if st.button("Créer la liste"):
            st.session_state.game = game
            st.session_state.faction = faction
            st.session_state.points = points
            st.session_state.list_name = name
            st.session_state.units = factions[game][faction]["units"]
            st.session_state.army_list = []
            st.session_state.army_cost = 0
            st.session_state.page = "army"
            st.rerun()

    # ==================================================
    # PAGE ARMÉE
    # ==================================================

    if st.session_state.page == "army":
        st.title(st.session_state.list_name)
        st.caption(f"{st.session_state.game} • {st.session_state.faction} • {st.session_state.army_cost}/{st.session_state.points} pts")

        if st.button("⬅ Retour"):
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
        selected_options = {}
        mount = None
        weapon = unit["weapons"][0]

        for group in unit.get("upgrade_groups", []):
            st.markdown(f"**{group['group']}**")

            if group["type"] == "multiple":
                for opt in group["options"]:
                    if st.checkbox(f"{opt['name']} (+{opt['cost']} pts)"):
                        selected_options.setdefault(group["group"], []).append(opt)
                        cost += opt["cost"]

            elif group["type"] == "weapon":
                choices = ["Arme de base"] + [o["name"] for o in group["options"]]
                choice = st.radio("Arme", choices)
                if choice != "Arme de base":
                    opt = next(o for o in group["options"] if o["name"] == choice)
                    weapon = opt["weapon"]
                    cost += opt.get("cost", 0)

            elif group["type"] == "mount":
                choices = ["Aucune"] + [o["name"] for o in group["options"]]
                choice = st.radio("Monture", choices)
                if choice != "Aucune":
                    opt = next(o for o in group["options"] if o["name"] == choice)
                    mount = opt["mount"]
                    cost += opt.get("cost", 0)

        st.markdown(f"### Coût : {cost} pts")

        if st.button("Ajouter à l'armée"):
            st.session_state.army_list.append({
                "name": unit["name"],
                "quality": unit["quality"],
                "defense": unit["defense"],
                "cost": cost,
                "base_rules": unit.get("special_rules", []),
                "current_weapon": weapon,
                "options": selected_options,
                "mount": mount
            })
            st.session_state.army_cost += cost
            st.rerun()

        st.divider()
        st.subheader("Liste de l'armée")

        for i, u in enumerate(st.session_state.army_list):
            coriace = calculate_total_coriace(u)
            st.markdown(f"### {u['name']} [{u['cost']} pts]")
            st.caption(f"Q{u['quality']}+ / D{u['defense']}+" + (f" • Coriace {coriace}" if coriace else ""))

            if u.get("base_rules"):
                st.markdown("**Règles spéciales**")
                st.caption(", ".join(u["base_rules"]))

            if u.get("mount"):
                st.markdown("**Monture**")
                st.caption(u["mount"]["name"])

            if u.get("options"):
                st.markdown("**Options**")
                for g in u["options"].values():
                    for o in g:
                        st.caption(o["name"])

            if st.button("Supprimer", key=f"del_{i}"):
                st.session_state.army_cost -= u["cost"]
                st.session_state.army_list.pop(i)
                st.rerun()

if __name__ == "__main__":
    main()
