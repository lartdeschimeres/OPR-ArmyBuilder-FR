import json
import re
from pathlib import Path
from collections import defaultdict
import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime
import os

# Compteur global pour éviter les conflits de clés
if "localstorage_counter" not in st.session_state:
    st.session_state.localstorage_counter = 0

def get_unique_key():
    """Génère une clé unique pour éviter les conflits."""
    st.session_state.localstorage_counter += 1
    return f"localstorage_value_{st.session_state.localstorage_counter}"

def localstorage_get(key):
    """Récupère une valeur du LocalStorage via JavaScript."""
    unique_key = get_unique_key()
    get_js = f"""
    <script>
    const value = localStorage.getItem('{key}');
    const input = window.parent.document.createElement('input');
    input.style.display = 'none';
    input.id = '{unique_key}';
    input.value = value || 'null';
    window.parent.document.body.appendChild(input);
    </script>
    """
    components.html(get_js, height=0)

    js = f"""
    <script>
    const value = document.getElementById('{unique_key}').value;
    window.parent.document.getElementById('{unique_key}').remove();
    </script>
    """
    components.html(js, height=0)
    value = st.text_input("hidden_input", key=unique_key, label_visibility="collapsed")
    return value

def localstorage_set(key, value):
    """Stocke une valeur dans le LocalStorage."""
    set_js = f"""
    <script>
    localStorage.setItem('{key}', {json.dumps(value)});
    </script>
    """
    components.html(set_js, height=0)

def save_army_list(army_list_data, player_name="default"):
    """Sauvegarde une liste d'armée dans le LocalStorage."""
    army_lists = json.loads(localstorage_get(f"army_lists_{player_name}") or "[]")
    army_lists.append(army_list_data)
    localstorage_set(f"army_lists_{player_name}", army_lists)

def load_army_lists(player_name="default"):
    """Charge les listes d'armées depuis le LocalStorage."""
    return json.loads(localstorage_get(f"army_lists_{player_name}") or "[]")

def delete_army_list(player_name, list_index):
    """Supprime une liste d'armée du LocalStorage."""
    army_lists = json.loads(localstorage_get(f"army_lists_{player_name}") or "[]")
    if list_index < 0 or list_index >= len(army_lists):
        return False
    army_lists.pop(list_index)
    localstorage_set(f"army_lists_{player_name}", army_lists)
    return True

