import json
import streamlit as st
from pathlib import Path
from datetime import datetime
import streamlit.components.v1 as components
import hashlib
import re

# ======================================================
# CONFIGURATION POUR SIMON
# ======================================================
st.set_page_config(
    page_title="OPR Army Forge FR - Simon Joinville Fouquet",
    page_title="OPR Army Forge FR",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Chemins des fichiers
BASE_DIR = Path(__file__).resolve().parent
FACTIONS_DIR = BASE_DIR / "lists" / "data" / "factions"
FACTIONS_DIR.mkdir(parents=True, exist_ok=True)

# ======================================================
# FONCTIONS UTILITAIRES
# ======================================================
def format_special_rule(rule):
    """Formate les règles spéciales avec parenthèses"""
    if not isinstance(rule, str):
        return str(rule)
    if "(" in rule and ")" in rule:
        return rule
    match = re.search(r"(\D+)(\d+)", rule)
    if match:
        return f"{match.group(1)}({match.group(2)})"
    return rule

def extract_coriace_value(rule):
    """Extrait la valeur numérique de Coriace d'une règle"""
    if not isinstance(rule, str):
        return 0
    match = re.search(r"Coriace\s*\(?(\d+)\)?", rule)
    if match:
        return int(match.group(1))
    return 0

def get_coriace_from_rules(rules):
    """Calcule la Coriace depuis une liste de règles"""
    if not rules or not isinstance(rules, list):
        return 0
    total = 0
    for rule in rules:
        total += extract_coriace_value(rule)
    return total

def get_mount_details(mount):
    """Récupère les détails d'une monture"""
    if not mount:
        return None, 0

    mount_data = mount
    if 'mount' in mount:
        mount_data = mount['mount']

    # Récupérer les règles spéciales
    special_rules = []
    if 'special_rules' in mount_data and isinstance(mount_data['special_rules'], list):
        special_rules = mount_data['special_rules']

    # Calculer la coriace de la monture
    coriace = get_coriace_from_rules(special_rules)

    return special_rules, coriace

def format_weapon_details(weapon):
    """Formate les détails d'une arme pour l'affichage"""
    if not weapon:
        return {
            "name": "Arme non spécifiée",
            "attacks": "?",
            "ap": "?",
            "special": []
        }

    weapon_data = {
        "name": weapon.get('name', 'Arme non nommée'),
        "attacks": weapon.get('attacks', '?'),
        "ap": weapon.get('armor_piercing', '?'),
        "special": weapon.get('special_rules', [])
    }

    return weapon_data

def format_mount_details(mount):
    """Formate les détails d'une monture pour l'affichage"""
    if not mount:
        return "Aucune monture"

    mount_name = mount.get('name', 'Monture non nommée')

    # Vérifier si c'est un objet mount imbriqué
    mount_data = mount
    if 'mount' in mount:
        mount_data = mount['mount']

    details = mount_name

    # Ajouter les caractéristiques de la monture si disponibles
    if 'quality' in mount_data or 'defense' in mount_data:
        details += " ("
        if 'quality' in mount_data:
            details += f"Qua{mount_data['quality']}+"
        if 'defense' in mount_data:
            details += f" Déf{mount_data['defense']}+"
        details += ")"

    # Ajouter les règles spéciales
    if 'special_rules' in mount_data and mount_data['special_rules']:
        details += " | " + ", ".join(mount_data['special_rules'])

    # Ajouter les attaques de la monture si disponibles
    if 'weapons' in mount_data and mount_data['weapons']:
        for weapon in mount_data['weapons']:
            weapon_details = format_weapon_details(weapon)
            details += " | " + f"{weapon_details['name']} (A{weapon_details['attacks']}, PA({weapon_details['ap']})"
            if weapon_details['special']:
                details += ", " + ", ".join(weapon_details['special'])
            details += ")"

    return details

def format_unit_option(u):
    """Formate l'affichage des unités dans la liste déroulante"""
    name_part = f"{u['name']} [1]"

    # Calcul de la Coriace
    coriace = get_coriace_from_rules(u.get('special_rules', []))
    if 'mount' in u and u['mount']:
        _, mount_coriace = get_mount_details(u['mount'])
        coriace += mount_coriace

    # Ajout de la Qualité, Défense et Coriace
    qua_def_coriace = f"Qua {u['quality']}+ / Déf {u.get('defense', '?')}+"
    if coriace > 0:
        qua_def_coriace += f" / Coriace {coriace}"

    # Armes
    weapons_part = ""
    if 'weapons' in u and u['weapons']:
        weapons = []
        for weapon in u['weapons']:
            weapon_details = format_weapon_details(weapon)
            weapons.append(f"{weapon_details['name']} (A{weapon_details['attacks']}, PA({weapon_details['ap']}){', ' + ', '.join(weapon_details['special']) if weapon_details['special'] else ''})")
        weapons_part = " | ".join(weapons)

    # Règles spéciales
    rules_part = ""
    if 'special_rules' in u and u['special_rules']:
        rules_part = ", ".join(u['special_rules'])

    result = f"{name_part} - {qua_def_coriace}"

    if weapons_part:
        result += f" - {weapons_part}"

    if rules_part:
        result += f" - {rules_part}"

    result += f" {u['base_cost']}pts"
    return result

def find_option_by_name(options, name):
    """Trouve une option par son nom de manière sécurisée"""
    try:
        return next((o for o in options if o.get("name") == name), None)
    except Exception:
        return None

# ======================================================
# LOCAL STORAGE
# ======================================================
def ls_get(key):
    """Récupère une valeur du LocalStorage"""
    try:
        unique_key = f"{key}_{hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()[:8]}"
        components.html(
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
            height=0
        )
        return st.text_input("", key=unique_key, label_visibility="collapsed")
    except Exception as e:
        st.error(f"Erreur LocalStorage: {e}")
        return None

def ls_set(key, value):
    """Stocke une valeur dans le LocalStorage"""
    try:
        if not isinstance(value, str):
            value = json.dumps(value)
        escaped_value = value.replace("'", "\\'").replace('"', '\\"')
        components.html(
            f"""
            <script>
            localStorage.setItem("{key}", `{escaped_value}`);
            </script>
            """,
            height=0
        )
    except Exception as e:
        st.error(f"Erreur LocalStorage: {e}")

# ======================================================
# CHARGEMENT DES FACTIONS
# ======================================================
@st.cache_data
def load_factions():
    """Charge les factions depuis les fichiers JSON"""
    factions = {}
    games = set()

    if not FACTIONS_DIR.exists():
        st.error(f"Dossier {FACTIONS_DIR} introuvable!")
        return {}, []

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
            st.warning(f"Erreur chargement {fp.name}: {e}")

    return factions, sorted(games)

# ======================================================
# INITIALISATION
# ======================================================
factions_by_game, games = load_factions()

if "page" not in st.session_state:
    st.session_state.page = "setup"
    st.session_state.army_list = []
    st.session_state.army_cost = 0
    st.session_state.current_player = "Simon"

# ======================================================
# PAGE 1 – CONFIGURATION
# ======================================================
if st.session_state.page == "setup":
    st.title("OPR Army Forge FR")

    # Section pour charger depuis GitHub
    with st.expander("Charger une liste depuis GitHub"):
        github_repo = st.text_input("URL du dépôt GitHub", "https://github.com/SimonJoinvilleFouquet/opr-army-forge")
        github_file = st.text_input("Chemin du fichier", "listes/mes_listes.json")

        if st.button("Charger depuis GitHub"):
            st.warning("Fonctionnalité GitHub simulée. En environnement réel, cette fonction chargerait directement depuis GitHub.")
            st.info("Pour l'instant, utilisez l'import JSON classique ci-dessous.")

    if not games:
        st.error("Aucun jeu trouvé")
        st.stop()

    game = st.selectbox("Jeu", games)
    faction = st.selectbox("Faction", factions_by_game[game].keys())
    points = st.number_input("Points", 250, 5000, 1000, 250)
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
            st.error(f"Erreur d'import: {e}")

    if st.button("Créer une nouvelle liste"):
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

    # Initialisation
    base_cost = unit["base_cost"]
    weapon = unit.get("weapons", [{}])[0]
    selected_options = {}
    mount = None
    combined = False
    weapon_cost = 0
    mount_cost = 0
    upgrades_cost = 0

    # Unité combinée (pas pour les héros)
    if unit.get("type", "").lower() != "hero":
        combined = st.checkbox("Unité combinée", value=False)

    # Options de l'unité
    for group in unit.get("upgrade_groups", []):
        st.markdown(f"**{group['group']}**")

        if group["type"] == "weapon":
            # Formatage des options d'armes
            weapon_options = ["Arme de base"]
            for o in group["options"]:
                weapon_details = format_weapon_details(o["weapon"])
                cost_diff = o["cost"]
                weapon_options.append(f"{o['name']} (A{weapon_details['attacks']}, PA({weapon_details['ap']}){', ' + ', '.join(weapon_details['special']) if weapon_details['special'] else ''}) (+{cost_diff} pts)")

            selected_weapon = st.radio("Arme", weapon_options, key=f"{unit['name']}_weapon")
            if selected_weapon != "Arme de base":
                opt_name = selected_weapon.split(" (")[0]
                opt = next((o for o in group["options"] if o["name"] == opt_name), None)
                if opt:
                    weapon = opt["weapon"]
                    weapon_cost = opt["cost"]

        elif group["type"] == "mount":
            # NOUVELLE IMPLEMENTATION POUR LES MONTURES
            mount_labels = ["Aucune monture"]
            mount_map = {}

            for o in group["options"]:
                mount_details = format_mount_details(o)
                label = f"{mount_details} (+{o['cost']} pts)"
                mount_labels.append(label)
                mount_map[label] = o

            selected_mount = st.radio("Monture", mount_labels, key=f"{unit['name']}_mount")

            if selected_mount != "Aucune monture":
                opt = mount_map[selected_mount]
                mount = opt
                mount_cost = opt["cost"]

        else:  # Améliorations d'unité (checkbox multiples)
            if group["group"] == "Améliorations de rôle":
                option_names = ["Aucune"] + [
                    f"{o['name']} (+{o['cost']} pts)" for o in group["options"]
                ]
                selected = st.radio(group["group"], option_names, key=f"{unit['name']}_{group['group']}")
                if selected != "Aucune":
                    opt_name = selected.split(" (+")[0]
                    opt = next((o for o in group["options"] if o["name"] == opt_name), None)
                    if opt:
                        if group["group"] not in selected_options:
                            selected_options[group["group"]] = []
                        selected_options[group["group"]].append(opt)
                        upgrades_cost += opt["cost"]
            else:
                # Utilisation de checkbox pour les améliorations d'unité
                st.write("Sélectionnez les améliorations (plusieurs choix possibles):")
                for o in group["options"]:
                    if st.checkbox(f"{o['name']} (+{o['cost']} pts)", key=f"{unit['name']}_{group['group']}_{o['name']}"):
                        if group["group"] not in selected_options:
                            selected_options[group["group"]] = []
                        if not any(opt.get("name") == o["name"] for opt in selected_options.get(group["group"], [])):
                            selected_options[group["group"]].append(o)
                            upgrades_cost += o["cost"]

    # Calcul du coût CORRIGÉ pour tous les types d'unités
    cost = base_cost + weapon_cost + mount_cost + upgrades_cost

    st.markdown(f"**Coût total: {cost} pts**")

    if st.button("Ajouter à l'armée"):
        # Préparation des données de l'unité
        unit_weapon = format_weapon_details(weapon)

        unit_data = {
            "name": unit["name"],
            "cost": cost,
            "quality": unit["quality"],
            "defense": unit["defense"],
            "rules": [format_special_rule(r) for r in unit.get("special_rules", [])],
            "weapon": unit_weapon,  # On stocke les données formatées
            "options": selected_options,
            "mount": mount,
            "coriace": calculate_total_coriace({
                'special_rules': unit.get('special_rules', []),
                'mount': mount,
                'options': selected_options,
                'weapon': weapon,
                'type': unit.get('type', '')
            }),
            "combined": combined if unit.get("type", "").lower() != "hero" else False,
            "type": unit.get("type", "")
        }
        st.session_state.army_list.append(unit_data)
        st.session_state.army_cost += cost
        st.rerun()

    # Liste de l'armée
    st.divider()
    st.subheader("Liste de l'armée")

    if not st.session_state.army_list:
        st.info("Ajoutez des unités pour commencer")

    for i, u in enumerate(st.session_state.army_list):
        with st.container():
            # Affichage du nom et des stats avec Coriace intégrée
            qua_def_coriace = f"Qua {u['quality']}+ / Déf {u['defense']}+"
            if u.get("coriace"):
                qua_def_coriace += f" / Coriace {u['coriace']}"

            unit_header = f"### {u['name']} ({u['cost']} pts) | {qua_def_coriace}"
            st.markdown(unit_header)

            # Affichage des règles spéciales
            if u.get("rules"):
                rules_text = ", ".join(u["rules"])
                st.markdown(f"**Règles spéciales:** {rules_text}")

            # Affichage des armes avec leurs caractéristiques
            if 'weapon' in u and u['weapon']:
                weapon_info = u['weapon']  # On utilise directement les données formatées
                st.markdown(f"**Arme:** {weapon_info['name']} (A{weapon_info['attacks']}, PA({weapon_info['ap']}){', ' + ', '.join(weapon_info['special']) if weapon_info['special'] else ''})")

            # Affichage des améliorations
            if u.get("options"):
                for group_name, opts in u["options"].items():
                    if isinstance(opts, list) and opts:
                        st.markdown(f"**{group_name}:**")
                        for opt in opts:
                            st.markdown(f"• {opt.get('name', '')}")

            # Affichage de la monture avec ses détails
            if u.get("mount"):
                mount_details = format_mount_details(u["mount"])
                st.markdown(f"**Monture:** {mount_details}")

            if st.button(f"Supprimer {u['name']}", key=f"del_{i}"):
                st.session_state.army_cost -= u["cost"]
                st.session_state.army_list.pop(i)
                st.rerun()

    # Sauvegarde/Export
    st.divider()
    col1, col2, col3, col4, col5 = st.columns(5)

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
            if not isinstance(current_lists, list):
                current_lists = []
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

    with col3:
        # Export HTML standard
        html_content_standard = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Liste OPR - {army_data['name']}</title>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    margin: 20px;
                    color: #333;
                }}
                .army-title {{
                    text-align: center;
                    margin-bottom: 20px;
                    color: #2c3e50;
                }}
                .army-info {{
                    text-align: center;
                    margin-bottom: 30px;
                    color: #666;
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
                    border-bottom: 1px solid #eee;
                    padding-bottom: 10px;
                }}
                .unit-stats {{
                    display: flex;
                    margin-bottom: 15px;
                }}
                .stat-badge {{
                    background-color: #3498db;
                    color: white;
                    padding: 8px 12px;
                    border-radius: 4px;
                    margin-right: 10px;
                    font-weight: bold;
                    text-align: center;
                    min-width: 80px;
                }}
                .stat-value {{
                    font-size: 1.2em;
                }}
                .stat-label {{
                    font-size: 0.8em;
                    display: block;
                    margin-bottom: 3px;
                }}
                .section-title {{
                    font-weight: bold;
                    margin: 15px 0 10px 0;
                    color: #2c3e50;
                    border-bottom: 1px solid #eee;
                    padding-bottom: 5px;
                }}
                .weapon-table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-bottom: 15px;
                }}
                .weapon-table th {{
                    background-color: #f8f9fa;
                    text-align: left;
                    padding: 8px;
                    border-bottom: 1px solid #ddd;
                }}
                .weapon-table td {{
                    padding: 8px;
                    border-bottom: 1px solid #eee;
                }}
                .rules-list {{
                    margin: 10px 0;
                }}
                .special-rules {{
                    font-style: italic;
                    color: #555;
                    margin-bottom: 15px;
                }}
                .unit-cost {{
                    float: right;
                    background-color: #3498db;
                    color: white;
                    padding: 5px 10px;
                    border-radius: 4px;
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
            coriace = unit.get('coriace')
            qua_def_coriace = f"Qua {unit['quality']}+ / Déf {unit['defense']}+"
            if coriace:
                qua_def_coriace += f" / Coriace {coriace}"

            # Règles spéciales
            rules = unit.get('rules', [])
            special_rules = ", ".join(rules) if rules else "Aucune"

            # Armes
            weapon_info = unit.get('weapon', {})

            html_content_standard += f"""
            <div class="unit-container">
                <div class="unit-header">
                    {unit['name']}
                    <span class="unit-cost">{unit['cost']} pts</span>
                </div>

                <div class="unit-stats">
                    <div class="stat-badge">
                        <div class="stat-label">Qualité</div>
                        <div class="stat-value">{unit['quality']}+</div>
                    </div>
                    <div class="stat-badge">
                        <div class="stat-label">Défense</div>
                        <div class="stat-value">{unit['defense']}+</div>
                    </div>
            """
            if coriace:
                html_content_standard += f"""
                    <div class="stat-badge">
                        <div class="stat-label">Coriace</div>
                        <div class="stat-value">{coriace}</div>
                    </div>
                """

            html_content_standard += """
                </div>
            """

            # Règles spéciales
            if rules:
                html_content_standard += f'<div class="special-rules"><strong>Règles spéciales:</strong> {special_rules}</div>'

            # Armes
            if weapon_info:
                html_content_standard += """
                    <div class="section-title">Arme</div>
                    <table class="weapon-table">
                        <thead>
                            <tr>
                                <th>Nom</th>
                                <th>PORT</th>
                                <th>ATK</th>
                                <th>PA</th>
                                <th>SPE</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td>{weapon_info['name']}</td>
                                <td>-</td>
                                <td>{weapon_info['attacks']}</td>
                                <td>{weapon_info['ap']}</td>
                                <td>{', '.join(weapon_info['special']) if weapon_info['special'] else '-'}</td>
                            </tr>
                        </tbody>
                    </table>
                """

            # Améliorations
            if 'options' in unit and unit['options']:
                for group_name, opts in unit['options'].items():
                    if isinstance(opts, list) and opts:
                        html_content_standard += f'<div class="section-title">{group_name}:</div>'
                        for opt in opts:
                            html_content_standard += f'<div>• {opt.get("name", "")}</div>'

            # Monture
            if 'mount' in unit and unit['mount']:
                mount_details = format_mount_details(unit["mount"])
                html_content_standard += f'<div class="section-title">Monture</div><p>{mount_details}</p>'

            html_content_standard += "</div>"

        html_content_standard += "</body></html>"

        st.download_button(
            "Exporter en HTML Standard",
            html_content_standard,
            file_name=f"{st.session_state.list_name}.html",
            mime="text/html"
        )

    with col4:
        # EXPORT HTML AU FORMAT FICHE CORRIGÉ
        html_content_fiche = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Fiches OPR - {army_data['name']}</title>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background-color: #f5f5f5;
                    color: #333;
                }}
                .army-title {{
                    text-align: center;
                    color: #2c3e50;
                    margin-bottom: 20px;
                }}
                .army-info {{
                    text-align: center;
                    margin-bottom: 30px;
                    color: #666;
                }}
                .unit-card {{
                    background-color: white;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    margin-bottom: 20px;
                    overflow: hidden;
                    width: 100%;
                    page-break-inside: avoid;
                }}
                .unit-header {{
                    background-color: #2c3e50;
                    color: white;
                    padding: 15px;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }}
                .unit-name {{
                    font-size: 1.5em;
                    font-weight: bold;
                }}
                .unit-cost {{
                    background-color: #3498db;
                    padding: 5px 10px;
                    border-radius: 4px;
                    font-weight: bold;
                }}
                .unit-stats {{
                    display: flex;
                    padding: 15px;
                    background-color: #f8f9fa;
                    border-bottom: 1px solid #eee;
                }}
                .stat-badge {{
                    background-color: #3498db;
                    color: white;
                    padding: 8px 12px;
                    border-radius: 4px;
                    margin-right: 10px;
                    font-weight: bold;
                    text-align: center;
                    min-width: 80px;
                }}
                .stat-value {{
                    font-size: 1.2em;
                }}
                .stat-label {{
                    font-size: 0.8em;
                    display: block;
                    margin-bottom: 3px;
                }}
                .unit-details {{
                    padding: 15px;
                }}
                .section-title {{
                    font-weight: bold;
                    margin-bottom: 10px;
                    color: #2c3e50;
                    border-bottom: 1px solid #eee;
                    padding-bottom: 5px;
                }}
                .weapon-table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-bottom: 15px;
                }}
                .weapon-table th {{
                    background-color: #f8f9fa;
                    text-align: left;
                    padding: 8px;
                    border-bottom: 1px solid #ddd;
                }}
                .weapon-table td {{
                    padding: 8px;
                    border-bottom: 1px solid #eee;
                }}
                .rules-section {{
                    margin-bottom: 15px;
                }}
                .rules-title {{
                    font-weight: bold;
                    color: #2c3e50;
                    margin-bottom: 5px;
                }}
                .rules-content {{
                    font-style: italic;
                    color: #555;
                }}
                @media print {{
                    .unit-card {{
                        page-break-inside: avoid;
                        break-inside: avoid;
                    }}
                }}
            </style>
        </head>
        <body>
            <h1 class="army-title">OPR Army Forge - {army_data['name']}</h1>
            <div class="army-info">
                <strong>Jeu:</strong> {army_data['game']} |
                <strong>Faction:</strong> {army_data['faction']} |
                <strong>Points:</strong> {army_data['total_cost']}/{army_data['points']}
            </div>
        """

        for unit in army_data['army_list']:
            # Récupérer les données de l'unité
            unit_name = unit['name']
            unit_cost = unit['cost']
            quality = unit.get('quality', '?')
            defense = unit.get('defense', '?')
            coriace = unit.get('coriace', None)

            # Règles spéciales
            rules = unit.get('rules', [])
            special_rules = ", ".join(rules) if rules else "Aucune"

            # Armes
            weapon_info = unit.get('weapon', {})
            if not weapon_info or not isinstance(weapon_info, dict):
                weapon_info = {
                    "name": "Arme non spécifiée",
                    "attacks": "?",
                    "ap": "?",
                    "special": []
                }

            # Monture
            mount_details = ""
            if 'mount' in unit and unit['mount']:
                mount_details = format_mount_details(unit['mount'])

            # Améliorations
            upgrades = []
            if 'options' in unit and unit['options']:
                for group_name, opts in unit['options'].items():
                    if isinstance(opts, list):
                        for opt in opts:
                            upgrades.append(opt.get('name', ''))

            # Génération de la fiche unité
            html_content_fiche += f"""
            <div class="unit-card">
                <div class="unit-header">
                    <div class="unit-name">{unit_name}</div>
                    <div class="unit-cost">{unit_cost} pts</div>
                </div>

                <div class="unit-stats">
                    <div class="stat-badge">
                        <div class="stat-label">Qualité</div>
                        <div class="stat-value">{quality}+</div>
                    </div>
                    <div class="stat-badge">
                        <div class="stat-label">Défense</div>
                        <div class="stat-value">{defense}+</div>
                    </div>
            """
            if coriace:
                html_content_fiche += f"""
                    <div class="stat-badge">
                        <div class="stat-label">Coriace</div>
                        <div class="stat-value">{coriace}</div>
                    </div>
                """

            html_content_fiche += """
                </div>

                <div class="unit-details">
            """

            # Règles spéciales
            if rules:
                html_content_fiche += f"""
                    <div class="rules-section">
                        <div class="rules-title">Règles spéciales</div>
                        <div class="rules-content">{special_rules}</div>
                    </div>
                """

            # Armes
            html_content_fiche += """
                    <div class="section-title">Arme</div>
                    <table class="weapon-table">
                        <thead>
                            <tr>
                                <th>Nom</th>
                                <th>PORT</th>
                                <th>ATK</th>
                                <th>PA</th>
                                <th>SPE</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td>{weapon_info['name']}</td>
                                <td>-</td>
                                <td>{weapon_info['attacks']}</td>
                                <td>{weapon_info['ap']}</td>
                                <td>{', '.join(weapon_info['special']) if weapon_info['special'] else '-'}</td>
                            </tr>
                        </tbody>
                    </table>
            """

            # Améliorations
            if upgrades:
                html_content_fiche += """
                    <div class="section-title">Améliorations</div>
                    <table class="weapon-table">
                        <thead>
                            <tr>
                                <th>Nom</th>
                                <th>SPE</th>
                            </tr>
                        </thead>
                        <tbody>
                """
                for upgrade in upgrades:
                    html_content_fiche += f"""
                            <tr>
                                <td>{upgrade}</td>
                                <td>-</td>
                            </tr>
                    """
                html_content_fiche += """
                        </tbody>
                    </table>
                """

            # Monture
            if mount_details and mount_details != "Aucune monture":
                html_content_fiche += f"""
                    <div class="section-title">Monture</div>
                    <p>{mount_details}</p>
                """

            html_content_fiche += """
                </div>
            </div>
            """

        html_content_fiche += """
        </body>
        </html>
        """

        st.download_button(
            "Exporter en Fiches Unités",
            html_content_fiche,
            file_name=f"{st.session_state.list_name}_fiches.html",
            mime="text/html"
        )

    with col5:
        if st.button("Réinitialiser"):
            st.session_state.army_list = []
            st.session_state.army_cost = 0
            st.rerun()
