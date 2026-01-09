import json
from pathlib import Path
import streamlit as st

# -------------------------------------------------
# CONFIG GÉNÉRALE
# -------------------------------------------------
st.set_page_config(page_title="OPR Army Builder FR", layout="centered")
st.title("OPR Army Builder 🇫🇷")

BASE_DIR = Path(__file__).resolve().parent
GAMES_DIR = BASE_DIR / "lists" / "data"

# -------------------------------------------------
# CHARGEMENT DES JEUX
# -------------------------------------------------
if not GAMES_DIR.exists():
    st.error(f"Dossier jeux introuvable : {GAMES_DIR}")
    st.stop()

game_dirs = [d for d in GAMES_DIR.iterdir() if d.is_dir()]

if not game_dirs:
    st.error("Aucun jeu trouvé")
    st.stop()

# Sélecteur de jeu
selected_game = st.selectbox(
    "Sélectionner le jeu",
    [d.name for d in game_dirs]
)

# -------------------------------------------------
# CHARGEMENT DES FACTIONS POUR LE JEU SÉLECTIONNÉ
# -------------------------------------------------
GAME_FACTIONS_DIR = GAMES_DIR / selected_game

if not GAME_FACTIONS_DIR.exists():
    st.error(f"Dossier factions introuvable pour le jeu {selected_game}")
    st.stop()

faction_files = sorted(GAME_FACTIONS_DIR.glob("*.json"))

if not faction_files:
    st.error(f"Aucun fichier faction trouvé pour le jeu {selected_game}")
    st.stop()

faction_map = {}

for fp in faction_files:
    try:
        with open(fp, encoding="utf-8") as f:
            data = json.load(f)
            name = data.get("faction", fp.stem)
            faction_map[name] = fp
    except Exception as e:
        st.warning(f"Impossible de lire {fp.name} : {e}")

# Sélecteur de faction
selected_faction = st.selectbox(
    "Sélectionner la faction",
    sorted(faction_map.keys())
)

# -------------------------------------------------
# CHARGEMENT DE LA FACTION
# -------------------------------------------------
FACTION_PATH = faction_map[selected_faction]

with open(FACTION_PATH, encoding="utf-8") as f:
    faction = json.load(f)

# -------------------------------------------------
# AFFICHAGE FACTION
# -------------------------------------------------
st.subheader(f"Faction : {faction.get('faction','Inconnue')}")
st.caption(f"Jeu : {faction.get('game', selected_game)}")

units = faction.get("units", [])
if not units:
    st.warning("Aucune unité disponible pour cette faction.")
    st.stop()

# -------------------------------------------------
# SESSION STATE
# -------------------------------------------------
if "selected_unit" not in st.session_state:
    st.session_state.selected_unit = units[0]["name"]

# -------------------------------------------------
# SÉLECTEUR D’UNITÉ
# -------------------------------------------------
def unit_label(u):
    return f"{u['name']} ({u['base_cost']} pts | Q{u['quality']}+ / D{u['defense']}+)"

unit_names = [u["name"] for u in units]

selected_name = st.selectbox(
    "Choisir une unité",
    unit_names,
    index=unit_names.index(st.session_state.selected_unit),
    format_func=lambda n: unit_label(next(u for u in units if u["name"] == n))
)

st.session_state.selected_unit = selected_name
unit = next(u for u in units if u["name"] == selected_name)

# -------------------------------------------------
# PROFIL DE BASE
# -------------------------------------------------
st.divider()
st.subheader("Profil de base")

st.write(f"**Type :** {unit.get('type','—')}")
st.write(f"**Qualité :** {unit.get('quality','?')}+")
st.write(f"**Défense :** {unit.get('defense','?')}+")
st.write(f"**Coût de base :** {unit.get('base_cost',0)} pts")

# -------------------------------------------------
# OPTIONS & CALCUL
# -------------------------------------------------
st.divider()
st.subheader("Options")

total_cost = unit.get("base_cost", 0)
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
        total_cost += opt.get("cost", 0)

        if "special_rules" in opt:
            final_rules.extend(opt["special_rules"])

        if "weapon" in opt:
            final_weapons = [opt["weapon"]]

# -------------------------------------------------
# PROFIL FINAL
# -------------------------------------------------
st.divider()
st.subheader("Profil final")

st.markdown(f"## 💰 Coût total : **{total_cost} pts**")

st.markdown("### 🛡️ Règles spéciales")
if final_rules:
    for r in sorted(set(final_rules)):
        st.write(f"- {r}")
else:
    st.write("—")

st.markdown("### ⚔️ Armes")
if final_weapons:
    for w in final_weapons:
        st.write(
            f"- **{w.get('name','Arme')}** | "
            f"A{w.get('attacks','?')} | "
            f"PA({w.get('armor_piercing','?')}) "
            f"{' '.join(w.get('special_rules', []))}"
        )
else:
    st.write("—")
