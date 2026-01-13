import json
import streamlit as st
import re
from pathlib import Path
from copy import deepcopy

st.set_page_config(page_title="OPR Army Forge FR", layout="wide")

BASE_DIR = Path(__file__).resolve().parent
FACTIONS_DIR = BASE_DIR / "lists" / "data" / "factions"

# ==================================================
# SESSION
# ==================================================

if "page" not in st.session_state:
    st.session_state.page = "setup"
if "army" not in st.session_state:
    st.session_state.army = []
if "faction" not in st.session_state:
    st.session_state.faction = None
if "points" not in st.session_state:
    st.session_state.points = 2000

# ==================================================
# UTILITAIRES
# ==================================================

def extract_coriace(rules):
    """Calcule la valeur totale de Coriace à partir des règles."""
    total = 0
    for r in rules:
        m = re.search(r"Coriace\s*\(?\+?(\d+)\)?", r)
        if m:
            total += int(m.group(1))
    return total

def calculate_total_coriace(unit_data):
    """Calcule la valeur totale de Coriace pour une unité (inclut armes, montures et améliorations)."""
    total = 0

    # Règles de base
    total += extract_coriace(unit_data["rules"])

    # Monture
    if unit_data.get("mount"):
        total += extract_coriace(unit_data["mount"].get("special_rules", []))

    # Armes
    for weapon in unit_data.get("weapons", []):
        total += extract_coriace(weapon.get("special_rules", []))

    return total

def load_factions():
    """Charge les factions depuis les fichiers JSON."""
    data = []
    for fp in FACTIONS_DIR.glob("*.json"):
        with open(fp, encoding="utf-8") as f:
            data.append(json.load(f))
    return data

# ==================================================
# PAGE SETUP
# ==================================================

if st.session_state.page == "setup":
    st.title("⚙️ Création de la liste")

    factions = load_factions()
    games = sorted(set(f["game"] for f in factions))

    game = st.selectbox("Jeu", games)
    game_factions = [f for f in factions if f["game"] == game]

    faction_name = st.selectbox("Faction", [f["faction"] for f in game_factions])
    faction = next(f for f in game_factions if f["faction"] == faction_name)

    st.session_state.points = st.number_input("Limite de points", 250, 5000, st.session_state.points, 250)

    if st.button("➡️ Composer l’armée"):
        st.session_state.faction = faction
        st.session_state.page = "army"
        st.rerun()

# ==================================================
# PAGE ARMY
# ==================================================

