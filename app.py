import json
import streamlit as st
from pathlib import Path
from datetime import datetime
import re
import math

st.set_page_config(
    page_title="OPR Army Forge",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown(
    """
    <style>
    /* --- Nettoyage Streamlit --- */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {background: transparent;}

    /* --- Fond général --- */
    .stApp {
        background: #121212;
        color: #e0e0e0;
    }

    /* --- Sidebar --- */
    section[data-testid="stSidebar"] {
        background: #1e1e1e;
        border-right: 1px solid #333;
    }

    /* --- Titres --- */
    h1, h2, h3 {
        color: #bb86fc;
        letter-spacing: 0.04em;
    }

    /* --- Cartes --- */
    .card {
        background: #2d2d2d;
        border: 2px solid #bb86fc;
        border-radius: 8px;
        padding: 1.2rem;
        transition: all 0.2s ease;
        cursor: pointer;
        box-shadow: 0 0 10px rgba(187, 134, 252, 0.2);
    }

    .card:hover {
        border-color: #9c27b0;
        box-shadow: 0 0 20px rgba(187, 134, 252, 0.4);
        transform: translateY(-2px);
    }

    /* --- Badges --- */
    .badge {
        display: inline-block;
        padding: 0.25rem 0.6rem;
        border-radius: 4px;
        background: #bb86fc;
        color: white;
        font-size: 0.75rem;
        margin-bottom: 0.5rem;
        font-weight: bold;
    }

    /* --- Boutons --- */
    button[kind="primary"] {
        background: linear-gradient(135deg, #bb86fc, #9c27b0) !important;
        color: white !important;
        font-weight: bold;
        border-radius: 6px;
        padding: 0.6rem 1rem;
        border: none;
    }

    /* --- Règles et sorts --- */
    .rule-item, .spell-item {
        font-size: 14px;
        margin-bottom: 5px;
        display: flex;
        align-items: center;
    }

    .rule-name, .spell-name {
        font-weight: bold;
        color: #bb86fc;
        margin-right: 10px;
    }

    .rule-description, .spell-description {
        color: #ccc;
    }

    /* --- Expanders --- */
    .stExpander {
        background-color: #1e1e1e;
        border-radius: 8px;
        border: 1px solid #333;
        margin-bottom: 10px;
    }

    /* --- Progress bars --- */
    .stProgress > div > div > div {
        background: linear-gradient(90deg, #bb86fc, #9c27b0);
    }

    /* --- Inputs --- */
    div[data-baseweb="select"] > div,
    div[data-baseweb="input"] input,
    div[data-baseweb="base-input"] input {
        background-color: #2d2d2d !important;
        color: #e0e0e0 !important;
        border: 1px solid #bb86fc !important;
        border-radius: 6px !important;
        font-weight: 500;
    }

    div[data-baseweb="select"] span {
        color: #e0e0e0 !important;
    }

    /* --- Checkbox --- */
    [role="checkbox"] {
        color: #e0e0e0;
    }

    /* --- Radio buttons --- */
    [role="radiogroup"] > div[data-baseweb="radio"] label {
        color: #e0e0e0;
    }

    [role="radiogroup"] > div[data-baseweb="radio"] div {
        background: #2d2d2d;
        border: 1px solid #bb86fc;
    }

    [role="radiogroup"] > div[data-baseweb="radio"] div:hover {
        background: #bb86fc;
        color: #000;
    }
    </style>
    """,
    unsafe_allow_html=True
)

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
if "game" not in st.session_state:
    st.session_state.game = None
if "faction" not in st.session_state:
    st.session_state.faction = None
if "points" not in st.session_state:
    st.session_state.points = 0
if "list_name" not in st.session_state:
    st.session_state.list_name = ""
if "units" not in st.session_state:
    st.session_state.units = []
if "faction_special_rules" not in st.session_state:  # Modifié
    st.session_state.faction_special_rules = []  # Modifié
if "faction_spells" not in st.session_state:
    st.session_state.faction_spells = []

# ======================================================
# SIDEBAR – CONTEXTE & NAVIGATION
# ======================================================
with st.sidebar:
    st.markdown(
        "<div style='height:1px;'></div>",
        unsafe_allow_html=True
    )

with st.sidebar:
    st.title("🛡️ Army Forge")

    st.subheader("📋 Armée")

    game = st.session_state.get("game", "—")
    faction = st.session_state.get("faction", "—")
    points = st.session_state.get("points", 0)
    army_cost = st.session_state.get("army_cost", 0)

    st.markdown(f"**Jeu :** {game}")
    st.markdown(f"**Faction :** {faction}")
    st.markdown(f"**Format :** {points} pts")

    if points > 0:
        st.progress(min(army_cost / points, 1.0))
        st.markdown(f"**Coût :** {army_cost} / {points} pts")

        if army_cost > points:
            st.error("⚠️ Dépassement de points")

    st.divider()

    st.subheader("🧭 Navigation")

    if st.button("⚙️ Configuration", use_container_width=True):
        st.session_state.page = "setup"
        st.rerun()

    if st.button("🧩 Construction", use_container_width=True):
        if all(key in st.session_state for key in ["game", "faction", "points", "list_name"]):
            st.session_state.page = "army"
            st.rerun()
        else:
            st.error("Veuillez compléter la configuration avant de passer à la construction.")

# ======================================================
# CONFIGURATION DES JEUX OPR (EXTENSIBLE)
# ======================================================
GAME_CONFIG = {
    "Age of Fantasy": {
        "min_points": 250,
        "max_points": 10000,
        "default_points": 1000,
        "hero_limit": 375,
        "unit_copy_rule": 750,
        "unit_max_cost_ratio": 0.35,
        "unit_per_points": 150
    },

    "Age of Fantasy: Regiments": {
        "min_points": 500,
        "max_points": 20000,
        "default_points": 2000,
        "hero_limit": 500,
        "unit_copy_rule": 1000,
        "unit_max_cost_ratio": 0.4,
        "unit_per_points": 200
    },

    "Grimdark Future": {
        "min_points": 250,
        "max_points": 10000,
        "default_points": 1000,
        "hero_limit": 375,
        "unit_copy_rule": 750,
        "unit_max_cost_ratio": 0.35,
        "unit_per_points": 150
    },

    "Grimdark Future: Firefight": {
        "min_points": 150,
        "max_points": 1000,
        "default_points": 300,
        "hero_limit": 300,
        "unit_copy_rule": 300,
        "unit_max_cost_ratio": 0.6,
        "unit_per_points": 100
    },

    "Age of Fantasy: Skirmish": {
        "min_points": 150,
        "max_points": 1000,
        "default_points": 300,
        "hero_limit": 300,
        "unit_copy_rule": 300,
        "unit_max_cost_ratio": 0.6,
        "unit_per_points": 100
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

def export_army_json():
    return {
        "game": st.session_state.game,
        "faction": st.session_state.faction,
        "points": st.session_state.points,
        "list_name": st.session_state.list_name,
        "army_cost": st.session_state.army_cost,
        "units": st.session_state.army_list,
        "exported_at": datetime.now().isoformat()
    }

def export_army_html():
    html = f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{st.session_state.list_name}</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background-color: #121212;
                color: #e0e0e0;
                margin: 0;
                padding: 20px;
            }}
            .container {{
                max-width: 800px;
                margin: 0 auto;
                background-color: #1e1e1e;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 0 10px rgba(0, 0, 0, 0.5);
            }}
            h1, h2 {{
                color: #bb86fc;
                text-align: center;
            }}
            .army-info {{
                display: flex;
                justify-content: space-between;
                margin-bottom: 20px;
                padding-bottom: 10px;
                border-bottom: 1px solid #444;
            }}
            .army-stats {{
                font-size: 14px;
                color: #ccc;
                text-align: right;
            }}
            .army-details {{
                color: #ccc;
            }}
            h2 {{
                font-size: 20px;
                margin-bottom: 20px;
            }}
            .unit {{
                background-color: #2d2d2d;
                border: 2px solid #bb86fc;
                border-radius: 8px;
                padding: 15px;
                margin-bottom: 15px;
            }}
            .unit-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 10px;
            }}
            .unit-name {{
                font-weight: bold;
                font-size: 16px;
                color: #bb86fc;
            }}
            .unit-cost {{
                color: #ff5252;
                font-weight: bold;
            }}
            .unit-characteristics {{
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 10px;
                margin-bottom: 15px;
            }}
            .characteristic {{
                display: flex;
                justify-content: space-between;
            }}
            .characteristic-label {{
                color: #bb86fc;
            }}
            .characteristic-value {{
                color: #fff;
            }}
            .weapons-section, .mount-section {{
                margin-top: 10px;
                padding: 10px;
                background-color: #2a2a2a;
                border-radius: 4px;
                border-left: 3px solid #bb86fc;
            }}
            .weapon-item {{
                margin-bottom: 10px;
            }}
            .weapon-name {{
                font-weight: bold;
                color: #4dd0e1;
            }}
            .weapon-details {{
                margin-left: 10px;
                color: #ccc;
            }}
            .rules-section, .spells-section {{
                margin-top: 20px;
                padding: 15px;
                background-color: #2a2a2a;
                border-radius: 6px;
                border-left: 3px solid #bb86fc;
            }}
            .rule-item, .spell-item {{
                font-size: 14px;
                margin-bottom: 5px;
                display: flex;
                align-items: center;
            }}
            .rule-name, .spell-name {{
                font-weight: bold;
                color: #bb86fc;
                margin-right: 10px;
            }}
            .rule-description, .spell-description {{
                color: #ccc;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>{st.session_state.list_name}</h1>
            <div class="army-info">
                <div class="army-details">
                    <div><strong>Jeu:</strong> {st.session_state.game}</div>
                    <div><strong>Faction:</strong> {st.session_state.faction}</div>
                </div>
                <div class="army-stats">
                    <strong>Points:</strong> {st.session_state.army_cost} / {st.session_state.points}
                </div>
            </div>
            <h2>Liste de l'Armée</h2>
    """

    for u in st.session_state.army_list:
        # Calcul de la valeur Coriace
        coriace_value = u.get('defense', 3) + (u.get('mount', {}).get('defense_bonus', 0) if u.get('mount') else 0)

        html += f"""
            <div class="unit">
                <div class="unit-header">
                    <div class="unit-name">{u['name']}</div>
                    <div class="unit-cost">{u['cost']} pts</div>
                </div>
                <div class="unit-characteristics">
                    <div class="characteristic">
                        <span class="characteristic-label">Taille:</span>
                        <span class="characteristic-value">{u.get('size', '?')}</span>
                    </div>
                    <div class="characteristic">
                        <span class="characteristic-label">Qualité:</span>
                        <span class="characteristic-value">{u.get('quality', '?')}+</span>
                    </div>
                    <div class="characteristic">
                        <span class="characteristic-label">Coriace:</span>
                        <span class="characteristic-value">{coriace_value}</span>
                    </div>
                </div>
        """

        # Ajout des armes
        if u.get('weapon'):
            html += '<div class="weapons-section"><strong>Armes:</strong>'
            for weapon in u['weapon']:
                html += f"""
                    <div class="weapon-item">
                        <span class="weapon-name">{weapon.get('name', 'Arme non nommée')}</span>
                        <div class="weapon-details">
                            <span>Attaques: {weapon.get('attacks', '?')}</span>,
                            <span>Pénétration: {weapon.get('armor_piercing', '?')}</span>
                """
                if weapon.get('special_rules'):
                    html += f'<br><span>Règles spéciales: {", ".join(weapon["special_rules"])}</span>'
                html += "</div></div>"
            html += "</div>"

        # Ajout de la monture
        if u.get('mount'):
            mount = u['mount']
            html += f"""
                <div class="mount-section">
                    <strong>Monture:</strong>
                    <div class="weapon-item">
                        <span class="weapon-name">{mount.get('name', 'Monture non nommée')}</span>
                        <div class="weapon-details">
                            <span>Bonus de défense: {mount.get('defense_bonus', 0)}</span>
                        </div>
                    </div>
                </div>
            """

        html += "</div>"

    # Ajout des règles spéciales de la faction
    if hasattr(st.session_state, 'faction_special_rules') and st.session_state.faction_special_rules:
        html += """
            <div class="rules-section">
                <h2>Règles Spéciales de la Faction</h2>
        """
        for rule in st.session_state.faction_special_rules:
            if isinstance(rule, dict):
                html += f"""
                    <div class="rule-item">
                        <span class="rule-name">{rule.get('name', 'Règle sans nom')}:</span>
                        <span class="rule-description">{rule.get('description', '')}</span>
                    </div>
                """
            else:
                html += f"""
                    <div class="rule-item">
                        <span>{rule}</span>
                    </div>
                """
        html += "</div>"

    # Ajout des sorts de la faction
    if hasattr(st.session_state, 'faction_spells') and st.session_state.faction_spells:
        html += """
            <div class="spells-section">
                <h2>Sorts de la Faction</h2>
        """
        for spell in st.session_state.faction_spells:
            if isinstance(spell, dict):
                html += f"""
                    <div class="spell-item">
                        <span class="spell-name">{spell.get('name', 'Sort sans nom')}:</span>
                        <span class="spell-description">Coût: {spell.get('cost', '?')} pts, Portée: {spell.get('range', '?')}, {spell.get('description', '')}</span>
                    </div>
                """
            else:
                html += f"""
                    <div class="spell-item">
                        <span>{spell}</span>
                    </div>
                """
        html += "</div>"

    html += """
        </div>
    </body>
    </html>
    """
    return html

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
                    if "faction_special_rules" not in data:
                        data["faction_special_rules"] = []
                    if "spells" not in data:
                        data["spells"] = []
                    factions[game][faction] = data
                    games.add(game)
        except Exception as e:
            st.warning(f"Erreur chargement {fp.name}: {e}")
    return factions, sorted(games) if games else list(GAME_CONFIG.keys())
    
# ======================================================
# PAGE 1 – CONFIGURATION
# ======================================================
if st.session_state.page == "setup":

    # --------------------------------------------------
    # TITRE
    # --------------------------------------------------
    st.markdown("## 🛡️ OPR Army Forge")
    st.markdown(
        "<p class='muted'>Construisez, équilibrez et façonnez vos armées pour "
        "Age of Fantasy et Grimdark Future.</p>",
        unsafe_allow_html=True
    )

    st.markdown("---")

    # --------------------------------------------------
    # CHARGEMENT DES FACTIONS
    # --------------------------------------------------
    factions_by_game, games = load_factions()
    if not games:
        st.error("Aucun jeu trouvé")
        st.stop()

    # --------------------------------------------------
    # CARTES DE CONFIGURATION
    # --------------------------------------------------
    col1, col2, col3 = st.columns(3)

    # --- JEU ---
    with col1:
        st.markdown("<span class='badge'>Jeu</span>", unsafe_allow_html=True)
        game = st.selectbox(
            "Choisissez un système",
            games,
            index=games.index(st.session_state.get("game")) if st.session_state.get("game") in games else 0,
            label_visibility="collapsed"
        )

    # --- FACTION ---
    with col2:
        st.markdown("<span class='badge'>Faction</span>", unsafe_allow_html=True)
        faction = st.selectbox(
            "Faction",
            list(factions_by_game[game].keys()),
            index=0,
            label_visibility="collapsed"
        )

    # --- FORMAT ---
    with col3:
        st.markdown("<span class='badge'>Format</span>", unsafe_allow_html=True)
        game_cfg = GAME_CONFIG.get(game, {})
        points = st.number_input(
            "Points",
            min_value=game_cfg.get("min_points", 250),
            max_value=game_cfg.get("max_points", 10000),
            value=game_cfg.get("default_points", 1000),
            step=250,
            label_visibility="collapsed"
        )

    st.markdown("")

    # --------------------------------------------------
    # NOM DE LA LISTE + ACTION
    # --------------------------------------------------
    colA, colB = st.columns([2, 1])

    with colA:
        st.markdown("<span class='badge'>Nom de la liste</span>", unsafe_allow_html=True)
        list_name = st.text_input(
            "Nom de la liste",
            value=st.session_state.get(
                "list_name",
                f"Liste_{datetime.now().strftime('%Y%m%d')}"
            ),
            label_visibility="collapsed"
        )

    with colB:
        st.markdown("<span class='badge'>Action</span>", unsafe_allow_html=True)
        st.markdown(
            "<p class='muted'>Prêt à forger votre armée ?</p>",
            unsafe_allow_html=True
        )

        can_build = all([game, faction, points > 0, list_name.strip() != ""])

        if st.button(
            "🔥 Construire l’armée",
            use_container_width=True,
            type="primary",
            disabled=not can_build
        ):
            st.session_state.game = game
            st.session_state.faction = faction
            st.session_state.points = points
            st.session_state.list_name = list_name

            faction_data = factions_by_game[game][faction]
            st.session_state.units = faction_data["units"]
            st.session_state.faction_special_rules = faction_data.get("faction_special_rules", [])
            st.session_state.faction_spells = faction_data.get("spells", [])

            st.session_state.army_list = []
            st.session_state.army_cost = 0
            st.session_state.unit_selections = {}

            st.session_state.page = "army"
            st.rerun()

# ======================================================
# PAGE 2 – CONSTRUCTEUR D'ARMÉE
# ======================================================
elif st.session_state.page == "army":
    if not all(key in st.session_state for key in ["game", "faction", "points", "list_name", "units", "faction_spells"]):
        st.error("Erreur de configuration. Veuillez retourner à la page de configuration.")
        st.stop()

    # ======================================================
    # SÉCURISATION DU SESSION STATE
    # ======================================================
    st.session_state.setdefault("list_name", "Nouvelle Armée")
    st.session_state.setdefault("army_cost", 0)
    st.session_state.setdefault("army_list", [])
    st.session_state.setdefault("unit_selections", {})

    # ======================================================
    # TITRE & NAVIGATION
    # ======================================================
    st.title(
        f"{st.session_state.list_name} "
        f"- {st.session_state.army_cost}/{st.session_state.points} pts"
    )

    if st.button("⬅️ Retour à la configuration"):
        st.session_state.page = "setup"
        st.rerun()

    st.divider()
    st.subheader("📤 Export de la liste")

    colE1, colE2 = st.columns(2)

    with colE1:
        json_data = json.dumps(export_army_json(), indent=2, ensure_ascii=False)
        st.download_button(
            "📄 Export JSON",
            data=json_data,
            file_name=f"{st.session_state.list_name}.json",
            mime="application/json",
            use_container_width=True
        )

    with colE2:
        html_data = export_army_html()
        st.download_button(
            "🌐 Export HTML",
            data=html_data,
            file_name=f"{st.session_state.list_name}.html",
            mime="text/html",
            use_container_width=True
        )

    # ======================================================
    # BARRE DE PROGRESSION DES POINTS
    # ======================================================
    st.subheader("📊 Points de l'Armée")
    points_used = st.session_state.army_cost
    points_total = st.session_state.points
    progress_ratio = min(points_used / points_total, 1.0) if points_total > 0 else 0

    # Affichage de la barre de progression
    st.progress(progress_ratio)

    # Affichage des points en texte
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Points utilisés :** {points_used} pts")
    with col2:
        st.markdown(f"**Points totaux :** {points_total} pts")

    # Avertissement si dépassement
    if points_used > points_total:
        st.error("⚠️ Dépassement du total de points autorisé")

    st.divider()

    # ======================================================
    # BARRE DE PROGRESSION – PALIERS D’ARMÉE
    # ======================================================
    points = st.session_state.points
    game_cfg = GAME_CONFIG.get(st.session_state.game, {})

    st.subheader("📊 Progression de l’armée")
    col1, col2, col3 = st.columns(3)

    with col1:
        units_cap = math.floor(points / game_cfg.get("unit_per_points", 150))
        units_now = len(
            [u for u in st.session_state.army_list if u.get("type") != "hero"]
        )
        st.progress(min(units_now / max(units_cap, 1), 1.0))
        st.caption(f"Unités : {units_now} / {units_cap}")

    with col2:
        heroes_cap = math.floor(points / game_cfg.get("hero_limit", 375))
        heroes_now = len(
            [u for u in st.session_state.army_list if u.get("type") == "hero"]
        )
        st.progress(min(heroes_now / max(heroes_cap, 1), 1.0))
        st.caption(f"Héros : {heroes_now} / {heroes_cap}")

    with col3:
        copy_cap = 1 + math.floor(points / game_cfg.get("unit_copy_rule", 750))
        st.progress(min(copy_cap / 5, 1.0))
        st.caption(f"Copies max : {copy_cap} / unité")

    st.divider()

    # ======================================================
    # RÈGLES SPÉCIALES DE FACTION
    # ======================================================
    if hasattr(st.session_state, 'faction_special_rules') and st.session_state.faction_special_rules:
        with st.expander("📜 Règles spéciales de la faction", expanded=True):
            for rule in st.session_state.faction_special_rules:
                if isinstance(rule, dict):
                    st.markdown(f"**{rule.get('name', 'Règle sans nom')}**: {rule.get('description', '')}", unsafe_allow_html=True)
                else:
                    st.markdown(f"- {rule}", unsafe_allow_html=True)

    # ======================================================
    # SORTS DE LA FACTION
    # ======================================================
    if hasattr(st.session_state, 'faction_spells') and st.session_state.faction_spells:
        with st.expander("✨ Sorts de la faction", expanded=True):
            for spell in st.session_state.faction_spells:
                if isinstance(spell, dict):
                    st.markdown(f"**{spell.get('name', 'Sort sans nom')}**: Coût: {spell.get('cost', '?')} pts, Portée: {spell.get('range', '?')}, {spell.get('description', '')}", unsafe_allow_html=True)
                else:
                    st.markdown(f"- {spell}", unsafe_allow_html=True)

    # ======================================================
    # LISTE DE L'ARMÉE
    # ======================================================
    st.subheader("Liste de l'Armée")

    if not st.session_state.army_list:
        st.markdown("Aucune unité ajoutée pour le moment.")
    else:
        for i, unit_data in enumerate(st.session_state.army_list):
            with st.expander(f"{unit_data['name']} - {unit_data['cost']} pts", expanded=False):
                st.markdown(f"**Type :** {unit_data['type']}")
                st.markdown(f"**Taille :** {unit_data.get('size', '?')}")
                st.markdown(f"**Qualité :** {unit_data.get('quality', '?')}+")
                st.markdown(f"**Défense :** {unit_data.get('defense', '?')}+")

                if st.button(f"Supprimer {unit_data['name']}", key=f"delete_{i}"):
                    st.session_state.army_cost -= unit_data['cost']
                    st.session_state.army_list.pop(i)
                    st.rerun()

    st.divider()

    # ======================================================
    # SÉLECTION DE L’UNITÉ
    # ======================================================
    unit = st.selectbox(
        "Unité disponible",
        st.session_state.units,
        format_func=format_unit_option,
        key="unit_select",
    )

    unit_key = f"unit_{unit['name']}"
    st.session_state.unit_selections.setdefault(unit_key, {})

    weapons = list(unit.get("weapons", []))
    selected_options = {}
    mount = None
    weapon_cost = 0
    mount_cost = 0
    upgrades_cost = 0

    # ======================================================
    # AMÉLIORATIONS
    # ======================================================
    for g_idx, group in enumerate(unit.get("upgrade_groups", [])):
        g_key = f"group_{g_idx}"
        st.subheader(group.get("group", "Améliorations"))

        # ---------- ARMES ----------
        if group.get("type") == "weapon":
            choices = ["Arme de base"]
            opt_map = {}

            for o in group.get("options", []):
                label = f"{o['name']} (+{o['cost']} pts)"
                choices.append(label)
                opt_map[label] = o

            current = st.session_state.unit_selections[unit_key].get(g_key, choices[0])
            choice = st.radio(
                "Sélection de l’arme",
                choices,
                index=choices.index(current) if current in choices else 0,
                key=f"{unit_key}_{g_key}_weapon",
            )

            st.session_state.unit_selections[unit_key][g_key] = choice

            if choice != "Arme de base":
                opt = opt_map[choice]
                weapon_cost += opt["cost"]
                weapons = (
                    [opt["weapon"]]
                    if unit.get("type") == "hero"
                    else weapons + [opt["weapon"]]
                )

        # ---------- MONTURE ----------
        elif group.get("type") == "mount":
            choices = ["Aucune monture"]
            opt_map = {}

            for o in group.get("options", []):
                label = f"{o['name']} (+{o['cost']} pts)"
                choices.append(label)
                opt_map[label] = o

            current = st.session_state.unit_selections[unit_key].get(g_key, choices[0])
            choice = st.radio(
                "Monture",
                choices,
                index=choices.index(current) if current in choices else 0,
                key=f"{unit_key}_{g_key}_mount",
            )

            st.session_state.unit_selections[unit_key][g_key] = choice

            if choice != "Aucune monture":
                mount = opt_map[choice]
                mount_cost = mount["cost"]

        # ---------- OPTIONS / RÔLES ----------
        elif group.get("type") == "role" and unit.get("type") == "hero":

            choices = ["Aucun rôle"]
            opt_map = {}

            for o in group.get("options", []):
                label = f"{o['name']} (+{o['cost']} pts)"
                choices.append(label)
                opt_map[label] = o

            current = st.session_state.unit_selections[unit_key].get(g_key, choices[0])

            choice = st.radio(
                "Rôle du héros",
                choices,
                index=choices.index(current) if current in choices else 0,
                key=f"{unit_key}_{g_key}_role",
            )

            st.session_state.unit_selections[unit_key][g_key] = choice

            if choice != "Aucun rôle":
                opt = opt_map[choice]
                upgrades_cost += opt["cost"]
                selected_options[group.get("group", "Rôle")] = [opt]

        # ---------- OPTIONS NORMALES (checkbox) ----------
        else:
            for o in group.get("options", []):
                opt_key = f"{unit_key}_{g_key}_{o['name']}"
                checked = st.checkbox(
                    f"{o['name']} (+{o['cost']} pts)",
                    value=st.session_state.unit_selections[unit_key].get(opt_key, False),
                    key=opt_key,
                )
                st.session_state.unit_selections[unit_key][opt_key] = checked
                if checked:
                    upgrades_cost += o["cost"]
                    selected_options.setdefault(
                        group.get("group", "Options"), []
                    ).append(o)

    # ======================================================
    # EFFECTIFS & COÛT
    # ======================================================
    multiplier = (
        2
        if unit.get("type") != "hero"
        and st.checkbox("Unité combinée")
        else 1
    )

    base_cost = unit.get("base_cost", 0)
    final_cost = (
        (base_cost + weapon_cost) * multiplier
        + upgrades_cost
        + mount_cost
    )

    # ======================================================
    # VUE EN TEMPS RÉEL DU COÛT DE L'UNITÉ
    # ======================================================
    st.subheader("Coût de l'unité sélectionnée")
    st.markdown(f"**Coût total :** {final_cost} pts")
    st.divider()

    # ======================================================
    # AJOUT À L’ARMÉE
    # ======================================================
    if st.button("➕ Ajouter à l’armée"):

        # --- Vérification du plafond de points ---
        if st.session_state.army_cost + final_cost > st.session_state.points:
            st.error(
                f"⛔ Dépassement du format : "
                f"{st.session_state.army_cost + final_cost} / {st.session_state.points} pts"
            )
            st.stop()

        unit_data = {
            "name": unit["name"],
            "type": unit.get("type", "unit"),
            "cost": final_cost,
            "size": (
                unit.get("size", 10) * multiplier
                if unit.get("type") != "hero"
                else 1
            ),
            "quality": unit.get("quality"),
            "defense": unit.get("defense"),
            "weapon": weapons,
            "options": selected_options,
            "mount": mount,
        }

        test_army = st.session_state.army_list + [unit_data]

        if validate_army_rules(
            test_army,
            st.session_state.points,
            st.session_state.game,
        ):
            st.session_state.army_list.append(unit_data)
            st.session_state.army_cost += final_cost
            st.rerun()