def generate_html_content(army_list_data):
    """Génère le contenu HTML pour une liste d'armée."""
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Liste d'armée OPR - {army_list_data['name']}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1 {{ color: #333; }}
            .unit-container {{
                border: 2px solid #4a89dc;
                border-radius: 10px;
                padding: 15px;
                margin-bottom: 20px;
                background: white;
            }}
            .unit-header {{
                display: flex;
                justify-content: space-between;
                margin-bottom: 10px;
                border-bottom: 1px solid #eee;
                padding-bottom: 5px;
            }}
            .unit-name {{
                font-size: 1.3em;
                font-weight: bold;
                color: #333;
            }}
            .unit-cost {{
                color: #666;
                font-size: 1.1em;
            }}
            .stats-container {{
                display: flex;
                gap: 20px;
                margin-bottom: 15px;
            }}
            .stat {{
                text-align: center;
                flex: 1;
            }}
            .stat-value {{
                font-weight: bold;
                font-size: 1.2em;
            }}
            .stat-label {{
                font-size: 0.9em;
                color: #666;
            }}
            .section-title {{
                font-weight: bold;
                color: #4a89dc;
                margin: 10px 0 5px 0;
                border-bottom: 1px dashed #ddd;
                padding-bottom: 3px;
            }}
            .weapons-table {{
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 10px;
            }}
            .weapons-table th, .weapons-table td {{
                border: 1px solid #ddd;
                padding: 8px;
                text-align: left;
            }}
            .weapons-table th {{
                background-color: #f5f5f5;
            }}
            .rules-list {{
                margin-left: 20px;
                color: #555;
            }}
            .upgrade-item {{
                display: flex;
                justify-content: space-between;
                margin-bottom: 3px;
            }}
            .combined-badge {{
                background-color: #28a745;
                color: white;
                padding: 3px 8px;
                border-radius: 12px;
                font-size: 0.8em;
                display: inline-block;
                margin-left: 10px;
            }}
            @media print {{
                body {{ margin: 0; padding: 20px; }}
                .unit-container {{ border: none; box-shadow: none; }}
            }}
        </style>
    </head>
    <body>
        <h1>Liste d'armée OPR - {army_list_data['name']}</h1>
        <h2>{army_list_data['game']} - {army_list_data['faction']} - {army_list_data['total_cost']}/{army_list_data['points']} pts</h2>
    """

    for u in army_list_data['army_list']:
        coriace_value = calculate_total_coriace(u)
        html_content += f"""
        <div class="unit-container">
            <div class="unit-header">
                <div>
                    <span class="unit-name">{u['name']}</span>
                    {f'<span class="combined-badge">Unité combinée</span>' if u.get("combined", False) else ''}
                </div>
                <div class="unit-cost">{u['cost']} pts</div>
            </div>

            <div class="stats-container">
                <div class="stat">
                    <div class="stat-value">{u['quality']}+</div>
                    <div class="stat-label">Qualité</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{u['defense']}+</div>
                    <div class="stat-label">Défense</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{coriace_value}</div>
                    <div class="stat-label">Coriace</div>
                </div>
            </div>
        """

        # Règles spéciales de base
        if u.get("base_rules"):
            base_rules = [r for r in u['base_rules'] if not r.startswith("Coriace")]
            if base_rules:
                html_content += f"""
                <div class="section-title">Règles spéciales de base</div>
                <div class="rules-list">{', '.join(base_rules)}</div>
                """

        # Armes
        if 'current_weapon' in u:
            weapon = u['current_weapon']
            html_content += """
            <div class="section-title">Armes</div>
            <table class="weapons-table">
                <thead>
                    <tr>
                        <th>Nom</th>
                        <th>ATK</th>
                        <th>AP</th>
                        <th>Règles Spéciales</th>
                    </tr>
                </thead>
                <tbody>
            """

            weapon_name = weapon.get('name', 'Arme de base')
            attacks = weapon.get('attacks', '?')
            armor_piercing = weapon.get('armor_piercing', '?')
            special_rules = ', '.join(weapon.get('special_rules', []))

            html_content += f"""
                    <tr>
                        <td>{weapon_name}</td>
                        <td>{attacks}</td>
                        <td>{armor_piercing}</td>
                        <td>{special_rules}</td>
                    </tr>
            """

            html_content += """
                </tbody>
            </table>
            """

        # Monture
        if u.get("mount"):
            mount = u['mount']
            html_content += f"""
            <div class="section-title">Monture</div>
            <div class="upgrade-item">
                <span><strong>{mount.get('name', '')}</strong></span>
            </div>
            """
            if 'special_rules' in mount and mount['special_rules']:
                html_content += f"""
                <div class="rules-list">{', '.join(mount['special_rules'])}</div>
                """

        # Améliorations
        if u.get("options"):
            html_content += """
            <div class="section-title">Améliorations d'unité</div>
            """
            for group_name, opt_group in u["options"].items():
                if isinstance(opt_group, list):
                    for opt in opt_group:
                        if isinstance(opt, dict):
                            html_content += f"""
                            <div class="upgrade-item">
                                <span>- {opt.get('name', '')}</span>
                                <span>+{opt.get('cost', 0)} pts</span>
                            </div>
                            """
                elif isinstance(opt_group, dict):
                    html_content += f"""
                    <div class="upgrade-item">
                        <span>- {opt_group.get('name', '')}</span>
                        <span>+{opt_group.get('cost', 0)} pts</span>
                    </div>
                    """

        html_content += "</div>"

    html_content += """
    </body>
    </html>
    """
    return html_content

def auto_export(army_list_data, list_name):
    """Génère et télécharge automatiquement HTML et JSON."""
    # Générer le HTML
    html_content = generate_html_content(army_list_data)
    html_filename = f"{list_name or 'army_list'}.html"
    with open(html_filename, "w", encoding="utf-8") as f:
        f.write(html_content)

    # Générer le JSON
    json_data = {
        "name": army_list_data['name'],
        "game": army_list_data['game'],
        "faction": army_list_data['faction'],
        "points": army_list_data['points'],
        "army_list": army_list_data['army_list'],
        "total_cost": army_list_data['total_cost'],
        "date": datetime.now().isoformat(),
        "metadata": {
            "version": "1.0",
            "source": "OPR Army Builder",
            "coriace_total": sum(calculate_total_coriace(u) for u in army_list_data['army_list'])
        }
    }
    json_filename = f"{list_name or 'army_list'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    json_str = json.dumps(json_data, indent=2, ensure_ascii=False)

    # Afficher les boutons de téléchargement
    col1, col2 = st.columns(2)
    with col1:
        with open(html_filename, "r", encoding="utf-8") as f:
            st.download_button(
                label="📄 Télécharger HTML",
                data=f,
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

    # Supprimer le fichier HTML temporaire
    try:
        os.remove(html_filename)
    except:
        pass

def repair_army_list(army_list):
    """Répare une liste d'armée sauvegardée."""
    repaired_list = []
    for unit in army_list:
        try:
            if not isinstance(unit, dict):
                continue
            repaired_unit = unit.copy()
            repaired_unit.setdefault("type", "Infantry")
            repaired_unit.setdefault("base_cost", repaired_unit.get("cost", 0))
            required_keys = ["name", "cost", "quality", "defense"]
            if all(key in repaired_unit for key in required_keys):
                repaired_list.append(repaired_unit)
        except Exception as e:
            continue
    return repaired_list

