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
# FONCTIONS UTILITAIRES (définies en premier)
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
    match = re.search(r"Coriace\s*$?(\d+)$?", rule)
    if match:
        return int(match.group(1))
    return 0

def calculate_coriace_from_rules(rules):
    """Calcule la Coriace depuis une liste de règles"""
    if not rules or not isinstance(rules, list):
        return 0
    total = 0
    for rule in rules:
        total += extract_coriace_value(rule)
    return total

def get_coriace_sources(unit_data, combined=False):
    """Retourne les sources de Coriace avec leurs valeurs"""
    sources = {}

    # 1. Règles de base
    base_coriace = 0
    if 'special_rules' in unit_data:
        base_coriace = calculate_coriace_from_rules(unit_data['special_rules'])
        if base_coriace > 0:
            sources['Règles de base'] = base_coriace

    # 2. Monture
    mount_coriace = 0
    if 'mount' in unit_data and unit_data['mount']:
        if 'special_rules' in unit_data['mount']:
            mount_coriace = calculate_coriace_from_rules(unit_data['mount']['special_rules'])
            if mount_coriace > 0:
                sources['Monture'] = mount_coriace

    # 3. Améliorations
    options_coriace = 0
    if 'options' in unit_data:
        for opts in unit_data['options'].values():
            if isinstance(opts, list):
                for opt in opts:
                    if 'special_rules' in opt:
                        options_coriace += calculate_coriace_from_rules(opt['special_rules'])
            elif isinstance(opts, dict) and 'special_rules' in opts:
                options_coriace += calculate_coriace_from_rules(opts['special_rules'])
        if options_coriace > 0:
            sources['Améliorations'] = options_coriace

    # 4. Armes
    weapon_coriace = 0
    if 'weapon' in unit_data and 'special_rules' in unit_data['weapon']:
        weapon_coriace = calculate_coriace_from_rules(unit_data['weapon']['special_rules'])
        if weapon_coriace > 0:
            sources['Armes'] = weapon_coriace

    # 5. Unité combinée
    combined_coriace = 0
    if combined and unit_data.get('type', '').lower() != 'hero':
        combined_coriace = base_coriace
        sources['Unité combinée'] = combined_coriace

    total = sum(sources.values())
    return sources, total

def calculate_total_coriace(unit_data, combined=False):
    """Calcule la Coriace TOTALE d'une unité"""
    sources, total = get_coriace_sources(unit_data, combined)
    return total if total > 0 else None

