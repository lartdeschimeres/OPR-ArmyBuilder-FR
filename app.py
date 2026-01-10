import json
from pathlib import Path
import streamlit as st

# -------------------------------------------------
# CONFIG GÉNÉRALE
# -------------------------------------------------
st.set_page_config(page_title="OPR Army Builder FR", layout="centered")
st.title("OPR Army Builder 🇫🇷")

BASE_DIR = Path(__file__).resolve().parent
FACTIONS_DIR = BASE_DIR / "lists" / "data" / "factions"

# -------------------------------------------------
# CHARGEMENT DES FACTIONS
# -------------------------------------------------
if not FACTIONS_DIR.exists():
    st.error(f"Dossier factions introuvable : {FACTIONS_DIR}")
    st.stop()

faction_files = sorted(FACTIONS_DIR.glob("*.json"))
if not faction_files:
    st.error("Aucun fichier faction trouvé")
    st.stop()

games = set()
faction_map = {}

for fp in faction_files:
    try:
        with open(fp, encoding="utf-8") as f:
            data = json.load(f)
            game = data.get("game", "Inconnu")
            name = data.get("faction", fp.stem)
            games.add(game)
            faction_map[name] = {"file": fp, "game": game}
    except Exception as e:
        st.warning(f"Impossible de lire {fp.name} : {e}")

# -------------------------------------------------
# SÉLECTEURS JEU / FACTION
# -------------------------------------------------
selected_game = st.selectbox("Sélectionner le jeu", sorted(games))

game_factions = {
    name: info for name, info in faction_map.items()
    if info["game"] == selected_game
}

selected_faction = st.selectbox(
    "Sélectionner la faction",
    sorted(game_factions.keys())
)

# -------------------------------------------------
# OBJECTIF DE POINTS
# -------------------------------------------------
army_target_cost = st.number_input(
    "Coût total souhaité pour l'armée",
    min_value=0,
    value=1000,
    step=50
)

# -------------------------------------------------
# CHARGEMENT FACTION
# -------------------------------------------------
FACTION_PATH = game_factions[selected_faction]["file"]

with open(FACTION_PATH, encoding="utf-8") as f:
    faction = json.load(f)

st.subheader(f"Faction : {faction['faction']}")
st.caption(f"Jeu : {faction['game']}")

units = faction.get("units", [])
if not units:
    st.warning("Aucune unité disponible")
    st.stop()

# -------------------------------------------------
# SESSION STATE
# -------------------------------------------------
if "army_list" not in st.session_state:
    st.session_state.army_list = []

if "army_total_cost" not in st.session_state:
    st.session_state.army_total_cost = 0

# -------------------------------------------------
# CONFIGURATION D’UNITÉ
# -------------------------------------------------
st.divider()
st.subheader("Configurer une unité")

unit_names = [u["name"] for u in units]

selected_name = st.selectbox(
    "Choisir une unité",
    unit_names,
    format_func=lambda n: next(
        f"{u['name']} ({u['base_cost']} pts | Q{u['quality']}+ / D{u['defense']}+)"
        for u in units if u["name"] == n
    )
)

unit = next(u for u in units if u["name"] == selected_name)

total_cost = unit["base_cost"]
final_rules = list(unit.get("special_rules", []))
current_weapon = unit["weapons"][0]
selected_options = {}
selected_mount = None

# -------------------------------------------------
# ARMES DE BASE
# -------------------------------------------------
st.subheader("Armes de base")
for w in unit.get("weapons", []):
    st.write(
        f"- **{w['name']}** | A{w['attacks']} | PA({w['armor_piercing']})"
    )

# -------------------------------------------------
# OPTIONS
# -------------------------------------------------
for group in unit.get("upgrade_groups", []):
    key = f"{unit['name']}_{group['group']}"
    options = ["— Aucun —"] + [o["name"] for o in group["options"]]

    choice = st.selectbox(group["group"], options, key=key)

    if choice != "— Aucun —":
        opt = next(o for o in group["options"] if o["name"] == choice)
        total_cost += opt.get("cost", 0)

        if group["type"] == "mount":
            selected_mount = opt
        else:
            selected_options[group["group"]] = opt

        final_rules.extend(opt.get("special_rules", []))

        if "weapon" in opt:
            current_weapon = opt["weapon"] | {"name": opt["name"]}

# -------------------------------------------------
# PROFIL FINAL
# -------------------------------------------------
st.divider()
st.subheader("Profil final")
st.markdown(f"### 💰 Coût total : **{total_cost} pts**")

# -------------------------------------------------
# AJOUT À L’ARMÉE
# -------------------------------------------------
if st.button("➕ Ajouter à l'armée"):
    st.session_state.army_list.append({
        "name": unit["name"],
        "cost": total_cost,
        "rules": final_rules,
        "options": selected_options,
        "mount": selected_mount,
        "weapon": current_weapon,
        "quality": unit["quality"],
        "defense": unit["defense"]
    })
    st.session_state.army_total_cost += total_cost
    st.success("Unité ajoutée à l'armée")

# -------------------------------------------------
# LISTE DE L’ARMÉE
# -------------------------------------------------
st.divider()
st.subheader("Liste de l'armée")

if not st.session_state.army_list:
    st.write("Aucune unité ajoutée.")
else:
    for i, u in enumerate(st.session_state.army_list, 1):
        col_card, col_btn = st.columns([5, 1])

        with col_card:
            st.markdown(f"""
<div style="border:1px solid #ccc;
            border-radius:8px;
            padding:15px;
            margin-bottom:15px;
            background:#f9f9f9">

<strong>{u['name']} [{i}]</strong> — {u['cost']} pts<br><br>

<div style="display:flex; gap:10px; margin-bottom:10px">
  <span style="background:#4a89dc;
               color:white;
               padding:4px 12px;
               border-radius:14px;
               font-size:0.9em">
    Qualité {u['quality']}+
  </span>
  <span style="background:#5cb85c;
               color:white;
               padding:4px 12px;
               border-radius:14px;
               font-size:0.9em">
    Défense {u['defense']}+
  </span>
</div>

<strong>Règles spéciales :</strong><br>
{', '.join(sorted(set(u.get('base_rules', [])))) or 'Aucune'}
<br><br>

<strong>Arme :</strong><br>
{u['weapon']['name']} |
A{u['weapon']['attacks']} |
PA({u['weapon']['armor_piercing']})
{f" | {', '.join(u['weapon'].get('special_rules', []))}" if u['weapon'].get('special_rules') else ''}
<br><br>

<strong>Options sélectionnées :</strong><br>
{', '.join(opt['name'] for opt in u['options'].values()) or 'Aucune'}
<br><br>

{f"""
<strong style="color:#4a89dc">Monture :</strong><br>
{u['mount']['name']} — {', '.join(u['mount'].get('special_rules', []))}
""" if u.get("mount") else ""}

</div>
""", unsafe_allow_html=True)

        with col_btn:
            if st.button("❌", key=f"delete_{i}"):
                st.session_state.army_total_cost -= u["cost"]
                st.session_state.army_list.pop(i - 1)
                st.rerun()

# -------------------------------------------------
# TOTAL & PROGRESSION
# -------------------------------------------------
st.markdown(f"### 💰 Coût total de l'armée : {st.session_state.army_total_cost} pts")
st.progress(
    st.session_state.army_total_cost / army_target_cost
    if army_target_cost > 0 else 0
)