def extract_coriace(rules):
    """Extrait la valeur de Coriace à partir des règles."""
    total = 0
    if not isinstance(rules, list):
        return 0
    for r in rules:
        if not isinstance(r, str):
            continue
        m = re.search(r"Coriace\s*\(?\+?(\d+)\)?", r)
        if m:
            total += int(m.group(1))
    return total

def calculate_total_coriace(unit_data):
    """Calcule la valeur totale de Coriace pour une unité."""
    total = 0

    # Règles de base
    if "base_rules" in unit_data and isinstance(unit_data["base_rules"], list):
        total += extract_coriace(unit_data["base_rules"])

    # Options
    if "options" in unit_data and isinstance(unit_data["options"], dict):
        for option_group in unit_data["options"].values():
            if isinstance(option_group, list):
                for option in option_group:
                    if isinstance(option, dict) and "special_rules" in option:
                        total += extract_coriace(option["special_rules"])
            elif isinstance(option_group, dict) and "special_rules" in option_group:
                total += extract_coriace(option_group["special_rules"])

    # Monture
    if "mount" in unit_data and isinstance(unit_data["mount"], dict):
        if "special_rules" in unit_data["mount"]:
            total += extract_coriace(unit_data["mount"]["special_rules"])

    # Armes
    if "weapons" in unit_data and isinstance(unit_data["weapons"], list):
        for weapon in unit_data["weapons"]:
            if isinstance(weapon, dict) and "special_rules" in weapon:
                total += extract_coriace(weapon["special_rules"])

    # Héros spécifiques
    if unit_data.get("type", "").lower() == "hero":
        if "options" in unit_data and isinstance(unit_data["options"], dict):
            for group_name, option_group in unit_data["options"].items():
                if isinstance(option_group, list):
                    for option in option_group:
                        if isinstance(option, dict) and "special_rules" in option:
                            total += extract_coriace(option["special_rules"])
                elif isinstance(option_group, dict) and "special_rules" in option_group:
                    total += extract_coriace(option_group["special_rules"])

    return total

