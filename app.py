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
    if not isinstance(rule, str):
        return str(rule)
    if "(" in rule and ")" in rule:
        return rule
    match = re.search(r"(\D+)(\d+)", rule)
    if match:
        return f"{match.group(1)}({match.group(2)})"
    return rule

def extract_coriace_value(rule):
    if not isinstance(rule, str):
        return 0
    match = re.search(r"Coriace\s*\(?(\d+)\)?", rule)
    if match:
        return int(match.group(1))
    return 0

def get_coriace_from_rules(rules):
    if not rules or not isinstance(rules, list):
        return 0
    total = 0
    for rule in rules:
        total += extract_coriace_value(rule)
    return total

def get_mount_details(mount):
    if not mount:
        return None, 0

    mount_data = mount
    if 'mount' in mount:
        mount_data = mount['mount']

    special_rules = []
    if 'special_rules' in mount_data and isinstance(mount_data['special_rules'], list):
        special_rules = mount_data['special_rules']

    coriace = get_coriace_from_rules(special_rules)
    return special_rules, coriace

def calculate_total_coriace(unit_data, combined=False):
    total = 0

    if 'special_rules' in unit_data:
        total += get_coriace_from_rules(unit_data['special_rules'])

    if 'mount' in unit_data and unit_data['mount']:
        _, mount_coriace = get_mount_details(unit_data['mount'])
        total += mount_coriace

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
        total += get_coriace_from_rules(unit_data.get('special_rules', []))

    return total if total > 0 else None

def format_weapon_details(weapon):
    if not weapon:
        return {"name": "Arme non spécifiée", "attacks": "?", "ap": "?", "special": []}

    return {
        "name": weapon.get('name', 'Arme non nommée'),
        "attacks": weapon.get('attacks', '?'),
        "ap": weapon.get('armor_piercing', '?'),
        "special": weapon.get('special_rules', [])
    }

def format_mount_details(mount):
    if not mount:
        return "Aucune monture"

    mount_data = mount['mount'] if 'mount' in mount else mount
    details = mount.get('name', 'Monture')

    if 'special_rules' in mount_data:
        details += " | " + ", ".join(mount_data['special_rules'])

    return details

def format_unit_option(u):
    coriace = get_coriace_from_rules(u.get('special_rules', []))
    defense = u.get('defense', '?')
    result = f"{u['name']} [1] - Qua {u['quality']}+ / Déf {defense}"
    if coriace:
        result += f" / Coriace {coriace}"
    result += f" - {u['base_cost']} pts"
    return result

# ======================================================
# LOCAL STORAGE
# ======================================================
def ls_get(key):
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

def ls_set(key, value):
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

