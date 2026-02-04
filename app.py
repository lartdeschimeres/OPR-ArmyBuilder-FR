import json
import streamlit as st
from pathlib import Path
from datetime import datetime
import re
import math

# ======================================================
# INITIALISATION
# ======================================================
if "page" not in st.session_state:
    st.session_state.page = "setup"
if "army_list" not in st.session_state:
    st.session_state.army_list = []
if "army_cost" not in st.session_state:
    st.session_state.army_cost = 0
if "unit_selections" not in st.session_state:
    st.session_state.unit_selections = {}

# ======================================================
# CONFIGURATION DES JEUX
# ======================================================
GAME_COVERS = {
    "Age of Fantasy": "assets/games/aof_cover.jpg",
    "Age of Fantasy Quest": "assets/games/aofq_cover.jpg",
    "Age of Fantasy Regiments": "assets/games/aofr_cover.jpg",
    "Grimdark Future": "assets/games/gf_cover.jpg",
    "Grimdark Future Firefight": "assets/games/gff_cover.jpg",
    "Grimdark Future Squad": "assets/games/gfsq_cover.jpg",
}

BASE_DIR = Path(__file__).resolve().parent

GAME_CARDS = {
    "Grimdark Future": {
        "image": BASE_DIR / "assets/games/gf_cover.jpg",
        "description": "Escarmouches sci-fi à grande échelle"
    },
    "Grimdark Future Firefight": {
        "image": BASE_DIR / "assets/games/gff_cover.jpg",
        "description": "Combat tactique en petites escouades"
    },
    "Age of Fantasy": {
        "image": BASE_DIR / "assets/games/aof_cover.jpg",
        "description": "Batailles fantasy"
    },
    "Age of Fantasy Skirmish": {
        "image": BASE_DIR / "assets/games/aofs_cover.jpg",
        "description": "Fantasy en escarmouche"
    },
}

