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

# Fonctions utilitaires simplifiées
def format_unit_name(u):
    name = f"{u['name']}"
    if u.get('type') == "hero":
        name += " [1]"
    else:
        name += f" [{u.get('size', 10)}]"
    return name

def format_weapon(weapon):
    if not weapon:
        return "Arme non spécifiée"
    return f"{weapon.get('name', 'Arme')} (A{weapon.get('attacks', '?')}, PA({weapon.get('armor_piercing', '?')}))"

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

    # Faction par défaut si aucun fichier n'est trouvé
    default_faction = {
        "game": "Age of Fantasy",
        "faction": "Disciples de la Guerre",
        "special_rules_descriptions": {
            "Éclaireur": "Déplacement facilité en terrain difficile.",
            "Furieux": "Relance les 1 en attaque.",
            "Né pour la guerre": "Relance les 1 en test de moral.",
            "Héros": "Personnage inspirant.",
            "Coriace(1)": "Ignore 1 point de dégât par phase."
        },
        "units": []
    }

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
            except Exception:
                continue

    if not games:
        factions["Age of Fantasy"] = {"Disciples de la Guerre": default_faction}
        games.add("Age of Fantasy")

    return factions, sorted(games)

# Initialisation
factions_by_game, games = load_factions()

if "page" not in st.session_state:
    st.session_state.page = "faction_select"
    st.session_state.army_list = []
    st.session_state.army_cost = 0
    st.session_state.history = []
    st.session_state.current_unit = None
    st.session_state.current_options = {
        'combined': False,
        'weapon': None,
        'mount': None,
        'selected_options': {}
    }

# PAGE 1 - Sélection de la faction
if st.session_state.page == "faction_select":
    st.title("OPR Army Forge FR")

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

    if st.button("Créer une nouvelle liste"):
        st.session_state.game = game
        st.session_state.faction = st.selectbox("Faction", list(factions_by_game[game].keys()))
        st.session_state.points = points
        st.session_state.list_name = list_name
        st.session_state.units = factions_by_game[game][st.session_state.faction]["units"]
        st.session_state.army_list = []
        st.session_state.army_cost = 0
        st.session_state.history = []
        st.session_state.page = "army_builder"
        st.rerun()

