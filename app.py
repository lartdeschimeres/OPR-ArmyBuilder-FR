import json
import streamlit as st
from pathlib import Path
from datetime import datetime
import re
import math

# ======================================================
# CSS GLOBAL
# ======================================================
st.markdown("""
<style>

/* --- Nettoyage Streamlit --- */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* --- Fond général --- */
.stApp {
    background: #0a0a0a;
    color: #e0e0e0;
}

/* --- Titres --- */
h1, h2, h3 {
    color: #ff8c00;
    letter-spacing: 0.04em;
    text-shadow: 0 0 5px rgba(255, 140, 0, 0.5);
}

/* --- Cartes --- */
.card {
    background: linear-gradient(180deg, #1a1a1a, #0d0d0d);
    border: 2px solid #ff8c00;
    border-radius: 8px;
    padding: 1.2rem;
    transition: all 0.2s ease;
    cursor: pointer;
    height: 100%;
    box-shadow: 0 0 10px rgba(255, 140, 0, 0.3);
}

.card:hover {
    border-color: #ffcc00;
    box-shadow: 0 0 20px rgba(255, 204, 0, 0.6);
    transform: translateY(-2px);
}

/* --- Texte secondaire --- */
.muted {
    color: #aaa;
    font-size: 0.9rem;
}

/* --- Badge --- */
.badge {
    display: inline-block;
    padding: 0.2rem 0.6rem;
    border-radius: 4px;
    background: #ff8c00;
    color: #000;
    font-size: 0.75rem;
    margin-bottom: 0.6rem;
    font-weight: bold;
}

/* --- Inputs visibles --- */
div[data-baseweb="select"] > div,
div[data-baseweb="input"] input,
div[data-baseweb="base-input"] input {
    background-color: #1a1a1a !important;
    color: #ff8c00 !important;
    border: 1px solid #ff8c00 !important;
    border-radius: 6px !important;
    font-weight: 500;
}

div[data-baseweb="select"] span {
    color: #ff8c00 !important;
}

/* --- Bouton principal --- */
button[kind="primary"] {
    background: linear-gradient(135deg, #ff8c00, #ffcc00) !important;
    color: #000 !important;
    font-weight: bold !important;
    border-radius: 6px !important;
    padding: 0.6rem 1rem !important;
    border: none !important;
    box-shadow: 0 0 10px rgba(255, 140, 0, 0.5);
}

button[kind="primary"]:hover {
    filter: brightness(1.2);
    box-shadow: 0 0 20px rgba(255, 204, 0, 0.8);
}

/* --- Avertissements --- */
.stAlert {
    background: #ff8c00;
    color: #000;
    border-radius: 6px;
    padding: 0.8rem;
}

/* --- Barre de progression --- */
.stProgress > div > div > div {
    background: linear-gradient(90deg, #ff8c00, #ffcc00);
}

/* --- Export HTML --- */
body {
    background: #0a0a0a;
    color: #e0e0e0;
    font-family: Arial, sans-serif;
}

h1 {
    color: #ff8c00;
}

.unit {
    border: 1px solid #ff8c00;
    border-radius: 8px;
    padding: 12px;
    margin-bottom: 12px;
    background: #1a1a1a;
}

</style>
""", unsafe_allow_html=True)

# ======================================================
# INITIALISATION
# ======================================================
if "page" not in st.session_state:
    st.session_state.page = "setup"
if "army_list" not in st.session_state:
    st.session_state.army_list = []
if "army_cost" not in st.session_state:
    st.session_state.army_cost = 0
if "unit_selections" not in st.session_state:
    st.session_state.unit_selections = {}

# ======================================================
# SIDEBAR – CONTEXTE & NAVIGATION
# ======================================================
with st.sidebar:
    st.title("🛡️ Army Forge")

    st.subheader("📋 Armée")

    game = st.session_state.get("game", "—")
    faction = st.session_state.get("faction", "—")
    points = st.session_state.get("points", 0)
    army_cost = st.session_state.get("army_cost", 0)

    st.markdown(f"**Jeu :** {game}")
    st.markdown(f"**Faction :** {faction}")
    st.markdown(f"**Format :** {points} pts")

    if points > 0:
        st.progress(min(army_cost / points, 1.0))
        st.markdown(f"**Coût :** {army_cost} / {points} pts")

        if army_cost > points:
            st.error("⚠️ Dépassement de points")

    st.divider()

    st.subheader("🧭 Navigation")

    if st.button("⚙️ Configuration", use_container_width=True):
        st.session_state.page = "setup"
        st.rerun()

    if st.button("🧩 Construction", use_container_width=True):
        st.session_state.page = "army"
        st.rerun()