st.set_page_config(
    page_title="OPR Army Forge FR",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS personnalisé pour les cartes de jeu
st.markdown("""
<style>
    .game-card {
        border-radius: 8px;
        overflow: hidden;
        transition: all 0.3s ease;
        border: 2px solid transparent;
        cursor: pointer;
        min-width: 200px;
        margin: 10px;
    }
    .game-card.selected {
        border: 2px solid #4a90e2;
        box-shadow: 0 0 15px rgba(74, 144, 226, 0.5);
    }
    .game-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.2);
    }
    .game-image {
        width: 100%;
        height: 150px;
        object-fit: cover;
    }
    .game-title {
        text-align: center;
        padding: 10px;
        background: #f8f9fa;
        font-weight: bold;
    }
    .game-grid {
        display: flex;
        flex-wrap: wrap;
        justify-content: center;
        gap: 20px;
        margin-bottom: 30px;
    }
    .game-button {
        width: 100%;
        margin-top: 10px;
        background: #4a90e2;
        color: white;
        border: none;
        padding: 8px;
        border-radius: 4px;
        cursor: pointer;
    }
    .game-button:disabled {
        background: #cccccc;
        cursor: not-allowed;
    }
</style>
""", unsafe_allow_html=True)

# ======================================================
# CONFIGURATION DES JEUX
# ======================================================
GAME_CONFIG = {
    "Age of Fantasy": {
        "max_points": 10000,
        "min_points": 250,
        "default_points": 1000,
        "hero_limit": 375,
        "unit_copy_rule": 750,
        "unit_max_cost_ratio": 0.35,
        "unit_per_points": 150
    },
    "Grimdark Future": {
        "max_points": 10000,
        "min_points": 250,
        "default_points": 1000,
        "hero_limit": 375,
        "unit_copy_rule": 750,
        "unit_max_cost_ratio": 0.35,
        "unit_per_points": 150
    }
}

# ======================================================
# FONCTIONS DE VALIDATION
# ======================================================
def check_hero_limit(army_list, army_points, game_config):
    max_heroes = math.floor(army_points / game_config["hero_limit"])
    hero_count = sum(1 for unit in army_list if unit.get("type") == "hero")
    if hero_count > max_heroes:
        st.error(f"Limite de héros dépassée! Max: {max_heroes} (1 héros/{game_config['hero_limit']} pts)")
        return False
    return True

def check_unit_max_cost(army_list, army_points, game_config, new_unit_cost=None):
    max_cost = army_points * game_config["unit_max_cost_ratio"]
    for unit in army_list:
        if unit["cost"] > max_cost:
            st.error(f"Unité {unit['name']} dépasse {int(max_cost)} pts (35% du total)")
            return False
    if new_unit_cost and new_unit_cost > max_cost:
        st.error(f"Cette unité dépasse {int(max_cost)} pts (35% du total)")
        return False
    return True

def check_unit_copy_rule(army_list, army_points, game_config):
    x_value = math.floor(army_points / game_config["unit_copy_rule"])
    max_copies = 1 + x_value
    unit_counts = {}
    for unit in army_list:
        name = unit["name"]
        unit_counts[name] = unit_counts.get(name, 0) + 1
    for unit_name, count in unit_counts.items():
        if count > max_copies:
            st.error(f"Trop de copies de {unit_name}! Max: {max_copies}")
            return False
    return True

def validate_army_rules(army_list, army_points, game):
    game_config = GAME_CONFIG.get(game, {})
    return (check_hero_limit(army_list, army_points, game_config) and
            check_unit_max_cost(army_list, army_points, game_config) and
            check_unit_copy_rule(army_list, army_points, game_config))

# ======================================================
# FONCTIONS UTILITAIRES
# ======================================================
def format_weapon_details(weapon):
    if not weapon:
        return {"name": "Arme non spécifiée", "attacks": "?", "ap": "?", "special": []}
    return {
        "name": weapon.get('name', 'Arme non nommée'),
        "attacks": weapon.get('attacks', '?'),
        "ap": weapon.get('armor_piercing', '?'),
        "special": weapon.get('special_rules', [])
    }

def format_unit_option(u):
    name_part = f"{u['name']}"
    if u.get('type') == "hero":
        name_part += " [1]"
    else:
        name_part += f" [{u.get('size', 10)}]"
    qua_def = f"Qua {u['quality']}+ / Déf {u.get('defense', '?')}"
    result = f"{name_part} - {qua_def} {u['base_cost']}pts"
    return result

# ======================================================
# CHARGEMENT DES FACTIONS
# ======================================================
@st.cache_data
def load_factions():
    factions = {}
    games = set()
    FACTIONS_DIR = Path(__file__).resolve().parent / "lists" / "data" / "factions"
    for fp in FACTIONS_DIR.glob("*.json"):
        try:
            with open(fp, encoding="utf-8") as f:
                data = json.load(f)
                game = data.get("game")
                faction = data.get("faction")
                if game and faction:
                    if game not in factions:
                        factions[game] = {}
                    factions[game][faction] = data
                    games.add(game)
        except Exception as e:
            st.warning(f"Erreur chargement {fp.name}: {e}")
    return factions, sorted(games) if games else list(GAME_CONFIG.keys())

# ======================================================
# PAGE 1 – CONFIGURATION (avec cartes cliquables)
# ======================================================
if st.session_state.page == "setup":
    st.title("OPR Army Forge - Configuration")

    # Section d'import de liste
    st.divider()
    st.subheader("🔄 Recharger une liste JSON")
    uploaded = st.file_uploader(
        "Importer une liste exportée",
        type=["json"],
        key="import_json"
    )
    if uploaded is not None:
        try:
            data = json.load(uploaded)
            required_keys = {"game", "faction", "army_list", "points"}
            if not required_keys.issubset(data.keys()):
                st.error("❌ Fichier JSON invalide ou incomplet")
            else:
                st.session_state.game = data["game"]
                st.session_state.faction = data["faction"]
                st.session_state.points = data["points"]
                st.session_state.list_name = data.get("name", "Liste importée")
                st.session_state.army_list = data["army_list"]
                st.session_state.army_cost = data.get("total_cost", 0)
                factions_by_game, _ = load_factions()
                st.session_state.units = factions_by_game[st.session_state.game][st.session_state.faction]["units"]
                st.session_state.page = "army"
                st.success("✅ Liste chargée avec succès")
                st.rerun()
        except Exception as e:
            st.error(f"❌ Erreur lors du chargement : {e}")

    # Section de sélection des jeux (CARTES CLIQUABLES)
    st.divider()
    st.subheader("🎮 Choisis ton jeu")

    factions_by_game, games = load_factions()
    if not games:
        st.error("Aucun jeu trouvé")
        st.stop()

    # Grille de cartes de jeu
    st.markdown('<div class="game-grid">', unsafe_allow_html=True)

    for game_name in games:
        card = GAME_CARDS.get(game_name)
        is_selected = st.session_state.get("game") == game_name

        # Conteneur de la carte
        st.markdown(f"""
        <div class="game-card {'selected' if is_selected else ''}">
            <img class="game-image" src="file/{card['image'] if card and card.get('image') and card['image'].exists() else 'assets/games/onepagerules_round_128x128.png'}">
            <div class="game-title">{game_name}</div>
            <button class="game-button" {'disabled' if is_selected else ''} onclick="window.location.href='?game={game_name}'">
                {'✅ Sélectionné' if is_selected else '✔ Sélectionner'}
            </button>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # Gestion de la sélection via URL
    query_params = st.experimental_get_query_params()
    if "game" in query_params and query_params["game"][0] in games:
        st.session_state.game = query_params["game"][0]
        st.rerun()

    # Jeu non sélectionné → on bloque la suite
    if "game" not in st.session_state:
        st.info("⬆️ Sélectionne un jeu pour continuer")
        st.stop()

    game = st.session_state.game
    game_config = GAME_CONFIG.get(game, GAME_CONFIG["Age of Fantasy"])

    # PARAMÈTRES DE LISTE
    st.divider()
    st.subheader("⚙️ Paramètres de la liste")

    factions_by_game, _ = load_factions()
    faction = st.selectbox("Faction", factions_by_game[game].keys())
    points = st.number_input(
        "Points",
        min_value=game_config["min_points"],
        max_value=game_config["max_points"],
        value=game_config["default_points"],
        step=game_config["point_step"]
    )
    list_name = st.text_input(
        "Nom de la liste",
        f"Liste_{datetime.now().strftime('%Y%m%d')}"
    )

    # PASSAGE À LA CONSTRUCTION DE L'ARMÉE
    st.divider()
    st.markdown("### 🚀 Étape suivante")
    st.info("Tu pourras ajouter, modifier et exporter ton armée à l'étape suivante.")

    if st.button("➡️ Construire l'armée", use_container_width=True):
        st.session_state.game = game
        st.session_state.faction = faction
        st.session_state.points = points
        st.session_state.list_name = list_name
        st.session_state.units = factions_by_game[game][faction]["units"]
        st.session_state.army_list = []
        st.session_state.army_cost = 0
        st.session_state.page = "army"
        st.rerun()

# ======================================================
# PAGE 2 – CONSTRUCTEUR D'ARMÉE (inchangé)
# ======================================================
elif st.session_state.page == "army":
    # Initialisation sécurisée
    if "widget_counter" not in st.session_state:
        st.session_state.widget_counter = 0

    # Nettoyage des anciennes clés spécifiques
    if "unit" in locals():
        keys_to_clean = [k for k in st.session_state.keys()
                        if k.startswith("unit_") and unit["name"] in k]
        for k in keys_to_clean:
            del st.session_state[k]

    st.title(f"{st.session_state.list_name} - {st.session_state.army_cost}/{st.session_state.points} pts")

    if st.button("Retour à la configuration"):
        st.session_state.page = "setup"
        st.rerun()

    # Sélection de l'unité
    unit = st.selectbox(
        "Unité disponible",
        st.session_state.units,
        format_func=format_unit_option,
        key="unit_select"
    )

    # Initialisation des variables
    weapon = unit.get("weapons", [])
    selected_options = {}
    mount = None
    weapon_cost = 0
    mount_cost = 0
    upgrades_cost = 0

    # Traitement des améliorations
    for group_idx, group in enumerate(unit.get("upgrade_groups", [])):
        st.session_state.widget_counter += 1
        unique_key = f"unit_{unit['name']}_{group_idx}"

        st.subheader(group['group'])

        if group["type"] == "weapon":
            # Boutons radio pour les armes (choix unique)
            weapon_options = ["Arme de base"]
            for o in group["options"]:
                weapon_details = format_weapon_details(o["weapon"])
                weapon_options.append(f"{o['name']} (+{o['cost']} pts)")

            current_selection = st.session_state.get(f"{unique_key}_weapon", weapon_options[0])
            selected_weapon = st.radio(
                "Sélectionnez une arme",
                weapon_options,
                index=weapon_options.index(current_selection) if current_selection in weapon_options else 0,
                key=f"{unique_key}_weapon"
            )

            st.session_state[f"{unique_key}_weapon"] = selected_weapon

            if selected_weapon != "Arme de base":
                opt_name = selected_weapon.split(" (+")[0]
                opt = next((o for o in group["options"] if o["name"] == opt_name), None)
                if opt:
                    if unit.get("type") == "hero":
                        weapon = [opt["weapon"]]
                    else:
                        weapon = unit.get("weapons", []) + [opt["weapon"]]
                    weapon_cost += opt["cost"]

        elif group["type"] == "mount":
            # Boutons radio pour les montures
            mount_options = ["Aucune monture"]
            mount_map = {}
            for o in group["options"]:
                mount_options.append(f"{o['name']} (+{o['cost']} pts)")
                mount_map[f"{o['name']} (+{o['cost']} pts)"] = o

            current_selection = st.session_state.get(f"{unique_key}_mount", mount_options[0])
            selected_mount = st.radio(
                "Sélectionnez une monture",
                mount_options,
                index=mount_options.index(current_selection) if current_selection in mount_options else 0,
                key=f"{unique_key}_mount"
            )

            st.session_state[f"{unique_key}_mount"] = selected_mount

            if selected_mount != "Aucune monture":
                opt = mount_map.get(selected_mount)
                if opt:
                    mount = opt
                    mount_cost = opt["cost"]

        else:
            # Checkboxes pour les améliorations (choix multiples)
            if unit.get("type") == "hero":
                option_labels = ["Aucune amélioration"]
                option_map = {}
                for o in group["options"]:
                    label = f"{o['name']} (+{o['cost']} pts)"
                    option_labels.append(label)
                    option_map[label] = o

                current_selection = st.session_state.get(f"{unique_key}_hero", option_labels[0])
                selected = st.radio(
                    f"Amélioration – {group['group']}",
                    option_labels,
                    index=option_labels.index(current_selection) if current_selection in option_labels else 0,
                    key=f"{unique_key}_hero"
                )

                st.session_state[f"{unique_key}_hero"] = selected

                if selected != "Aucune amélioration":
                    opt = option_map.get(selected)
                    if opt:
                        selected_options[group['group']] = [opt]
                        upgrades_cost += opt["cost"]
            else:
                for o in group["options"]:
                    option_key = f"{unique_key}_{o['name']}"
                    if option_key not in st.session_state:
                        st.session_state[option_key] = False

                    if st.checkbox(
                        f"{o['name']} (+{o['cost']} pts)",
                        value=st.session_state.get(option_key, False),
                        key=option_key
                    ):
                        st.session_state[option_key] = True
                        selected_options.setdefault(group["group"], []).append(o)
                        upgrades_cost += o["cost"]
                    else:
                        st.session_state[option_key] = False

    # Doublage des effectifs (UNIQUEMENT pour les unités non-héros)
    if unit.get("type") != "hero":
        double_size = st.checkbox("Unité combinée (doubler les effectifs)")
        multiplier = 2 if double_size else 1
    else:
        multiplier = 1

    # Calcul du coût final
    base_cost = unit.get("base_cost", 0)
    core_cost = (base_cost + weapon_cost) * multiplier
    final_cost = core_cost + upgrades_cost + mount_cost

    # Affichage des informations finales
    if unit.get("type") == "hero":
        st.markdown("**Effectif final : [1]** (héros)")
    else:
        st.markdown(f"**Effectif final : [{unit.get('size', 10) * multiplier}]**")

    if st.button("Ajouter à l'armée"):
        try:
            unit_data = {
                "name": unit["name"],
                "type": unit.get("type", "unit"),
                "cost": final_cost,
                "base_cost": base_cost,
                "size": unit.get("size", 10) * multiplier if unit.get("type") != "hero" else 1,
                "quality": unit.get("quality", 3),
                "defense": unit.get("defense", 3),
                "rules": unit.get("special_rules", []),
                "weapon": weapon,
                "options": selected_options,
                "mount": mount,
                "game": st.session_state.game
            }

            # Validation des règles
            test_army = st.session_state.army_list.copy()
            test_army.append(unit_data)
            test_total = st.session_state.army_cost + final_cost

            if test_total > st.session_state.points:
                st.error(f"Limite de points dépassée! ({st.session_state.points} pts max)")
            elif not validate_army_rules(test_army, st.session_state.points, st.session_state.game):
                pass
            else:
                st.session_state.army_list.append(unit_data)
                st.session_state.army_cost += final_cost
                st.rerun()

        except Exception as e:
            st.error(f"Erreur: {str(e)}")

    # Affichage de la liste de l'armée
    st.divider()
    st.subheader("Liste de l'armée")
    if not st.session_state.army_list:
        st.info("Ajoutez des unités pour commencer")

    for i, u in enumerate(st.session_state.army_list):
        with st.expander(f"{u['name']} ({u['cost']} pts)"):
            st.markdown(f"**Qualité/Défense**: {u['quality']}+/{u['defense']}+")
            if 'weapon' in u and u['weapon']:
                st.markdown("**Armes:**")
                for w in u['weapon']:
                    st.markdown(f"- {w.get('name', 'Arme')} (A{w.get('attacks', '?')}, PA{w.get('ap', '?')})")

            if u.get("options"):
                for group_name, opts in u["options"].items():
                    st.markdown(f"**{group_name}:** {', '.join(o.get('name', '') for o in opts)}")

            if st.button(f"Supprimer {u['name']}", key=f"del_{i}"):
                st.session_state.army_cost -= u["cost"]
                st.session_state.army_list.pop(i)
                st.rerun()

    # Export
    st.divider()
    st.subheader("Exporter l'armée")
    army_data = {
        "name": st.session_state.list_name,
        "game": st.session_state.game,
        "faction": st.session_state.faction,
        "army_list": st.session_state.army_list
    }

    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "Exporter en JSON",
            json.dumps(army_data, indent=2, ensure_ascii=False),
            f"{st.session_state.list_name}.json"
        )
    with col2:
        html = f"""<!DOCTYPE html>
<html>
<head>
<style>
body {{ background: #2e2f2b; color: #e6e6e6; font-family: Arial; }}
.unit {{ background: #3a3c36; padding: 15px; margin-bottom: 20px; border-radius: 5px; }}
</style>
</head>
<body>
<h1>{st.session_state.list_name}</h1>
"""
        for unit in st.session_state.army_list:
            html += f"""
<div class="unit">
<h2>{unit['name']} [{unit['size']}] - {unit['cost']} pts</h2>
<p>Qualité {unit['quality']}+ / Défense {unit['defense']}+</p>
"""
            if 'weapon' in unit and unit['weapon']:
                html += "<h3>Armes:</h3><ul>"
                for w in unit['weapon']:
                    html += f"<li>{w.get('name', 'Arme')} (A{w.get('attacks', '?')}, PA{w.get('ap', '?')})</li>"
                html += "</ul>"
            html += "</div>"
        html += "</body></html>"

        st.download_button(
            "Exporter en HTML",
            html,
            f"{st.session_state.list_name}.html",
            mime="text/html"
        )