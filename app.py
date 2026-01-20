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

def calculate_total_coriace(unit_data, combined=False):
    """
    Calcule la Coriace TOTALE d'une unité
    """
    total = 0

    # 1. Règles de base de l'unité
    if 'special_rules' in unit_data:
        total += get_coriace_from_rules(unit_data['special_rules'])

    # 2. Monture
    if 'mount' in unit_data and unit_data['mount']:
        special_rules, mount_coriace = get_mount_details(unit_data['mount'])
        total += mount_coriace

    # 3. Améliorations
    if 'options' in unit_data:
        for opts in unit_data['options'].values():
            if isinstance(opts, list):
                for opt in opts:
                    if 'special_rules' in opt:
                        total += get_coriace_from_rules(opt['special_rules'])
            elif isinstance(opts, dict) and 'special_rules' in opts:
                total += get_coriace_from_rules(opts['special_rules'])

    # 4. Armes
    if 'weapon' in unit_data and 'special_rules' in unit_data['weapon']:
        total += get_coriace_from_rules(unit_data['weapon']['special_rules'])

    # 5. Pour les unités combinées (mais PAS pour les héros)
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

    # Ajouter les attaques de la monture si disponibles
    if 'weapons' in mount_data and mount_data['weapons']:
        for weapon in mount_data['weapons']:
            details += " | " + format_weapon_details(weapon)

    return details

def format_unit_option(u):
    """Formate l'affichage des unités dans la liste déroulante"""
    name_part = f"{u['name']} [1]"
    qua_def = f"Qua {u['quality']}+ Def {u['defense']}+"

    weapons_part = ""
    if 'weapons' in u and u['weapons']:
        weapons = []
        for weapon in u['weapons']:
            weapon_name = weapon.get('name', '')
            weapon_details = format_weapon_details(weapon)
            weapons.append(f"{weapon_name} ({weapon_details})")
        weapons_part = " | ".join(weapons)

    rules_part = ""
    if 'special_rules' in u and u['special_rules']:
        rules_part = ", ".join(u['special_rules'])

    result = f"{name_part} - {qua_def}"

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
    st.title("OPR Army Builder FR")

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
                opt_name = selected_mount.split(" (")[0]
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
                        if not any(opt.get("name") == o["name"] for opt in selected_options.get(group["group"], [])):
                            selected_options[group["group"]].append(o)
                            upgrades_cost += o["cost"]

    # Calcul du coût CORRIGÉ pour tous les types d'unités
    cost = base_cost + weapon_cost + mount_cost + upgrades_cost

    # Calcul de la Coriace TOTALE
    total_coriace = calculate_total_coriace({
        'special_rules': unit.get('special_rules', []),
        'mount': mount,
        'options': selected_options,
        'weapon': weapon,
        'type': unit.get('type', '')
    })

    # Affichage des informations de vérification
    st.markdown(f"**Coût total: {cost} pts**")

    # Vérification spécifique pour les héros avec monture
    if unit.get('type', '').lower() == 'hero' and mount:
        hero_coriace = get_coriace_from_rules(unit.get('special_rules', []))
        mount_special_rules, mount_coriace = get_mount_details(mount)
        st.markdown(f"**Vérification:**")
        st.markdown(f"- Coût: {base_cost} (base) + {weapon_cost} (arme) + {mount_cost} (monture) + {upgrades_cost} (améliorations) = {cost}")
        st.markdown(f"- Coriace: {hero_coriace} (héros) + {mount_coriace} (monture) = {total_coriace}")

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
            unit_header = f"### {u['name']} ({u['cost']} pts)"
            if 'quality' in u and 'defense' in u:
                unit_header += f" | Qua {u['quality']}+ / Déf {u['defense']}+"
            st.markdown(unit_header)

            if u.get("rules"):
                rules_text = ", ".join(u["rules"])
                st.markdown(f"**Règles spéciales:** {rules_text}")

            if 'weapon' in u and u['weapon']:
                weapon_name = u['weapon'].get('name', 'Arme non nommée')
                weapon_details = format_weapon_details(u['weapon'])
                st.markdown(f"**Arme:** {weapon_name} ({weapon_details})")

            if u.get("options"):
                for group_name, opts in u["options"].items():
                    if isinstance(opts, list) and opts:
                        st.markdown(f"**{group_name}:**")
                        for opt in opts:
                            st.markdown(f"• {opt.get('name', '')}")

            if u.get("mount"):
                mount_details = format_mount_details(u["mount"])
                st.markdown(f"**Monture:** {mount_details}")

            if u.get("coriace"):
                st.markdown(f"**Coriace:** {u['coriace']}")

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
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Liste OPR - {army_data['name']}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .unit {{ border: 1px solid #ddd; padding: 15px; margin-bottom: 20px; border-radius: 5px; }}
                .unit-header {{ font-size: 1.2em; font-weight: bold; margin-bottom: 5px; }}
                .coriace {{ color: #d63031; font-weight: bold; }}
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
                    {unit['name']} ({unit['cost']} pts)
                </div>
            """

            if unit.get('rules'):
                html_content += f'<div><strong>Règles spéciales:</strong> {", ".join(unit["rules"])}</div>'

            if 'weapon' in unit:
                weapon_name = unit['weapon'].get('name', 'Arme non nommée')
                weapon_details = format_weapon_details(unit['weapon'])
                html_content += f'<div><strong>Arme:</strong> {weapon_name} ({weapon_details})</div>'

            if unit.get('options'):
                for group_name, opts in unit['options'].items():
                    if isinstance(opts, list) and opts:
                        html_content += f'<div><strong>{group_name}:</strong>'
                        for opt in opts:
                            html_content += f'<div>• {opt.get("name", "")}</div>'
                        html_content += '</div>'

            if unit.get('mount'):
                mount_details = format_mount_details(unit["mount"])
                html_content += f'<div><strong>Monture:</strong> {mount_details}</div>'

            if unit.get('coriace'):
                html_content += f'<div class="coriace"><strong>Coriace:</strong> {unit["coriace"]}</div>'

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
