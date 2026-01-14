import json
import re
from pathlib import Path
from collections import defaultdict
import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime
import os

# ======================
# Gestion du LocalStorage
# ======================

def localstorage_get(key):
    """Récupère une valeur du LocalStorage."""
    try:
        get_js = f"""
        <script>
        const value = localStorage.getItem('{key}');
        const input = document.createElement('input');
        input.style.display = 'none';
        input.id = 'localstorage_value_{key}';
        input.value = value || 'null';
        document.body.appendChild(input);
        </script>
        """
        components.html(get_js, height=0)
        value = st.text_input(f"localstorage_value_{key}", key=f"localstorage_value_{key}", label_visibility="collapsed")
        return None if value == "null" else value
    except Exception as e:
        st.error(f"Erreur LocalStorage: {e}")
        return None

def localstorage_set(key, value):
    """Stocke une valeur dans le LocalStorage."""
    try:
        set_js = f"""
        <script>
        localStorage.setItem('{key}', JSON.stringify({json.dumps(value)}));
        </script>
        """
        components.html(set_js, height=0)
    except Exception as e:
        st.error(f"Erreur LocalStorage: {e}")

def load_army_lists(player_name="default"):
    """Charge les listes d'armées."""
    try:
        data = localstorage_get(f"army_lists_{player_name}")
        return json.loads(data) if data else []
    except Exception as e:
        st.error(f"Erreur chargement listes: {e}")
        return []

def save_army_list(army_list_data, player_name="default"):
    """Sauvegarde une liste d'armée."""
    try:
        current_lists = load_army_lists(player_name)
        current_lists.append(army_list_data)
        localstorage_set(f"army_lists_{player_name}", current_lists)
        return True
    except Exception as e:
        st.error(f"Erreur sauvegarde: {e}")
        return False

def delete_army_list(player_name, list_index):
    """Supprime une liste d'armée."""
    try:
        current_lists = load_army_lists(player_name)
        if 0 <= list_index < len(current_lists):
            current_lists.pop(list_index)
            localstorage_set(f"army_lists_{player_name}", current_lists)
            return True
        return False
    except Exception as e:
        st.error(f"Erreur suppression: {e}")
        return False

# ======================
# Génération de fichiers
# ======================

