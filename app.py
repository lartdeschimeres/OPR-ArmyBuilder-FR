import json
import re
from pathlib import Path
from collections import defaultdict
import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime
import os

# Compteur global pour éviter les conflits de clés dans le LocalStorage
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

    # Utilise un input caché pour récupérer la valeur
    value = st.text_input("hidden_input", key=unique_key, label_visibility="collapsed")
    return value

def localstorage_set(key, value):
    """Stocke une valeur dans le LocalStorage via JavaScript."""
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

def export_data(player_name="default"):
    """Exporte les données vers un fichier JSON."""
    army_lists = json.loads(localstorage_get(f"army_lists_{player_name}") or "[]")
    if not army_lists:
        st.warning("Aucune donnée à exporter.")
        return

    data = {
        "player_name": player_name,
        "army_lists": army_lists,
        "date": datetime.now().isoformat()
    }

    filename = f"opr_army_builder_{player_name}_{datetime.now().strftime('%Y%m%d')}.json"
    json_str = json.dumps(data, indent=2, ensure_ascii=False)
    st.download_button(
        label="💾 Exporter mes données",
        data=json_str,
        file_name=filename,
        mime="application/json"
    )

def import_data():
    """Importe des données depuis un fichier JSON."""
    uploaded_file = st.file_uploader("📁 Importer un fichier de sauvegarde", type=["json"])
    if uploaded_file is not None:
        try:
            data = json.load(uploaded_file)
            player_name = data.get("player_name", "default")
            localstorage_set(f"army_lists_{player_name}", data["army_lists"])
            st.session_state.current_player = player_name
            st.session_state.player_army_lists = data["army_lists"]
            st.success(f"Données importées pour le profil '{player_name}' !")
            st.rerun()
        except Exception as e:
            st.error(f"Erreur lors de l'import: {str(e)}")

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
            .army-card {{
                border: 2px solid #4a89dc;
                border-radius: 15px;
                padding: 15px;
                margin-bottom: 20px;
                background: white;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }}
            .unit-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 10px;
            }}
            .unit-name {{
                font-size: 1.2em;
                font-weight: bold;
                color: #333;
                margin: 0;
            }}
            .unit-points {{
                color: #666;
                font-size: 0.9em;
            }}
            .badges-container {{
                display: flex;
                gap: 8px;
                margin-bottom: 15px;
                flex-wrap: wrap;
            }}
            .badge {{
                padding: 6px 12px;
                border-radius: 20px;
                font-size: 0.9em;
                font-weight: 500;
                color: white;
                text-align: center;
            }}
            .quality-badge {{
                background-color: #4a89dc;
            }}
            .defense-badge {{
                background-color: #4a89dc;
            }}
            .coriace-badge {{
                background-color: #4a89dc;
            }}
            .section {{
                margin-bottom: 12px;
            }}
            .section-title {{
                font-weight: bold;
                color: #4a89dc;
                margin-bottom: 5px;
                font-size: 0.95em;
            }}
            .section-content {{
                margin-left: 10px;
                font-size: 0.9em;
                color: #555;
            }}
            .combined-badge {{
                background-color: #28a745;
                color: white;
                padding: 4px 8px;
                border-radius: 12px;
                font-size: 0.8em;
                margin-left: 10px;
            }}
            @media print {{
                body {{
                    margin: 0;
                    padding: 20px;
                }}
                .army-card {{
                    border: none;
                    box-shadow: none;
                    margin-bottom: 10px;
                    page-break-inside: avoid;
                }}
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
        <div class="army-card">
            <div class="unit-header">
                <h3 class="unit-name">{u['name']}</h3>
                <span class="unit-points">{u['cost']} pts</span>
            </div>
            <div class="badges-container">
                <span class="badge quality-badge">Qualité {u['quality']}+</span>
                <span class="badge defense-badge">Défense {u['defense']}+</span>
        """

        if coriace_value > 0:
            html_content += f'<span class="badge coriace-badge">Coriace {coriace_value}</span>'

        if u.get("combined", False):
            html_content += '<span class="combined-badge">Unité combinée</span>'

        html_content += """
            </div>
        """

        if u.get("base_rules"):
            rules = [r for r in u['base_rules'] if not r.startswith("Coriace")]
            if rules:
                html_content += f"""
                <div class="section">
                    <div class="section-title">Règles spéciales</div>
                    <div class="section-content">{', '.join(rules)}</div>
                </div>
                """

        if 'current_weapon' in u:
            weapon = u['current_weapon']
            weapon_name = weapon.get('name', 'Arme de base')
            attacks = weapon.get('attacks', '?')
            armor_piercing = weapon.get('armor_piercing', '?')
            weapon_line = f"{weapon_name} | A{attacks} | PA({armor_piercing})"

            if 'special_rules' in weapon and weapon['special_rules']:
                weapon_line += f", {', '.join(weapon['special_rules'])}"

            html_content += f"""
            <div class="section">
                <div class="section-title">Arme équipée</div>
                <div class="section-content">{weapon_line}</div>
            </div>
            """

        if u.get("mount"):
            mount = u['mount']
            mount_rules = mount.get('special_rules', [])
            html_content += f"""
            <div class="section">
                <div class="section-title">Monture</div>
                <div class="section-content">
                    <strong>{mount.get('name', '')}</strong>
            """
            if mount_rules:
                html_content += f"<br>{', '.join(mount_rules)}"
            html_content += """
                </div>
            </div>
            """

        html_content += "</div>"

    html_content += """
    </body>
    </html>
    """
    return html_content

def repair_army_list(army_list):
    """Répare une liste d'armée sauvegardée si elle a des problèmes de structure."""
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
    """Calcule la valeur totale de Coriace pour une unité (inclut TOUTES les sources)."""
    total = 0

    # 1. Règles de base de l'unité
    if "base_rules" in unit_data and isinstance(unit_data["base_rules"], list):
        total += extract_coriace(unit_data["base_rules"])

    # 2. Règles spéciales des options
    if "options" in unit_data and isinstance(unit_data["options"], dict):
        for option_group in unit_data["options"].values():
            if isinstance(option_group, list):
                for option in option_group:
                    if isinstance(option, dict) and "special_rules" in option:
                        total += extract_coriace(option["special_rules"])
            elif isinstance(option_group, dict) and "special_rules" in option_group:
                total += extract_coriace(option_group["special_rules"])

    # 3. Règles spéciales de la monture
    if "mount" in unit_data and isinstance(unit_data["mount"], dict):
        if "special_rules" in unit_data["mount"]:
            total += extract_coriace(unit_data["mount"]["special_rules"])

    # 4. Règles spéciales des armes
    if "weapons" in unit_data and isinstance(unit_data["weapons"], list):
        for weapon in unit_data["weapons"]:
            if isinstance(weapon, dict) and "special_rules" in weapon:
                total += extract_coriace(weapon["special_rules"])

    # 5. Vérification spécifique pour les héros
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

def auto_export(army_list_data, list_name):
    """Génère et télécharge automatiquement les fichiers HTML et JSON."""
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

    # Créer un conteneur pour les boutons de téléchargement
    download_container = st.container()
    with download_container:
        col1, col2 = st.columns(2)
        with col1:
            with open(html_filename, "r", encoding="utf-8") as f:
                st.download_button(
                    label="📄 Télécharger le HTML",
                    data=f,
                    file_name=html_filename,
                    mime="text/html"
                )
        with col2:
            st.download_button(
                label="📁 Télécharger le JSON",
                data=json_str,
                file_name=json_filename,
                mime="application/json"
            )

    # Supprimer les fichiers temporaires après téléchargement
    try:
        os.remove(html_filename)
    except:
        pass

def main():
    # Initialisation de la session
    if "page" not in st.session_state:
        st.session_state.page = "login"

    # Configuration de la page
    st.set_page_config(page_title="OPR Army Builder FR", layout="centered")

    # Définir les chemins locaux (pour les factions)
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

            # Vérification du dossier
            if not FACTIONS_DIR.exists():
                st.error(f"Le dossier {FACTIONS_DIR} n'existe pas!")
                FACTIONS_DIR.mkdir(parents=True, exist_ok=True)
                return {}, []

            # Charger les factions depuis les fichiers
            faction_files = list(FACTIONS_DIR.glob("*.json"))
            if not faction_files:
                st.warning(f"Aucun fichier JSON trouvé dans {FACTIONS_DIR}")
                return {}, []

            for fp in faction_files:
                try:
                    with open(fp, encoding="utf-8") as f:
                        data = json.load(f)

                        # Vérification des champs obligatoires
                        if "game" not in data or "faction" not in data:
                            st.warning(f"Fichier {fp.name} invalide: champs 'game' ou 'faction' manquants")
                            continue

                        game = data["game"]
                        faction_name = data["faction"]

                        if game not in factions:
                            factions[game] = {}
                        factions[game][faction_name] = data
                        games.add(game)

                except json.JSONDecodeError:
                    st.warning(f"Fichier JSON invalide: {fp.name}")
                except Exception as e:
                    st.warning(f"Erreur avec {fp.name}: {str(e)}")

            return factions, sorted(games)
        except Exception as e:
            st.error(f"Erreur critique lors du chargement: {str(e)}")
            return {}, []

    # Charger les factions au démarrage
    if not st.session_state["factions"] or not st.session_state["games"]:
        st.session_state["factions"], st.session_state["games"] = load_factions()

    # PAGE 1 — Accueil (sans login, avec pseudo optionnel)
    if st.session_state.page == "login":
        st.title("OPR Army Builder 🇫🇷")
        st.subheader("Bienvenue !")

        # Champ optionnel pour un pseudo
        player_name = st.text_input("Pseudo (optionnel)", value=st.session_state.current_player)

        if st.button("Commencer"):
            st.session_state.current_player = player_name
            st.session_state.player_army_lists = load_army_lists(player_name)
            st.session_state.page = "setup"
            st.rerun()

    # PAGE 2 — Configuration de la liste
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
            # Bouton pour exporter toutes les listes en JSON
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
                            "source": "OPR Army Builder",
                            "total_lists": len(army_lists),
                            "total_coriace": sum(calculate_total_coriace(u) for army in army_lists for u in army["army_list"])
                        }
                    }
                    json_filename = f"OPR_All_Army_Lists_{st.session_state.current_player}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                    json_str = json.dumps(data, indent=2, ensure_ascii=False)
                    st.download_button(
                        label="Télécharger le fichier JSON",
                        data=json_str,
                        file_name=json_filename,
                        mime="application/json"
                    )

        with col2:
            # Bouton pour importer un fichier JSON
            uploaded_file = st.file_uploader("📥 Importer un fichier JSON", type=["json"], key="json_importer")
            if uploaded_file is not None:
                try:
                    imported_data = json.load(uploaded_file)
                    if "army_lists" in imported_data and "player_name" in imported_data:
                        player_name = imported_data["player_name"]
                        localstorage_set(f"army_lists_{player_name}", imported_data["army_lists"])
                        st.session_state.current_player = player_name
                        st.session_state.player_army_lists = imported_data["army_lists"]
                        st.success(f"Données importées pour le profil '{player_name}' !")
                        st.rerun()
                    else:
                        st.error("Fichier JSON invalide: format incorrect")
                except Exception as e:
                    st.error(f"Erreur lors de l'import: {str(e)}")

        st.info("""
        💡 **Sauvegarde et synchronisation** :
        Vos listes sont sauvegardées **localement dans votre navigateur**.
        Pour les retrouver sur un autre appareil :
        1. Exportez vos données (bouton ci-dessus).
        2. Transférez le fichier (e-mail, cloud, clé USB).
        3. Importez-le sur l'autre appareil.
        """)

        st.subheader("Mes listes d'armées sauvegardées")

        if st.session_state.player_army_lists:
            for i, army_list in enumerate(st.session_state.player_army_lists):
                col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                with col1:
                    with st.expander(f"{army_list['name']} - {army_list['game']} - {army_list['total_cost']}/{army_list['points']} pts"):
                        st.write(f"Créée le: {army_list['date'][:10]}")
                        if st.button(f"Charger cette liste", key=f"load_{i}"):
                            try:
                                st.session_state.game = army_list['game']
                                st.session_state.faction = army_list['faction']
                                st.session_state.points = army_list['points']
                                st.session_state.list_name = army_list['name']
                                st.session_state.army_total_cost = army_list['total_cost']
                                st.session_state.army_list = repair_army_list(army_list['army_list'])
                                st.session_state.page = "army"
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erreur lors du chargement: {str(e)}")

                with col2:
                    if st.button(f"📄 Exporter", key=f"export_{i}"):
                        army_list_data = {
                            "name": army_list['name'],
                            "game": army_list['game'],
                            "faction": army_list['faction'],
                            "points": army_list['points'],
                            "army_list": army_list['army_list'],
                            "total_cost": army_list['total_cost'],
                            "date": army_list['date']
                        }
                        auto_export(army_list_data, army_list['name'])

                with col3:
                    if st.button(f"❌ Supprimer", key=f"delete_{i}"):
                        if delete_army_list(st.session_state.current_player, i):
                            st.session_state.player_army_lists = load_army_lists(st.session_state.current_player)
                            st.success(f"Liste supprimée avec succès!")
                            st.rerun()
                        else:
                            st.error("Erreur lors de la suppression de la liste")
        else:
            st.info("Vous n'avez pas encore sauvegardé de listes d'armées")

        st.divider()
        st.subheader("Créer une nouvelle liste")

        if not st.session_state["games"]:
            st.error("Aucun jeu disponible. Vérifiez que vos fichiers JSON sont dans le bon dossier.")
        else:
            st.session_state.game = st.selectbox(
                "Jeu",
                st.session_state["games"],
                index=0 if st.session_state["games"] else None
            )

            if st.session_state.game:
                available_factions = list(st.session_state["factions"][st.session_state.game].keys())
                if not available_factions:
                    st.warning(f"Aucune faction disponible pour {st.session_state.game}")
                else:
                    st.session_state.faction = st.selectbox(
                        "Faction",
                        available_factions,
                        index=0 if available_factions else None
                    )

                    st.session_state.points = st.number_input(
                        "Format de la partie (points)",
                        min_value=250,
                        step=250,
                        value=1000
                    )

                    st.session_state.list_name = st.text_input(
                        "Nom de la liste",
                        value="Ma liste d'armée"
                    )

                    if st.button("➡️ Ma liste"):
                        if st.session_state.game and st.session_state.faction:
                            faction_data = st.session_state["factions"][st.session_state.game][st.session_state.faction]
                            st.session_state.units = faction_data["units"]
                            st.session_state.page = "army"
                            st.rerun()
                        else:
                            st.error("Veuillez sélectionner un jeu et une faction")

    # PAGE 3 — Composition de l'armée
    elif st.session_state.page == "army":
        st.title(st.session_state.list_name)
        st.caption(f"{st.session_state.game} — {st.session_state.faction} — {st.session_state.army_total_cost}/{st.session_state.points} pts")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("⬅️ Retour configuration"):
                st.session_state.page = "setup"
                st.rerun()
        with col2:
            if st.button("🚪 Quitter"):
                st.session_state.page = "login"
                st.rerun()

        units = st.session_state.units

        # Section pour ajouter une unité
        st.divider()
        st.subheader("Ajouter une unité")

        unit = st.selectbox(
            "Unité",
            units,
            format_func=lambda u: f"{u['name']} ({u['base_cost']} pts)",
        )

        # Option pour unité combinée (uniquement pour les unités non-héros)
        combined_unit = False
        if unit.get("type", "").lower() != "hero":
            combined_unit = st.checkbox("Unité combinée (x2 effectif, coût x2)", value=False)

        total_cost = unit["base_cost"]
        if combined_unit:
            total_cost = unit["base_cost"] * 2

        base_rules = list(unit.get("special_rules", []))
        options_selected = {}
        current_weapon = None
        mount_selected = None
        weapon_replaced = False
        weapon_cost_multiplier = 2 if combined_unit else 1

        # Trouver l'arme de base par défaut
        default_weapon = unit.get("weapons", [{"name": "Arme non définie", "attacks": "?", "armor_piercing": "?"}])[0]
        current_weapon = default_weapon.copy()

        # Options standards
        for group in unit.get("upgrade_groups", []):
            group_name = group["group"]

            st.write(f"### {group_name}")
            if group.get("description"):
                st.caption(group.get("description", ""))

            # Cas spécial pour les améliorations de rôle (choix unique)
            if "rôle" in group_name.lower() or "role" in group_name.lower():
                choice = st.radio(
                    group_name,
                    ["— Aucun —"] + [f"{o['name']} (+{o['cost']} pts)" for o in group["options"]],
                    key=f"{unit['name']}_{group['group']}"
                )

                if choice != "— Aucun —":
                    opt_name = choice.split(" (+")[0]
                    opt = next(o for o in group["options"] if o["name"] == opt_name)
                    cost = opt.get("cost", 0) * weapon_cost_multiplier
                    total_cost += cost
                    options_selected[group["group"]] = opt

            # Remplacement d'arme (choix unique avec radio buttons)
            elif group.get("type") == "weapon":
                weapon_options = ["— Garder l'arme de base —"]
                for opt in group["options"]:
                    weapon_name = opt["name"]
                    weapon_cost = opt.get("cost", 0) * weapon_cost_multiplier
                    weapon_details = []

                    if "weapon" in opt:
                        weapon = opt["weapon"]
                        weapon_details.append(f"A{weapon.get('attacks', '?')}")
                        weapon_details.append(f"PA({weapon.get('armor_piercing', '?')})")
                        if "special_rules" in weapon and weapon["special_rules"]:
                            weapon_details.extend(weapon["special_rules"])

                    details_str = f" ({', '.join(weapon_details)})" if weapon_details else ""
                    weapon_options.append(f"{weapon_name} (+{weapon_cost} pts){details_str}")

                choice = st.radio(
                    group["group"],
                    weapon_options,
                    key=f"{unit['name']}_{group['group']}"
                )

                if choice != "— Garder l'arme de base —":
                    opt_name = choice.split(" (+")[0]
                    opt = next(o for o in group["options"] if o["name"] == opt_name)
                    cost = opt.get("cost", 0) * weapon_cost_multiplier
                    total_cost += cost
                    options_selected[group["group"]] = opt
                    current_weapon = opt["weapon"].copy()
                    current_weapon["name"] = opt["name"]
                    weapon_replaced = True

            # Montures (choix unique avec radio buttons)
            elif group.get("type") == "mount":
                mount_options = ["— Aucune monture —"]
                for opt in group["options"]:
                    mount_name = opt["name"]
                    mount_cost = opt.get("cost", 0)
                    mount_details = []

                    if "mount" in opt and "special_rules" in opt["mount"]:
                        mount_details = opt["mount"]["special_rules"]

                    details_str = f" ({', '.join(mount_details)})" if mount_details else ""
                    mount_options.append(f"{mount_name} (+{mount_cost} pts){details_str}")

                choice = st.radio(
                    group["group"],
                    mount_options,
                    key=f"{unit['name']}_{group['group']}"
                )

                if choice != "— Aucune monture —":
                    opt_name = choice.split(" (+")[0]
                    opt = next(o for o in group["options"] if o["name"] == opt_name)
                    total_cost += opt.get("cost", 0)
                    options_selected[group["group"]] = opt
                    mount_selected = opt.get("mount")

            # Options multiples (checkboxes)
            elif group.get("type") == "multiple":
                selected_options = []
                for opt in group["options"]:
                    display_cost = opt["cost"] * weapon_cost_multiplier if combined_unit else opt["cost"]
                    if st.checkbox(f"{opt['name']} (+{display_cost} pts)", key=f"{unit['name']}_{group['group']}_{opt['name']}"):
                        selected_options.append(opt)
                        total_cost += opt["cost"] * weapon_cost_multiplier

                if selected_options:
                    options_selected[group["group"]] = selected_options

        # Calcul de la valeur de Coriace
        coriace_value = calculate_total_coriace({
            "base_rules": base_rules,
            "options": options_selected,
            "mount": mount_selected,
            "weapons": [current_weapon]
        })

        st.markdown(f"### 💰 Coût : **{total_cost} pts**")
        if coriace_value > 0:
            st.markdown(f"**Coriace totale : {coriace_value}**")

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
                "combined": combined_unit,
                "weapon_replaced": weapon_replaced,
                "weapon_info": {
                    "is_replaced": weapon_replaced,
                    "original_name": default_weapon.get("name", ""),
                    "current_name": current_weapon.get("name", "")
                }
            }

            if mount_selected:
                unit_data["mount"] = mount_selected

            if combined_unit and "[10]" in unit_data["name"]:
                unit_data["name"] = unit_data["name"].replace("[10]", "[20]")

            st.session_state.army_list.append(unit_data)
            st.session_state.army_total_cost += total_cost
            st.rerun()

        # Validation de la liste d'armée
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

        # Barre de progression et boutons
        st.divider()
        progress = min(1.0, st.session_state.army_total_cost / st.session_state.points) if st.session_state.points else 0
        st.progress(progress)
        st.markdown(f"**{st.session_state.army_total_cost} / {st.session_state.points} pts**")

        # Avertissements et erreurs
        if st.session_state.army_total_cost > st.session_state.points:
            excess = st.session_state.army_total_cost - st.session_state.points
            st.warning(f"⚠️ Votre armée dépasse de {excess} pts la limite de {st.session_state.points} pts")

        if not st.session_state.is_army_valid:
            st.warning("⚠️ La liste d'armée n'est pas valide :")
            for error in st.session_state.validation_errors:
                st.error(f"- {error}")

        # Liste de l'armée
        st.divider()
        st.subheader("Liste de l'armée")

        if not st.session_state.army_list:
            st.info("Votre armée est vide. Ajoutez des unités pour commencer.")

        for i, u in enumerate(st.session_state.army_list):
            coriace_value = calculate_total_coriace(u)

            with st.container(border=True):
                st.subheader(u["name"])

                q, d, c = st.columns(3)
                q.metric("Qualité", f"{u['quality']}+")
                d.metric("Défense", f"{u['defense']}+")
                c.metric("Coriace totale", coriace_value)

                if u.get("base_rules"):
                    rules = [r for r in u['base_rules'] if not r.startswith("Coriace")]
                    if rules:
                        st.markdown("**Règles spéciales**")
                        st.caption(", ".join(rules))

                if 'current_weapon' in u:
                    weapon = u['current_weapon']
                    st.markdown("**Arme équipée**")
                    st.caption(f"{weapon.get('name', 'Arme de base')} | A{weapon.get('attacks', '?')} | PA({weapon.get('armor_piercing', '?')})")

                if u.get("options"):
                    st.markdown("**Options sélectionnées**")
                    options_names = []
                    for opt_group in u["options"].values():
                        if isinstance(opt_group, list):
                            for opt in opt_group:
                                if isinstance(opt, dict):
                                    options_names.append(opt.get("name", ""))
                        elif isinstance(opt_group, dict):
                            options_names.append(opt_group.get("name", ""))
                    if options_names:
                        st.caption(", ".join(options_names))

                if u.get("mount"):
                    mount = u['mount']
                    st.markdown("**Monture**")
                    st.caption(f"{mount.get('name', '')} – {', '.join(mount.get('special_rules', []))}")

                st.metric("Coût", u["cost"])
                if st.button(f"🗑 Supprimer {u['name']}", key=f"del_{i}"):
                    st.session_state.army_total_cost -= u["cost"]
                    st.session_state.army_list.pop(i)
                    st.rerun()

        # Résumé de l'armée
        if st.session_state.army_list:
            st.divider()
            st.subheader("Résumé de l'armée")

            total_points = sum(u["cost"] for u in st.session_state.army_list)
            total_coriace = sum(calculate_total_coriace(u) for u in st.session_state.army_list)

            st.metric("Total des points", f"{total_points}/{st.session_state.points}")
            st.metric("Coriace totale de l'armée", total_coriace)

            if total_points > st.session_state.points:
                st.warning(f"⚠️ Votre armée dépasse de {total_points - st.session_state.points} points !")

        # Boutons de sauvegarde/export
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("💾 Sauvegarder la liste"):
                if not st.session_state.list_name:
                    st.warning("Veuillez donner un nom à votre liste avant de sauvegarder")
                else:
                    army_list_data = {
                        "name": st.session_state.list_name,
                        "game": st.session_state.game,
                        "faction": st.session_state.faction,
                        "points": st.session_state.points,
                        "army_list": st.session_state.army_list,
                        "total_cost": st.session_state.army_total_cost,
                        "date": datetime.now().isoformat()
                    }
                    save_army_list(army_list_data, st.session_state.current_player)
                    st.session_state.player_army_lists = load_army_lists(st.session_state.current_player)
                    st.success(f"Liste '{st.session_state.list_name}' sauvegardée avec succès!")

        with col2:
            if st.button("📄 Exporter en HTML/JSON"):
                if not st.session_state.list_name:
                    st.warning("Veuillez donner un nom à votre liste avant d'exporter")
                else:
                    army_list_data = {
                        "name": st.session_state.list_name,
                        "game": st.session_state.game,
                        "faction": st.session_state.faction,
                        "points": st.session_state.points,
                        "army_list": st.session_state.army_list,
                        "total_cost": st.session_state.army_total_cost,
                        "date": datetime.now().isoformat()
                    }
                    auto_export(army_list_data, st.session_state.list_name)

        with col3:
            if st.button("🧹 Réinitialiser la liste"):
                st.session_state.army_list = []
                st.session_state.army_total_cost = 0
                st.rerun()

if __name__ == "__main__":
    main()
