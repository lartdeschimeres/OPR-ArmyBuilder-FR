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
    page_title="OPR Army Builder FR - Simon Joinville Fouquet",
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

def get_mount_coriace(mount):
    """Calcule spécifiquement la Coriace de la monture"""
    if not mount:
        return 0

    if 'special_rules' in mount and isinstance(mount['special_rules'], list):
        return get_coriace_from_rules(mount['special_rules'])

    elif 'mount' in mount and isinstance(mount['mount'], dict):
        mount_data = mount['mount']
        if 'special_rules' in mount_data and isinstance(mount_data['special_rules'], list):
            return get_coriace_from_rules(mount_data['special_rules'])

    return 0

def calculate_total_coriace(unit_data, combined=False):
    """Calcule la Coriace TOTALE d'une unité"""
    total = 0

    if 'special_rules' in unit_data:
        total += get_coriace_from_rules(unit_data['special_rules'])

    if 'mount' in unit_data:
        total += get_mount_coriace(unit_data['mount'])

    if 'options' in unit_data:
        for opts in unit_data['options'].values():
            if isinstance(opts, list):
                for opt in opts:
                    if 'special_rules' in opt:
                        total += get_coriace_from_rules(opt['special_rules'])
            elif isinstance(opts, dict) and 'special_rules' in opts:
                total += get_coriace_from_rules(opts['special_rules'])

    if 'weapon' in unit_data and 'special_rules' in unit_data['weapon']:
        total += get_coriace_from_rules(unit_data['weapon']['special_rules'])

    if combined and unit_data.get('type', '').lower() != 'hero':
        base_coriace = get_coriace_from_rules(unit_data.get('special_rules', []))
        total += base_coriace

    return total if total > 0 else None

def format_weapon_details(weapon):
    """Formate les détails d'une arme pour l'affichage"""
    if not weapon:
        return "Arme non spécifiée"

    attacks = weapon.get('attacks', '?')
    armor_piercing = weapon.get('armor_piercing', '?')
    special_rules = weapon.get('special_rules', [])

    details = f"A{attacks}, AP({armor_piercing})"

    if special_rules:
        details += ", " + ", ".join(special_rules)

    return details

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

    return details

