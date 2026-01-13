import streamlit as st
import re
from copy import deepcopy

st.set_page_config(page_title="OPR Army Forge FR", layout="wide")

# --------------------------------------------------
# UTILITAIRES
# --------------------------------------------------

def extract_coriace(rules):
    """Extrait la valeur Coriace depuis une liste de règles"""
    total = 0
    for r in rules:
        m = re.search(r"Coriace\s*\(?\+?(\d+)\)?", r)
        if m:
            total += int(m.group(1))
    return total


def format_rules(rules):
    return ", ".join(sorted(set(rules))) if rules else "Aucune"


# --------------------------------------------------
# DONNÉES EXEMPLE (à remplacer par JSON faction)
# --------------------------------------------------

UNIT_TEMPLATE = {
    "name": "Maître de la Guerre Élu",
    "type": "Hero",
    "base_cost": 60,
    "quality": 4,
    "defense": 4,
    "base_rules": [
        "Héros",
        "Né pour la guerre",
        "Coriace (3)"
    ],
    "weapons": [
        {"name": "Arme lourde", "attacks": 3, "ap": 1}
    ],
    "option_groups": {
        "role": [
            {"name": "Seigneur de Guerre", "cost": 35},
            {"name": "Conquérant", "cost": 20}
        ],
        "mount": [
            {
                "name": "Dragon du Ravage",
                "cost": 320,
                "rules": [
                    "Coriace (+12)",
                    "Volant",
                    "Effrayant (2)"
                ]
            }
        ]
    }
}


# --------------------------------------------------
# SESSION STATE
# --------------------------------------------------

if "army" not in st.session_state:
    st.session_state.army = []

if "current_unit" not in st.session_state:
    st.session_state.current_unit = None


# --------------------------------------------------
# INTERFACE
# --------------------------------------------------

st.title("🔥 OPR Army Forge – FR")

col_left, col_right = st.columns([1, 2])

# --------------------------------------------------
# AJOUT D’UNITÉ
# --------------------------------------------------

with col_left:
    st.header("Ajouter une unité")

    unit = deepcopy(UNIT_TEMPLATE)

    st.subheader(unit["name"])

    # Sélecteurs d’options
    selected_options = []
    selected_mount = None
    extra_cost = 0

    for group, options in unit["option_groups"].items():
        names = ["Aucune"] + [o["name"] for o in options]
        choice = st.selectbox(group.capitalize(), names, key=group)

        if choice != "Aucune":
            opt = next(o for o in options if o["name"] == choice)
            extra_cost += opt["cost"]

            if group == "mount":
                selected_mount = opt
            else:
                selected_options.append(opt)

    total_cost = unit["base_cost"] + extra_cost

    if st.button("Ajouter à l'armée"):
        st.session_state.army.append({
            "profile": unit,
            "options": selected_options,
            "mount": selected_mount,
            "cost": total_cost
        })


# --------------------------------------------------
# LISTE DE L’ARMÉE
# --------------------------------------------------

with col_right:
    st.header("📜 Liste de l’armée")

    if not st.session_state.army:
        st.info("Aucune unité ajoutée.")
    else:
        for i, u in enumerate(st.session_state.army):
            profile = u["profile"]

            with st.container(border=True):
                cols = st.columns([3, 1])

                # -------------------------------
                # PROFIL
                # -------------------------------
                with cols[0]:
                    st.subheader(profile["name"])

                    q_col, d_col, c_col = st.columns(3)

                    with q_col:
                        st.metric("Qualité", f"{profile['quality']}+")

                    with d_col:
                        st.metric("Défense", f"{profile['defense']}+")

                    # Coriace total
                    base_coriace = extract_coriace(profile["base_rules"])
                    mount_coriace = extract_coriace(u["mount"]["rules"]) if u["mount"] else 0
                    total_coriace = base_coriace + mount_coriace

                    with c_col:
                        st.metric("Coriace total", total_coriace)

                    # RÈGLES SPÉCIALES (BASE UNIQUEMENT)
                    st.markdown("**Règles spéciales**")
                    st.caption(format_rules(profile["base_rules"]))

                    # OPTIONS SÉLECTIONNÉES
                    if u["options"]:
                        st.markdown("**Options sélectionnées**")
                        st.caption(", ".join(opt["name"] for opt in u["options"]))

                    # MONTURE
                    if u["mount"]:
                        st.markdown("**Monture**")
                        st.caption(
                            f"{u['mount']['name']} — "
                            + format_rules(u["mount"]["rules"])
                        )

                # -------------------------------
                # COÛT & SUPPRESSION
                # -------------------------------
                with cols[1]:
                    st.metric("Coût", u["cost"])
                    if st.button("🗑 Supprimer", key=f"del_{i}"):
                        st.session_state.army.pop(i)
                        st.rerun()
