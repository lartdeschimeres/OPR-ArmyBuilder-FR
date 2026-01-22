import json
import streamlit as st
from pathlib import Path
from datetime import datetime
import hashlib
import re
import base64
import math
import os

# ======================================================
# CONFIGURATION POUR SIMON
# ======================================================
st.set_page_config(
    page_title="OPR Army Forge FR - Simon Joinville Fouquet",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Chemins des fichiers
BASE_DIR = Path(__file__).resolve().parent
FACTIONS_DIR = BASE_DIR / "lists" / "data" / "factions"
os.makedirs(FACTIONS_DIR, exist_ok=True)

# ======================================================
# CONFIGURATION DES JEUX ET LEURS LIMITATIONS
# ======================================================
GAME_CONFIG = {
    "Age of Fantasy": {
        "display_name": "Age of Fantasy",
        "max_points": 10000,
        "min_points": 250,
        "default_points": 1000,
        "point_step": 250,
        "description": "Jeu de bataille rangée dans un univers fantasy médiéval",
        "hero_limit": 375,
        "unit_copy_rule": 750,
        "unit_max_cost_ratio": 0.35,
        "unit_per_points": 150
    }
}

# ======================================================
# FONCTIONS POUR LES RÈGLES SPÉCIFIQUES
# ======================================================
def check_hero_limit(army_list, army_points, game_config):
    """Vérifie la limite de héros"""
    if game_config.get("hero_limit"):
        max_heroes = math.floor(army_points / game_config["hero_limit"])
        hero_count = sum(1 for unit in army_list if unit.get("type") == "hero")
        return hero_count <= max_heroes
    return True

def check_unit_max_cost(army_list, army_points, game_config, new_unit_cost=None):
    """Vérifie qu'aucune unité ne dépasse le ratio maximum de coût"""
    if not game_config.get("unit_max_cost_ratio"):
        return True

    max_cost = army_points * game_config["unit_max_cost_ratio"]

    # Vérifier les unités existantes
    for unit in army_list:
        if unit["cost"] > max_cost:
            return False

    # Vérifier la nouvelle unité si fournie
    if new_unit_cost and new_unit_cost > max_cost:
        return False

    return True

# ======================================================
# FONCTIONS UTILITAIRES
# ======================================================
def format_unit_option(u):
    """Formate l'affichage des unités dans la liste déroulante"""
    name_part = f"{u['name']}"

    # Pour les héros, toujours afficher [1]
    if u.get('type') == "hero":
        name_part += " [1]"
    else:
        # Pour les unités normales, afficher la taille de base
        base_size = u.get('size', 10)
        name_part += f" [{base_size}]"

    qua_def = f"Qua {u['quality']}+ / Déf {u.get('defense', '?')}"

    weapons_part = ""
    if 'weapons' in u and u['weapons']:
        weapon = u['weapons'][0]
        weapons_part = f"{weapon.get('name', 'Arme')} (A{weapon.get('attacks', '?')}, PA({weapon.get('armor_piercing', '?')}))"

    rules_part = ""
    if 'special_rules' in u and u['special_rules']:
        rules_part = ", ".join(u['special_rules'])

    result = f"{name_part} - {qua_def}"

    if weapons_part:
        result += f" - {weapons_part}"

    if rules_part:
        result += f" - {rules_part}"

    result += f" {u['base_cost']}pts"
    return result

# ======================================================
# LOCAL STORAGE
# ======================================================
def ls_get(key):
    """Récupère une valeur du LocalStorage"""
    try:
        unique_key = f"{key}_{hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()[:8]}"
        st.markdown(
            f"""
            <script>
            const value = localStorage.getItem("{key}");
            const input = document.createElement("input");
            input.type = "hidden";
            input.id = "{unique_key}";
            input.value = value || "";
            document.body.appendChild(input);
            </script>
            """,
            unsafe_allow_html=True
        )
        return st.text_input("", key=unique_key, label_visibility="collapsed")
    except Exception:
        return None

def ls_set(key, value):
    """Stocke une valeur dans le LocalStorage"""
    try:
        if not isinstance(value, str):
            value = json.dumps(value)
        escaped_value = value.replace("'", "\\'").replace('"', '\\"')
        st.markdown(
            f"""
            <script>
            localStorage.setItem("{key}", `{escaped_value}`);
            </script>
            """,
            unsafe_allow_html=True
        )
    except Exception:
        pass

# ======================================================
# CHARGEMENT DES FACTIONS
# ======================================================
@st.cache_data
def load_factions():
    """Charge les factions depuis les fichiers JSON"""
    factions = {}
    games = set()

    # Création d'un fichier de faction par défaut si le dossier est vide
    if not list(FACTIONS_DIR.glob("*.json")):
        default_faction = {
            "game": "Age of Fantasy",
            "faction": "Disciples de la Guerre",
            "units": [
                {
                    "name": "Barbares de la Guerre",
                    "type": "unit",
                    "size": 10,
                    "base_cost": 50,
                    "quality": 3,
                    "defense": 5,
                    "special_rules": ["Éclaireur", "Furieux", "Né pour la guerre"],
                    "weapons": [{
                        "name": "Armes à une main",
                        "attacks": 1,
                        "armor_piercing": 0,
                        "special_rules": []
                    }]
                },
                {
                    "name": "Maître de la Guerre Élu",
                    "type": "hero",
                    "size": 1,
                    "base_cost": 150,
                    "quality": 3,
                    "defense": 5,
                    "special_rules": ["Héros", "Éclaireur", "Furieux"],
                    "weapons": [{
                        "name": "Arme héroïque",
                        "attacks": 2,
                        "armor_piercing": 1,
                        "special_rules": ["Magique(1)"]
                    }]
                }
            ]
        }
        with open(FACTIONS_DIR / "default.json", "w", encoding="utf-8") as f:
            json.dump(default_faction, f, indent=2)

    # Chargement des factions existantes
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
        except Exception:
            continue

    # Si aucun jeu trouvé, on utilise Age of Fantasy par défaut
    if not games:
        games = ["Age of Fantasy"]
        factions = {
            "Age of Fantasy": {
                "Disciples de la Guerre": {
                    "game": "Age of Fantasy",
                    "faction": "Disciples de la Guerre",
                    "units": [
                        {
                            "name": "Barbares de la Guerre",
                            "type": "unit",
                            "size": 10,
                            "base_cost": 50,
                            "quality": 3,
                            "defense": 5,
                            "special_rules": ["Éclaireur", "Furieux", "Né pour la guerre"],
                            "weapons": [{
                                "name": "Armes à une main",
                                "attacks": 1,
                                "armor_piercing": 0,
                                "special_rules": []
                            }]
                        }
                    ]
                }
            }
        }

    return factions, sorted(games)

# ======================================================
# INITIALISATION
# ======================================================
try:
    factions_by_game, games = load_factions()
except Exception:
    factions_by_game = {
        "Age of Fantasy": {
            "Disciples de la Guerre": {
                "game": "Age of Fantasy",
                "faction": "Disciples de la Guerre",
                "units": [
                    {
                        "name": "Barbares de la Guerre",
                        "type": "unit",
                        "size": 10,
                        "base_cost": 50,
                        "quality": 3,
                        "defense": 5,
                        "special_rules": ["Éclaireur", "Furieux", "Né pour la guerre"],
                        "weapons": [{
                            "name": "Armes à une main",
                            "attacks": 1,
                            "armor_piercing": 0,
                            "special_rules": []
                        }]
                    }
                ]
            }
        }
    }
    games = ["Age of Fantasy"]

if "page" not in st.session_state:
    st.session_state.page = "setup"
    st.session_state.army_list = []
    st.session_state.army_cost = 0

# ======================================================
# PAGE 1 – CONFIGURATION
# ======================================================
if st.session_state.page == "setup":
    st.title("OPR Army Forge FR")

    # Affichage des informations sur les jeux disponibles
    st.subheader("Jeux disponibles")
    for game_key, config in GAME_CONFIG.items():
        with st.expander(f"📖 {config['display_name']}"):
            st.markdown(f"""
            **Description**: {config['description']}
            - **Points**: {config['min_points']} à {config['max_points']} (défaut: {config['default_points']})
            """)

    # Liste des listes sauvegardées
    st.subheader("Mes listes sauvegardées")

    # Chargement des listes sauvegardées
    saved_lists = ls_get("opr_saved_lists")
    if saved_lists:
        try:
            saved_lists = json.loads(saved_lists)
            if isinstance(saved_lists, list):
                for i, saved_list in enumerate(saved_lists):
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.markdown(f"**{saved_list.get('name', 'Liste sans nom')}**")
                        st.caption(f"{saved_list.get('game', 'Inconnu')} • {saved_list.get('faction', 'Inconnue')} • {saved_list.get('total_cost', 0)}/{saved_list.get('points', 0)} pts")
                    with col2:
                        if st.button(f"Charger", key=f"load_{i}"):
                            st.session_state.game = saved_list["game"]
                            st.session_state.faction = saved_list["faction"]
                            st.session_state.points = saved_list["points"]
                            st.session_state.list_name = saved_list["name"]
                            st.session_state.army_list = saved_list["army_list"]
                            st.session_state.army_cost = saved_list["total_cost"]
                            st.session_state.units = factions_by_game[saved_list["game"]][saved_list["faction"]]["units"]
                            st.session_state.page = "army"
                            st.rerun()
        except Exception:
            pass

    if not games:
        st.error("Aucun jeu trouvé")
        st.stop()

    # Sélection du jeu
    game = st.selectbox("Jeu", games)
    game_config = GAME_CONFIG.get(game, GAME_CONFIG["Age of Fantasy"])

    points = st.number_input(
        "Points",
        min_value=game_config["min_points"],
        max_value=game_config["max_points"],
        value=game_config["default_points"],
        step=game_config["point_step"]
    )

    list_name = st.text_input("Nom de la liste", f"Liste_{datetime.now().strftime('%Y%m%d')}")

    # Import JSON
    uploaded = st.file_uploader("Importer une liste JSON", type=["json"])
    if uploaded:
        try:
            data = json.load(uploaded)
            if not all(key in data for key in ["game", "faction", "army_list"]):
                st.error("Format JSON invalide")
                st.stop()

            st.session_state.game = data["game"]
            st.session_state.faction = data["faction"]
            st.session_state.points = data["points"]
            st.session_state.list_name = data["name"]
            st.session_state.army_list = data["army_list"]
            st.session_state.army_cost = data["total_cost"]
            st.session_state.units = factions_by_game[data["game"]][data["faction"]]["units"]
            st.session_state.page = "army"
            st.rerun()
        except Exception as e:
            st.error(f"Erreur d'import: {str(e)}")

    if st.button("Créer une nouvelle liste"):
        st.session_state.game = game
        st.session_state.faction = st.selectbox("Faction", list(factions_by_game[game].keys()))
        st.session_state.points = points
        st.session_state.list_name = list_name
        st.session_state.units = factions_by_game[game][st.session_state.faction]["units"]
        st.session_state.army_list = []
        st.session_state.army_cost = 0
        st.session_state.page = "army"
        st.rerun()

# ======================================================
# PAGE 2 – CONSTRUCTEUR D'ARMÉE
# ======================================================
elif st.session_state.page == "army":
    st.title(st.session_state.list_name)
    st.caption(f"{st.session_state.game} • {st.session_state.faction} • {st.session_state.army_cost}/{st.session_state.points} pts")

    if st.button("⬅ Retour"):
        st.session_state.page = "setup"
        st.rerun()

    # Ajout d'une unité
    st.divider()
    st.subheader("Ajouter une unité")

    # Sélection de l'unité
    unit = st.selectbox(
        "Unité disponible",
        st.session_state.units,
        format_func=format_unit_option,
        index=0,
        key="unit_select"
    )

    # Récupération des données de base
    base_size = unit.get('size', 10)
    base_cost = unit["base_cost"]

    # Gestion des unités combinées - CORRECTION DÉFINITIVE POUR LES HÉROS
    if unit.get("type") == "hero":
        combined = False  # Les héros ne peuvent JAMAIS être combinés
    else:
        combined = st.checkbox("Unité combinée", value=False)

    # Calcul du coût final
    if combined and unit.get("type") != "hero":
        final_cost = (base_cost) * 2  # On double le coût de base pour les unités combinées
        unit_size = base_size * 2
    else:
        final_cost = base_cost
        unit_size = base_size

    st.markdown(f"**Coût total: {final_cost} pts**")
    st.markdown(f"**Taille de l'unité: {unit_size} figurines**")

    if st.button("Ajouter à l'armée"):
        try:
            unit_data = {
                "name": unit["name"],
                "type": unit.get("type", "unit"),
                "cost": final_cost,
                "base_cost": base_cost,
                "size": unit_size,
                "quality": unit["quality"],
                "defense": unit.get("defense", 3),
                "rules": unit.get("special_rules", []),
                "weapon": unit.get("weapons", [{}])[0],
                "combined": combined and unit.get("type") != "hero",
            }

            st.session_state.army_list.append(unit_data)
            st.session_state.army_cost += final_cost
            st.rerun()

        except Exception as e:
            st.error(f"Erreur lors de la création de l'unité: {str(e)}")

    # Liste de l'armée
    st.divider()
    st.subheader("Liste de l'armée")

    if not st.session_state.army_list:
        st.info("Ajoutez des unités pour commencer")

    for i, u in enumerate(st.session_state.army_list):
        with st.container():
            unit_header = f"### {u['name']} [{u.get('size', 10)}] ({u['cost']} pts) | Qua {u['quality']}+ / Déf {u.get('defense', '?')}+"
            if u.get("type") == "hero":
                unit_header += " | 🌟 Héros"
            st.markdown(unit_header)

            if u.get("rules"):
                rules_text = ", ".join(u["rules"])
                st.markdown(f"**Règles spéciales:** {rules_text}")

            if 'weapon' in u and u['weapon']:
                st.markdown(f"**Arme:** {u['weapon'].get('name', 'Arme non nommée')} (A{u['weapon'].get('attacks', '?')}, PA({u['weapon'].get('armor_piercing', '?')}))")

            if st.button(f"Supprimer {u['name']}", key=f"del_{i}"):
                st.session_state.army_cost -= u["cost"]
                st.session_state.army_list.pop(i)
                st.rerun()

    # Sauvegarde/Export
    st.divider()
    col1, col2 = st.columns(2)

    army_data = {
        "name": st.session_state.list_name,
        "game": st.session_state.game,
        "faction": st.session_state.faction,
        "points": st.session_state.points,
        "total_cost": st.session_state.army_cost,
        "army_list": st.session_state.army_list,
        "date": datetime.now().isoformat()
    }

    with col1:
        if st.button("Sauvegarder"):
            saved_lists = []
            try:
                existing_lists = ls_get("opr_saved_lists")
                if existing_lists:
                    saved_lists = json.loads(existing_lists)
            except:
                pass

            saved_lists.append(army_data)
            try:
                ls_set("opr_saved_lists", saved_lists)
            except:
                st.warning("La sauvegarde locale n'est pas disponible, mais vous pouvez exporter en JSON.")
            st.success("Liste sauvegardée!")

    with col2:
        st.download_button(
            "Exporter en JSON",
            json.dumps(army_data, indent=2, ensure_ascii=False),
            file_name=f"{st.session_state.list_name}.json",
            mime="application/json"
        )

        # Export HTML
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Liste OPR - {army_data['name']}</title>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 20px;
                    color: #333;
                }}
                .army-title {{
                    text-align: center;
                    margin-bottom: 20px;
                    color: #2c3e50;
                }}
                .unit-container {{
                    background-color: white;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    margin-bottom: 20px;
                    padding: 20px;
                }}
                .unit-header {{
                    font-size: 1.5em;
                    font-weight: bold;
                    margin-bottom: 10px;
                    color: #2c3e50;
                }}
                .hero-badge {{
                    background-color: gold;
                    color: black;
                    padding: 2px 8px;
                    border-radius: 10px;
                    margin-left: 10px;
                    font-weight: bold;
                }}
            </style>
        </head>
        <body>
            <h1 class="army-title">Liste d'armée OPR - {army_data['name']}</h1>
            <div class="army-info">
                <strong>Jeu:</strong> {army_data['game']} |
                <strong>Faction:</strong> {army_data['faction']} |
                <strong>Points:</strong> {army_data['total_cost']}/{army_data['points']}
            </div>
        """

        for unit in army_data['army_list']:
            unit_name = f"{unit['name']} [{unit.get('size', 10)}]"
            hero_badge = '<span class="hero-badge">HÉROS</span>' if unit.get('type') == "hero" else ""

            html_content += f"""
            <div class="unit-container">
                <div class="unit-header">
                    {unit_name} ({unit['cost']} pts)
                    {hero_badge}
                </div>
                <div>Qualité: {unit['quality']}+ / Défense: {unit.get('defense', '?')}+</div>
            """

            if unit.get('rules'):
                rules_text = ", ".join(unit['rules'])
                html_content += f"<div><strong>Règles spéciales:</strong> {rules_text}</div>"

            if 'weapon' in unit and unit['weapon']:
                html_content += f"<div><strong>Arme:</strong> {unit['weapon'].get('name', 'Arme non nommée')} (A{unit['weapon'].get('attacks', '?')}, PA({unit['weapon'].get('armor_piercing', '?')}))</div>"

            html_content += "</div>"

        html_content += """
        </body>
        </html>
        """

        st.download_button(
            "Exporter en HTML",
            html_content,
            file_name=f"{st.session_state.list_name}.html",
            mime="text/html"
        )
