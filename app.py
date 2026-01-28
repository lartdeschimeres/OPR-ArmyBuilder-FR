import json
import streamlit as st
from pathlib import Path
from datetime import datetime
import hashlib
import re
import math

# Initialisation de la session
if 'page' not in st.session_state:
    st.session_state.page = "setup"
if 'army_list' not in st.session_state:
    st.session_state.army_list = []
if 'army_cost' not in st.session_state:
    st.session_state.army_cost = 0

# Configuration de la page
st.set_page_config(
    page_title="OPR Army Forge FR",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS personnalisé
st.markdown("""
<style>
    .hero-role { background-color: #f0f2f6; padding: 10px; border-radius: 5px; margin-bottom: 15px; }
    .unit-option { margin: 5px 0; }
    .rule-badge { background-color: #4a4a4a; color: white; padding: 3px 8px; border-radius: 10px; margin-right: 5px; font-size: 12px; }
    .weapon-info { font-family: monospace; background-color: #f8f9fa; padding: 5px; border-radius: 3px; }
    .dark-export { background-color: #2e2e2e; color: #e0e0e0; }
</style>
""", unsafe_allow_html=True)

# ======================================================
# CONFIGURATION DES JEUX
# ======================================================
GAME_CONFIG = {
    "Age of Fantasy": {
        "max_points": 10000,
        "min_points": 250,
        "default_points": 1000,
        "hero_limit": 375,
        "unit_copy_rule": 750,
        "unit_max_cost_ratio": 0.35,
    }
}

# ======================================================
# FONCTIONS UTILITAIRES
# ======================================================
def format_weapon(weapon):
    """Formate les détails d'une arme"""
    if not weapon:
        return "Arme non spécifiée"
    details = f"{weapon.get('name', 'Arme')} (A{weapon.get('attacks', '?')}, PA{weapon.get('armor_piercing', '?')})"
    if weapon.get('special_rules'):
        details += f" | {', '.join(weapon['special_rules'])}"
    return details

def calculate_coriace(rules):
    """Calcule la valeur de coriace à partir des règles"""
    if not rules or not isinstance(rules, list):
        return 0
    total = 0
    for rule in rules:
        if isinstance(rule, str) and "Coriace" in rule:
            match = re.search(r"Coriace\s*\(?(\d+)\)?", rule)
            if match:
                total += int(match.group(1))
    return total

# ======================================================
# CHARGEMENT DES FACTIONS (exemple simplifié)
# ======================================================
def load_factions():
    return {
        "Age of Fantasy": {
            "Disciples de la Guerre": {
                "units": [
                    {
                        "name": "Maître de la Guerre Élu",
                        "type": "hero",
                        "size": 1,
                        "base_cost": 150,
                        "quality": 3,
                        "defense": 5,
                        "special_rules": ["Héros", "Éclaireur", "Furieux"],
                        "weapons": [{"name": "Arme héroïque", "attacks": 2, "armor_piercing": 1, "special_rules": ["Magique(1)"]}],
                        "upgrade_groups": [
                            {
                                "group": "Améliorations de rôle",
                                "type": "role_upgrades",
                                "options": [
                                    {"name": "Conquérant", "cost": 20, "special_rules": ["Aura d'Éclaireur"]},
                                    {"name": "Maraudeur", "cost": 30, "special_rules": ["Aura de Combatant imprévisible"]},
                                    {"name": "Porteur de la bannière", "cost": 30, "special_rules": ["Effrayant(3)"]},
                                    {"name": "Ensorceleur", "cost": 35, "special_rules": ["Aura de Voile fluctuant"]},
                                    {"name": "Seigneur de Guerre", "cost": 35, "special_rules": ["Aura de Boost de Guerrier-né"]},
                                    {"name": "Sorcier", "cost": 40, "special_rules": ["Lanceur de sorts(2)"]},
                                    {"name": "Maître Sorcier", "cost": 60, "special_rules": ["Lanceur de sorts(3)"]}
                                ]
                            }
                        ]
                    },
                    {
                        "name": "Barbares de la Guerre",
                        "type": "unit",
                        "size": 10,
                        "base_cost": 50,
                        "quality": 3,
                        "defense": 5,
                        "special_rules": ["Éclaireur", "Furieux"],
                        "weapons": [{"name": "Armes à une main", "attacks": 1, "armor_piercing": 0}],
                        "upgrade_groups": [
                            {
                                "group": "Améliorations d'unité",
                                "type": "unit_upgrades",
                                "options": [
                                    {"name": "Icône du Ravage", "cost": 20},
                                    {"name": "Sergent", "cost": 5},
                                    {"name": "Bannière", "cost": 5},
                                    {"name": "Musicien", "cost": 10}
                                ]
                            }
                        ]
                    }
                ]
            }
        }
    }

# ======================================================
# PAGE DE CONFIGURATION
# ======================================================
def setup_page():
    st.title("OPR Army Forge")
    st.subheader("Configuration de la liste d'armée")

    factions = load_factions()
    game = st.selectbox("Jeu", list(GAME_CONFIG.keys()))
    faction = st.selectbox("Faction", list(factions[game].keys()))
    points = st.number_input(
        "Points",
        min_value=GAME_CONFIG[game]["min_points"],
        max_value=GAME_CONFIG[game]["max_points"],
        value=GAME_CONFIG[game]["default_points"]
    )
    list_name = st.text_input("Nom de la liste", "Ma Liste")

    if st.button("Créer une nouvelle liste"):
        st.session_state.game = game
        st.session_state.faction = faction
        st.session_state.points = points
        st.session_state.list_name = list_name
        st.session_state.units = factions[game][faction]["units"]
        st.session_state.page = "army"
        st.rerun()

# ======================================================
# PAGE DE CONSTRUCTION D'ARMÉE
# ======================================================
def army_page():
    st.markdown(f"""
    <div style='background-color: #f0f2f6; padding: 10px; border-radius: 5px;'>
        <h2>{st.session_state.list_name}</h2>
        <p>{st.session_state.army_cost}/{st.session_state.points} pts</p>
    </div>
    """, unsafe_allow_html=True)

    if st.button("⬅ Retour à la configuration"):
        st.session_state.page = "setup"
        st.rerun()

    # Sélection de l'unité
    unit = st.selectbox(
        "Unité disponible",
        st.session_state.units,
        format_func=lambda u: f"{u['name']} [{u.get('size', 1)}] - {u['base_cost']} pts",
        key="unit_select"
    )

    # Initialisation des variables
    selected_options = {}
    weapon = unit.get("weapons", [{}])[0]
    mount = None
    upgrades_cost = 0

    # Section Armes
    if unit.get("weapons"):
        st.subheader("Armes")
        weapon_options = [format_weapon(w) for w in unit["weapons"]]
        selected_weapon = st.selectbox(
            "Choisir une arme",
            weapon_options,
            index=0,
            key=f"{unit['name']}_weapon"
        )
        weapon = unit["weapons"][weapon_options.index(selected_weapon)]

    # Section Améliorations
    if "upgrade_groups" in unit:
        for group in unit["upgrade_groups"]:
            st.subheader(group["group"])

            if unit.get("type") == "hero" and group["type"] == "role_upgrades":
                # Pour les héros: boutons radio (choix unique)
                option_names = ["Aucune amélioration"] + [
                    f"{o['name']} (+{o['cost']} pts)"
                    for o in group["options"]
                ]
                selected_option = st.radio(
                    "Choisir une amélioration de rôle",
                    option_names,
                    key=f"{unit['name']}_{group['group']}"
                )

                if selected_option != "Aucune amélioration":
                    opt_name = selected_option.split(" (+")[0]
                    opt = next(o for o in group["options"] if o["name"] == opt_name)
                    selected_options[group["group"]] = [opt]
                    upgrades_cost += opt["cost"]
            else:
                # Pour les unités: cases à cocher (choix multiples)
                st.write("Sélectionnez les améliorations (plusieurs choix possibles):")
                for o in group["options"]:
                    if st.checkbox(
                        f"{o['name']} (+{o['cost']} pts)",
                        key=f"{unit['name']}_{group['group']}_{o['name']}"
                    ):
                        if group["group"] not in selected_options:
                            selected_options[group["group"]] = []
                        if not any(opt.get("name") == o["name"] for opt in selected_options.get(group["group"], [])):
                            selected_options[group["group"]].append(o)
                            upgrades_cost += o["cost"]

    # Calcul du coût final
    final_cost = unit["base_cost"] + upgrades_cost

    # Affichage des informations
    st.markdown(f"**Effectif final:** [{unit.get('size', 1)}]")
    st.markdown(f"**Coût total:** {final_cost} pts")

    if st.button("Ajouter à l'armée"):
        unit_data = {
            "name": unit["name"],
            "type": unit.get("type", "unit"),
            "cost": final_cost,
            "size": unit.get("size", 1),
            "quality": unit["quality"],
            "defense": unit["defense"],
            "rules": unit.get("special_rules", []),
            "weapon": weapon,
            "options": selected_options,
            "coriace": calculate_coriace(unit.get("special_rules", []))
        }

        st.session_state.army_list.append(unit_data)
        st.session_state.army_cost += final_cost
        st.rerun()

    # Affichage de la liste d'armée
    st.subheader("Liste de l'armée")
    if not st.session_state.army_list:
        st.info("Ajoutez des unités pour commencer")

    for i, u in enumerate(st.session_state.army_list):
        with st.container():
            st.markdown(f"### {u['name']} [{u['size']}] ({u['cost']} pts)")
            st.markdown(f"**Qualité:** {u['quality']}+ | **Défense:** {u['defense']}+")

            if u.get("rules"):
                rules = ", ".join([f"<span class='rule-badge'>{r}</span>" for r in u["rules"]])
                st.markdown(f"**Règles spéciales:** {rules}", unsafe_allow_html=True)

            if u.get("weapon"):
                st.markdown(f"**Arme:** <span class='weapon-info'>{format_weapon(u['weapon'])}</span>",
                           unsafe_allow_html=True)

            if u.get("options"):
                for group_name, opts in u["options"].items():
                    st.markdown(f"**{group_name}:**")
                    for opt in opts:
                        st.markdown(f"• {opt.get('name', '')}")

            if st.button(f"Supprimer {u['name']}", key=f"del_{i}"):
                st.session_state.army_cost -= u["cost"]
                st.session_state.army_list.pop(i)
                st.rerun()

# ======================================================
# EXPORT HTML (couleurs foncées)
# ======================================================
def export_to_html(army_list, army_name):
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{army_name} - Liste d'Armée</title>
        <style>
            body {{
                background-color: #2e2e2e;
                color: #e0e0e0;
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 20px;
            }}
            .army-container {{
                max-width: 800px;
                margin: 0 auto;
                background-color: #3a3a3a;
                padding: 20px;
                border-radius: 10px;
            }}
            .unit-card {{
                background-color: #4a4a4a;
                margin-bottom: 20px;
                padding: 15px;
                border-radius: 5px;
                border: 1px solid #666;
            }}
            .unit-header {{
                display: flex;
                justify-content: space-between;
                margin-bottom: 10px;
                padding-bottom: 10px;
                border-bottom: 1px solid #666;
            }}
            .rule-badge {{
                background-color: #5a5a5a;
                color: white;
                padding: 3px 8px;
                border-radius: 10px;
                margin-right: 5px;
                font-size: 12px;
            }}
            .weapon-info {{
                font-family: monospace;
                background-color: #3a3a3a;
                padding: 5px;
                border-radius: 3px;
                display: inline-block;
            }}
        </style>
    </head>
    <body>
        <div class="army-container">
            <h1 style="text-align: center; color: #ff9500;">{army_name}</h1>
            <h2 style="text-align: center; color: #aaa;">Total: {sum(u['cost'] for u in army_list)} pts</h2>
    """

    for unit in army_list:
        html += f"""
            <div class="unit-card">
                <div class="unit-header">
                    <h3 style="margin: 0; color: #ff9500;">{unit['name']} [{unit['size']}]</h3>
                    <span>{unit['cost']} pts</span>
                </div>
                <p><strong>Qualité:</strong> {unit['quality']}+ | <strong>Défense:</strong> {unit['defense']}+</p>
        """

        if unit.get("rules"):
            rules = " ".join(f'<span class="rule-badge">{r}</span>' for r in unit["rules"])
            html += f"<p><strong>Règles spéciales:</strong> {rules}</p>"

        if unit.get("weapon"):
            html += f"<p><strong>Arme:</strong> <span class='weapon-info'>{format_weapon(unit['weapon'])}</span></p>"

        if unit.get("options"):
            for group_name, opts in unit["options"].items():
                html += f"<p><strong>{group_name}:</strong> {', '.join(o['name'] for o in opts)}</p>"

        html += "</div>"

    html += """
        </div>
    </body>
    </html>
    """
    return html

# ======================================================
# POINT D'ENTRÉE
# ======================================================
def main():
    if st.session_state.page == "setup":
        setup_page()
    elif st.session_state.page == "army":
        army_page()

    # Bouton d'export (visible uniquement en page army)
    if st.session_state.page == "army" and st.session_state.army_list:
        st.divider()
        html_content = export_to_html(st.session_state.army_list, st.session_state.list_name)
        st.download_button(
            label="📄 Exporter en HTML (couleurs foncées)",
            data=html_content,
            file_name=f"{st.session_state.list_name}.html",
            mime="text/html"
        )

if __name__ == "__main__":
    main()
