import json
import re
from pathlib import Path
from collections import defaultdict
import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime
import hashlib
import os

# Configuration de base
def main():
    # Initialisation de la session
    if "page" not in st.session_state:
        st.session_state.page = "army"  # On commence directement sur la page de l'armée pour simplifier

    # Configuration de la page
    st.set_page_config(page_title="OPR Army Builder FR", layout="centered")

    # Règles spécifiques par jeu
    GAME_RULES = {
        "Age of Fantasy": {
            "hero_per_points": 375,
            "unit_copies": {750: 1},
            "max_unit_percentage": 35,
            "unit_per_points": 150,
        }
    }

    # Initialisation de l'état de la session
    def init_session_state():
        defaults = {
            "game": "Age of Fantasy",
            "faction": "Disciples de la Guerre",
            "points": 1000,
            "list_name": "Ma liste d'armée",
            "army_list": [],
            "army_total_cost": 0,
            "is_army_valid": True,
            "validation_errors": [],
            "units": [
                {
                    "name": "Maître de la Guerre Élu",
                    "type": "Hero",
                    "base_cost": 60,
                    "quality": 4,
                    "defense": 4,
                    "special_rules": ["Attaque versatile", "Héros", "Né pour la guerre"],
                    "weapons": [
                        {
                            "name": "Paire d'armes à une main lourdes",
                            "range": "-",
                            "attacks": 4,
                            "armor_piercing": 1
                        }
                    ],
                    "upgrade_groups": [
                        {
                            "group": "Option",
                            "type": "multiple",
                            "options": [
                                {
                                    "name": "Conquérant (Aura d'Éclaireur)",
                                    "cost": 15,
                                    "special_rules": ["Aura d'Éclaireur"]
                                },
                                {
                                    "name": "Marauder (Aura de combat imprévisible)",
                                    "cost": 10,
                                    "special_rules": ["Aura de combat imprévisible"]
                                },
                                {
                                    "name": "Manticore",
                                    "cost": 195,
                                    "mount": {
                                        "name": "Manticore",
                                        "special_rules": ["Vol", "Coriace (9)", "Peur", "Attaque mortelle"]
                                    }
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        for key, default in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = default

    init_session_state()

    def calculate_coriace_value(unit_data):
        """Calcule la valeur totale de Coriace pour une unité"""
        coriace_value = 0

        # 1. Vérifier la valeur de base de Coriace
        if 'coriace' in unit_data:
            coriace_value += unit_data['coriace']

        # 2. Vérifier dans les règles spéciales
        if 'base_rules' in unit_data:
            for rule in unit_data['base_rules']:
                if isinstance(rule, str):
                    match = re.search(r'Coriace \((\d+)\)', rule)
                    if match:
                        coriace_value += int(match.group(1))

        # 3. Vérifier dans les options
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

        # 4. Vérifier dans l'arme équipée
        if 'current_weapon' in unit_data and isinstance(unit_data['current_weapon'], dict) and 'special_rules' in unit_data['current_weapon']:
            for rule in unit_data['current_weapon']['special_rules']:
                if isinstance(rule, str):
                    match = re.search(r'Coriace \((\d+)\)', rule)
                    if match:
                        coriace_value += int(match.group(1))

        # 5. Vérifier dans la monture
        if 'mount' in unit_data and isinstance(unit_data['mount'], dict) and 'special_rules' in unit_data['mount']:
            for rule in unit_data['mount']['special_rules']:
                if isinstance(rule, str):
                    match = re.search(r'Coriace \((\d+)\)', rule)
                    if match:
                        coriace_value += int(match.group(1))

        return coriace_value

    def validate_army(army_list, game_rules, total_cost, total_points):
        errors = []

        if not army_list:
            errors.append("Aucune unité dans l'armée")
            return False, errors

        if game_rules == GAME_RULES["Age of Fantasy"]:
            heroes = sum(1 for u in army_list if u.get("type", "").lower() == "hero")
            max_heroes = max(1, total_points // game_rules["hero_per_points"])
            if heroes > max_heroes:
                errors.append(f"Trop de héros (max: {max_heroes} pour {total_points} pts)")

            unit_counts = defaultdict(int)
            for unit in army_list:
                unit_counts[unit["name"]] += 1

            max_copies = 1 + (total_points // 750)
            for unit_name, count in unit_counts.items():
                if count > max_copies:
                    errors.append(f"Trop de copies de '{unit_name}' (max: {max_copies})")

            for unit in army_list:
                percentage = (unit["cost"] / total_points) * 100
                if percentage > game_rules["max_unit_percentage"]:
                    errors.append(f"'{unit['name']}' ({unit['cost']} pts) dépasse {game_rules['max_unit_percentage']}% du total ({total_points} pts)")

            max_units = total_points // game_rules["unit_per_points"]
            if len(army_list) > max_units:
                errors.append(f"Trop d'unités (max: {max_units} pour {total_points} pts)")

        return len(errors) == 0, errors

    # PAGE 3 — Composition de l'armée
    if st.session_state.page == "army":
        st.title(st.session_state.list_name)
        st.caption(f"{st.session_state.game} — {st.session_state.faction} — {st.session_state.army_total_cost}/{st.session_state.points} pts")

        units = st.session_state.units

        # Section pour ajouter une unité
        st.divider()
        st.subheader("Ajouter une unité")

        unit = st.selectbox(
            "Unité",
            units,
            format_func=lambda u: f"{u['name']} ({u['base_cost']} pts)",
        )

        total_cost = unit["base_cost"]
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
            group_name = "Option" if group["group"] == "Remplacement de figurine" else group["group"]

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
        coriace_value = 0
        for rule in base_rules:
            match = re.search(r'Coriace \((\d+)\)', rule)
            if match:
                coriace_value += int(match.group(1))

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
                "type": unit.get("type", "Infantry")
            }

            # Calcul de la valeur totale de Coriace
            unit_data["coriace"] = calculate_coriace_value(unit_data)

            # Ajouter la monture si elle existe
            if mount_selected:
                unit_data["mount"] = mount_selected

            st.session_state.army_list.append(unit_data)
            st.session_state.army_total_cost += total_cost
            st.rerun()

        # Validation de la liste d'armée
        if st.session_state.game in GAME_RULES:
            st.session_state.is_army_valid, st.session_state.validation_errors = validate_army(
                st.session_state.army_list,
                GAME_RULES[st.session_state.game],
                st.session_state.army_total_cost,
                st.session_state.points
            )
        else:
            st.session_state.is_army_valid = True
            st.session_state.validation_errors = []

        if not st.session_state.is_army_valid:
            st.warning("⚠️ La liste d'armée n'est pas valide :")
            for error in st.session_state.validation_errors:
                st.write(f"- {error}")

        # Liste de l'armée (affichage sous forme de fiches)
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
                            # Exclure les options qui sont des changements d'armes
                            if not (isinstance(opt, dict) and 'weapon' in opt):
                                other_options.append(opt["name"])
                    else:
                        if not (isinstance(opt_group, dict) and 'weapon' in opt_group):
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

            # Bouton de suppression UNIQUEMENT en dessous
            if st.button(f"❌ Supprimer {u['name']}", key=f"del_{i}"):
                st.session_state.army_total_cost -= u["cost"]
                st.session_state.army_list.pop(i)
                st.rerun()

        # Barre de progression et boutons
        st.divider()
        progress = st.session_state.army_total_cost / st.session_state.points if st.session_state.points else 0
        st.progress(progress)
        st.markdown(f"**{st.session_state.army_total_cost} / {st.session_state.points} pts**")

if __name__ == "__main__":
    main()