def generate_html(army_data):
    """Génère le HTML pour export"""
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Liste OPR - {army_data['name']}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .unit {{ border: 1px solid #ddd; padding: 15px; margin-bottom: 20px; border-radius: 5px; }}
            .stats {{ display: flex; gap: 20px; margin: 10px 0; }}
            .stat {{ text-align: center; flex: 1; }}
            table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: center; }}
            th {{ background-color: #f2f2f2; }}
        </style>
    </head>
    <body>
        <h1>Liste d'armée OPR - {army_data['name']}</h1>
        <h2>{army_data['game']} • {army_data['faction']} • {army_data['total_cost']}/{army_data['points']} pts</h2>
    """

    for unit in army_data['army_list']:
        coriace = unit.get('coriace')
        html += f"""
        <div class="unit">
            <h3>{unit['name']} [{unit['cost']} pts]</h3>
            <div class="stats">
                <div class="stat"><strong>Qua:</strong> {unit['quality']}+</div>
                <div class="stat"><strong>Déf:</strong> {unit['defense']}+</div>
                {'<div class="stat"><strong>Coriace:</strong> ' + str(coriace) + '</div>' if coriace else ''}
            </div>
        """

        if unit.get('rules'):
            html += f"<p><strong>Règles spéciales:</strong> {', '.join(unit['rules'])}</p>"

        if 'weapon' in unit:
            html += f"""
            <p><strong>Armes:</strong></p>
            <table>
                <tr><th>Nom</th><th>ATK</th><th>AP</th><th>Règles spéciales</th></tr>
                <tr>
                    <td>{unit['weapon'].get('name', '-')}</td>
                    <td>{unit['weapon'].get('attacks', '-')}</td>
                    <td>{unit['weapon'].get('armor_piercing', '-')}</td>
                    <td>{', '.join(unit['weapon'].get('special_rules', [])) or '-'}</td>
                </tr>
            </table>
            """

        if unit.get('options'):
            html += "<p><strong>Améliorations:</strong></p><ul>"
            for opts in unit['options'].values():
                if isinstance(opts, list):
                    for opt in opts:
                        html += f"<li>{format_special_rule(opt.get('name', ''))}</li>"
            html += "</ul>"

        if unit.get('mount'):
            html += f"<p><strong>Monture:</strong> {unit['mount']['name']}</p>"
            if 'special_rules' in unit['mount']:
                html += f"<p>Règles: {', '.join(unit['mount']['special_rules'])}</p>"

        html += "</div>"

    html += "</body></html>"
    return html

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

    unit = st.selectbox(
        "Unité disponible",
        st.session_state.units,
        format_func=lambda u: f"{u['name']} ({u['base_cost']} pts)"
    )

    # Initialisation
    cost = unit["base_cost"]
    weapon = unit.get("weapons", [{}])[0]
    selected_options = {}
    mount = None
    combined = False

    # Unité combinée (pas pour les héros)
    if unit.get("type", "").lower() != "hero":
        combined = st.checkbox("Unité combinée (+100% coût)", value=False)
        if combined:
            cost *= 2

    # Options de l'unité
    for group in unit.get("upgrade_groups", []):
        st.markdown(f"**{group['group']}**")

        if group["type"] == "weapon":
            weapon_options = ["Arme de base"] + [
                f"{o['name']} (+{o['cost'] * (2 if combined else 1)} pts)" for o in group["options"]
            ]
            selected = st.radio("Arme", weapon_options, key=f"{unit['name']}_weapon")
            if selected != "Arme de base":
                opt_name = selected.split(" (+")[0]
                opt = next(o for o in group["options"] if o["name"] == opt_name)
                weapon = opt["weapon"]
                cost += opt["cost"] * (2 if combined else 1)

        elif group["type"] == "mount":
            mount_options = ["Aucune monture"] + [
                f"{o['name']} (+{o['cost'] * (2 if combined else 1)} pts)" for o in group["options"]
            ]
            selected = st.radio("Monture", mount_options, key=f"{unit['name']}_mount")
            if selected != "Aucune monture":
                opt_name = selected.split(" (+")[0]
                opt = next(o for o in group["options"] if o["name"] == opt_name)
                mount = opt
                cost += opt["cost"] * (2 if combined else 1)

        else:  # Améliorations
            option_names = ["Aucune"] + [
                f"{o['name']} (+{o['cost'] * (2 if combined else 1)} pts)" for o in group["options"]
            ]
            selected = st.radio(group["group"], option_names, key=f"{unit['name']}_{group['group']}")
            if selected != "Aucune":
                opt_name = selected.split(" (+")[0]
                opt = next(o for o in group["options"] if o["name"] == opt_name)
                if group["group"] not in selected_options:
                    selected_options[group["group"]] = []
                selected_options[group["group"]].append(opt)
                cost += opt["cost"] * (2 if combined else 1)

    # Calcul de la Coriace TOTALE
    unit_data_for_calc = {
        'special_rules': unit.get('special_rules', []),
        'mount': mount,
        'options': selected_options,
        'weapon': weapon,
        'type': unit.get('type', '')
    }

    total_coriace = calculate_total_coriace(unit_data_for_calc, combined)

    # Affichage des détails
    st.markdown(f"**Coût total: {cost} pts**")
    if total_coriace is not None:
        st.markdown(f"**Coriace totale: {total_coriace}**")

        # Détail du calcul pour vérification
        with st.expander("Voir le détail du calcul de Coriace"):
            sources, _ = get_coriace_sources(unit_data_for_calc, combined)

            if not sources:
                st.warning("Aucune source de Coriace trouvée")
            else:
                for source, value in sources.items():
                    st.write(f"- {source}: {value}")

                st.write(f"**Total calculé: {sum(sources.values())}**")

                # Vérification de la monture
                if mount and 'Monture' not in sources:
                    st.warning("⚠️ La monture sélectionnée ne contribue pas à la Coriace (vérifiez ses règles spéciales)")

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
            st.markdown(f"### {u['name']} – {u['cost']} pts")
            if u.get("combined"):
                st.markdown("**Unité combinée**")

            c1, c2, c3 = st.columns(3)
            c1.metric("Qualité", f"{u['quality']}+")
            c2.metric("Défense", f"{u['defense']}+")
            if u.get("coriace"):
                c3.metric("Coriace", u["coriace"])

            if u.get("rules"):
                st.markdown("**Règles spéciales**")
                st.caption(", ".join(u["rules"]))

            if 'weapon' in u:
                st.markdown("**Armes**")
                st.caption(f"{u['weapon'].get('name', '-')} | A{u['weapon'].get('attacks', '?')} PA{u['weapon'].get('armor_piercing', '?')}")

            if u.get("options"):
                st.markdown("**Améliorations**")
                for opts in u["options"].values():
                    if isinstance(opts, list):
                        for opt in opts:
                            st.caption(f"• {format_special_rule(opt.get('name', ''))}")

            if u.get("mount"):
                st.markdown("**Monture**")
                st.caption(u["mount"]["name"])
                if "special_rules" in u["mount"]:
                    st.caption(", ".join(u["mount"]["special_rules"]))

            if st.button(f"Supprimer", key=f
