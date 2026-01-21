import json
import streamlit as st
from pathlib import Path
from datetime import datetime
import hashlib
import re
from weasyprint import HTML
import base64
import tempfile
import os

# ======================================================
# CONFIGURATION
# ======================================================
st.set_page_config(
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
    """Formate les règles spéciales"""
    if not isinstance(rule, str):
        return str(rule)
    if "(" in rule and ")" in rule:
        return rule
    match = re.search(r"(\D+)(\d+)", rule)
    if match:
        return f"{match.group(1)}({match.group(2)})"
    return rule

def extract_coriace_value(rule):
    """Extrait la valeur de Coriace"""
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

def format_weapon_details(weapon):
    """Formate les détails d'une arme"""
    if not weapon:
        return {
            "name": "Arme non spécifiée",
            "attacks": "?",
            "ap": "?",
            "special": []
        }
    return {
        "name": weapon.get('name', 'Arme non nommée'),
        "attacks": weapon.get('attacks', '?'),
        "ap": weapon.get('armor_piercing', '?'),
        "special": weapon.get('special_rules', [])
    }

def format_unit_option(u):
    """Formate l'affichage des unités"""
    name_part = f"{u['name']} [1]"
    qua_def = f"Qua {u['quality']}+ / Déf {u.get('defense', '?')}+"
    result = f"{name_part} - {qua_def} - {u['base_cost']}pts"
    return result

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
                    "name": "Guerrier",
                    "base_cost": 60,
                    "quality": 3,
                    "defense": 3,
                    "type": "infantry",
                    "special_rules": [],
                    "weapons": [{
                        "name": "Épée",
                        "attacks": 1,
                        "armor_piercing": 0,
                        "special_rules": []
                    }]
                }
            ]
        }
        with open(FACTIONS_DIR / "default.json", "w", encoding="utf-8") as f:
            json.dump(default_faction, f, indent=2)

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

    return factions, sorted(games) if games else ["Age of Fantasy"]

def generate_pdf(html_content, filename):
    """Génère un PDF à partir de contenu HTML"""
    try:
        # Créer un fichier temporaire HTML
        with tempfile.NamedTemporaryFile(delete=False, suffix='.html', mode='w', encoding='utf-8') as temp_html:
            temp_html.write(html_content)
            temp_html_path = temp_html.name

        # Générer le PDF
        HTML(temp_html_path).write_pdf(filename)

        # Lire le fichier PDF généré
        with open(filename, "rb") as f:
            pdf_bytes = f.read()

        # Supprimer les fichiers temporaires
        os.unlink(temp_html_path)
        os.unlink(filename)

        return pdf_bytes

    except Exception as e:
        st.error(f"Erreur lors de la génération du PDF: {e}")
        return None

# ======================================================
# INITIALISATION
# ======================================================
factions_by_game, games = load_factions()

if "page" not in st.session_state:
    st.session_state.page = "setup"
    st.session_state.army_list = []
    st.session_state.army_cost = 0

# ======================================================
# PAGE 1 – CONFIGURATION
# ======================================================
if st.session_state.page == "setup":
    st.title("OPR Army Forge FR")

    if not games:
        st.error("Aucun jeu trouvé")
        st.stop()

    game = st.selectbox("Jeu", games)
    faction = st.selectbox("Faction", factions_by_game[game].keys())
    points = st.number_input("Points", 250, 5000, 1000, 250)
    list_name = st.text_input("Nom de la liste", f"Liste_{datetime.now().strftime('%Y%m%d')}")

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
    weapon_data = format_weapon_details(weapon)

    st.markdown(f"**Coût total: {base_cost} pts**")

    if st.button("Ajouter à l'armée"):
        unit_data = {
            "name": unit["name"],
            "cost": base_cost,
            "quality": unit["quality"],
            "defense": unit["defense"],
            "rules": unit.get("special_rules", []),
            "weapon": weapon_data,
            "coriace": 0,
            "type": unit.get("type", "")
        }
        st.session_state.army_list.append(unit_data)
        st.session_state.army_cost += base_cost
        st.rerun()

    # Liste de l'armée
    st.divider()
    st.subheader("Liste de l'armée")

    if not st.session_state.army_list:
        st.info("Ajoutez des unités pour commencer")

    for i, u in enumerate(st.session_state.army_list):
        with st.container():
            unit_header = f"### {u['name']} ({u['cost']} pts) | Qua {u['quality']}+ / Déf {u['defense']}+"
            st.markdown(unit_header)

            if u.get("rules"):
                rules_text = ", ".join(u["rules"])
                st.markdown(f"**Règles spéciales:** {rules_text}")

            if 'weapon' in u:
                st.markdown(f"**Arme:** {u['weapon']['name']} (A{u['weapon']['attacks']}, PA({u['weapon']['ap']}){', ' + ', '.join(u['weapon']['special']) if u['weapon']['special'] else ''})")

            if st.button(f"Supprimer {u['name']}", key=f"del_{i}"):
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
        st.download_button(
            "Exporter en JSON",
            json.dumps(army_data, indent=2, ensure_ascii=False),
            file_name=f"{st.session_state.list_name}.json",
            mime="application/json"
        )

    with col2:
        # Génération du HTML pour export
        html_content = f"""
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
            # Règles spéciales
            rules = unit.get('rules', [])
            special_rules = ", ".join(rules) if rules else "Aucune"

            # Armes
            weapon_info = unit.get('weapon', {})
            if not isinstance(weapon_info, dict):
                weapon_info = {
                    "name": "Arme non spécifiée",
                    "attacks": "?",
                    "ap": "?",
                    "special": []
                }

            html_content += f"""
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
                </div>
            """

            # Règles spéciales
            if rules:
                html_content += f'<div class="special-rules"><strong>Règles spéciales:</strong> {special_rules}</div>'

            # Armes
            html_content += """
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

            html_content += "</div>"

        html_content += "</body></html>"

        # Bouton pour exporter en PDF
        if st.button("Exporter en PDF"):
            with st.spinner("Génération du PDF en cours..."):
                # Créer un fichier temporaire pour le PDF
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                    pdf_bytes = generate_pdf(html_content, tmp.name)
                    if pdf_bytes:
                        st.success("PDF généré avec succès!")
                        st.download_button(
                            label="Télécharger le PDF",
                            data=pdf_bytes,
                            file_name=f"{st.session_state.list_name}.pdf",
                            mime="application/pdf"
                        )
                    else:
                        st.error("Échec de la génération du PDF")

    with col3:
        if st.button("Réinitialiser"):
            st.session_state.army_list = []
            st.session_state.army_cost = 0
            st.rerun()
