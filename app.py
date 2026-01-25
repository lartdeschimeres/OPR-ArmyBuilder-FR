import json
import streamlit as st
from pathlib import Path
from datetime import datetime
import hashlib
import copy

# Configuration initiale
st.set_page_config(
    page_title="OPR Army Forge FR - Simon Joinville Fouquet",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Chemins des fichiers
BASE_DIR = Path(__file__).resolve().parent
FACTIONS_DIR = BASE_DIR / "lists" / "data" / "factions"
FACTIONS_DIR.mkdir(parents=True, exist_ok=True)

# Configuration des jeux
GAME_CONFIG = {
    "Age of Fantasy": {
        "display_name": "Age of Fantasy",
        "max_points": 10000,
        "min_points": 250,
        "default_points": 1000,
        "point_step": 250,
        "description": "Jeu de bataille dans un univers fantasy médiéval",
        "hero_limit": 375,
        "unit_copy_rule": 750,
        "unit_max_cost_ratio": 0.35,
        "unit_per_points": 150
    }
}

# CSS global pour l'esthétique
st.markdown("""
<style>
    /* Style général */
    .main {
        max-width: 1200px;
        margin: 0 auto;
        padding: 20px;
    }

    /* Style des cartes */
    .card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }

    /* Style des boutons */
    .stButton>button {
        background-color: #4a6fa5;
        color: white;
        border: none;
        padding: 10px 20px;
        border-radius: 4px;
        font-weight: bold;
        margin-top: 10px;
    }

    .stButton>button:hover {
        background-color: #3a5a8f;
    }

    /* Style des titres */
    .title {
        color: #2c3e50;
        margin-bottom: 20px;
    }

    /* Style des sous-titres */
    .subtitle {
        color: #4a6fa5;
        margin-top: 30px;
        margin-bottom: 15px;
    }

    /* Style des champs de formulaire */
    .stTextInput>div>div>input {
        border-radius: 4px;
        border: 1px solid #ddd;
        padding: 10px;
    }

    /* Style des sélecteurs */
    .stSelectbox>div>div>select {
        border-radius: 4px;
        border: 1px solid #ddd;
        padding: 10px;
    }

    /* Style des cartes de liste sauvegardée */
    .saved-list {
        background-color: white;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    /* Style des unités */
    .unit-card {
        background-color: #2a2a2a;
        color: white;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 15px;
        cursor: pointer;
    }

    .hero-card {
        background-color: #2a2a2a;
        color: white;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 15px;
        cursor: pointer;
        border-left: 4px solid #ffd700;
    }

    /* Style des règles spéciales */
    .faction-rules {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 20px;
        border-left: 4px solid #3498db;
    }

    /* Style des accordéons */
    .rule-title {
        font-weight: bold;
        color: #2c3e50;
        margin-bottom: 10px;
    }

    /* Style des options */
    .option-card {
        background-color: #f0f0f0;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Fonctions utilitaires
def format_weapon(weapon):
    if not weapon:
        return "Arme non spécifiée"
    return f"{weapon.get('name', 'Arme')} (A{weapon.get('attacks', '?')}, PA({weapon.get('armor_piercing', '?')}))"

def format_mount(mount):
    if not mount:
        return "Aucune monture"
    mount_data = mount.get('mount', mount)
    details = mount.get('name', 'Monture')
    if 'quality' in mount_data or 'defense' in mount_data:
        details += " ("
        if 'quality' in mount_data:
            details += f"Qua{mount_data['quality']}+"
        if 'defense' in mount_data:
            details += f" Déf{mount_data['defense']}+"
        details += ")"
    return details

# Local Storage
def ls_get(key):
    try:
        unique_key = f"{key}_{hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()[:8]}"
        st.markdown(f"""
        <script>
        const value = localStorage.getItem("{key}");
        const input = document.createElement("input");
        input.type = "hidden";
        input.id = "{unique_key}";
        input.value = value || "";
        document.body.appendChild(input);
        </script>
        """, unsafe_allow_html=True)
        return st.text_input("", key=unique_key, label_visibility="collapsed")
    except Exception:
        return None

def ls_set(key, value):
    try:
        if not isinstance(value, str):
            value = json.dumps(value)
        escaped_value = value.replace("'", "\\'").replace('"', '\\"')
        st.markdown(f"""
        <script>
        localStorage.setItem("{key}", `{escaped_value}`);
        </script>
        """, unsafe_allow_html=True)
    except Exception:
        pass

# Chargement des factions
@st.cache_data
def load_factions():
    factions = {}
    games = set()

    if FACTIONS_DIR.exists():
        for fp in FACTIONS_DIR.glob("*.json"):
            try:
                with open(fp, encoding="utf-8") as f:
                    data = json.load(f)
                    game = data.get("game")
                    faction = data.get("faction")
                    if game and faction:
                        factions.setdefault(game, {})[faction] = data
                        games.add(game)
            except Exception as e:
                st.warning(f"Erreur de chargement du fichier {fp.name}: {e}")

    if not games:
        st.warning("Aucun fichier de faction trouvé. Veuillez ajouter vos fichiers JSON dans le dossier 'lists/data/factions/'")
        return {}, []

    return factions, sorted(games)

# Initialisation
factions_by_game, games = load_factions()

if "page" not in st.session_state:
    st.session_state.page = "faction_select"
    st.session_state.army_list = []
    st.session_state.army_cost = 0
    st.session_state.history = []
    st.session_state.current_unit = None
    st.session_state.current_options = {}

# PAGE 1 - Sélection de la faction et création de liste
if st.session_state.page == "faction_select":
    st.markdown("<div class='main'>", unsafe_allow_html=True)
    st.markdown("<h1 class='title'>OPR Army Forge FR</h1>", unsafe_allow_html=True)

    # Sélection du jeu
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("Jeu")
    game = st.selectbox(
        "Sélectionnez un jeu",
        games,
        key="game_select"
    )

    # Sélection de la faction
    if game in factions_by_game:
        st.subheader("Faction")
        faction_options = list(factions_by_game[game].keys())
        faction = st.selectbox(
            "Sélectionnez une faction",
            faction_options,
            key="faction_select"
        )

    # Points
    game_config = GAME_CONFIG.get(game, GAME_CONFIG["Age of Fantasy"])
    st.subheader("Points")
    points = st.number_input(
        "Points de l'armée",
        min_value=game_config["min_points"],
        max_value=game_config["max_points"],
        value=game_config["default_points"],
        step=game_config["point_step"],
        key="points_input"
    )

    # Nom de la liste
    st.subheader("Nom de la liste")
    list_name = st.text_input(
        "Nom de votre liste d'armée",
        f"Liste_{datetime.now().strftime('%Y%m%d')}",
        key="list_name_input"
    )
    st.markdown("</div>", unsafe_allow_html=True)

    # Chargement des listes sauvegardées
    st.markdown("<h2 class='subtitle'>Mes listes sauvegardées</h2>", unsafe_allow_html=True)
    st.markdown("<div class='saved-lists-container'>", unsafe_allow_html=True)

    saved_lists = ls_get("opr_saved_lists")
    if saved_lists:
        try:
            saved_lists = json.loads(saved_lists)
            if isinstance(saved_lists, list):
                for i, saved_list in enumerate(saved_lists):
                    st.markdown(f"""
                    <div class='saved-list'>
                        <div>
                            <h4 style='margin:0;'>{saved_list.get('name', 'Liste sans nom')}</h4>
                            <p style='margin:5px 0; color:#666;'>{saved_list.get('game', 'Inconnu')} • {saved_list.get('faction', 'Inconnue')} • {saved_list.get('total_cost', 0)}/{saved_list.get('points', 0)} pts</p>
                        </div>
                        <div>
                            <button onclick="document.getElementById('load-{i}').click()" style='background-color:#4a6fa5; color:white; border:none; padding:8px 16px; border-radius:4px;'>Charger</button>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    if st.button(f"Charger la liste {i}", key=f"load-{i}"):
                        st.session_state.game = saved_list["game"]
                        st.session_state.faction = saved_list["faction"]
                        st.session_state.points = saved_list["points"]
                        st.session_state.list_name = saved_list["name"]
                        st.session_state.army_list = saved_list["army_list"]
                        st.session_state.army_cost = saved_list["total_cost"]
                        st.session_state.units = factions_by_game[saved_list["game"]][saved_list["faction"]]["units"]
                        st.session_state.history = []
                        st.session_state.page = "army_builder"
                        st.rerun()
        except Exception as e:
            st.error(f"Erreur chargement listes: {e}")

    st.markdown("</div>", unsafe_allow_html=True)

    # Import JSON
    st.markdown("<h2 class='subtitle'>Importer une liste</h2>", unsafe_allow_html=True)
    uploaded_file = st.file_uploader(
        "Choisissez un fichier JSON à importer",
        type=["json"],
        key="json_uploader"
    )

    if uploaded_file is not None:
        try:
            army_data = json.load(uploaded_file)
            if all(key in army_data for key in ["game", "faction", "army_list", "points"]):
                st.session_state.game = army_data["game"]
                st.session_state.faction = army_data["faction"]
                st.session_state.points = army_data["points"]
                st.session_state.list_name = army_data.get("name", f"Liste_importée_{datetime.now().strftime('%Y%m%d')}")
                st.session_state.army_list = army_data["army_list"]
                st.session_state.army_cost = army_data.get("total_cost", 0)
                st.session_state.units = factions_by_game[army_data["game"]][army_data["faction"]]["units"]
                st.session_state.history = []
                st.session_state.page = "army_builder"
                st.rerun()
            else:
                st.error("Le fichier JSON n'a pas le format attendu")
        except Exception as e:
            st.error(f"Erreur lors de l'import: {e}")

    # Bouton pour créer une nouvelle liste
    if st.button("Créer une nouvelle liste", key="create_list"):
        if game in factions_by_game and 'faction' in locals():
            st.session_state.game = game
            st.session_state.faction = faction
            st.session_state.points = points
            st.session_state.list_name = list_name
            st.session_state.units = factions_by_game[game][faction]["units"]
            st.session_state.army_list = []
            st.session_state.army_cost = 0
            st.session_state.history = []
            st.session_state.page = "army_builder"
            st.rerun()
        else:
            st.error("Veuillez sélectionner un jeu et une faction valides")

    st.markdown("</div>", unsafe_allow_html=True)

# PAGE 2 - Liste des unités (rectangles cliquables)
elif st.session_state.page == "army_builder":
    st.markdown("<div class='main'>", unsafe_allow_html=True)
    st.markdown(f"<h1 class='title'>{st.session_state.list_name}</h1>", unsafe_allow_html=True)
    st.caption(f"{st.session_state.game} • {st.session_state.faction} • {st.session_state.army_cost}/{st.session_state.points} pts")

    # Boutons de contrôle
    col1, col2 = st.columns(2)
    with col1:
        if st.button("⬅ Retour", key="back_to_faction_select"):
            st.session_state.page = "faction_select"
            st.rerun()

    # Affichage des règles spéciales
    if 'special_rules_descriptions' in factions_by_game[st.session_state.game][st.session_state.faction]:
        st.markdown("<div class='faction-rules'>", unsafe_allow_html=True)
        st.markdown("<h3 class='rule-title'>📜 Règles Spéciales de la Faction</h3>", unsafe_allow_html=True)

        for rule_name, description in factions_by_game[st.session_state.game][st.session_state.faction]['special_rules_descriptions'].items():
            with st.expander(f"**{rule_name}**"):
                st.write(description)

        st.markdown("</div>", unsafe_allow_html=True)

    # Séparation par type (Héros/Unités)
    heroes = [u for u in st.session_state.units if u.get('type', '').lower() == 'hero']
    units = [u for u in st.session_state.units if u.get('type', '').lower() != 'hero']

    if heroes:
        st.markdown("<h2 class='subtitle'>🌟 HÉROS</h2>", unsafe_allow_html=True)
        for unit in heroes:
            with st.container():
                st.markdown(f"""
                <div class='hero-card' onclick="document.getElementById('select_{unit['name'].replace(' ', '_')}_hero').click()">
                    <div style='display: flex; justify-content: space-between; align-items: center;'>
                        <div>
                            <h4 style='margin:0; color:#ffd700;'>{unit['name']} [1]</h4>
                            <p style='margin:5px 0; color:#aaa;'>Qua {unit['quality']}+ / Déf {unit.get('defense', '?')}+</p>
                        </div>
                        <div style='text-align: right;'>
                            <p style='margin:0; color:#4CAF50; font-weight: bold;'>{unit['base_cost']} pts</p>
                        </div>
                    </div>
                    <div style='margin-top: 10px; color:#ccc;'>
                        <p style='margin:5px 0; font-style: italic;'>{', '.join(unit.get('special_rules', []))}</p>
                        <p style='margin:5px 0;'>{format_weapon(unit['weapons'][0]) if 'weapons' in unit and unit['weapons'] else 'Aucune arme'}</p>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                if st.button(f"Sélectionner {unit['name']}", key=f"select_{unit['name'].replace(' ', '_')}_hero"):
                    st.session_state.current_unit = unit
                    st.session_state.current_options = {
                        'weapon': unit['weapons'][0] if 'weapons' in unit and unit['weapons'] else None,
                        'mount': None,
                        'selected_options': {}
                    }
                    st.session_state.page = "unit_options"
                    st.rerun()

    if units:
        st.markdown("<h2 class='subtitle'>🏳️ UNITÉS</h2>", unsafe_allow_html=True)
        for unit in units:
            with st.container():
                st.markdown(f"""
                <div class='unit-card' onclick="document.getElementById('select_{unit['name'].replace(' ', '_')}_unit').click()">
                    <div style='display: flex; justify-content: space-between; align-items: center;'>
                        <div>
                            <h4 style='margin:0; color:#fff;'>{unit['name']} [{unit.get('size', 10)}]</h4>
                            <p style='margin:5px 0; color:#aaa;'>Qua {unit['quality']}+ / Déf {unit.get('defense', '?')}+</p>
                        </div>
                        <div style='text-align: right;'>
                            <p style='margin:0; color:#4CAF50; font-weight: bold;'>{unit['base_cost']} pts</p>
                        </div>
                    </div>
                    <div style='margin-top: 10px; color:#ccc;'>
                        <p style='margin:5px 0; font-style: italic;'>{', '.join(unit.get('special_rules', []))}</p>
                        <p style='margin:5px 0;'>{format_weapon(unit['weapons'][0]) if 'weapons' in unit and unit['weapons'] else 'Aucune arme'}</p>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                if st.button(f"Sélectionner {unit['name']}", key=f"select_{unit['name'].replace(' ', '_')}_unit"):
                    st.session_state.current_unit = unit
                    st.session_state.current_options = {
                        'combined': False,
                        'weapon': unit['weapons'][0] if 'weapons' in unit and unit['weapons'] else None,
                        'mount': None,
                        'selected_options': {}
                    }
                    st.session_state.page = "unit_options"
                    st.rerun()

    # Affichage de la liste d'armée actuelle
    st.divider()
    st.markdown(f"<h2 class='subtitle'>Liste d'armée actuelle ({st.session_state.army_cost}/{st.session_state.points} pts)</h2>", unsafe_allow_html=True)

    if not st.session_state.army_list:
        st.info("Ajoutez des unités pour commencer à construire votre armée")

    for i, u in enumerate(st.session_state.army_list):
        with st.container():
            st.markdown(f"""
            <div class={'hero-card' if u.get('type') == 'hero' else 'unit-card'}>
                <div style='display: flex; justify-content: space-between; align-items: center;'>
                    <div>
                        <h4 style='margin:0; color:{"#ffd700" if u.get("type") == "hero" else "#fff"};'>{u['name']} [{u.get('size', 1)}] {'🌟' if u.get('type') == 'hero' else ''}</h4>
                        <p style='margin:5px 0; color:#aaa;'>Qua {u['quality']}+ / Déf {u.get('defense', '?')}+</p>
                    </div>
                    <div style='text-align: right;'>
                        <p style='margin:0; color:#4CAF50; font-weight: bold;'>{u['cost']} pts</p>
                    </div>
                </div>
                <div style='margin-top: 10px; color:#ccc;'>
                    <p style='margin:5px 0;'>{format_weapon(u.get('weapon', {}))}</p>
                    {f"<p style='margin:5px 0;'>Monture: {format_mount(u.get('mount'))}</p>" if u.get('mount') else ""}
                </div>
            </div>
            """, unsafe_allow_html=True)

            if st.button(f"Supprimer {u['name']}", key=f"del_{i}"):
                st.session_state.history.append({
                    "army_list": copy.deepcopy(st.session_state.army_list),
                    "army_cost": st.session_state.army_cost
                })
                st.session_state.army_cost -= u["cost"]
                st.session_state.army_list.pop(i)
                st.rerun()

    # Export
    st.divider()
    col1, col2, col3 = st.columns(3)

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
        if st.button("Sauvegarder", key="save_list"):
            saved_lists = ls_get("opr_saved_lists")
            current_lists = json.loads(saved_lists) if saved_lists else []
            current_lists.append(army_data)
            ls_set("opr_saved_lists", current_lists)
            st.success("Liste sauvegardée!")

    with col2:
        st.download_button(
            "Exporter en JSON",
            json.dumps(army_data, indent=2, ensure_ascii=False),
            file_name=f"{st.session_state.list_name}.json",
            mime="application/json",
            key="export_json"
        )

    with col3:
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Liste OPR - {army_data['name']}</title>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .army-title {{ text-align: center; margin-bottom: 20px; }}
                .unit {{ margin-bottom: 20px; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
                .hero {{ background-color: #fffde7; }}
                .stats {{ display: flex; gap: 10px; margin-bottom: 10px; }}
                .stat {{ background: #e3f2fd; padding: 5px 10px; border-radius: 3px; }}
            </style>
        </head>
        <body>
            <h1 class="army-title">Liste d'armée: {army_data['name']}</h1>
            <p><strong>Faction:</strong> {army_data['faction']} | <strong>Points:</strong> {army_data['total_cost']}/{army_data['points']}</p>
        """

        for unit in army_data['army_list']:
            html_content += f"""
            <div class="unit {'hero' if unit.get('type') == 'hero' else ''}">
                <h3>{unit['name']} [{unit.get('size', 1)}] ({unit['cost']} pts)</h3>
                <div class="stats">
                    <div class="stat"><strong>Qualité:</strong> {unit['quality']}+</div>
                    <div class="stat"><strong>Défense:</strong> {unit.get('defense', '?')}+</div>
                </div>
                <p><strong>Arme:</strong> {format_weapon(unit.get('weapon', {}))}</p>
                {f"<p><strong>Monture:</strong> {format_mount(unit.get('mount'))}</p>" if unit.get('mount') else ""}
            </div>
            """

        html_content += """
        </body>
        </html>
        """

        st.download_button(
            "Exporter en HTML",
            html_content,
            file_name=f"{st.session_state.list_name}.html",
            mime="text/html",
            key="export_html"
        )

    st.markdown("</div>", unsafe_allow_html=True)

# PAGE 3 - Options de l'unité (avec radio buttons pour les héros)
elif st.session_state.page == "unit_options":
    unit = st.session_state.current_unit
    options = st.session_state.current_options

    st.markdown("<div class='main'>", unsafe_allow_html=True)
    st.markdown(f"<h1 class='title'>Personnaliser: {unit['name']}</h1>", unsafe_allow_html=True)
    st.caption(f"Type: {'Héros' if unit.get('type', '').lower() == 'hero' else 'Unité'} • Base: {unit['base_cost']} pts")

    # Bouton retour
    if st.button("⬅ Retour à la liste", key="back_to_army_builder"):
        st.session_state.page = "army_builder"
        st.rerun()

    # Affichage des caractéristiques de base
    st.markdown(f"""
    <div class='option-card'>
        <h4 style='margin-top: 0;'>Caractéristiques de base</h4>
        <p><strong>Taille:</strong> {unit.get('size', 1)} | <strong>Qualité:</strong> {unit['quality']}+ | <strong>Défense:</strong> {unit.get('defense', '?')}+</p>
        <p><strong>Règles spéciales:</strong> {', '.join(unit.get('special_rules', []))}</p>
    </div>
    """, unsafe_allow_html=True)

    # Option "Unité combinée" (désactivée pour les héros)
    if unit.get('type', '').lower() != 'hero':
        options['combined'] = st.checkbox("Unité combinée", value=options.get('combined', False), key="combined_unit")

    # Sélection des options
    total_cost = unit['base_cost']
    current_size = unit.get('size', 1)

    # Gestion des armes
    if 'weapons' in unit and unit['weapons']:
        st.markdown("<h3 class='subtitle'>Armes</h3>", unsafe_allow_html=True)

        if unit.get('type', '').lower() == 'hero':
            # Pour les héros: radio buttons pour chaque arme
            weapon_options = [f"{format_weapon(weapon)}" for weapon in unit['weapons']]
            selected_weapon = st.radio(
                "Sélectionnez une arme",
                weapon_options,
                index=0,
                key="weapon_radio"
            )
            selected_index = weapon_options.index(selected_weapon)
            options['weapon'] = unit['weapons'][selected_index]

    # Gestion des améliorations de rôle
    if 'upgrade_groups' in unit:
        for group in unit['upgrade_groups']:
            if group['type'] == 'multiple' and group['group'] == 'Améliorations de rôle':
                st.markdown(f"<h3 class='subtitle'>{group['group']}</h3>", unsafe_allow_html=True)

                role_options = [f"{option['name']} (+{option['cost']} pts)" for option in group['options']]
                selected_role = st.radio(
                    "Sélectionnez une amélioration de rôle",
                    ["Aucune amélioration"] + role_options,
                    index=0,
                    key=f"role_radio_{group['group']}"
                )

                if selected_role != "Aucune amélioration":
                    role_name = selected_role.split(" (+")[0]
                    selected_role_option = next(opt for opt in group['options'] if opt['name'] == role_name)
                    options['selected_options'][group['group']] = [selected_role_option]
                    total_cost += selected_role_option['cost']
                else:
                    options['selected_options'][group['group']] = []

    # Gestion des changements d'armes
    if 'upgrade_groups' in unit:
        for group in unit['upgrade_groups']:
            if group['type'] == 'weapon' and group['group'] == 'Remplacement d\'arme':
                st.markdown(f"<h3 class='subtitle'>{group['group']}</h3>", unsafe_allow_html=True)

                weapon_options = [f"{format_weapon(option['weapon'])} (+{option['cost']} pts)" for option in group['options']]
                selected_weapon_replacement = st.radio(
                    "Sélectionnez une arme de remplacement",
                    ["Aucun remplacement"] + weapon_options,
                    index=0,
                    key=f"weapon_replacement_radio_{group['group']}"
                )

                if selected_weapon_replacement != "Aucun remplacement":
                    weapon_name = selected_weapon_replacement.split(" (+")[0]
                    selected_weapon_option = next(opt for opt in group['options'] if format_weapon(opt['weapon']) == weapon_name)
                    options['weapon'] = selected_weapon_option['weapon']
                    total_cost += selected_weapon_option['cost']

    # Gestion des montures
    if 'upgrade_groups' in unit:
        for group in unit['upgrade_groups']:
            if group['type'] == 'mount':
                st.markdown(f"<h3 class='subtitle'>{group['group']}</h3>", unsafe_allow_html=True)

                mount_options = [f"{option['name']} (+{option['cost']} pts)" for option in group['options']]
                selected_mount = st.radio(
                    "Sélectionnez une monture",
                    ["Aucune monture"] + mount_options,
                    index=0,
                    key=f"mount_radio_{group['group']}"
                )

                if selected_mount != "Aucune monture":
                    mount_name = selected_mount.split(" (+")[0]
                    selected_mount_option = next(opt for opt in group['options'] if opt['name'] == mount_name)
                    options['mount'] = selected_mount_option
                    total_cost += selected_mount_option['cost']
                else:
                    options['mount'] = None

    # Gestion des améliorations d'unité (checkbox multiples)
    if 'upgrade_groups' in unit:
        for group in unit['upgrade_groups']:
            if group['type'] != 'mount' and group['type'] != 'weapon' and group['type'] != 'multiple':
                st.markdown(f"<h3 class='subtitle'>{group['group']}</h3>", unsafe_allow_html=True)

                for option in group['options']:
                    if st.checkbox(f"{option['name']} (+{option['cost']} pts)", key=f"upgrade_{group['group']}_{option['name']}"):
                        if group['group'] not in options['selected_options']:
                            options['selected_options'][group['group']] = []
                        if not any(opt['name'] == option['name'] for opt in options['selected_options'].get(group['group'], [])):
                            options['selected_options'][group['group']].append(option)
                            total_cost += option['cost']

    # Calcul du coût final
    if options.get('combined', False) and unit.get('type', '').lower() != 'hero':
        base_weapon_cost = 0
        if 'upgrade_groups' in unit:
            for group in unit['upgrade_groups']:
                if group['type'] == 'weapon' and group['group'] == 'Remplacement d\'arme' and options['weapon']:
                    selected_weapon_option = next((opt for opt in group['options'] if format_weapon(opt['weapon']) == format_weapon(options['weapon'])), None)
                    if selected_weapon_option:
                        base_weapon_cost = selected_weapon_option['cost']
        total_cost = (unit['base_cost'] + base_weapon_cost) * 2
        total_cost += sum(opt['cost'] for group in options['selected_options'].values() for opt in group)
        total_cost += options['mount']['cost'] if options['mount'] else 0
        current_size = unit.get('size', 1) * 2
    else:
        total_cost = unit['base_cost'] + \
                     (options['mount']['cost'] if options['mount'] else 0) + \
                     sum(opt['cost'] for group in options['selected_options'].values() for opt in group)
        current_size = unit.get('size', 1)

    st.markdown(f"""
    <div class='option-card'>
        <h4 style='margin-top: 0;'>Récapitulatif</h4>
        <p><strong>Taille finale:</strong> {current_size} {'(x2 combinée)' if options.get('combined', False) and unit.get('type', '').lower() != 'hero' else ''}</p>
        <p><strong>Coût total:</strong> {total_cost} pts</p>
    </div>
    """, unsafe_allow_html=True)

    # Bouton pour ajouter à l'armée
    if st.button("Ajouter à l'armée", key="add_to_army"):
        unit_data = {
            "name": unit["name"],
            "type": unit.get("type", "unit"),
            "cost": total_cost,
            "size": current_size,
            "quality": unit["quality"],
            "defense": unit["defense"],
            "rules": unit.get("special_rules", []),
            "weapon": options['weapon'],
            "mount": options['mount'],
            "options": options['selected_options'],
            "combined": options.get('combined', False) and unit.get('type', '').lower() != 'hero'
        }

        st.session_state.army_list.append(unit_data)
        st.session_state.army_cost += total_cost
        st.session_state.page = "army_builder"
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)
