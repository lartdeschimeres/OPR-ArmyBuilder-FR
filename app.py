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
# CHARGEMENT DES FACTIONS ET EXTRACTION DES JEUX
# -------------------------------------------------
if not FACTIONS_DIR.exists():
    st.error(f"Dossier factions introuvable : {FACTIONS_DIR}")
    st.stop()

faction_files = sorted(FACTIONS_DIR.glob("*.json"))

if not faction_files:
    st.error("Aucun fichier faction trouvé")
    st.stop()

# Extraire les jeux uniques depuis les fichiers
games = set()
faction_map = {}

for fp in faction_files:
    try:
        with open(fp, encoding="utf-8") as f:
            data = json.load(f)
            game = data.get("game", "Inconnu")
            games.add(game)
            name = data.get("faction", fp.stem)
            faction_map[name] = {"file": fp, "game": game}
    except Exception as e:
        st.warning(f"Impossible de lire {fp.name} : {e}")

if not games:
    st.error("Aucun jeu trouvé dans les fichiers")
    st.stop()

# Sélecteur de jeu
selected_game = st.selectbox(
    "Sélectionner le jeu",
    sorted(games)
)

# Filtrer les factions pour le jeu sélectionné
game_factions = {
    name: info for name, info in faction_map.items()
    if info["game"] == selected_game
}

if not game_factions:
    st.error(f"Aucune faction trouvée pour le jeu {selected_game}")
    st.stop()

# Sélecteur de faction
selected_faction = st.selectbox(
    "Sélectionner la faction",
    sorted(game_factions.keys())
)

# -------------------------------------------------
# CHAMP POUR LE COÛT TOTAL SOUHAITÉ DE L'ARMÉE
# -------------------------------------------------
army_target_cost = st.number_input(
    "Coût total souhaité pour l'armée (en points) :",
    min_value=0,
    value=1000,
    step=50
)

# -------------------------------------------------
# CHARGEMENT DE LA FACTION
# -------------------------------------------------
FACTION_PATH = game_factions[selected_faction]["file"]

try:
    with open(FACTION_PATH, encoding="utf-8") as f:
        faction = json.load(f)
except Exception as e:
    st.error(f"Erreur lors de la lecture du fichier {FACTION_PATH}: {e}")
    st.stop()

# -------------------------------------------------
# AFFICHAGE FACTION
# -------------------------------------------------
st.subheader(f"Faction : {faction.get('faction', 'Inconnue')}")
st.caption(f"Jeu : {faction.get('game', selected_game)}")

units = faction.get("units", [])
if not units:
    st.warning("Aucune unité disponible pour cette faction.")
    st.stop()

# -------------------------------------------------
# SESSION STATE POUR LA LISTE D'ARMÉE
# -------------------------------------------------
if "army_list" not in st.session_state:
    st.session_state.army_list = []
if "army_total_cost" not in st.session_state:
    st.session_state.army_total_cost = 0

# -------------------------------------------------
# SÉLECTEUR D'UNITÉ
# -------------------------------------------------
st.divider()
st.subheader("Configurer une unité")

if "selected_unit" not in st.session_state:
    st.session_state.selected_unit = units[0]["name"]

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
# OPTIONS & CALCUL
# -------------------------------------------------
total_cost = unit.get("base_cost", 0)
final_rules = list(unit.get("special_rules", []))
current_weapon = unit.get("weapons", [{"name": "Arme non définie", "attacks": "?", "armor_piercing": "?"}])[0]
selected_options = {}

# Affichage des armes de base
st.subheader("Armes de base")
for w in unit.get("weapons", []):
    st.write(
        f"- **{w.get('name', 'Arme non définie')}** | "
        f"A{w.get('attacks', '?')} | "
        f"PA({w.get('armor_piercing', '?')})"
    )

# -------------------------------------------------
# SÉLECTEURS D'OPTIONS
# -------------------------------------------------
for group in unit.get("upgrade_groups", []):
    key = f"{unit['name']}_{group['group']}"
    options = ["— Aucun —"] + [opt["name"] for opt in group["options"]]
    choice = st.selectbox(
        f"{group['group']}",
        options,
        key=key
    )

    if choice != "— Aucun —":
        opt = next(o for o in group["options"] if o["name"] == choice)
        total_cost += opt.get("cost", 0)
        selected_options[group["group"]] = opt
        if "special_rules" in opt:
            final_rules.extend(opt["special_rules"])
        if "weapon" in opt:
            current_weapon = opt["weapon"]
            current_weapon["name"] = opt["name"]

