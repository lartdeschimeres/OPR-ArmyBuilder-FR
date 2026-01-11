import json
import re
import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime

# Configuration de base
def main():
    # Initialisation de la session
    if "army_list" not in st.session_state:
        st.session_state.army_list = []
    if "army_total_cost" not in st.session_state:
        st.session_state.army_total_cost = 0

    # Configuration de la page
    st.set_page_config(page_title="OPR Army Builder FR", layout="centered")
    st.title("OPR Army Builder 🇫🇷")

    # Données de faction intégrées directement
    factions_data = {
        "Disciples de la Guerre": {
            "units": [
                {
                    "name": "Maître de la Guerre Élu",
                    "type": "Hero",
                    "base_cost": 60,
                    "quality": 3,
                    "defense": 3,
                    "special_rules": ["Attaque versatile", "Héros", "Né pour la guerre"],
                    "weapons": [
                        {
                            "name": "Hallebarde lourde",
                            "range": "-",
                            "attacks": 3,
                            "armor_piercing": 1
                        }
                    ],
                    "upgrade_groups": [
                        {
                            "group": "Option",
                            "type": "multiple",
                            "options": [
                                {
                                    "name": "Marauder (Aura de combat imprévisible)",
                                    "cost": 10,
                                    "special_rules": ["Aura de combat imprévisible"]
                                },
                                {
                                    "name": "Grande bête",
                                    "cost": 100,
                                    "mount": {
                                        "name": "Grande bête",
                                        "special_rules": ["Coriace (3)", "Peur", "Mouvement rapide"]
                                    }
                                }
                            ]
                        }
                    ]
                },
                {
                    "name": "Barbares de la Guerre [10]",
                    "type": "Infantry",
                    "base_cost": 100,
                    "quality": 3,
                    "defense": 4,
                    "special_rules": ["Éclaireur", "Furieux", "Né pour la guerre"],
                    "weapons": [
                        {
                            "name": "Armes à une main",
                            "range": "-",
                            "attacks": 1,
                            "armor_piercing": 0
                        }
                    ],
                    "upgrade_groups": [
                        {
                            "group": "Remplacement d'armes",
                            "type": "weapon",
                            "options": [
                                {
                                    "name": "Lance (A1, Contre-charge)",
                                    "cost": 35,
                                    "weapon": {
                                        "name": "Lance",
                                        "range": "-",
                                        "attacks": 1,
                                        "armor_piercing": 0,
                                        "special_rules": ["Contre-charge"]
                                    }
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    }

    # Sélection de la faction
    faction_name = st.selectbox("Sélectionnez une faction", list(factions_data.keys()))
    units = factions_data[faction_name]["units"]

    # Section pour ajouter une unité
    st.divider()
    st.subheader("Ajouter une unité")

    unit = st.selectbox(
        "Unité",
        units,
        format_func=lambda u: f"{u['name']} ({u['base_cost']} pts)",
    )

    # Option pour unité combinée (uniquement pour les unités non-héros)
    combined_unit = False
    if unit.get("type", "").lower() != "hero":
        combined_unit = st.checkbox("Unité combinée (x2 effectif, coût x2 hors améliorations)", value=False)

    total_cost = unit["base_cost"]
    if combined_unit:
        total_cost = unit["base_cost"] * 2

    base_rules = list(unit.get("special_rules", []))
    options_selected = {}
    current_weapon = unit.get("weapons", [{"name": "Arme non définie", "attacks": "?", "armor_piercing": "?"}])[0]
    mount_selected = None

    # Affichage des armes de base
    st.subheader("Armes de base")
    for w in unit.get("weapons", []):
        st.write(f"- **{w.get('name', 'Arme non définie')}** | A{w.get('attacks', '?')} | PA({w.get('armor_piercing', '?')})")

    # Options standards
    for group in unit.get("upgrade_groups", []):
        group_name = group["group"]

        st.write(f"### {group_name}")
        if group.get("description"):
            st.caption(group["description"])

        if group.get("type") == "multiple":
            selected_options = []
            for opt in group["options"]:
                if st.checkbox(f"{opt['name']} (+{opt['cost']} pts)", key=f"{unit['name']}_{group['group']}_{opt['name']}"):
                    selected_options.append(opt)
                    total_cost += opt["cost"]

            if selected_options:
                options_selected[group["group"]] = selected_options
        else:
            choice = st.selectbox(
                group["group"],
                ["— Aucun —"] + [o["name"] for o in group["options"]],
                key=f"{unit['name']}_{group['group']}"
            )

            if choice != "— Aucun —":
                opt = next(o for o in group["options"] if o["name"] == choice)
                total_cost += opt.get("cost", 0)
                options_selected[group["group"]] = opt
                if group["type"] == "weapon":
                    current_weapon = opt["weapon"]
                    current_weapon["name"] = opt["name"]
                elif group["type"] == "mount":
                    mount_selected = opt.get("mount")
                    if mount_selected:
                        total_cost += mount_selected.get("cost", 0)

    def calculate_coriace_value(unit_data):
        """Calcule la valeur totale de Coriace pour une unité"""
        coriace_value = 0

        # 1. Vérifier dans les règles spéciales
        if 'base_rules' in unit_data:
            for rule in unit_data['base_rules']:
                if isinstance(rule, str):
                    match = re.search(r'Coriace \((\d+)\)', rule)
                    if match:
                        coriace_value += int(match.group(1))

        # 2. Vérifier dans les options
        if 'options' in unit_data:
            for option_group in unit_data['options'].values():
                if isinstance(option_group, list):
                    for option in option_group:
                        if isinstance(option, dict) and 'special_rules' in option:
                            for rule in option['special_rules']:
                                if isinstance(rule, str):
                                    match = re.search(r'Coriace \((\d+)\)', rule)
                                    if match:
                                        coriace_value += int(match.group(1))
                elif isinstance(option_group, dict) and 'special_rules' in option_group:
                    for rule in option_group['special_rules']:
                        if isinstance(rule, str):
                            match = re.search(r'Coriace \((\d+)\)', rule)
                            if match:
                                coriace_value += int(match.group(1))

        # 3. Vérifier dans la monture
        if 'mount' in unit_data and isinstance(unit_data['mount'], dict) and 'special_rules' in unit_data['mount']:
            for rule in unit_data['mount']['special_rules']:
                if isinstance(rule, str):
                    match = re.search(r'Coriace \((\d+)\)', rule)
                    if match:
                        coriace_value += int(match.group(1))

        return coriace_value

    # Section pour les améliorations d'unité (Sergent, Bannière, Musicien) en colonnes UNIQUEMENT pour les unités non-héros
    if unit.get("type", "").lower() != "hero":
        st.divider()
        st.subheader("Améliorations d'unité")

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.checkbox("Sergent (+5 pts)"):
                total_cost += 5
                if "Améliorations" not in options_selected:
                    options_selected["Améliorations"] = []
                options_selected["Améliorations"].append({"name": "Sergent", "cost": 5})

        with col2:
            if st.checkbox("Bannière (+5 pts)"):
                total_cost += 5
                if "Améliorations" not in options_selected:
                    options_selected["Améliorations"] = []
                options_selected["Améliorations"].append({"name": "Bannière", "cost": 5})

        with col3:
            if st.checkbox("Musicien (+10 pts)"):
                total_cost += 10
                if "Améliorations" not in options_selected:
                    options_selected["Améliorations"] = []
                options_selected["Améliorations"].append({"name": "Musicien", "cost": 10})

    # Calcul de la valeur de Coriace
    coriace_value = calculate_coriace_value({
        "base_rules": base_rules,
        "options": options_selected,
        "mount": mount_selected
    })

    st.markdown(f"### 💰 Coût : **{total_cost} pts**")
    if coriace_value > 0:
        st.markdown(f"**Coriace totale : {coriace_value}**")

    if st.button("➕ Ajouter à l'armée"):
        # Préparation des données de l'unité
        unit_data = {
            "name": unit["name"],
            "cost": total_cost,
            "quality": unit["quality"],
            "defense": unit["defense"],
            "base_rules": base_rules,
            "options": options_selected,
            "current_weapon": current_weapon,
            "type": unit.get("type", "Infantry"),
            "combined": combined_unit  # Ajout de l'information sur l'unité combinée
        }

        # Ajouter la monture si elle existe
        if mount_selected:
            unit_data["mount"] = mount_selected

        # Mise à jour du nom pour refléter l'unité combinée
        if combined_unit and "[10]" in unit_data["name"]:
            unit_data["name"] = unit_data["name"].replace("[10]", "[20]")

        st.session_state.army_list.append(unit_data)
        st.session_state.army_total_cost += total_cost
        st.rerun()

    # Liste de l'armée
    st.divider()
    st.subheader("Liste de l'armée")

    for i, u in enumerate(st.session_state.army_list):
        # Calcul de la valeur totale de Coriace
        coriace_value = calculate_coriace_value(u)

        # Génération du HTML pour la fiche
        html_content = f"""
        <style>
        .army-card {{
            border: 2px solid #4a89dc;
            border-radius: 15px;
            padding: 15px;
            margin-bottom: 20px;
            background: white;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        .unit-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }}
        .unit-name {{
            font-size: 1.2em;
            font-weight: bold;
            color: #333;
            margin: 0;
        }}
        .unit-points {{
            color: #666;
            font-size: 0.9em;
        }}
        .badges-container {{
            display: flex;
            gap: 8px;
            margin-bottom: 15px;
            flex-wrap: wrap;
        }}
        .badge {{
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 0.9em;
            font-weight: 500;
            color: white;
            text-align: center;
        }}
        .quality-badge {{
            background-color: #4a89dc;
        }}
        .defense-badge {{
            background-color: #4a89dc;
        }}
        .coriace-badge {{
            background-color: #4a89dc;
        }}
        .section {{
            margin-bottom: 12px;
        }}
        .section-title {{
            font-weight: bold;
            color: #4a89dc;
            margin-bottom: 5px;
            font-size: 0.95em;
        }}
        .section-content {{
            margin-left: 10px;
            font-size: 0.9em;
            color: #555;
        }}
        .combined-badge {{
            background-color: #28a745;
            color: white;
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 0.8em;
            margin-left: 10px;
        }}
        </style>

        <div class="army-card">
            <div class="unit-header">
                <h3 class="unit-name">{u['name']}</h3>
                <span class="unit-points">{u['cost']} pts</span>
            </div>

            <div class="badges-container">
                <span class="badge quality-badge">Qualité {u['quality']}+</span>
                <span class="badge defense-badge">Défense {u['defense']}+</span>
        """

        if coriace_value > 0:
            html_content += f'<span class="badge coriace-badge">Coriace {coriace_value}</span>'

        # Badge pour unité combinée
        if u.get("combined", False):
            html_content += '<span class="combined-badge">Unité combinée</span>'

        html_content += """
            </div>
        """

        # Règles spéciales
        if u.get("base_rules"):
            rules = [r for r in u['base_rules'] if not r.startswith("Coriace")]
            if rules:
                html_content += f"""
                <div class="section">
                    <div class="section-title">Règles spéciales</div>
                    <div class="section-content">{', '.join(rules)}</div>
                </div>
                """

        # Arme équipée
        if 'current_weapon' in u:
            weapon = u['current_weapon']
            html_content += f"""
            <div class="section">
                <div class="section-title">Arme équipée</div>
                <div class="section-content">
                    {weapon.get('name', 'Arme de base')} | A{weapon.get('attacks', '?')} | PA({weapon.get('armor_piercing', '?')})
                </div>
            </div>
            """

        # Options (sans les changements d'armes)
        other_options = []
        for group_name, opt_group in u.get("options", {}).items():
            if group_name != "Améliorations":
                if isinstance(opt_group, list):
                    for opt in opt_group:
                        if not (isinstance(opt, dict) and ('weapon' in opt or 'mount' in opt)):
                            other_options.append(opt["name"])
                else:
                    if not (isinstance(opt_group, dict) and ('weapon' in opt_group or 'mount' in opt_group)):
                        other_options.append(opt_group["name"])

        if other_options:
            html_content += f"""
            <div class="section">
                <div class="section-title">Options</div>
                <div class="section-content">{', '.join(other_options)}</div>
            </div>
            """

        # Monture (si elle existe) - Section spécifique
        if u.get("mount"):
            mount = u['mount']
            mount_rules = []
            if 'special_rules' in mount:
                mount_rules = mount['special_rules']

            html_content += f"""
            <div class="section">
                <div class="section-title">Monture</div>
                <div class="section-content">
                    <strong>{mount.get('name', '')}</strong>
            """

            if mount_rules:
                html_content += f"<br>{', '.join(mount_rules)}"

            html_content += """
                </div>
            </div>
            """

        # Améliorations (Sergent, Bannière, Musicien) UNIQUEMENT pour les unités non-héros
        if "Améliorations" in u.get("options", {}) and u.get("type", "").lower() != "hero":
            improvements = [opt["name"] for opt in u["options"]["Améliorations"]]
            if improvements:
                html_content += f"""
                <div class="section">
                    <div class="section-title">Améliorations</div>
                    <div class="section-content">{', '.join(improvements)}</div>
                </div>
                """

        html_content += "</div>"

        components.html(html_content, height=300)

        # Bouton de suppression
        if st.button(f"❌ Supprimer {u['name']}", key=f"del_{i}"):
            st.session_state.army_total_cost -= u["cost"]
            st.session_state.army_list.pop(i)
            st.rerun()

if __name__ == "__main__":
    main()