# ======================================================
# CHARGEMENT DES FACTIONS
# ======================================================
@st.cache_data
def load_factions():
    factions = {}
    games = set()

    for fp in FACTIONS_DIR.glob("*.json"):
        with open(fp, encoding="utf-8") as f:
            data = json.load(f)
            game = data.get("game")
            faction = data.get("faction")
            if game and faction:
                factions.setdefault(game, {})[faction] = data
                games.add(game)

    return factions, sorted(games)

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

    game = st.selectbox("Jeu", games)
    faction = st.selectbox("Faction", factions_by_game[game].keys())
    points = st.number_input("Points", 250, 5000, 1000, 250)
    list_name = st.text_input("Nom de la liste", f"Liste_{datetime.now().strftime('%Y%m%d')}")

    uploaded = st.file_uploader("Importer une liste JSON", type=["json"])
    if uploaded:
        data = json.load(uploaded)
        st.session_state.game = data["game"]
        st.session_state.faction = data["faction"]
        st.session_state.points = data["points"]
        st.session_state.list_name = data["name"]
        st.session_state.army_list = data["army_list"]
        st.session_state.army_cost = data["total_cost"]
        st.session_state.units = factions_by_game[data["game"]][data["faction"]]["units"]
        st.session_state.page = "army"
        st.rerun()

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
    st.caption(
        f"{st.session_state.game} • {st.session_state.faction} • "
        f"{st.session_state.army_cost}/{st.session_state.points} pts"
    )

    if st.button("⬅ Retour"):
        st.session_state.page = "setup"
        st.rerun()

    st.divider()
    st.subheader("Ajouter une unité")

    unit = st.selectbox(
        "Unité disponible",
        st.session_state.units,
        format_func=format_unit_option
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

    if unit.get("type", "").lower() != "hero":
        combined = st.checkbox("Unité combinée", value=False)

    for group in unit.get("upgrade_groups", []):
        st.markdown(f"**{group['group']}**")

        if group["type"] == "weapon":
            weapon_options = ["Arme de base"]
            for o in group["options"]:
                w = format_weapon_details(o["weapon"])
                weapon_options.append(
                    f"{o['name']} (A{w['attacks']}, PA({w['ap']})"
                    f"{', ' + ', '.join(w['special']) if w['special'] else ''}) (+{o['cost']} pts)"
                )

            selected_weapon = st.radio("Arme", weapon_options)
            if selected_weapon != "Arme de base":
                opt_name = selected_weapon.split(" (")[0]
                opt = next(o for o in group["options"] if o["name"] == opt_name)
                weapon = opt["weapon"]
                weapon_cost = opt["cost"]

        elif group["type"] == "mount":
            mount_labels = ["Aucune monture"]
            mount_map = {}

            for o in group["options"]:
                label = f"{format_mount_details(o)} (+{o['cost']} pts)"
                mount_labels.append(label)
                mount_map[label] = o

            selected_mount = st.radio("Monture", mount_labels)
            if selected_mount != "Aucune monture":
                mount = mount_map[selected_mount]
                mount_cost = mount["cost"]

        else:
            for o in group["options"]:
                if st.checkbox(f"{o['name']} (+{o['cost']} pts)"):
                    selected_options.setdefault(group["group"], []).append(o)
                    upgrades_cost += o["cost"]

    cost = base_cost + weapon_cost + mount_cost + upgrades_cost
    st.markdown(f"**Coût total: {cost} pts**")

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
            "coriace": calculate_total_coriace({
                "special_rules": unit.get("special_rules", []),
                "mount": mount,
                "options": selected_options,
                "weapon": weapon,
                "type": unit.get("type", "")
            }),
            "combined": combined,
            "type": unit.get("type", "")
        }
        st.session_state.army_list.append(unit_data)
        st.session_state.army_cost += cost
        st.rerun()

    # =========================
    # LISTE DE L’ARMÉE
    # =========================
    st.divider()
    st.subheader("Liste de l'armée")

    for i, u in enumerate(st.session_state.army_list):
        st.markdown(
            f"### {u['name']} ({u['cost']} pts) "
            f"| Qua {u['quality']}+ / Déf {u['defense']}+"
            f"{' / Coriace ' + str(u['coriace']) if u.get('coriace') else ''}"
        )

        if u.get("rules"):
            st.markdown(f"**Règles spéciales:** {', '.join(u['rules'])}")

        w = format_weapon_details(u["weapon"])
        st.markdown(
            f"**Arme:** {w['name']} (A{w['attacks']}, PA({w['ap']})"
            f"{', ' + ', '.join(w['special']) if w['special'] else ''})"
        )

        if u.get("options"):
            for g, opts in u["options"].items():
                st.markdown(f"**{g}:** " + ", ".join(o["name"] for o in opts))

        if u.get("mount"):
            st.markdown(f"**Monture:** {format_mount_details(u['mount'])}")

        if st.button("Supprimer", key=f"del_{i}"):
            st.session_state.army_cost -= u["cost"]
            st.session_state.army_list.pop(i)
            st.rerun()

    # =========================
    # EXPORTS
    # =========================
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
        st.download_button(
            "Exporter JSON",
            json.dumps(army_data, indent=2, ensure_ascii=False),
            file_name=f"{army_data['name']}.json"
        )

    with col2:
        st.download_button(
            "Exporter HTML",
            json.dumps(army_data, indent=2, ensure_ascii=False),
            file_name=f"{army_data['name']}.html"
        )

    # =========================
    # EXPORT HTML – FICHES UNITÉS (CORRIGÉ)
    # =========================
    with col3:
        html = f"""
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>{army_data['name']} – Fiches Unités</title>
<style>
body {{ font-family: Arial; background:#eee; padding:20px; }}
.card {{ background:white; padding:15px; margin-bottom:20px; border-radius:8px; }}
.header {{ font-size:22px; font-weight:bold; }}
.stats span {{ margin-right:10px; }}
.section {{ margin-top:10px; }}
</style>
</head>
<body>
<h1>{army_data['name']}</h1>
<p>{army_data['game']} – {army_data['faction']} ({army_data['total_cost']} pts)</p>
"""

        for u in army_data["army_list"]:
            w = format_weapon_details(u["weapon"])
            html += f"""
<div class="card">
<div class="header">{u['name']} ({u['cost']} pts)</div>
<div class="stats">
<span>Qua {u['quality']}+</span>
<span>Déf {u['defense']}+</span>
{f"<span>Coriace {u['coriace']}</span>" if u.get("coriace") else ""}
</div>

<div class="section"><strong>Règles:</strong> {", ".join(u.get("rules", []))}</div>

<div class="section">
<strong>Arme:</strong> {w['name']} (A{w['attacks']}, PA({w['ap']})
{", " + ", ".join(w['special']) if w['special'] else ""})
</div>
"""

            if u.get("options"):
                html += "<div class='section'><strong>Améliorations:</strong><ul>"
                for opts in u["options"].values():
                    for o in opts:
                        html += f"<li>{o['name']}</li>"
                html += "</ul></div>"

            if u.get("mount"):
                html += f"<div class='section'><strong>Monture:</strong> {format_mount_details(u['mount'])}</div>"

            html += "</div>"

        html += "</body></html>"

        st.download_button(
            "Exporter Fiches HTML",
            html,
            file_name=f"{army_data['name']}_fiches.html",
            mime="text/html"
        )

    with col4:
        if st.button("Réinitialiser"):
            st.session_state.army_list = []
            st.session_state.army_cost = 0
            st.rerun()
