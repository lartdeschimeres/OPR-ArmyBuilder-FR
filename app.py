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

# PAGE 1 - Sélection de la faction
if st.session_state.page == "faction_select":
    st.title("OPR Army Forge FR")

    if not games:
        st.error("Aucun jeu trouvé. Veuillez ajouter des fichiers de faction dans le dossier approprié.")
        st.stop()

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

    # Chargement des listes sauvegardées
    st.subheader("Mes listes sauvegardées")
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
                            st.session_state.history = []
                            st.session_state.page = "army_builder"
                            st.rerun()
        except Exception as e:
            st.error(f"Erreur chargement listes: {e}")

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

# PAGE 2 - Liste des unités (rectangles cliquables)
elif st.session_state.page == "army_builder":
    st.title(st.session_state.list_name)
    st.caption(f"{st.session_state.game} • {st.session_state.faction} • {st.session_state.army_cost}/{st.session_state.points} pts")

    # Boutons de contrôle
    col1, col2 = st.columns(2)
    with col1:
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
        .rule-title {
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 10px;
        }
        </style>
        """, unsafe_allow_html=True)

        st.markdown('<div class="faction-rules">', unsafe_allow_html=True)
        st.subheader("📜 Règles Spéciales de la Faction")

        for rule_name, description in factions_by_game[st.session_state.game][st.session_state.faction]['special_rules_descriptions'].items():
            with st.expander(f"**{rule_name}**"):
                st.write(description)

        st.markdown('</div>', unsafe_allow_html=True)

    # Séparation par type (Héros/Unités)
    heroes = [u for u in st.session_state.units if u.get('type') == 'hero']
    units = [u for u in st.session_state.units if u.get('type') != 'hero']

    if heroes:
        st.subheader("🌟 HÉROS")
        for unit in heroes:
            with st.container():
                # Rectangle cliquable pour le héros
                st.markdown(f"""
                <div style="background-color: #2a2a2a; color: white; padding: 15px; border-radius: 8px; margin-bottom: 15px; cursor: pointer;"
                    onclick="document.getElementById('select-{unit['name'].replace(' ', '-')}').click()">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <h4 style="margin: 0; color: #ffd700;">{unit['name']} [1]</h4>
                            <p style="margin: 5px 0; color: #aaa;">Qua {unit['quality']}+ / Déf {unit.get('defense', '?')}+</p>
                        </div>
                        <div style="text-align: right;">
                            <p style="margin: 0; color: #4CAF50; font-weight: bold;">{unit['base_cost']} pts</p>
                        </div>
                    </div>
                    <div style="margin-top: 10px; color: #ccc;">
                        <p style="margin: 5px 0; font-style: italic;">{', '.join(unit.get('special_rules', []))}</p>
                        <p style="margin: 5px 0;">
                            {format_weapon(unit['weapons'][0]) if 'weapons' in unit and unit['weapons'] else 'Aucune arme'}
                        </p>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Bouton caché pour sélectionner l'unité
                if st.button(f"Sélectionner {unit['name']}", key=f"select-{unit['name'].replace(' ', '-')}"):
                    st.session_state.current_unit = unit
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
                # Rectangle cliquable pour l'unité
                st.markdown(f"""
                <div style="background-color: #1e1e1e; color: white; padding: 15px; border-radius: 8px; margin-bottom: 15px; cursor: pointer;"
                    onclick="document.getElementById('select-{unit['name'].replace(' ', '-')}').click()">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <h4 style="margin: 0; color: #fff;">{unit['name']} [{unit.get('size', 10)}]</h4>
                            <p style="margin: 5px 0; color: #aaa;">Qua {unit['quality']}+ / Déf {unit.get('defense', '?')}+</p>
                        </div>
                        <div style="text-align: right;">
                            <p style="margin: 0; color: #4CAF50; font-weight: bold;">{unit['base_cost']} pts</p>
                        </div>
                    </div>
                    <div style="margin-top: 10px; color: #ccc;">
                        <p style="margin: 5px 0; font-style: italic;">{', '.join(unit.get('special_rules', []))}</p>
                        <p style="margin: 5px 0;">
                            {format_weapon(unit['weapons'][0]) if 'weapons' in unit and unit['weapons'] else 'Aucune arme'}
                        </p>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Bouton caché pour sélectionner l'unité
                if st.button(f"Sélectionner {unit['name']}", key=f"select-{unit['name'].replace(' ', '-')}"):
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
    st.subheader(f"Liste d'armée actuelle ({st.session_state.army_cost}/{st.session_state.points} pts)")

    if not st.session_state.army_list:
        st.info("Ajoutez des unités pour commencer à construire votre armée")

    for i, u in enumerate(st.session_state.army_list):
        with st.container():
            st.markdown(f"""
            <div style="background-color: {'#2a2a2a' if u.get('type') == 'hero' else '#1e1e1e'}; color: white; padding: 15px; border-radius: 8px; margin-bottom: 10px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <h4 style="margin: 0; color: {'#ffd700' if u.get('type') == 'hero' else '#fff'};">
                            {u['name']} [{u.get('size', 1)}] {'🌟' if u.get('type') == 'hero' else ''}
                        </h4>
                        <p style="margin: 5px 0; color: #aaa;">
                            Qua {u['quality']}+ / Déf {u.get('defense', '?')}+
                        </p>
                    </div>
                    <div style="text-align: right; color: #4CAF50; font-weight: bold;">
                        {u['cost']} pts
                    </div>
                </div>
                <div style="margin-top: 10px; color: #ccc;">
                    <p style="margin: 5px 0;">
                        {format_weapon(u.get('weapon', {}))}
                    </p>
                    {f"<p style='margin: 5px 0;'>Monture: {format_mount(u.get('mount'))}</p>" if u.get('mount') else ""}
                </div>
            </div>
            """, unsafe_allow_html=True)

            if st.button(f"Supprimer", key=f"del-{i}"):
                st.session_state.history.append({
                    "army_list": copy.deepcopy(st.session_state.army_list),
                    "army_cost": st.session_state.army_cost
                })
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

# PAGE 3 - Options de l'unité (avec checkbox pour les héros)
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
        <p><strong>Règles spéciales:</strong> {', '.join(unit.get('special_rules', []))}</p>
    </div>
    """, unsafe_allow_html=True)

    # Option "Unité combinée" (désactivée pour les héros)
    if unit.get('type') != 'hero':
        options['combined'] = st.checkbox("Unité combinée", value=options['combined'])

    # Sélection des options
    total_cost = unit['base_cost']
    current_size = unit.get('size', 10)

    # Gestion des armes
    if 'weapons' in unit and unit['weapons']:
        st.subheader("Armes")
        weapon_options = [format_weapon(w) for w in unit['weapons']]

        if unit.get('type') == 'hero':
            # Pour les héros: checkbox pour chaque arme
            for i, weapon in enumerate(unit['weapons']):
                if st.checkbox(f"{format_weapon(weapon)}", key=f"weapon-{i}"):
                    options['weapon'] = weapon
        else:
            # Pour les unités: selectbox
            selected_weapon = st.selectbox(
                "Sélectionnez une arme",
                weapon_options,
                index=0,
                key="weapon_select"
            )
            selected_index = weapon_options.index(selected_weapon)
            options['weapon'] = unit['weapons'][selected_index]

    # Gestion des montures
    if 'upgrade_groups' in unit:
        for group in unit['upgrade_groups']:
            if group['type'] == 'mount' and 'options' in group:
                st.subheader(group['group'])

                if unit.get('type') == 'hero':
                    # Pour les héros: checkbox pour chaque monture
                    for option in group['options']:
                        if st.checkbox(f"{option['name']} (+{option['cost']} pts)", key=f"mount-{option['name']}"):
                            options['mount'] = option
                            total_cost += option['cost']
                else:
                    # Pour les unités: selectbox
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

    # Gestion des améliorations (toujours avec checkbox pour les héros)
    if 'upgrade_groups' in unit:
        for group in unit['upgrade_groups']:
            if group['type'] == 'upgrades' and 'options' in group:
                st.subheader(group['group'])

                if unit.get('type') == 'hero':
                    # Pour les héros: checkbox pour chaque amélioration
                    for option in group['options']:
                        if st.checkbox(f"{option['name']} (+{option['cost']} pts)", key=f"upgrade-{group['group']}-{option['name']}"):
                            if group['group'] not in options['selected_options']:
                                options['selected_options'][group['group']] = []
                            if not any(opt['name'] == option['name'] for opt in options['selected_options'].get(group['group'], [])):
                                options['selected_options'][group['group']].append(option)
                                total_cost += option['cost']
                else:
                    # Pour les unités: selectbox ou checkbox selon le nombre d'options
                    if len(group['options']) == 1:
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
                    else:
                        for option in group['options']:
                            if st.checkbox(f"{option['name']} (+{option['cost']} pts)", key=f"upgrade_{group['group']}_{option['name']}"):
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
            "combined": options['combined'] and unit.get('type') != 'hero'
        }

        st.session_state.army_list.append(unit_data)
        st.session_state.army_cost += total_cost
        st.session_state.page = "army_builder"
        st.rerun()
