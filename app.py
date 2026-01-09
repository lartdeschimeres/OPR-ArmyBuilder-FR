import json
import streamlit as st
from pathlib import Path

# -----------------------------
# CONFIG
# -----------------------------
FACTION_PATH = Path("data/factions/disciplines_de_la_guerre.json")

st.set_page_config(page_title="OPR Army Builder 🇫🇷", layout="centered")
st.title("OPR Army Builder 🇫🇷")

# -----------------------------
# LOAD FACTION
# -----------------------------
if not FACTION_PATH.exists():
    st.error(f"Fichier faction introuvable : {FACTION_PATH}")
    st.stop()

with open(FACTION_PATH, encoding="utf-8") as f:
    faction = json.load(f)

st.subheader(f"Faction : {faction['faction']}")
st.caption(f"Jeu : {faction['game']}")

units = faction.get("units", [])
if not units:
    st.warning("Aucune unité dans cette faction.")
    st.stop()

# -----------------------------
# SESSION STATE
# -----------------------------
if "selected_unit_name" not in st.session_state:
    st.session_state.selected_unit_name = units[0]["name"]

# -----------------------------
# UNIT SELECTOR
# -----------------------------
def unit_label(u):
    return f"{u['name']} ({u['base_cost']} pts | Q{u['quality']}+ / D{u['defense']}+)"

unit_names = [u["name"] for u in units]

selected_name = st.selectbox(
    "Choisir une unité",
    unit_names,
    index=unit_names.index(st.session_state.selected_unit_name),
    format_func=lambda n: unit_label(next(u for u in units if u["name"] == n))
)

st.session_state.selected_unit_name = selected_name
unit = next(u for u in units if u["name"] == selected_name)

# -----------------------------
# BASE PROFILE
# -----------------------------
st.divider()
st.subheader("Profil de base")

st.write(f"**Type :** {unit['type']}")
st.write(f"**Qualité :** {unit['quality']}+")
st.write(f"**Défense :** {unit['defense']}+")
st.write(f"**Coût de base :** {unit['base_cost']} pts")

# -----------------------------
# OPTIONS
# -----------------------------
st.divider()
st.subheader("Options")

total_cost = unit["base_cost"]
final_rules = list(unit.get("special_rules", []))
final_weapons = list(unit.get("weapons", []))

for group in unit.get("upgrade_groups", []):
    key = f"{unit['name']}_{group['group']}"

    options = ["— Aucun —"] + [opt["name"] for opt in group["options"]]

    choice = st.selectbox(
        group["group"],
        options,
        key=key
    )

    if choice != "— Aucun —":
        opt = next(o for o in group["options"] if o["name"] == choice)
        total_cost += opt["cost"]

        if "special_rules" in opt:
            final_rules.extend(opt["special_rules"])

        if "weapon" in opt:
            final_weapons = [opt["weapon"]]

# -----------------------------
# FINAL PROFILE
# -----------------------------
st.divider()
st.subheader("Profil final")

st.markdown(f"## 💰 Coût total : **{total_cost} pts**")

st.markdown("### 🛡️ Règles spéciales")
for r in sorted(set(final_rules)):
    st.write(f"- {r}")

st.markdown("### ⚔️ Armes")
for w in final_weapons:
    st.write(
        f"- **{w.get('name','Arme')}** | "
        f"A{w['attacks']} | PA({w['armor_piercing']}) "
        f"{' '.join(w.get('special_rules', []))}"
    )