# PAGE 2 - Liste des unités
elif st.session_state.page == "army_builder":
    st.title(st.session_state.list_name)
    st.caption(f"{st.session_state.game} • {st.session_state.faction} • {st.session_state.army_cost}/{st.session_state.points} pts")

    # Bouton retour
    if st.button("⬅ Retour"):
        st.session_state.page = "faction_select"
        st.rerun()

    # Affichage des règles spéciales
    if 'special_rules_descriptions' in factions_by_game[st.session_state.game][st.session_state.faction]:
        st.markdown("""
        <style>
        .faction-rules {
            background-color: #f8f9fa;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 20px;
            border-left: 4px solid #3498db;
        }
        </style>
        """, unsafe_allow_html=True)

        st.markdown('<div class="faction-rules">', unsafe_allow_html=True)
        st.subheader("📜 Règles Spéciales de la Faction")

        for rule_name, description in factions_by_game[st.session_state.game][st.session_state.faction]['special_rules_descriptions'].items():
            st.markdown(f"""
            <div style="margin-bottom: 10px;">
                <div style="font-weight: bold;">{rule_name}:</div>
                <div style="font-size: 0.9em; color: #555; margin-left: 10px;">{description}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

    # Séparation par type (Héros/Unités)
    heroes = [u for u in st.session_state.units if u.get('type') == 'hero']
    units = [u for u in st.session_state.units if u.get('type') != 'hero']

    if heroes:
        st.subheader("🌟 HÉROS")
        for unit in heroes:
            with st.container():
                col1, col2 = st.columns([0.8, 0.2])
                with col1:
                    st.markdown(f"""
                    <div style="background-color: #2a2a2a; color: white; padding: 15px; border-radius: 8px; margin-bottom: 10px;">
                        <h4 style="margin: 0; color: #ffd700;">{format_unit_name(unit)}</h4>
                        <p style="margin: 5px 0; color: #aaa;">Qua {unit['quality']}+ / Déf {unit.get('defense', '?')}+</p>
                    </div>
                    """, unsafe_allow_html=True)

                with col2:
                    if st.button(f"Ajouter", key=f"add-{unit['name']}"):
                        st.session_state.current_unit = unit
                        # Initialisation des options avec les valeurs par défaut
                        st.session_state.current_options = {
                            'combined': False,
                            'weapon': unit['weapons'][0] if 'weapons' in unit and unit['weapons'] else None,
                            'mount': None,
                            'selected_options': {}
                        }
                        st.session_state.page = "unit_options"
                        st.rerun()

    if units:
        st.subheader("🏳️ UNITÉS")
        for unit in units:
            with st.container():
                col1, col2 = st.columns([0.8, 0.2])
                with col1:
                    st.markdown(f"""
                    <div style="background-color: #1e1e1e; color: white; padding: 15px; border-radius: 8px; margin-bottom: 10px;">
                        <h4 style="margin: 0; color: #fff;">{format_unit_name(unit)}</h4>
                        <p style="margin: 5px 0; color: #aaa;">Qua {unit['quality']}+ / Déf {unit.get('defense', '?')}+</p>
                    </div>
                    """, unsafe_allow_html=True)

                with col2:
                    if st.button(f"Ajouter", key=f"add-{unit['name']}"):
                        st.session_state.current_unit = unit
                        # Initialisation des options avec les valeurs par défaut
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
    st.subheader(f"Liste d'armée actuelle ({st.session_state.army_cost}/{st.session_state.points} pts)")

    if not st.session_state.army_list:
        st.info("Ajoutez des unités pour commencer à construire votre armée")

    for i, u in enumerate(st.session_state.army_list):
        with st.container():
            col1, col2 = st.columns([0.8, 0.2])
            with col1:
                st.markdown(f"""
                <div style="background-color: {'#2a2a2a' if u.get('type') == 'hero' else '#1e1e1e'}; color: white; padding: 15px; border-radius: 8px; margin-bottom: 10px;">
                    <h4 style="margin: 0; color: {'#ffd700' if u.get('type') == 'hero' else '#fff'};">
                        {u['name']} [{u.get('size', 1)}] {'🌟' if u.get('type') == 'hero' else ''}
                    </h4>
                    <p style="margin: 5px 0; color: #aaa;">
                        Qua {u['quality']}+ / Déf {u.get('defense', '?')}+
                    </p>
                    <p style="margin: 5px 0; color: #ccc;">
                        {format_weapon(u.get('weapon', {}))}
                    </p>
                </div>
                """, unsafe_allow_html=True)

            with col2:
                if st.button(f"Supprimer", key=f"del-{i}"):
                    st.session_state.army_cost -= u["cost"]
                    st.session_state.army_list.pop(i)
                    st.rerun()

    # Export
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
            mime="application/json"
        )

# PAGE 3 - Options de l'unité
elif st.session_state.page == "unit_options":
    unit = st.session_state.current_unit
    options = st.session_state.current_options

    st.title(f"Personnaliser: {unit['name']}")
    st.caption(f"Type: {'Héros' if unit.get('type') == 'hero' else 'Unité'} • Base: {unit['base_cost']} pts")

    # Bouton retour
    if st.button("⬅ Retour à la liste"):
        st.session_state.page = "army_builder"
        st.rerun()

    # Affichage des caractéristiques de base
    st.markdown(f"""
    <div style="background-color: #f0f0f0; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
        <h4 style="margin-top: 0;">Caractéristiques de base</h4>
        <p><strong>Taille:</strong> {unit.get('size', 10)} | <strong>Qualité:</strong> {unit['quality']}+ | <strong>Défense:</strong> {unit.get('defense', '?')}+</p>
    </div>
    """, unsafe_allow_html=True)

    # Option "Unité combinée" (désactivée pour les héros)
    if unit.get('type') != 'hero':
        options['combined'] = st.checkbox("Unité combinée", value=options['combined'])

    # Sélection des options
    total_cost = unit['base_cost']
    current_size = unit.get('size', 10)

    # Gestion des armes (vérification de l'existence)
    if 'weapons' in unit and unit['weapons'] and len(unit['weapons']) > 0:
        st.subheader("Armes")
        weapon_options = [format_weapon(w) for w in unit['weapons']]

        selected_weapon = st.selectbox(
            "Sélectionnez une arme",
            weapon_options,
            index=0,
            key="weapon_select"
        )

        # Trouver l'arme sélectionnée
        selected_index = weapon_options.index(selected_weapon)
        options['weapon'] = unit['weapons'][selected_index]

    # Gestion des montures
    if 'upgrade_groups' in unit:
        for group in unit['upgrade_groups']:
            if group['type'] == 'mount' and 'options' in group:
                st.subheader(group['group'])
                mount_options = ["Aucune monture"]
                mount_details = {}

                for option in group['options']:
                    mount_options.append(f"{option['name']} (+{option['cost']} pts)")
                    mount_details[option['name']] = option

                selected_mount = st.selectbox(
                    "Sélectionnez une monture",
                    mount_options,
                    index=0,
                    key=f"mount_{group['group']}"
                )

                if selected_mount != "Aucune monture":
                    mount_name = selected_mount.split(" (+")[0]
                    options['mount'] = mount_details[mount_name]
                    total_cost += mount_details[mount_name]['cost']
                else:
                    options['mount'] = None

    # Gestion des améliorations
    if 'upgrade_groups' in unit:
        for group in unit['upgrade_groups']:
            if group['type'] == 'upgrades' and 'options' in group:
                st.subheader(group['group'])

                if len(group['options']) == 1:  # Sélection unique
                    selected_option = st.selectbox(
                        f"Sélectionnez une {group['group'].lower()}",
                        ["Aucune"] + [f"{opt['name']} (+{opt['cost']} pts)" for opt in group['options']],
                        index=0,
                        key=f"upgrade_{group['group']}"
                    )

                    if selected_option != "Aucune":
                        option_name = selected_option.split(" (+")[0]
                        selected_opt = next(opt for opt in group['options'] if opt['name'] == option_name)
                        options['selected_options'][group['group']] = [selected_opt]
                        total_cost += selected_opt['cost']
                    else:
                        options['selected_options'][group['group']] = []
                else:  # Sélection multiple
                    for option in group['options']:
                        if st.checkbox(
                            f"{option['name']} (+{option['cost']} pts)",
                            key=f"upgrade_{group['group']}_{option['name']}"
                        ):
                            if group['group'] not in options['selected_options']:
                                options['selected_options'][group['group']] = []
                            if not any(opt['name'] == option['name'] for opt in options['selected_options'].get(group['group'], [])):
                                options['selected_options'][group['group']].append(option)
                                total_cost += option['cost']

    # Calcul du coût final
    if options['combined'] and unit.get('type') != 'hero':
        total_cost = (unit['base_cost'] +
                     (options['mount']['cost'] if options['mount'] else 0) +
                     sum(opt['cost'] for group in options['selected_options'].values() for opt in group)) * 2
        current_size = unit.get('size', 10) * 2
    else:
        total_cost = unit['base_cost'] + \
                     (options['mount']['cost'] if options['mount'] else 0) + \
                     sum(opt['cost'] for group in options['selected_options'].values() for opt in group)
        current_size = unit.get('size', 10)

    st.divider()
    st.markdown(f"""
    <div style="background-color: #e3f2fd; padding: 15px; border-radius: 8px;">
        <h4 style="margin-top: 0;">Récapitulatif</h4>
        <p><strong>Taille finale:</strong> {current_size} {'(x2 combinée)' if options['combined'] and unit.get('type') != 'hero' else ''}</p>
        <p><strong>Coût total:</strong> {total_cost} pts</p>
    </div>
    """, unsafe_allow_html=True)

    # Bouton pour ajouter à l'armée
    if st.button("Ajouter à l'armée"):
        # Préparation des données de l'unité
        unit_data = {
            "name": unit["name"],
            "type": unit.get("type", "unit"),
            "cost": total_cost,
            "size": current_size,
            "quality": unit["quality"],
            "defense": unit["defense"],
            "rules": unit.get("special_rules", []),
            "weapon": options['weapon'] if options.get('weapon') else (unit['weapons'][0] if 'weapons' in unit and unit['weapons'] else None),
            "mount": options['mount'],
            "options": options['selected_options']
        }

        st.session_state.army_list.append(unit_data)
        st.session_state.army_cost += total_cost
        st.session_state.page = "army_builder"
        st.rerun()