def format_unit_option(u):
    """Formate l'affichage des unités dans la liste déroulante"""
    # Nom [1]
    name_part = f"{u['name']} [1]"

    # QuaX+ DefY+
    qua_def = f"Qua {u['quality']}+ Def {u['defense']}+"

    # Liste des armes
    weapons_part = ""
    if 'weapons' in u and u['weapons']:
        weapons = []
        for weapon in u['weapons']:
            weapon_name = weapon.get('name', '')
            weapon_details = format_weapon_details(weapon)
            weapons.append(f"{weapon_name} ({weapon_details})")
        weapons_part = " | ".join(weapons)

    # Règles spéciales
    rules_part = ""
    if 'special_rules' in u and u['special_rules']:
        rules_part = ", ".join(u['special_rules'])

    # Construction du format final
    result = f"{name_part} - {qua_def}"

    if weapons_part:
        result += f" - {weapons_part}"

    if rules_part:
        result += f" - {rules_part}"

    # Ajout du coût à droite
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
    st.title("OPR Army Builder 🇫🇷")

    # Listes sauvegardées
    st.subheader("Mes listes sauvegardées")
    saved_lists = ls_get("opr_saved_lists")
    if saved_lists:
        try:
            saved_lists = json.loads(saved_lists)
            if isinstance(saved_lists, list):
                for i, saved_list in enumerate(saved_lists):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        with st.expander(f"{saved_list.get('name', 'Liste sans nom')} ({saved_list.get('total_cost', 0)}/{saved_list.get('points', 0)} pts)"):
                            st.write(f"**Jeu**: {saved_list.get('game', 'Inconnu')}")
                            st.write(f"**Faction**: {saved_list.get('faction', 'Inconnue')}")
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
        except Exception as e:
            st.error(f"Erreur chargement listes: {e}")

    if not games:
        st.error("Aucune faction trouvée")
        st.stop()

    game = st.selectbox("Jeu", games)
    faction = st.selectbox("Faction", factions_by_game[game].keys())
    points = st.number_input("Points", 250, 5000, 1000, 250)
    list_name = st.text_input("Nom de la liste", f"Liste_{datetime.now().strftime('%Y%m%d')}")

    # Import JSON
    uploaded = st.file_uploader("Importer une liste JSON", type="json")
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
            st.error(f"Erreur import: {e}")

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
                weapon_name = o["name"]
                weapon_details = format_weapon_details(o["weapon"])
                cost_diff = o["cost"]
                weapon_options.append(f"{weapon_name} ({weapon_details}) (+{cost_diff} pts)")

            selected_weapon = st.radio("Arme", weapon_options, key=f"{unit['name']}_weapon")
            if selected_weapon != "Arme de base":
                opt_name = selected_weapon.split(" (")[0]
                opt = find_option_by_name(group["options"], opt_name)
                if opt:
                    weapon = opt["weapon"]
                    weapon_cost = opt["cost"]

        elif group["type"] == "mount":
            # Formatage des options de monture
            mount_options = ["Aucune monture"]
            for o in group["options"]:
                mount_details = format_mount_details(o)
                cost_diff = o["cost"]
                mount_options.append(f"{mount_details} (+{cost_diff} pts)")

            selected_mount = st.radio("Monture", mount_options, key=f"{unit['name']}_mount")
            if selected_mount != "Aucune monture":
                opt_name = selected_mount.split(" (+")[0]
                opt = find_option_by_name(group["options"], opt_name)
                if opt:
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
                    opt = find_option_by_name(group["options"], opt_name)
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
                        # Vérifier si l'option n'est pas déjà sélectionnée
                        if not any(opt.get("name") == o["name"] for opt in selected_options.get(group["group"], [])):
                            selected_options[group["group"]].append(o)
                            upgrades_cost += o["cost"]

    # Calcul du coût CORRIGÉ pour les héros et unités combinées
    cost = base_cost + weapon_cost + mount_cost + upgrades_cost

    if combined and unit.get('type', '').lower() != 'hero':
        # Pour les unités combinées (non héros), on double (base + arme) et on ajoute les améliorations
        cost = (base_cost + weapon_cost) * 2 + mount_cost + upgrades_cost

    # Calcul de la Coriace TOTALE
    total_coriace = calculate_total_coriace({
        'special_rules': unit.get('special_rules', []),
        'mount': mount,
        'options': selected_options,
        'weapon': weapon,
        'type': unit.get('type', '')
    }, combined)

    st.markdown(f"**Coût total: {cost} pts**")

    # Affichage du détail du calcul
    with st.expander("Voir le détail du calcul"):
        st.write(f"- Coût de base: {base_cost} pts")
        if weapon_cost > 0:
            st.write(f"- Arme: +{weapon_cost} pts")
        if mount_cost > 0:
            st.write(f"- Monture: +{mount_cost} pts")
        if upgrades_cost > 0:
            st.write(f"- Améliorations: +{upgrades_cost} pts")
        if combined and unit.get('type', '').lower() != 'hero':
            st.write(f"- Unité combinée: ×2 sur (base + arme)")
        st.write(f"**Total: {cost} pts**")

    if st.button("Ajouter à l'armée"):
        unit_data = {
            "name": unit["name"],
            "cost": cost,
            "quality": unit["quality"],
            "defense": unit["defense"],
            "rules": [format_special_rule(r) for r in unit.get("special_rules", [])],
            "weapon": weapon,
            "options": selected_options,
            "mount": mount,
            "coriace": total_coriace,
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
            # Affichage amélioré du nom de l'unité avec ses caractéristiques
            unit_header = f"### {u['name']} ({u['cost']} pts)"
            if 'quality' in u and 'defense' in u:
                unit_header += f" | Qua {u['quality']}+ / Déf {u['defense']}+"

            st.markdown(unit_header)

            # Affichage des règles spéciales
            if u.get("rules"):
                rules_text = ", ".join(u["rules"])
                st.markdown(f"**Règles spéciales:** {rules_text}")

            # Affichage des armes avec leurs caractéristiques
            if 'weapon' in u and u['weapon']:
                weapon_name = u['weapon'].get('name', 'Arme non nommée')
                weapon_details = format_weapon_details(u['weapon'])
                st.markdown(f"**Arme:** {weapon_name} ({weapon_details})")

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
    col1, col2, col3, col4 = st.columns(4)

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
            "Export JSON",
            json.dumps(army_data, indent=2, ensure_ascii=False),
            file_name=f"{st.session_state.list_name}.json",
            mime="application/json"
        )

    with col3:
        # Génération HTML
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Liste OPR - {army_data['name']}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .unit {{ border: 1px solid #ddd; padding: 15px; margin-bottom: 20px; border-radius: 5px; }}
                .unit-header {{ font-size: 1.2em; font-weight: bold; margin-bottom: 5px; }}
                .stats {{ display: flex; gap: 20px; margin: 10px 0; }}
                .stat {{ text-align: center; flex: 1; }}
                .rules {{ font-style: italic; color: #555; margin: 5px 0; }}
                .weapon {{ margin: 10px 0; }}
                table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: center; }}
                .cost {{ float: right; color: #666; }}
            </style>
        </head>
        <body>
            <h1>Liste d'armée OPR - {army_data['name']}</h1>
            <h2>{army_data['game']} • {army_data['faction']} • {army_data['total_cost']}/{army_data['points']} pts</h2>
        """

        for unit in army_data['army_list']:
            coriace = unit.get('coriace')
            html_content += f"""
            <div class="unit">
                <div class="unit-header">
                    {unit['name']} <span class="cost">({unit['cost']} pts)</span>
                </div>
                <div class="stats">
                    Qua {unit['quality']}+ / Def {unit['defense']}+
                </div>
            """

            if unit.get('rules'):
                html_content += f'<div class="rules">{", ".join(unit["rules"])}</div>'

            if 'weapon' in unit:
                weapon_name = unit['weapon'].get('name', 'Arme non nommée')
                weapon_details = format_weapon_details(unit['weapon'])
                html_content += f'<div class="weapon"><strong>Arme:</strong> {weapon_name} ({weapon_details})</div>'

            if unit.get('options'):
                for group_name, opts in unit['options'].items():
                    if isinstance(opts, list) and opts:
                        html_content += f'<div class="options"><strong>{group_name}:</strong>'
                        for opt in opts:
                            html_content += f'<div>• {opt.get("name", "")}</div>'
                        html_content += '</div>'

            if unit.get('mount'):
                mount_details = format_mount_details(unit["mount"])
                html_content += f'<div class="mount"><strong>Monture:</strong> {mount_details}</div>'

            html_content += "</div>"

        html_content += "</body></html>"

        st.download_button(
            "Export HTML",
            html_content,
            file_name=f"{st.session_state.list_name}.html",
            mime="text/html"
        )

    with col4:
        if st.button("Réinitialiser"):
            st.session_state.army_list = []
            st.session_state.army_cost = 0
            st.rerun()