def validate_army(army_list, game_rules, total_cost, total_points):
    """Valide une liste d'armée selon les règles du jeu."""
    errors = []
    if not army_list:
        errors.append("Aucune unité dans l'armée")
        return False, errors
    if total_cost > total_points:
        errors.append(f"Dépassement de {total_cost - total_points} pts (max: {total_points} pts)")
    if game_rules:
        heroes = sum(1 for u in army_list if u.get("type", "").lower() == "hero")
        max_heroes = max(1, total_points // game_rules["hero_per_points"])
        if heroes > max_heroes:
            errors.append(f"Trop de héros ({heroes}/{max_heroes} max)")
        unit_counts = defaultdict(int)
        for unit in army_list:
            unit_counts[unit["name"]] += 1
        max_copies = 1 + (total_points // 750)
        for unit_name, count in unit_counts.items():
            if count > max_copies:
                errors.append(f"Trop de copies de '{unit_name}' ({count}/{max_copies} max)")
        for unit in army_list:
            percentage = (unit["cost"] / total_points) * 100
            if percentage > game_rules["max_unit_percentage"]:
                errors.append(f"'{unit['name']}' dépasse {game_rules['max_unit_percentage']}% du total")
        max_units = total_points // game_rules["unit_per_points"]
        if len(army_list) > max_units:
            errors.append(f"Trop d'unités ({len(army_list)}/{max_units} max)")
    return len(errors) == 0, errors

def main():
    # Initialisation de la session
    if "page" not in st.session_state:
        st.session_state.page = "login"

    # Configuration de la page
    st.set_page_config(page_title="OPR Army Builder FR", layout="centered")

    # Définir les chemins locaux
    BASE_DIR = Path(__file__).resolve().parent
    FACTIONS_DIR = BASE_DIR / "lists" / "data" / "factions"
    FACTIONS_DIR.mkdir(exist_ok=True, parents=True)

    # Règles spécifiques par jeu
    GAME_RULES = {
        "Age of Fantasy": {
            "hero_per_points": 375,
            "unit_copies": {750: 1},
            "max_unit_percentage": 35,
            "unit_per_points": 150,
        }
    }

    def init_session_state():
        defaults = {
            "game": None,
            "faction": None,
            "points": 1000,
            "list_name": "",
            "army_list": [],
            "army_total_cost": 0,
            "is_army_valid": True,
            "validation_errors": [],
            "current_player": "default",
            "player_army_lists": [],
            "units": [],
            "factions": {},
            "games": []
        }
        for key, default in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = default

    init_session_state()

    @st.cache_data
    def load_factions():
        try:
            factions = {}
            games = set()

            if not FACTIONS_DIR.exists():
                st.error(f"Le dossier {FACTIONS_DIR} n'existe pas!")
                FACTIONS_DIR.mkdir(parents=True, exist_ok=True)
                return {}, []

            faction_files = list(FACTIONS_DIR.glob("*.json"))
            if not faction_files:
                st.warning(f"Aucun fichier JSON trouvé dans {FACTIONS_DIR}")
                return {}, []

            for fp in faction_files:
                try:
                    with open(fp, encoding="utf-8") as f:
                        data = json.load(f)
                        if "game" not in data or "faction" not in data:
                            st.warning(f"Fichier {fp.name} invalide: champs manquants")
                            continue
                        game = data["game"]
                        faction_name = data["faction"]
                        if game not in factions:
                            factions[game] = {}
                        factions[game][faction_name] = data
                        games.add(game)
                except Exception as e:
                    st.warning(f"Erreur avec {fp.name}: {str(e)}")

            return factions, sorted(games)
        except Exception as e:
            st.error(f"Erreur critique: {str(e)}")
            return {}, []

    # Charger les factions
    if not st.session_state["factions"] or not st.session_state["games"]:
        st.session_state["factions"], st.session_state["games"] = load_factions()

    # PAGE 1 — Accueil
    if st.session_state.page == "login":
        st.title("OPR Army Builder 🇫🇷")
        st.subheader("Bienvenue !")

        player_name = st.text_input("Pseudo (optionnel)", value=st.session_state.current_player)
        if st.button("Commencer"):
            st.session_state.current_player = player_name
            st.session_state.player_army_lists = load_army_lists(player_name)
            st.session_state.page = "setup"
            st.rerun()

    # PAGE 2 — Configuration
    elif st.session_state.page == "setup":
        st.title("OPR Army Builder 🇫🇷")
        st.subheader(f"Bienvenue, {st.session_state.current_player}!")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Changer de pseudo"):
                st.session_state.page = "login"
                st.rerun()

        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Exporter toutes mes listes"):
                army_lists = load_army_lists(st.session_state.current_player)
                if not army_lists:
                    st.warning("Aucune liste à exporter.")
                else:
                    data = {
                        "player_name": st.session_state.current_player,
                        "army_lists": army_lists,
                        "date": datetime.now().isoformat(),
                        "metadata": {
                            "version": "1.0",
                            "total_lists": len(army_lists),
                            "total_coriace": sum(calculate_total_coriace(u) for army in army_lists for u in army["army_list"])
                        }
                    }
                    json_filename = f"OPR_All_Lists_{st.session_state.current_player}_{datetime.now().strftime('%Y%m%d')}.json"
                    json_str = json.dumps(data, indent=2, ensure_ascii=False)
                    st.download_button(
                        label="Télécharger JSON",
                        data=json_str,
                        file_name=json_filename,
                        mime="application/json"
                    )

        with col2:
            uploaded_file = st.file_uploader("📥 Importer un fichier JSON", type=["json"])
            if uploaded_file:
                try:
                    data = json.load(uploaded_file)
                    if "army_lists" in data and "player_name" in data:
                        localstorage_set(f"army_lists_{data['player_name']}", data["army_lists"])
                        st.session_state.current_player = data["player_name"]
                        st.session_state.player_army_lists = data["army_lists"]
                        st.success(f"Données importées pour {data['player_name']}!")
                        st.rerun()
                except Exception as e:
                    st.error(f"Erreur d'import: {str(e)}")

        st.info("""
        💡 **Sauvegarde** : Vos listes sont enregistrées dans votre navigateur.
        Pour les transférer :
        1. Exportez-les (bouton ci-dessus)
        2. Envoyez le fichier par e-mail/cloud
        3. Importez-le sur un autre appareil
        """)

        st.subheader("Mes listes sauvegardées")
        if st.session_state.player_army_lists:
            for i, army_list in enumerate(st.session_state.player_army_lists):
                col1, col2, col3 = st.columns([4, 1, 1])
                with col1:
                    with st.expander(f"{army_list['name']} ({army_list['total_cost']}/{army_list['points']} pts)"):
                        st.write(f"Jeu: {army_list['game']}")
                        st.write(f"Faction: {army_list['faction']}")
                        st.write(f"Créée le: {army_list['date'][:10]}")
                        if st.button(f"Charger", key=f"load_{i}"):
                            st.session_state.game = army_list['game']
                            st.session_state.faction = army_list['faction']
                            st.session_state.points = army_list['points']
                            st.session_state.list_name = army_list['name']
                            st.session_state.army_total_cost = army_list['total_cost']
                            st.session_state.army_list = repair_army_list(army_list['army_list'])
                            st.session_state.page = "army"
                            st.rerun()

                with col2:
                    if st.button(f"Exporter", key=f"export_{i}"):
                        auto_export(army_list, army_list['name'])

                with col3:
                    if st.button(f"❌ Supprimer", key=f"delete_{i}"):
                        if delete_army_list(st.session_state.current_player, i):
                            st.session_state.player_army_lists = load_army_lists(st.session_state.current_player)
                            st.success("Liste supprimée!")
                            st.rerun()

        else:
            st.info("Aucune liste sauvegardée")

        st.divider()
        st.subheader("Créer une nouvelle liste")

        if not st.session_state["games"]:
            st.error("Aucun jeu disponible. Vérifiez les fichiers JSON.")
        else:
            st.session_state.game = st.selectbox(
                "Jeu", st.session_state["games"],
                index=0 if st.session_state["games"] else None
            )

            if st.session_state.game:
                factions = list(st.session_state["factions"][st.session_state.game].keys())
                if not factions:
                    st.warning(f"Aucune faction pour {st.session_state.game}")
                else:
                    st.session_state.faction = st.selectbox(
                        "Faction", factions,
                        index=0 if factions else None
                    )

                    st.session_state.points = st.number_input(
                        "Points", min_value=250, max_value=5000,
                        value=1000, step=250
                    )

                    st.session_state.list_name = st.text_input(
                        "Nom de la liste", value="Ma liste d'armée"
                    )

                    if st.button("➡️ Créer la liste"):
                        if st.session_state.game and st.session_state.faction:
                            faction_data = st.session_state["factions"][st.session_state.game][st.session_state.faction]
                            st.session_state.units = faction_data["units"]
                            st.session_state.page = "army"
                            st.rerun()

    # PAGE 3 — Composition de l'armée
    elif st.session_state.page == "army":
        st.title(st.session_state.list_name)
        st.caption(f"{st.session_state.game} — {st.session_state.faction} — {st.session_state.army_total_cost}/{st.session_state.points} pts")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("⬅️ Retour"):
                st.session_state.page = "setup"
                st.rerun()
        with col2:
            if st.button("🚪 Quitter"):
                st.session_state.page = "login"
                st.rerun()

        # Section pour ajouter une unité
        st.divider()
        st.subheader("Ajouter une unité")

        unit = st.selectbox(
            "Unité",
            st.session_state.units,
            format_func=lambda u: f"{u['name']} ({u['base_cost']} pts)"
        )

        # Affichage des stats de base
        st.markdown(f"**{unit['name']}** - {unit['base_cost']} pts")
        col1, col2 = st.columns(2)
        col1.metric("Qualité", f"{unit['quality']}+")
        col2.metric("Défense", f"{unit['defense']}+")

        # Option unité combinée
        combined_unit = False
        if unit.get("type", "").lower() != "hero":
            combined_unit = st.checkbox("Unité combinée (x2 effectif, +100% coût)", value=False)

        total_cost = unit["base_cost"]
        if combined_unit:
            total_cost = unit["base_cost"] * 2

        # Initialisation des données
        base_rules = list(unit.get("special_rules", []))
        options_selected = {}
        current_weapon = unit.get("weapons", [{"name": "Arme de base"}])[0].copy()
        mount_selected = None

        # Armes de base
        st.markdown("**Armes de base**")
        for weapon in unit.get("weapons", []):
            st.caption(f"- {weapon.get('name', 'Inconnue')} (A{weapon.get('attacks', '?')}, PA{weapon.get('armor_piercing', '?')})")

        # Options par groupe
        for group in unit.get("upgrade_groups", []):
            st.subheader(group["group"])

            if group.get("type") == "multiple":
                # Options multiples (cases à cocher)
                for opt in group["options"]:
                    cost = opt["cost"] * (2 if combined_unit else 1)
                    if st.checkbox(
                        f"{opt['name']} (+{cost} pts)",
                        key=f"{unit['name']}_{group['group']}_{opt['name']}"
                    ):
                        if group["group"] not in options_selected:
                            options_selected[group["group"]] = []
                        options_selected[group["group"]].append(opt)
                        total_cost += cost

            elif group.get("type") == "weapon":
                # Choix d'arme (boutons radio)
                weapon_options = ["Arme de base"]
                for opt in group["options"]:
                    cost = opt.get("cost", 0) * (2 if combined_unit else 1)
                    weapon_options.append(f"{opt['name']} (+{cost} pts)")

                selected = st.radio(
                    "Choisir une arme",
                    weapon_options,
                    key=f"{unit['name']}_weapon"
                )
                if selected != "Arme de base":
                    opt_name = selected.split(" (+")[0]
                    opt = next(o for o in group["options"] if o["name"] == opt_name)
                    total_cost += opt.get("cost", 0) * (2 if combined_unit else 1)
                    current_weapon = opt["weapon"].copy()

            elif group.get("type") == "mount":
                # Choix de monture (boutons radio)
                mount_options = ["Aucune monture"]
                for opt in group["options"]:
                    cost = opt.get("cost", 0)
                    mount_options.append(f"{opt['name']} (+{cost} pts)")

                selected = st.radio(
                    "Choisir une monture",
                    mount_options,
                    key=f"{unit['name']}_mount"
                )
                if selected != "Aucune monture":
                    opt_name = selected.split(" (+")[0]
                    opt = next(o for o in group["options"] if o["name"] == opt_name)
                    total_cost += opt.get("cost", 0)
                    mount_selected = opt.get("mount")

        st.markdown(f"**Coût total: {total_cost} pts**")

        if st.button("➕ Ajouter à l'armée"):
            unit_data = {
                "name": unit["name"],
                "cost": total_cost,
                "quality": unit["quality"],
                "defense": unit["defense"],
                "base_rules": base_rules,
                "options": options_selected,
                "current_weapon": current_weapon,
                "type": unit.get("type", "Infantry"),
                "combined": combined_unit
            }

            if mount_selected:
                unit_data["mount"] = mount_selected

            if combined_unit and "[10]" in unit_data["name"]:
                unit_data["name"] = unit_data["name"].replace("[10]", "[20]")

            st.session_state.army_list.append(unit_data)
            st.session_state.army_total_cost += total_cost
            st.rerun()

        # Validation et affichage de l'armée
        st.divider()
        st.subheader("Liste de l'armée")

        if not st.session_state.army_list:
            st.info("Ajoutez des unités pour commencer.")

        for i, u in enumerate(st.session_state.army_list):
            with st.container():
                st.markdown(f"### {u['name']} [{u['cost']} pts]")
                if u.get("combined"):
                    st.markdown("**Unité combinée** (x2 effectif)")

                col1, col2, col3 = st.columns(3)
                col1.metric("Qualité", f"{u['quality']}+")
                col2.metric("Défense", f"{u['defense']}+")
                col3.metric("Coriace", calculate_total_coriace(u))

                # Règles spéciales
                if u.get("base_rules"):
                    rules = [r for r in u['base_rules'] if not r.startswith("Coriace")]
                    if rules:
                        st.markdown("**Règles spéciales**")
                        st.caption(", ".join(rules))

                # Armes
                if 'current_weapon' in u:
                    weapon = u['current_weapon']
                    st.markdown("**Armes**")
                    st.table({
                        "Nom": [weapon.get('name', 'Arme de base')],
                        "ATK": [weapon.get('attacks', '?')],
                        "AP": [weapon.get('armor_piercing', '?')],
                        "Règles": [', '.join(weapon.get('special_rules', []))]
                    })

                # Monture
                if u.get("mount"):
                    mount = u['mount']
                    st.markdown("**Monture**")
                    st.caption(f"**{mount.get('name', '')}**")
                    if 'special_rules' in mount:
                        st.caption(", ".join(mount['special_rules']))

                # Améliorations
                if u.get("options"):
                    st.markdown("**Améliorations**")
                    for group_name, opts in u["options"].items():
                        if isinstance(opts, list):
                            for opt in opts:
                                st.caption(f"- {opt.get('name', '')}")
                        elif isinstance(opts, dict):
                            st.caption(f"- {opts.get('name', '')}")

                if st.button(f"🗑 Supprimer", key=f"del_{i}"):
                    st.session_state.army_total_cost -= u["cost"]
                    st.session_state.army_list.pop(i)
                    st.rerun()

        # Validation et boutons
        st.divider()
        if st.session_state.game in GAME_RULES:
            st.session_state.is_army_valid, st.session_state.validation_errors = validate_army(
                st.session_state.army_list,
                GAME_RULES[st.session_state.game],
                st.session_state.army_total_cost,
                st.session_state.points
            )
        else:
            st.session_state.is_army_valid = st.session_state.army_total_cost <= st.session_state.points
            st.session_state.validation_errors = []
            if st.session_state.army_total_cost > st.session_state.points:
                st.session_state.is_army_valid = False
                st.session_state.validation_errors.append(
                    f"Dépassement de {st.session_state.army_total_cost - st.session_state.points} pts"
                )

        progress = min(1.0, st.session_state.army_total_cost / st.session_state.points) if st.session_state.points else 0
        st.progress(progress)
        st.markdown(f"**{st.session_state.army_total_cost} / {st.session_state.points} pts**")

        if not st.session_state.is_army_valid:
            st.warning("Problèmes avec la liste:")
            for error in st.session_state.validation_errors:
                st.error(f"- {error}")

        # Boutons d'action
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("💾 Sauvegarder"):
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
                    save_army_list(army_data, st.session_state.current_player)
                    st.session_state.player_army_lists = load_army_lists(st.session_state.current_player)
                    st.success(f"Liste '{st.session_state.list_name}' sauvegardée!")

        with col2:
            if st.button("📄 Exporter"):
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
                    auto_export(army_data, st.session_state.list_name)

        with col3:
            if st.button("🧹 Réinitialiser"):
                st.session_state.army_list = []
                st.session_state.army_total_cost = 0
                st.rerun()

if __name__ == "__main__":
    main()