# ======================================================
# CONFIGURATION DES JEUX
# ======================================================
GAME_CONFIG = {
    "Age of Fantasy": {
        "max_points": 10000,
        "min_points": 250,
        "default_points": 1000,
        "hero_limit": 375,  # 1 héros par 375pts
        "unit_copy_rule": 750,
        "unit_max_cost_ratio": 0.35,  # 35% du total
        "unit_per_points": 150
    },
    "Grimdark Future": {
        "max_points": 10000,
        "min_points": 250,
        "default_points": 1000,
        "hero_limit": 375,
        "unit_copy_rule": 750,
        "unit_max_cost_ratio": 0.35,
        "unit_per_points": 150
    }
}

# ======================================================
# FONCTIONS DE VALIDATION
# ======================================================
def check_hero_limit(army_list, army_points, game_config):
    max_heroes = math.floor(army_points / game_config["hero_limit"])
    hero_count = sum(1 for unit in army_list if unit.get("type") == "hero")
    if hero_count > max_heroes:
        st.error(f"Limite de héros dépassée! Max: {max_heroes} (1 héros/{game_config['hero_limit']} pts)")
        return False
    return True

def check_unit_max_cost(army_list, army_points, game_config, new_unit_cost=None):
    max_cost = army_points * game_config["unit_max_cost_ratio"]
    for unit in army_list:
        if unit["cost"] > max_cost:
            st.error(f"Unité {unit['name']} dépasse {int(max_cost)} pts (35% du total)")
            return False
    if new_unit_cost and new_unit_cost > max_cost:
        st.error(f"Cette unité dépasse {int(max_cost)} pts (35% du total)")
        return False
    return True

def check_unit_copy_rule(army_list, army_points, game_config):
    x_value = math.floor(army_points / game_config["unit_copy_rule"])
    max_copies = 1 + x_value
    unit_counts = {}
    for unit in army_list:
        name = unit["name"]
        unit_counts[name] = unit_counts.get(name, 0) + 1
    for unit_name, count in unit_counts.items():
        if count > max_copies:
            st.error(f"Trop de copies de {unit_name}! Max: {max_copies}")
            return False
    return True

def validate_army_rules(army_list, army_points, game):
    game_config = GAME_CONFIG.get(game, {})
    return (check_hero_limit(army_list, army_points, game_config) and
            check_unit_max_cost(army_list, army_points, game_config) and
            check_unit_copy_rule(army_list, army_points, game_config))

# ======================================================
# FONCTIONS UTILITAIRES
# ======================================================
def format_weapon_details(weapon):
    if not weapon:
        return {"name": "Arme non spécifiée", "attacks": "?", "ap": "?", "special": []}
    return {
        "name": weapon.get('name', 'Arme non nommée'),
        "attacks": weapon.get('attacks', '?'),
        "ap": weapon.get('armor_piercing', '?'),
        "special": weapon.get('special_rules', [])
    }

def format_unit_option(u):
    name_part = f"{u['name']}"
    if u.get('type') == "hero":
        name_part += " [1]"
    else:
        name_part += f" [{u.get('size', 10)}]"
    qua_def = f"Qua {u['quality']}+ / Déf {u.get('defense', '?')}"
    result = f"{name_part} - {qua_def} {u['base_cost']}pts"
    return result
def export_army_json():
    return {
        "game": st.session_state.game,
        "faction": st.session_state.faction,
        "points": st.session_state.points,
        "list_name": st.session_state.list_name,
        "army_cost": st.session_state.army_cost,
        "units": st.session_state.army_list,
        "exported_at": datetime.now().isoformat()
    }

