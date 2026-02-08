import json
import streamlit as st
from pathlib import Path
from datetime import datetime
import re
import math

# ======================================================
# CSS global
# ======================================================
st.markdown("""
<style>

/* --- Nettoyage Streamlit --- */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* --- Fond général --- */
.stApp {
    background: radial-gradient(circle at top, #1b1f2a, #0e1016);
    color: #e6e6e6;
}

/* --- Titres --- */
h1, h2, h3 {
    letter-spacing: 0.04em;
}

/* --- Cartes --- */
.card {
    background: linear-gradient(180deg, #23283a, #191d2b);
    border: 1px solid #303650;
    border-radius: 16px;
    padding: 1.5rem;
    transition: all 0.25s ease;
}

/* --- Inputs visibles --- */
div[data-baseweb="select"] > div,
div[data-baseweb="input"] input,
div[data-baseweb="base-input"] input {
    background-color: #f3f4f6 !important;
    color: #111827 !important;
    border-radius: 10px !important;
    font-weight: 500;
}

/* --- Bouton principal --- */
button[kind="primary"] {
    background: linear-gradient(135deg, #4da6ff, #2563eb) !important;
    color: white !important;
    font-weight: 600 !important;
    border-radius: 12px !important;
}

/* --- Texte secondaire --- */
.muted {
    color: #9aa4bf;
    font-size: 0.9rem;
}

/* --- Badge --- */
.badge {
    display: inline-block;
    padding: 0.2rem 0.6rem;
    border-radius: 8px;
    background: #2a3042;
    font-size: 0.75rem;
    margin-bottom: 0.6rem;
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
# SIDEBAR
# ======================================================
with st.sidebar:
    st.title("🛡️ Army Forge")
    st.markdown(f"**Jeu :** {st.session_state.get('game','—')}")
    st.markdown(f"**Faction :** {st.session_state.get('faction','—')}")
    st.markdown(f"**Format :** {st.session_state.get('points',0)} pts")

# ======================================================
# CONFIG DES JEUX
# ======================================================
GAME_CONFIG = {
    "Age of Fantasy": {"hero_limit": 375, "unit_copy_rule": 750, "unit_max_cost_ratio": 0.35, "unit_per_points": 150},
    "Grimdark Future": {"hero_limit": 375, "unit_copy_rule": 750, "unit_max_cost_ratio": 0.35, "unit_per_points": 150},
}

# ======================================================
# FONCTIONS UTILITAIRES
# ======================================================
def export_army_json():
    return {
        "game": st.session_state.game,
        "faction": st.session_state.faction,
        "points": st.session_state.points,
        "list_name": st.session_state.list_name,
        "army_cost": st.session_state.army_cost,
        "army_list": st.session_state.army_list,
        "exported_at": datetime.now().isoformat(),
    }


def export_army_html():
    html = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <title>{st.session_state.list_name}</title>
        <style>
            body {{
                background: #0e1016;
                color: #e6e6e6;
                font-family: Arial, sans-serif;
            }}
            h1 {{ color: #4da6ff; }}
            .unit {{
                border: 1px solid #2a3042;
                border-radius: 10px;
                padding: 10px;
                margin-bottom: 10px;
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
            Coût : {u['cost']} pts
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
    base = Path(__file__).resolve().parent / "lists" / "data" / "factions"
    for fp in base.glob("*.json"):
        with open(fp, encoding="utf-8") as f:
            data = json.load(f)
            factions.setdefault(data["game"], {})[data["faction"]] = data
            games.add(data["game"])
    return factions, sorted(games)

# ======================================================
# PAGE SETUP
# ======================================================
if st.session_state.page == "setup":

    st.markdown("## 🛡️ OPR Army Forge")
    st.markdown("<p class='muted'>Forgez vos armées One Page Rules.</p>", unsafe_allow_html=True)

    factions_by_game, games = load_factions()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("<div class='card'><span class='badge'>Jeu</span>", unsafe_allow_html=True)
        game = st.selectbox("", games, label_visibility="collapsed")
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown("<div class='card'><span class='badge'>Faction</span>", unsafe_allow_html=True)
        faction = st.selectbox("", factions_by_game[game].keys(), label_visibility="collapsed")
        st.markdown("</div>", unsafe_allow_html=True)

    with col3:
        st.markdown("<div class='card'><span class='badge'>Format</span>", unsafe_allow_html=True)
        points = st.number_input("", 250, 10000, 1000, 250, label_visibility="collapsed")
        st.markdown("</div>", unsafe_allow_html=True)

    colA, colB = st.columns([2,1])
    with colA:
        st.markdown("<div class='card'><span class='badge'>Liste</span>", unsafe_allow_html=True)
        list_name = st.text_input("", f"Liste_{datetime.now().strftime('%Y%m%d')}", label_visibility="collapsed")
        st.markdown("</div>", unsafe_allow_html=True)

    with colB:
        st.markdown("<div class='card'><span class='badge'>Action</span>", unsafe_allow_html=True)
        if st.button("🔥 Construire l’armée", use_container_width=True, type="primary"):
            st.session_state.update({
                "game": game,
                "faction": faction,
                "points": points,
                "list_name": list_name,
                "units": factions_by_game[game][faction]["units"],
                "faction_rules": factions_by_game[game][faction].get("special_rules", []),
                "faction_spells": factions_by_game[game][faction].get("spells", []),
                "army_list": [],
                "army_cost": 0,
                "page": "army"
            })
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
        
    col_exp1, col_exp2 = st.columns(2)

    with col_exp1:
        st.download_button(
            "📄 Export JSON",
            data=json.dumps(
                export_army_json(),
                indent=2,
                ensure_ascii=False
            ),
            file_name=f"{st.session_state.list_name}.json",
            mime="application/json",
        )

    with col_exp2:
        st.download_button(
            "🌐 Export HTML",
            data=export_army_html(),
            file_name=f"{st.session_state.list_name}.html",
            mime="text/html",
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

        # ---------- OPTIONS ----------
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