if st.session_state.page == "army":
    faction = st.session_state.faction
    units = faction["units"]

    st.title(f"📜 {faction['faction']} – {st.session_state.points} pts")

    # Affichage du total des points utilisés
    total_cost = sum(u["cost"] for u in st.session_state.army)
    st.caption(f"Points utilisés : {total_cost}/{st.session_state.points}")

    col_add, col_list = st.columns([1, 2])

    # ==================================================
    # AJOUT UNITÉ
    # ==================================================

    with col_add:
        st.header("Ajouter une unité")

        unit_name = st.selectbox("Unité", [u["name"] for u in units])
        base = next(u for u in units if u["name"] == unit_name)
        unit = deepcopy(base)

        cost = unit["base_cost"]
        rules = list(unit.get("special_rules", []))
        weapons = list(unit.get("weapons", []))

        selected_weapons = []
        selected_upgrades = []
        selected_mount = None

        # -------------------------
        # OPTIONS D'ESCOUADE (checkboxes uniques)
        # -------------------------
        st.subheader("Options d’escouade")
        if "upgrade_groups" in unit:
            for group in unit["upgrade_groups"]:
                if group["group"].lower() in ["améliorations d'unité", "améliorations d'escouade"]:
                    st.write(f"**{group['group']}**")
                    for opt in group["options"]:
                        if st.checkbox(f"{opt['name']} (+{opt['cost']} pts)", key=f"{unit_name}_{opt['name']}"):
                            selected_upgrades.append(opt["name"])
                            cost += opt["cost"]
                            rules.extend(opt.get("special_rules", []))

        # -------------------------
        # ARMES (checkboxes uniques)
        # -------------------------
        st.subheader("Armes")
        if "weapons" in unit and len(unit["weapons"]) > 1:
            for i, weapon in enumerate(unit["weapons"]):
                if st.checkbox(f"{weapon['name']} (inclus)", key=f"{unit_name}_weapon_{i}", value=i == 0):
                    selected_weapons = [weapon]
        else:
            selected_weapons = weapons

        # -------------------------
        # MONTURES (checkboxes uniques)
        # -------------------------
        st.subheader("Montures")
        for group in unit.get("upgrade_groups", []):
            if group["type"] == "mount":
                st.write(f"**{group['group']}**")
                for opt in group["options"]:
                    if st.checkbox(f"{opt['name']} (+{opt['cost']} pts)", key=f"{unit_name}_{opt['name']}"):
                        selected_mount = opt
                        cost += opt["cost"]
                        rules.extend(opt.get("special_rules", []))

        # -------------------------
        # AUTRES OPTIONS (checkboxes uniques)
        # -------------------------
        st.subheader("Autres options")
        for group in unit.get("upgrade_groups", []):
            if group["type"] not in ["mount", "weapon"] and "améliorations" not in group["group"].lower():
                st.write(f"**{group['group']}**")
                for opt in group["options"]:
                    if st.checkbox(f"{opt['name']} (+{opt['cost']} pts)", key=f"{unit_name}_{opt['name']}"):
                        selected_upgrades.append(opt["name"])
                        cost += opt["cost"]
                        rules.extend(opt.get("special_rules", []))

        if st.button("➕ Ajouter à l’armée"):
            st.session_state.army.append({
                "unit": unit,
                "weapons": selected_weapons or weapons,
                "rules": rules,
                "options": selected_upgrades,
                "mount": selected_mount,
                "cost": cost
            })
            st.rerun()

    # ==================================================
    # LISTE DE L'ARMÉE
    # ==================================================

    with col_list:
        st.header("Armée")

        if not st.session_state.army:
            st.info("Votre armée est vide. Ajoutez des unités pour commencer.")

        for i, u in enumerate(st.session_state.army):
            unit = u["unit"]
            coriace_total = calculate_total_coriace(u)

            with st.container(border=True):
                st.subheader(unit["name"])

                q, d, c = st.columns(3)
                q.metric("Qualité", f"{unit['quality']}+")
                d.metric("Défense", f"{unit['defense']}+")
                c.metric("Coriace totale", coriace_total)

                st.markdown("**Armes**")
                for w in u["weapons"]:
                    st.caption(f"{w['name']} – A{w['attacks']} PA({w['armor_piercing']})")

                st.markdown("**Règles spéciales**")
                st.caption(", ".join(sorted(set(u["rules"]))))

                if u["options"]:
                    st.markdown("**Options sélectionnées**")
                    st.caption(", ".join(u["options"]))

                if u["mount"]:
                    m = u["mount"]
                    st.markdown("**Monture**")
                    st.caption(
                        f"{m['name']} – "
                        + ", ".join(m.get("special_rules", []))
                    )

                st.metric("Coût", u["cost"])
                if st.button("🗑 Supprimer", key=f"del_{i}"):
                    st.session_state.army.pop(i)
                    st.rerun()

        # ==================================================
        # RÉSUMÉ DE L'ARMÉE
        # ==================================================

        if st.session_state.army:
            st.divider()
            st.subheader("Résumé de l'armée")

            total_points = sum(u["cost"] for u in st.session_state.army)
            total_coriace = sum(calculate_total_coriace(u) for u in st.session_state.army)

            st.metric("Total des points", f"{total_points}/{st.session_state.points}")
            st.metric("Coriace totale de l'armée", total_coriace)

            if total_points > st.session_state.points:
                st.warning(f"⚠️ Votre armée dépasse de {total_points - st.session_state.points} points !")