def export_army_html():
    html = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <title>{st.session_state.list_name}</title>
        <style>
            body {{
                background:#0e1016;
                color:#e6e6e6;
                font-family: Arial, sans-serif;
            }}
            h1 {{ color:#4da6ff; }}
            .unit {{
                border:1px solid #2a3042;
                border-radius:12px;
                padding:12px;
                margin-bottom:12px;
            }}
        </style>
    </head>
    <body>
        <h1>{st.session_state.list_name}</h1>
        <p>{st.session_state.game} – {st.session_state.faction}</p>
        <p>{st.session_state.army_cost} / {st.session_state.points} pts</p>
    """

    for u in st.session_state.army_list:
        html += f"""
        <div class="unit">
            <strong>{u['name']}</strong><br>
            Coût: {u['cost']} pts<br>
            Taille: {u.get('size', '?')}
        </div>
        """

    html += "</body></html>"
    return html
    
# ======================================================
# CHARGEMENT DES FACTIONS
# ======================================================
@st.cache_data
def load_factions():
    factions = {}
    games = set()
    FACTIONS_DIR = Path(__file__).resolve().parent / "lists" / "data" / "factions"
    for fp in FACTIONS_DIR.glob("*.json"):
        try:
            with open(fp, encoding="utf-8") as f:
                data = json.load(f)
                game = data.get("game")
                faction = data.get("faction")
                if game and faction:
                    if game not in factions:
                        factions[game] = {}
                    factions[game][faction] = data
                    games.add(game)
        except Exception as e:
            st.warning(f"Erreur chargement {fp.name}: {e}")
    return factions, sorted(games) if games else list(GAME_CONFIG.keys())

# ======================================================
# PAGE 1 – CONFIGURATION
# ======================================================
if st.session_state.page == "setup":

    st.markdown("## 🛡️ OPR Army Forge")
    st.markdown(
        "<p class='muted'>Construisez, équilibrez et façonnez vos armées pour "
        "Age of Fantasy et Grimdark Future.</p>",
        unsafe_allow_html=True
    )

    st.markdown("---")

    factions_by_game, games = load_factions()
    if not games:
        st.error("Aucun jeu trouvé")
        st.stop()

    # --- Sélection en cartes ---
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<span class='badge'>Jeu</span>", unsafe_allow_html=True)
        game = st.selectbox(
            "Choisissez un système",
            games,
            label_visibility="collapsed"
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<span class='badge'>Faction</span>", unsafe_allow_html=True)
        faction = st.selectbox(
            "Faction",
            factions_by_game[game].keys(),
            label_visibility="collapsed"
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with col3:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<span class='badge'>Format</span>", unsafe_allow_html=True)
        points = st.number_input(
            "Points",
            min_value=250,
            max_value=10000,
            value=1000,
            step=250,
            label_visibility="collapsed"
        )
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("")

    colA, colB = st.columns([2, 1])

    with colA:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<span class='badge'>Liste</span>", unsafe_allow_html=True)
        list_name = st.text_input(
            "Nom de la liste",
            f"Liste_{datetime.now().strftime('%Y%m%d')}",
            label_visibility="collapsed"
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with colB:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<span class='badge'>Action</span>", unsafe_allow_html=True)
        st.markdown("Prêt à forger votre armée ?", unsafe_allow_html=True)

        if st.button("🔥 Construire l’armée", use_container_width=True, type="primary"):
            st.session_state.game = game
            st.session_state.faction = faction
            st.session_state.points = points
            st.session_state.list_name = list_name

            faction_data = factions_by_game[game][faction]
            st.session_state.units = faction_data["units"]
            st.session_state.faction_rules = faction_data.get("special_rules", [])
            st.session_state.faction_spells = faction_data.get("spells", [])

            st.session_state.army_list = []
            st.session_state.army_cost = 0
            st.session_state.page = "army"
            st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

# ======================================================
# PAGE 2 – CONSTRUCTEUR D'ARMÉE
# ======================================================
elif st.session_state.page == "army":

    # ======================================================
    # SÉCURISATION DU SESSION STATE
    # ======================================================
    st.session_state.setdefault("list_name", "Nouvelle Armée")
    st.session_state.setdefault("army_cost", 0)
    st.session_state.setdefault("army_list", [])
    st.session_state.setdefault("unit_selections", {})

    # ======================================================
    # TITRE & NAVIGATION
    # ======================================================
    st.title(
        f"{st.session_state.list_name} "
        f"- {st.session_state.army_cost}/{st.session_state.points} pts"
    )

    if st.button("⬅️ Retour à la configuration"):
        st.session_state.page = "setup"
        st.rerun()

    st.divider()
    st.subheader("📤 Export de la liste")

    colE1, colE2 = st.columns(2)

    with colE1:
        json_data = json.dumps(export_army_json(), indent=2, ensure_ascii=False)
        st.download_button(
            "📄 Export JSON",
            data=json_data,
            file_name=f"{st.session_state.list_name}.json",
            mime="application/json",
            use_container_width=True
        )

    with colE2:
        html_data = export_army_html()
        st.download_button(
            "🌐 Export HTML",
            data=html_data,
            file_name=f"{st.session_state.list_name}.html",
            mime="text/html",
            use_container_width=True
        )
    
    # ======================================================
    # BARRE DE PROGRESSION – PALIERS D’ARMÉE
    # ======================================================
    points = st.session_state.points
    game_cfg = GAME_CONFIG.get(st.session_state.game, {})

    st.subheader("📊 Progression de l’armée")
    col1, col2, col3 = st.columns(3)

    with col1:
        units_cap = math.floor(points / game_cfg.get("unit_per_points", 150))
        units_now = len(
            [u for u in st.session_state.army_list if u.get("type") != "hero"]
        )
        st.progress(min(units_now / max(units_cap, 1), 1.0))
        st.caption(f"Unités : {units_now} / {units_cap}")

    with col2:
        heroes_cap = math.floor(points / game_cfg.get("hero_limit", 375))
        heroes_now = len(
            [u for u in st.session_state.army_list if u.get("type") == "hero"]
        )
        st.progress(min(heroes_now / max(heroes_cap, 1), 1.0))
        st.caption(f"Héros : {heroes_now} / {heroes_cap}")

    with col3:
        copy_cap = 1 + math.floor(points / game_cfg.get("unit_copy_rule", 750))
        st.progress(min(copy_cap / 5, 1.0))
        st.caption(f"Copies max : {copy_cap} / unité")

    st.divider()

    # ======================================================
    # RÈGLES SPÉCIALES DE FACTION
    # ======================================================
    if st.session_state.get("faction_rules"):
        with st.expander("📜 Règles spéciales de la faction", expanded=True):
            for rule in st.session_state.faction_rules:
                if isinstance(rule, dict):
                    st.markdown(
                        f"**{rule.get('name', 'Règle')}**\n\n"
                        f"{rule.get('description', '')}"
                    )
                else:
                    st.markdown(f"- {rule}")

    # ======================================================
    # SORTS DE LA FACTION
    # ======================================================
    if st.session_state.get("faction_spells"):
        with st.expander("✨ Sorts de la faction", expanded=False):
            for spell in st.session_state.faction_spells:
                if isinstance(spell, dict):
                    st.markdown(
                        f"**{spell.get('name', 'Sort')}**\n\n"
                        f"*Coût :* {spell.get('cost', '?')} pts  \n"
                        f"*Portée :* {spell.get('range', '?')}  \n\n"
                        f"{spell.get('description', '')}"
                    )
                else:
                    st.markdown(f"- {spell}")

    # ======================================================
    # SÉLECTION DE L’UNITÉ
    # ======================================================
    unit = st.selectbox(
        "Unité disponible",
        st.session_state.units,
        format_func=format_unit_option,
        key="unit_select",
    )

    unit_key = f"unit_{unit['name']}"
    st.session_state.unit_selections.setdefault(unit_key, {})

    weapons = list(unit.get("weapons", []))
    selected_options = {}
    mount = None
    weapon_cost = 0
    mount_cost = 0
    upgrades_cost = 0

    # ======================================================
    # AMÉLIORATIONS
    # ======================================================
    for g_idx, group in enumerate(unit.get("upgrade_groups", [])):
        g_key = f"group_{g_idx}"
        st.subheader(group.get("group", "Améliorations"))

        # ---------- ARMES ----------
        if group.get("type") == "weapon":
            choices = ["Arme de base"]
            opt_map = {}

            for o in group.get("options", []):
                label = f"{o['name']} (+{o['cost']} pts)"
                choices.append(label)
                opt_map[label] = o

            current = st.session_state.unit_selections[unit_key].get(g_key, choices[0])
            choice = st.radio(
                "Sélection de l’arme",
                choices,
                index=choices.index(current) if current in choices else 0,
                key=f"{unit_key}_{g_key}_weapon",
            )

            st.session_state.unit_selections[unit_key][g_key] = choice

            if choice != "Arme de base":
                opt = opt_map[choice]
                weapon_cost += opt["cost"]
                weapons = (
                    [opt["weapon"]]
                    if unit.get("type") == "hero"
                    else weapons + [opt["weapon"]]
                )

        # ---------- MONTURE ----------
        elif group.get("type") == "mount":
            choices = ["Aucune monture"]
            opt_map = {}

            for o in group.get("options", []):
                label = f"{o['name']} (+{o['cost']} pts)"
                choices.append(label)
                opt_map[label] = o

            current = st.session_state.unit_selections[unit_key].get(g_key, choices[0])
            choice = st.radio(
                "Monture",
                choices,
                index=choices.index(current) if current in choices else 0,
                key=f"{unit_key}_{g_key}_mount",
            )

            st.session_state.unit_selections[unit_key][g_key] = choice

            if choice != "Aucune monture":
                mount = opt_map[choice]
                mount_cost = mount["cost"]

        # ---------- OPTIONS / RÔLES ----------
        elif group.get("type") == "role" and unit.get("type") == "hero":

            choices = ["Aucun rôle"]
            opt_map = {}

            for o in group.get("options", []):
                label = f"{o['name']} (+{o['cost']} pts)"
                choices.append(label)
                opt_map[label] = o

            current = st.session_state.unit_selections[unit_key].get(g_key, choices[0])

            choice = st.radio(
                "Rôle du héros",
                choices,
                index=choices.index(current) if current in choices else 0,
                key=f"{unit_key}_{g_key}_role",
            )

            st.session_state.unit_selections[unit_key][g_key] = choice

            if choice != "Aucun rôle":
                opt = opt_map[choice]
                upgrades_cost += opt["cost"]
                selected_options[group.get("group", "Rôle")] = [opt]

        # ---------- OPTIONS NORMALES (checkbox) ----------
        else:
            for o in group.get("options", []):
                opt_key = f"{unit_key}_{g_key}_{o['name']}"
                checked = st.checkbox(
                    f"{o['name']} (+{o['cost']} pts)",
                    value=st.session_state.unit_selections[unit_key].get(opt_key, False),
                    key=opt_key,
                )
                st.session_state.unit_selections[unit_key][opt_key] = checked
                if checked:
                    upgrades_cost += o["cost"]
                    selected_options.setdefault(
                        group.get("group", "Options"), []
                    ).append(o)
    
    # ======================================================
    # EFFECTIFS & COÛT
    # ======================================================
    multiplier = (
        2
        if unit.get("type") != "hero"
        and st.checkbox("Unité combinée")
        else 1
    )

    base_cost = unit.get("base_cost", 0)
    final_cost = (
        (base_cost + weapon_cost) * multiplier
        + upgrades_cost
        + mount_cost
    )

    # ======================================================
    # AJOUT À L’ARMÉE
    # ======================================================
    if st.button("➕ Ajouter à l’armée"):

        # --- Vérification du plafond de points ---
        if st.session_state.army_cost + final_cost > st.session_state.points:
            st.error(
                f"⛔ Dépassement du format : "
                f"{st.session_state.army_cost + final_cost} / {st.session_state.points} pts"
            )
            st.stop()

        unit_data = {
            "name": unit["name"],
            "type": unit.get("type", "unit"),
            "cost": final_cost,
            "size": (
                unit.get("size", 10) * multiplier
                if unit.get("type") != "hero"
                else 1
            ),
            "quality": unit.get("quality"),
            "defense": unit.get("defense"),
            "weapon": weapons,
            "options": selected_options,
            "mount": mount,
        }

        test_army = st.session_state.army_list + [unit_data]

        if validate_army_rules(
            test_army,
            st.session_state.points,
            st.session_state.game,
        ):
            st.session_state.army_list.append(unit_data)
            st.session_state.army_cost += final_cost
            st.rerun() 