# -------------------------------------------------
# PROFIL FINAL DE L'UNITÉ
# -------------------------------------------------
st.divider()
st.subheader("Profil final de l'unité")

st.markdown(f"### 💰 Coût total : **{total_cost} pts**")

# -------------------------------------------------
# BOUTON POUR AJOUTER L'UNITÉ À L'ARMÉE
# -------------------------------------------------
if st.button("➕ Ajouter à l'armée"):
    st.session_state.army_list.append({
        "name": unit["name"],
        "cost": total_cost,
        "base_rules": [rule for rule in final_rules if rule not in sum([opt.get("special_rules", []) for opt in selected_options.values()], [])],
        "options": selected_options,
        "current_weapon": current_weapon,
        "quality": unit.get("quality", "?"),
        "defense": unit.get("defense", "?")
    })
    st.session_state.army_total_cost += total_cost
    st.success(f"Unité {unit['name']} ajoutée à l'armée !")

# -------------------------------------------------
# AFFICHAGE DE LA LISTE D'ARMÉE
# -------------------------------------------------
st.divider()
st.subheader("Liste de l'armée")

if not st.session_state.army_list:
    st.write("Aucune unité ajoutée pour le moment.")
else:
    for i, army_unit in enumerate(st.session_state.army_list, 1):
        with st.container():
            st.markdown(f"""
            <style>
            .army-card {{
                border: 1px solid #ccc;
                border-radius: 8px;
                padding: 15px;
                margin-bottom: 15px;
                background-color: #f9f9f9;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            .army-card-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 10px;
            }}
            .army-card-title {{
                font-size: 1.2em;
                font-weight: bold;
            }}
            .army-card-cost {{
                font-size: 1.1em;
                color: #666;
            }}
            .army-card-stats {{
                display: flex;
                gap: 10px;
                margin-bottom: 10px;
            }}
            .stat-badge {{
                background-color: #4a89dc;
                color: white;
                padding: 5px 10px;
                border-radius: 15px;
                font-size: 0.9em;
            }}
            .army-card-section {{
                margin-bottom: 10px;
            }}
            .army-card-section-title {{
                font-weight: bold;
                margin-bottom: 5px;
                color: #4a89dc;
            }}
            </style>
            <div class="army-card">
                <div class="army-card-header">
                    <div class="army-card-title">{army_unit['name']} [{i}] - {army_unit['cost']}pts</div>
                </div>
                <div class="army-card-stats">
                    <div class="stat-badge">Quality {army_unit['quality']}+</div>
                    <div class="stat-badge">Defense {army_unit['defense']}+</div>
                </div>
                <div class="army-card-section">
                    <div class="army-card-section-title">Règles spéciales</div>
                    <div>{', '.join(sorted(set(army_unit['base_rules']))) or 'Aucune'}</div>
                </div>
                <div class="army-card-section">
                    <div class="army-card-section-title">Arme équipée</div>
                    <div>
                        <strong>{army_unit['current_weapon'].get('name', 'Arme non définie')}</strong> |
                        A{army_unit['current_weapon'].get('attacks', '?')} |
                        PA({army_unit['current_weapon'].get('armor_piercing', '?')})
                        {f" | {', '.join(army_unit['current_weapon'].get('special_rules', []))}" if army_unit['current_weapon'].get('special_rules') else ''}
                    </div>
                </div>
                <div class="army-card-section">
                    <div class="army-card-section-title">Options sélectionnées</div>
                    <div>
                        {', '.join([f"{group}: {opt['name']}" for group, opt in army_unit['options'].items()]) or 'Aucune'}
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        col1, col2 = st.columns([4, 1])
        with col2:
            if st.button(f"❌ Supprimer", key=f"delete_{i}"):
                st.session_state.army_total_cost -= army_unit["cost"]
                st.session_state.army_list.pop(i-1)
                st.rerun()

    st.markdown(f"### 💰 **Coût total de l'armée : {st.session_state.army_total_cost} pts**")

# -------------------------------------------------
# INDICATEUR DE PROGRÈS
# -------------------------------------------------
progress = st.session_state.army_total_cost / army_target_cost if army_target_cost > 0 else 0.0
st.progress(progress)
st.write(f"Progression : {st.session_state.army_total_cost}/{army_target_cost} pts")