def generate_html(army_data):
    """Génère le HTML pour une liste d'armée."""
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Liste OPR - {army_data['name']}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; color: #333; }}
            .army-title {{ color: #2c3e50; margin-bottom: 5px; }}
            .army-subtitle {{ color: #7f8c8d; margin-bottom: 20px; }}
            .unit-card {{
                border: 1px solid #ddd; border-radius: 8px;
                padding: 15px; margin-bottom: 20px; background: #f9f9f9;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            .unit-header {{
                display: flex; justify-content: space-between;
                margin-bottom: 10px; padding-bottom: 5px;
                border-bottom: 1px solid #eee;
            }}
            .unit-name {{ font-size: 1.2em; font-weight: bold; }}
            .unit-cost {{ color: #e74c3c; font-weight: bold; }}
            .stats {{
                display: flex; gap: 20px; margin: 10px 0;
                flex-wrap: wrap;
            }}
            .stat {{
                text-align: center; flex: 1; min-width: 80px;
                background: #f0f8ff; padding: 8px; border-radius: 5px;
            }}
            .stat-value {{ font-weight: bold; font-size: 1.1em; }}
            .stat-label {{ font-size: 0.8em; color: #555; }}
            .section-title {{
                font-weight: bold; color: #3498db;
                margin: 12px 0 8px; border-bottom: 1px dashed #ddd;
                padding-bottom: 3px;
            }}
            .weapons-table {{
                width: 100%; border-collapse: collapse;
                margin: 10px 0; font-size: 0.9em;
            }}
            .weapons-table th, .weapons-table td {{
                border: 1px solid #ddd; padding: 8px;
                text-align: center;
            }}
            .weapons-table th {{ background-color: #f2f2f2; }}
            .weapons-table td:first-child {{ text-align: left; }}
            .rules-list {{ margin-left: 20px; color: #555; }}
            .upgrade-item {{
                display: flex; justify-content: space-between;
                margin-bottom: 3px; padding: 3px 0;
            }}
            .combined-badge {{
                background: #27ae60; color: white;
                padding: 2px 6px; border-radius: 4px;
                font-size: 0.8em; margin-left: 10px;
            }}
            @media print {{
                body {{ margin: 0; padding: 20px; }}
                .unit-card {{ border: none; box-shadow: none; }}
            }}
        </style>
    </head>
    <body>
        <h1 class="army-title">Liste d'armée OPR - {army_data['name']}</h1>
        <h2 class="army-subtitle">{army_data['game']} • {army_data['faction']} • {army_data['total_cost']}/{army_data['points']} pts</h2>
    """

    for unit in army_data['army_list']:
        coriace = calculate_total_coriace(unit)
        unit_name = unit.get('name', 'Unité sans nom')
        unit_cost = unit.get('cost', 0)
        unit_quality = unit.get('quality', 3)
        unit_defense = unit.get('defense', 3)

        html_content += f"""
        <div class="unit-card">
            <div class="unit-header">
                <div>
                    <span class="unit-name">{unit_name} [{len(unit.get('models', ['10']))}]</span>
                    {'<span class="combined-badge">Unité combinée</span>' if unit.get('combined') else ''}
                </div>
                <div class="unit-cost">[{unit_cost} pts]</div>
            </div>

            <div class="stats">
                <div class="stat">
                    <div class="stat-value">{unit_quality}+</div>
                    <div class="stat-label">Qua</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{unit_defense}+</div>
                    <div class="stat-label">Déf</div>
                </div>
        """

        if coriace:
            html_content += f"""
                <div class="stat">
                    <div class="stat-value">{coriace}</div>
                    <div class="stat-label">Coriace</div>
                </div>
            """

        html_content += """
            </div>
        """

        # Règles spéciales
        if 'base_rules' in unit and unit['base_rules']:
            rules = []
            for rule in unit['base_rules']:
                rules.append(format_special_rule(rule))

            if rules:
                html_content += """
                <div class="section-title">Règles spéciales</div>
                <div class="rules-list">
                """ + ", ".join(rules) + """
                </div>
                """

        # Armes
        if 'current_weapon' in unit:
            weapon = unit['current_weapon']
            weapon_name = weapon.get('name', 'Arme de base')
            weapon_range = weapon.get('range', '-')
            weapon_attacks = weapon.get('attacks', '?')
            weapon_ap = weapon.get('armor_piercing', '?')
            weapon_special = ', '.join(weapon.get('special_rules', [])) or '-'

            html_content += """
            <div class="section-title">Armes</div>
            <table class="weapons-table">
                <thead>
                    <tr>
                        <th>Nom</th>
                        <th>RNG</th>
                        <th>ATK</th>
                        <th>AP</th>
                        <th>SPE</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>""" + weapon_name + """</td>
                        <td>""" + weapon_range + """</td>
                        <td>""" + str(weapon_attacks) + """</td>
                        <td>""" + str(weapon_ap) + """</td>
                        <td>""" + weapon_special + """</td>
                    </tr>
                </tbody>
            </table>
            """

        # Monture
        if 'mount' in unit:
            mount = unit['mount']
            mount_name = mount.get('name', '')
            mount_rules = ', '.join(mount.get('special_rules', [])) if 'special_rules' in mount else ''

            html_content += f"""
            <div class="section-title">Monture</div>
            <div class="upgrade-item">
                <span><strong>{mount_name}</strong></span>
            </div>
            """

            if mount_rules:
                html_content += f"""
                <div class="rules-list">{mount_rules}</div>
                """

        # Améliorations
        if 'options' in unit and unit['options']:
            html_content += '<div class="section-title">Améliorations</div>'

            for group_name, opts in unit['options'].items():
                if isinstance(opts, list):
                    for opt in opts:
                        opt_name = opt.get('name', '')
                        formatted_name = format_special_rule(opt_name)
                        html_content += f"""
                        <div class="upgrade-item">
                            <span>• {formatted_name}</span>
                        </div>
                        """
                elif isinstance(opts, dict):
                    opt_name = opts.get('name', '')
                    formatted_name = format_special_rule(opt_name)
                    html_content += f"""
                    <div class="upgrade-item">
                        <span>• {formatted_name}</span>
                    </div>
                    """

        html_content += "</div>"

    html_content += """
    </body>
    </html>
    """
    return html_content

def auto_export(army_data, filename_prefix):
    """Exporte automatiquement HTML et JSON."""
    try:
        # HTML
        html_content = generate_html(army_data)
        html_filename = f"{filename_prefix}.html"

        # JSON
        json_data = {
            "name": army_data['name'],
            "game": army_data['game'],
            "faction": army_data['faction'],
            "points": army_data['points'],
            "army_list": army_data['army_list'],
            "total_cost": army_data['total_cost'],
            "date": datetime.now().isoformat()
        }
        json_filename = f"{filename_prefix}_{datetime.now().strftime('%Y%m%d')}.json"
        json_str = json.dumps(json_data, indent=2, ensure_ascii=False)

        # Boutons de téléchargement
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label="📄 Télécharger HTML",
                data=html_content,
                file_name=html_filename,
                mime="text/html"
            )
        with col2:
            st.download_button(
                label="📁 Télécharger JSON",
                data=json_str,
                file_name=json_filename,
                mime="application/json"
            )

    except Exception as e:
        st.error(f"Erreur export: {e}")

# ======================
# Calculs et validations
# ======================

def format_special_rule(rule):
    """Formate une règle spéciale avec parenthèses si nécessaire."""
    if not isinstance(rule, str):
        return str(rule)

    # Si la règle contient déjà des parenthèses, on la retourne telle quelle
    if "(" in rule and ")" in rule:
        return rule

    # Sinon, on cherche un nombre et on ajoute des parenthèses
    match = re.search(r"(\D+)(\d+)", rule)
    if match:
        return f"{match.group(1)}({match.group(2)})"
    return rule

def extract_coriace(rules):
    """Extrait la valeur de Coriace (ignore Coriace(0))."""
    if not isinstance(rules, list):
        return 0
    total = 0
    for rule in rules:
        if isinstance(rule, str):
            match = re.search(r"Coriace\s*\(?(\d+)\)?", rule)
            if match and int(match.group(1)) > 0:
                total += int(match.group(1))
    return total

def calculate_total_coriace(unit):
    """Calcule la Coriace totale (ignore les valeurs 0)."""
    total = 0

    # Règles de base
    if 'base_rules' in unit:
        total += extract_coriace(unit['base_rules'])

    # Options
    if 'options' in unit:
        for opts in unit['options'].values():
            if isinstance(opts, list):
                for opt in opts:
                    if isinstance(opt, dict) and 'special_rules' in opt:
                        total += extract_coriace(opt['special_rules'])
            elif isinstance(opts, dict) and 'special_rules' in opts:
                total += extract_coriace(opts['special_rules'])

    # Monture
    if 'mount' in unit and isinstance(unit['mount'], dict):
        if 'special_rules' in unit['mount']:
            total += extract_coriace(unit['mount']['special_rules'])

    # Armes
    if 'current_weapon' in unit and isinstance(unit['current_weapon'], dict):
        if 'special_rules' in unit['current_weapon']:
            total += extract_coriace(unit['current_weapon']['special_rules'])

    return total if total > 0 else None

def validate_army(army_list, game_rules, total_cost, total_points):
    """Valide une liste d'armée."""
    errors = []

    if not army_list:
        errors.append("Aucune unité dans l'armée")
        return False, errors

    if total_cost > total_points:
        errors.append(f"Dépassement de {total_cost - total_points} pts")

    if game_rules:
        heroes = sum(1 for u in army_list if u.get('type', '').lower() == 'hero')
        max_heroes = max(1, total_points // game_rules['hero_per_points'])
        if heroes > max_heroes:
            errors.append(f"Trop de héros ({heroes}/{max_heroes} max)")

        unit_counts = defaultdict(int)
        for unit in army_list:
            unit_counts[unit['name']] += 1

        max_copies = 1 + (total_points // 750)
        for name, count in unit_counts.items():
            if count > max_copies:
                errors.append(f"Trop de copies de '{name}' ({count}/{max_copies} max)")

    return len(errors) == 0, errors

# ======================
# Application principale
# ======================

def main():
    # Initialisation
    if "page" not in st.session_state:
        st.session_state.page = "login"
        st.session_state.current_player = "Simon"  # Pseudo par défaut
        st.session_state.player_army_lists = []

    st.set_page_config(
        page_title="OPR Army Builder FR - Simon Joinville Fouquet",
        layout="wide"
    )

    # Chemins des données
    BASE_DIR = Path(__file__).resolve().parent
    FACTIONS_DIR = BASE_DIR / "lists" / "data" / "factions"
    FACTIONS_DIR.mkdir(parents=True, exist_ok=True)

    # Règles des jeux
    GAME_RULES = {
        "Age of Fantasy": {
            "hero_per_points": 375,
            "unit_copies": {750: 1},
            "max_unit_percentage": 35,
            "unit_per_points": 150,
        }
    }

    @st.cache_data
    def load_factions():
        """Charge les factions depuis les fichiers JSON."""
        factions = {}
        games = set()

        if not FACTIONS_DIR.exists():
            st.error(f"Dossier {FACTIONS_DIR} introuvable!")
            return {}, []

        for fp in FACTIONS_DIR.glob("*.json"):
            try:
                with open(fp, encoding="utf-8") as f:
                    data = json.load(f)
                    if "game" in data and "faction" in data:
                        game = data["game"]
                        faction = data["faction"]
                        if game not in factions:
                            factions[game] = {}
                        factions[game][faction] = data
                        games.add(game)
            except Exception as e:
                st.warning(f"Erreur chargement {fp.name}: {e}")

        return factions, sorted(games)

    # Charger les factions
    if "factions" not in st.session_state or "games" not in st.session_state:
        st.session_state.factions, st.session_state.games = load_factions()

    # PAGE 1: Accueil
    if st.session_state.page == "login":
        st.title("OPR Army Builder 🇫🇷")
        st.subheader(f"Bienvenue, Simon!")

        player_name = st.text_input(
            "Pseudo",
            value=st.session_state.current_player
        )

        if st.button("Commencer"):
            st.session_state.current_player = player_name
            st.session_state.player_army_lists = load_army_lists(player_name)
            st.session_state.page = "setup"
            st.rerun()

    # PAGE 2: Configuration
    elif st.session_state.page == "setup":
        st.title("OPR Army Builder 🇫🇷")
        st.subheader(f"Bienvenue, {st.session_state.current_player}!")

        # Boutons d'action
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Changer de pseudo"):
                st.session_state.page = "login"
                st.rerun()

        with col2:
            if st.button("💾 Exporter toutes mes listes"):
                all_lists = load_army_lists(st.session_state.current_player)
                if not all_lists:
                    st.warning("Aucune liste à exporter")
                else:
                    data = {
                        "player_name": st.session_state.current_player,
                        "army_lists": all_lists,
                        "date": datetime.now().isoformat()
                    }
                    filename = f"OPR_All_Lists_{st.session_state.current_player}.json"
                    st.download_button(
                        label="Télécharger JSON",
                        data=json.dumps(data, indent=2, ensure_ascii=False),
                        file_name=filename,
                        mime="application/json"
                    )

        # Import de fichiers
        uploaded_file = st.file_uploader("📥 Importer un fichier JSON", type=["json"])

        if uploaded_file:
            try:
                data = json.load(uploaded_file)
                if isinstance(data, dict) and "army_lists" in data:
                    player_name = data.get("player_name", st.session_state.current_player)
                    if save_army_list(data, player_name):
                        st.session_state.current_player = player_name
                        st.session_state.player_army_lists = data["army_lists"]
                        st.success("✅ Fichier importé avec succès!")
                        st.rerun()
                    else:
                        st.error("❌ Erreur lors de l'import")
                else:
                    st.error("Format JSON invalide")
            except Exception as e:
                st.error(f"Erreur import: {e}")

        # Info sauvegarde
        st.info("""
        💡 **Sauvegarde automatique**:
        Vos listes sont enregistrées dans votre navigateur (LocalStorage).
        Pour les transférer:
        1. Exportez-les (bouton ci-dessus)
        2. Envoyez le fichier par e-mail/cloud
        3. Importez-le sur un autre appareil
        """)

        # Listes sauvegardées
        st.subheader("Mes listes sauvegardées")

        if not st.session_state.player_army_lists:
            st.session_state.player_army_lists = load_army_lists(st.session_state.current_player)

        if st.session_state.player_army_lists:
            for i, army in enumerate(st.session_state.player_army_lists):
                col1, col2, col3 = st.columns([4, 1, 1])
                with col1:
                    with st.expander(f"{army['name']} ({army['total_cost']}/{army['points']} pts)"):
                        st.write(f"**Jeu**: {army['game']}")
                        st.write(f"**Faction**: {army['faction']}")
                        st.write(f"**Date**: {army['date'][:10]}")

                        if st.button(f"Charger cette liste", key=f"load_{i}"):
                            try:
                                if (army['game'] in st.session_state.factions and
                                    army['faction'] in st.session_state.factions[army['game']]):

                                    st.session_state.game = army['game']
                                    st.session_state.faction = army['faction']
                                    st.session_state.points = army['points']
                                    st.session_state.list_name = army['name']
                                    st.session_state.army_total_cost = army['total_cost']
                                    st.session_state.army_list = army['army_list']
                                    st.session_state.units = st.session_state.factions[army['game']][army['faction']]['units']
                                    st.session_state.page = "army"
                                    st.rerun()
                                else:
                                    st.error("Faction introuvable")
                            except Exception as e:
                                st.error(f"Erreur chargement: {e}")

                with col2:
                    if st.button(f"Exporter", key=f"export_{i}"):
                        auto_export(army, army['name'])

                with col3:
                    if st.button(f"❌ Supprimer", key=f"delete_{i}"):
                        if delete_army_list(st.session_state.current_player, i):
                            st.session_state.player_army_lists = load_army_lists(st.session_state.current_player)
                            st.rerun()
        else:
            st.info("Aucune liste sauvegardée")

        # Création nouvelle liste
        st.divider()
        st.subheader("Créer une nouvelle liste")

        if not st.session_state.games:
            st.error("Aucun jeu disponible. Vérifiez le dossier 'lists/data/factions/'")
        else:
            game = st.selectbox("Jeu", st.session_state.games)
            factions = list(st.session_state.factions[game].keys()) if game in st.session_state.factions else []
            faction = st.selectbox("Faction", factions) if factions else None

            points = st.number_input(
                "Points de la partie",
                min_value=250,
                max_value=5000,
                value=1000,
                step=250
            )

            list_name = st.text_input(
                "Nom de la liste",
                value=f"Liste_{datetime.now().strftime('%Y%m%d')}"
            )

            if st.button("Créer la liste") and game and faction:
                st.session_state.game = game
                st.session_state.faction = faction
                st.session_state.points = points
                st.session_state.list_name = list_name
                st.session_state.army_list = []
                st.session_state.army_total_cost = 0
                st.session_state.units = st.session_state.factions[game][faction]['units']
                st.session_state.page = "army"
                st.rerun()

    # PAGE 3: Composition de l'armée
    elif st.session_state.page == "army":
        st.title(st.session_state.list_name)
        st.caption(f"{st.session_state.game} • {st.session_state.faction} • {st.session_state.army_total_cost}/{st.session_state.points} pts")

        # Boutons de navigation
        col1, col2 = st.columns(2)
        with col1:
            if st.button("⬅ Retour"):
                st.session_state.page = "setup"
                st.rerun()
        with col2:
            if st.button("🚪 Quitter"):
                st.session_state.page = "login"
                st.rerun()

        # Ajout d'une unité
        st.divider()
        st.subheader("Ajouter une unité")

        unit = st.selectbox(
            "Unité disponible",
            st.session_state.units,
            format_func=lambda u: f"{u['name']} ({u['base_cost']} pts)"
        )

        # Affichage des stats de base
        st.markdown(f"**{unit['name']}** - {unit['base_cost']} pts")
        col1, col2 = st.columns(2)
        col1.metric("Qua", f"{unit['quality']}+")
        col2.metric("Déf", f"{unit['defense']}+")

        # Option unité combinée
        combined = False
        if unit.get('type', '').lower() != 'hero':
            combined = st.checkbox("Unité combinée (+100% coût)", value=False)

        cost = unit["base_cost"] * 2 if combined else unit["base_cost"]
        base_rules = unit.get('special_rules', [])
        current_weapon = unit.get('weapons', [{}])[0].copy()
        selected_options = {}
        mount = None

        # Armes de base
        st.markdown("**Armes de base**")
        for weapon in unit.get("weapons", []):
            st.caption(f"- {weapon.get('name', 'Arme de base')} (A{weapon.get('attacks', '?')}, PA{weapon.get('armor_piercing', '?')})")

        # Options par catégorie
        for group in unit.get("upgrade_groups", []):
            st.subheader(group["group"])

            if group.get("type") == "multiple":
                # Options multiples (cases à cocher)
                for opt in group.get("options", []):
                    opt_cost = opt["cost"] * (2 if combined else 1)
                    if st.checkbox(
                        f"{opt['name']} (+{opt_cost} pts)",
                        key=f"{unit['name']}_{group['group']}_{opt['name']}"
                    ):
                        if group["group"] not in selected_options:
                            selected_options[group["group"]] = []
                        selected_options[group["group"]].append(opt)
                        cost += opt_cost

            elif group.get("type") == "weapon":
                # Choix d'arme (boutons radio)
                weapon_options = ["Arme de base"]
                for opt in group.get("options", []):
                    opt_cost = opt.get("cost", 0) * (2 if combined else 1)
                    weapon_options.append(f"{opt['name']} (+{opt_cost} pts)")

                selected = st.radio(
                    "Choisir une arme",
                    weapon_options,
                    key=f"{unit['name']}_weapon"
                )

                if selected != "Arme de base":
                    opt_name = selected.split(" (+")[0]
                    opt = next(o for o in group["options"] if o["name"] == opt_name)
                    cost += opt.get("cost", 0) * (2 if combined else 1)
                    current_weapon = opt.get("weapon", {})

            elif group.get("type") == "mount":
                # Choix de monture
                mount_options = ["Aucune monture"]
                for opt in group.get("options", []):
                    mount_options.append(f"{opt['name']} (+{opt.get('cost', 0)} pts)")

                selected = st.radio(
                    "Choisir une monture",
                    mount_options,
                    key=f"{unit['name']}_mount"
                )

                if selected != "Aucune monture":
                    opt_name = selected.split(" (+")[0]
                    opt = next(o for o in group["options"] if o["name"] == opt_name)
                    cost += opt.get("cost", 0)
                    mount = opt.get("mount")

        st.markdown(f"**Coût total: {cost} pts**")

        if st.button("Ajouter à l'armée"):
            unit_data = {
                'name': unit['name'],
                'cost': cost,
                'quality': unit['quality'],
                'defense': unit['defense'],
                'type': unit.get('type', 'Infantry'),
                'base_rules': [format_special_rule(rule) for rule in base_rules],
                'current_weapon': current_weapon,
                'options': selected_options,
                'combined': combined,
                'models': ['10']  # Par défaut pour l'affichage [10]
            }

            if mount:
                unit_data['mount'] = mount

            st.session_state.army_list.append(unit_data)
            st.session_state.army_total_cost += cost
            st.rerun()

        # Affichage de l'armée
        st.divider()
        st.subheader("Liste de l'armée")

        if not st.session_state.army_list:
            st.info("Ajoutez des unités pour commencer")

        for i, unit in enumerate(st.session_state.army_list):
            with st.container():
                coriace = calculate_total_coriace(unit)

                # En-tête de l'unité
                st.markdown(f"### {unit['name']} [{len(unit.get('models', ['10']))}] [{unit['cost']} pts]")

                # Stats
                stats_col1, stats_col2, stats_col3 = st.columns(3)
                stats_col1.metric("Qua", f"{unit['quality']}+")
                stats_col2.metric("Déf", f"{unit['defense']}+")
                if coriace:
                    stats_col3.metric("Coriace", coriace)

                # Règles spéciales
                if 'base_rules' in unit and unit['base_rules']:
                    st.markdown("**Règles spéciales**")
                    st.caption(", ".join(unit['base_rules']))

                # Armes
                if 'current_weapon' in unit:
                    weapon = unit['current_weapon']
                    st.markdown("**Armes**")

                    weapons_html = f"""
                    <style>
                    .custom-weapons-table {{
                        width: 100%;
                        border-collapse: collapse;
                        margin: 10px 0;
                        font-size: 0.9em;
                    }}
                    .custom-weapons-table th, .custom-weapons-table td {{
                        border: 1px solid #ddd;
                        padding: 8px;
                        text-align: center;
                    }}
                    .custom-weapons-table th {{
                        background-color: #f2f2f2;
                    }}
                    .custom-weapons-table td:first-child {{
                        text-align: left;
                    }}
                    </style>
                    <table class="custom-weapons-table">
                        <thead>
                            <tr>
                                <th>Nom</th>
                                <th>RNG</th>
                                <th>ATK</th>
                                <th>AP</th>
                                <th>SPE</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td>{weapon.get('name', 'Arme de base')}</td>
                                <td>{weapon.get('range', '-')}</td>
                                <td>{weapon.get('attacks', '?')}</td>
                                <td>{weapon.get('armor_piercing', '?')}</td>
                                <td>{', '.join(weapon.get('special_rules', [])) or '-'}</td>
                            </tr>
                        </tbody>
                    </table>
                    """
                    components.html(weapons_html, height=100)

                # Améliorations
                if 'options' in unit and unit['options']:
                    st.markdown("**Améliorations**")
                    for opts in unit['options'].values():
                        if isinstance(opts, list):
                            for opt in opts:
                                st.caption(f"• {opt.get('name', '')}")
                        elif isinstance(opts, dict):
                            st.caption(f"• {opts.get('name', '')}")

                if st.button(f"Supprimer", key=f"del_{i}"):
                    st.session_state.army_total_cost -= unit['cost']
                    st.session_state.army_list.pop(i)
                    st.rerun()

        # Validation et boutons
        st.divider()
        game_rules = GAME_RULES.get(st.session_state.game, {})
        is_valid, errors = validate_army(
            st.session_state.army_list,
            game_rules,
            st.session_state.army_total_cost,
            st.session_state.points
        )

        progress = min(1.0, st.session_state.army_total_cost / st.session_state.points) if st.session_state.points else 0
        st.progress(progress)
        st.markdown(f"**{st.session_state.army_total_cost}/{st.session_state.points} pts**")

        if not is_valid:
            st.warning("Problèmes avec la liste:")
            for error in errors:
                st.error(f"- {error}")

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("Sauvegarder"):
                if not st.session_state.list_name:
                    st.warning("Donnez un nom à votre liste")
                else:
                    army_data = {
                        "name": st.session_state.list_name,
                        "game": st.session_state.game,
                        "faction": st.session_state.faction,
                        "points": st.session_state.points,
                        "army_list": st.session_state.army_list,
                        "total_cost": st.session_state.army_total_cost,
                        "date": datetime.now().isoformat()
                    }
                    if save_army_list(army_data, st.session_state.current_player):
                        st.session_state.player_army_lists = load_army_lists(st.session_state.current_player)
                        st.success("Liste sauvegardée!")
                    else:
                        st.error("Erreur de sauvegarde")

        with col2:
            if st.button("Exporter"):
                army_data = {
                    "name": st.session_state.list_name,
                    "game": st.session_state.game,
                    "faction": st.session_state.faction,
                    "points": st.session_state.points,
                    "army_list": st.session_state.army_list,
                    "total_cost": st.session_state.army_total_cost,
                    "date": datetime.now().isoformat()
                }
                auto_export(army_data, st.session_state.list_name)

        with col3:
            if st.button("Réinitialiser"):
                st.session_state.army_list = []
                st.session_state.army_total_cost = 0
                st.rerun()

if __name__ == "__main__":
    main()
