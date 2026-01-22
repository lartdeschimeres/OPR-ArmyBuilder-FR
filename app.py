import json
import streamlit as st
from pathlib import Path
from datetime import datetime
import hashlib
import re
import base64
import math

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
# CONFIGURATION DES JEUX ET LEURS LIMITATIONS
# ======================================================
GAME_CONFIG = {
    "Age of Fantasy": {
        "display_name": "Age of Fantasy",
        "max_points": 10000,
        "min_points": 250,
        "default_points": 1000,
        "point_step": 250,
        "description": "Jeu de bataille rangée dans un univers fantasy médiéval",
        "hero_limit": 375,  # 1 Héros par tranche de 375 pts
        "unit_copy_rule": 750,  # 1+X copies où X=1 pour 750 pts
        "unit_max_cost_ratio": 0.35,  # 35% du total des points
        "unit_per_points": 150  # 1 unité maximum par tranche de 150 pts
    },
    "Grimdark Future": {
        "display_name": "Grimdark Future",
        "max_points": 10000,
        "min_points": 200,
        "default_points": 800,
        "point_step": 200,
        "description": "Jeu de bataille futuriste avec unités mécanisées",
        "hero_limit": 400,
        "unit_copy_rule": 800,
        "unit_max_cost_ratio": 0.40,
        "unit_per_points": 160
    }
}

# ======================================================
# FONCTIONS POUR LES RÈGLES SPÉCIFIQUES
# ======================================================
def check_hero_limit(army_list, army_points, game_config):
    """Vérifie la limite de héros"""
    if game_config.get("hero_limit"):
        max_heroes = math.floor(army_points / game_config["hero_limit"])
        hero_count = sum(1 for unit in army_list if unit.get("type") == "hero")

        if hero_count > max_heroes:
            st.error(f"Limite de héros dépassée! Maximum autorisé: {max_heroes} (1 héros par {game_config['hero_limit']} pts)")
            return False
    return True

# ... [les autres fonctions restent inchangées] ...

# ======================================================
# PAGE 2 – CONSTRUCTEUR D'ARMÉE (version corrigée)
# ======================================================
elif st.session_state.page == "army":
    st.title(st.session_state.list_name)
    st.caption(f"{st.session_state.game} • {st.session_state.faction} • {st.session_state.army_cost}/{st.session_state.points} pts")

    # Vérification des règles spécifiques au jeu
    game_config = GAME_CONFIG.get(st.session_state.game, GAME_CONFIG["Age of Fantasy"])

    if not validate_army_rules(st.session_state.army_list, st.session_state.points, st.session_state.game):
        st.warning("⚠️ Certaines règles spécifiques ne sont pas respectées. Voir les messages d'erreur ci-dessus.")

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

    # Récupération de la taille de base de l'unité
    base_size = unit.get('size', 10)
    base_cost = unit["base_cost"]

    # Vérification du coût maximum AVANT les améliorations
    max_cost = st.session_state.points * game_config["unit_max_cost_ratio"]
    if unit["base_cost"] > max_cost:
        st.error(f"Cette unité ({unit['base_cost']} pts) dépasse la limite de {int(max_cost)} pts ({int(game_config['unit_max_cost_ratio']*100)}% du total)")
        st.stop()

    # Initialisation
    weapon = unit.get("weapons", [{}])[0]
    selected_options = {}
    mount = None
    weapon_cost = 0
    mount_cost = 0
    upgrades_cost = 0

    # Gestion des unités combinées - CORRECTION POUR LES HÉROS
    if unit.get("type") == "hero":
        combined = False  # Les héros ne peuvent JAMAIS être combinés
        st.markdown("**Les héros ne peuvent pas être combinés**")
    else:
        combined = st.checkbox("Unité combinée", value=False)

    # Options de l'unité
    for group in unit.get("upgrade_groups", []):
        st.markdown(f"**{group['group']}**")

        if group["type"] == "weapon":
            weapon_options = ["Arme de base"]
            for o in group["options"]:
                weapon_details = format_weapon_details(o["weapon"])
                cost_diff = o["cost"]
                weapon_options.append(f"{o['name']} (A{weapon_details['attacks']}, PA({weapon_details['ap']}){', ' + ', '.join(weapon_details['special']) if weapon_details['special'] else ''}) (+{cost_diff} pts)")

            selected_weapon = st.radio("Arme", weapon_options, key=f"{unit['name']}_weapon")
            if selected_weapon != "Arme de base":
                opt_name = selected_weapon.split(" (")[0]
                opt = next((o for o in group["options"] if o["name"] == opt_name), None)
                if opt:
                    weapon = opt["weapon"]
                    weapon_cost = opt["cost"]

        elif group["type"] == "mount":
            mount_labels = ["Aucune monture"]
            mount_map = {}

            for o in group["options"]:
                mount_details = format_mount_details(o)
                label = f"{mount_details} (+{o['cost']} pts)"
                mount_labels.append(label)
                mount_map[label] = o

            selected_mount = st.radio("Monture", mount_labels, key=f"{unit['name']}_mount")

            if selected_mount != "Aucune monture":
                opt = mount_map[selected_mount]
                mount = opt
                mount_cost = opt["cost"]

        else:  # Améliorations d'unité
            if group["group"] == "Améliorations de rôle":
                option_names = ["Aucune"] + [
                    f"{o['name']} (+{o['cost']} pts)" for o in group["options"]
                ]
                selected = st.radio(group["group"], option_names, key=f"{unit['name']}_{group['group']}")
                if selected != "Aucune":
                    opt_name = selected.split(" (+")[0]
                    opt = next((o for o in group["options"] if o["name"] == opt_name), None)
                    if opt:
                        if group["group"] not in selected_options:
                            selected_options[group["group"]] = []
                        selected_options[group["group"]].append(opt)
                        upgrades_cost += opt["cost"]
            else:
                st.write("Sélectionnez les améliorations (plusieurs choix possibles):")
                for o in group["options"]:
                    if st.checkbox(f"{o['name']} (+{o['cost']} pts)", key=f"{unit['name']}_{group['group']}_{o['name']}"):
                        if group["group"] not in selected_options:
                            selected_options[group["group"]] = []
                        if not any(opt.get("name") == o["name"] for opt in selected_options.get(group["group"], [])):
                            selected_options[group["group"]].append(o)
                            upgrades_cost += o["cost"]

    # Calcul du coût final
    if combined and unit.get("type") != "hero":
        # Pour les unités combinées, on double le coût de base + armes seulement
        final_cost = (base_cost + weapon_cost) * 2 + mount_cost + upgrades_cost
        unit_size = base_size * 2
    else:
        final_cost = base_cost + weapon_cost + mount_cost + upgrades_cost
        unit_size = base_size

    # Vérification finale du coût maximum
    if not check_unit_max_cost(st.session_state.army_list, st.session_state.points, game_config, final_cost):
        st.stop()

    st.markdown(f"**Coût total: {final_cost} pts**")
    st.markdown(f"**Taille de l'unité: {unit_size} figurines**")

    if st.button("Ajouter à l'armée"):
        try:
            weapon_data = format_weapon_details(weapon)

            # Calcul de la coriace
            total_coriace = 0
            if 'special_rules' in unit and isinstance(unit.get('special_rules'), list):
                total_coriace += get_coriace_from_rules(unit['special_rules'])
            if mount:
                _, mount_coriace = get_mount_details(mount)
                total_coriace += mount_coriace
            if selected_options:
                for opts in selected_options.values():
                    if isinstance(opts, list):
                        for opt in opts:
                            if 'special_rules' in opt and isinstance(opt.get('special_rules'), list):
                                total_coriace += get_coriace_from_rules(opt['special_rules'])
            if 'special_rules' in weapon and isinstance(weapon.get('special_rules'), list):
                total_coriace += get_coriace_from_rules(weapon['special_rules'])
            if combined and unit.get('type') != "hero":
                base_coriace = get_coriace_from_rules(unit.get('special_rules', []))
                total_coriace += base_coriace

            total_coriace = total_coriace if total_coriace > 0 else None

            unit_data = {
                "name": unit["name"],
                "type": unit.get("type", "unit"),
                "cost": final_cost,
                "base_cost": base_cost,
                "size": unit_size,  # Taille finale
                "quality": unit["quality"],
                "defense": unit["defense"],
                "rules": [format_special_rule(r) for r in unit.get("special_rules", [])],
                "weapon": weapon_data,
                "options": selected_options,
                "mount": mount,
                "coriace": total_coriace,
                "combined": combined and unit.get("type") != "hero",  # On ne marque pas les héros comme combinés
            }

            # Vérification des règles avant d'ajouter
            test_army = st.session_state.army_list.copy()
            test_army.append(unit_data)
            test_total = st.session_state.army_cost + final_cost

            if not validate_army_rules(test_army, st.session_state.points, st.session_state.game, final_cost):
                st.error("Cette unité ne peut pas être ajoutée car elle violerait les règles du jeu.")
            else:
                st.session_state.army_list.append(unit_data)
                st.session_state.army_cost += final_cost
                st.rerun()

        except Exception as e:
            st.error(f"Erreur lors de la création de l'unité: {str(e)}")

    # Liste de l'armée
    st.divider()
    st.subheader("Liste de l'armée")

    if not st.session_state.army_list:
        st.info("Ajoutez des unités pour commencer")

    for i, u in enumerate(st.session_state.army_list):
        with st.container():
            qua_def_coriace = f"Qua {u['quality']}+ / Déf {u['defense']}+"
            if u.get("coriace"):
                qua_def_coriace += f" / Coriace {u['coriace']}"

            # Affichage du nom avec la taille FINAL de l'unité
            unit_header = f"### {u['name']} [{u.get('size', 10)}] ({u['cost']} pts) | {qua_def_coriace}"
            if u.get("type") == "hero":
                unit_header += " | 🌟 Héros"
            st.markdown(unit_header)

            if u.get("rules"):
                rules_text = ", ".join(u["rules"])
                st.markdown(f"**Règles spéciales:** {rules_text}")

            if 'weapon' in u and u['weapon']:
                weapon_details = format_weapon_details(u['weapon'])
                st.markdown(f"**Arme:** {weapon_details['name']} (A{weapon_details['attacks']}, PA({weapon_details['ap']}){', ' + ', '.join(weapon_details['special']) if weapon_details['special'] else ''})")

            if u.get("options"):
                for group_name, opts in u["options"].items():
                    if isinstance(opts, list) and opts:
                        st.markdown(f"**{group_name}:**")
                        for opt in opts:
                            st.markdown(f"• {opt.get('name', '')}")

            if u.get("mount"):
                mount_details = format_mount_details(u["mount"])
                st.markdown(f"**Monture:** {mount_details}")

            if st.button(f"Supprimer {u['name']}", key=f"del_{i}"):
                st.session_state.army_cost -= u["cost"]
                st.session_state.army_list.pop(i)
                st.rerun()

    # Sauvegarde/Export
    st.divider()
    col1, col2, col3 = st.columns(3)

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
            "Exporter en JSON",
            json.dumps(army_data, indent=2, ensure_ascii=False),
            file_name=f"{st.session_state.list_name}.json",
            mime="application/json"
        )

    with col3:
        # EXPORT HTML
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Liste OPR - {army_data['name']}</title>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 20px;
            color: #333;
        }}
        .army-title {{
            text-align: center;
            margin-bottom: 20px;
            color: #2c3e50;
        }}
        .army-info {{
            text-align: center;
            margin-bottom: 30px;
            color: #666;
        }}
        .unit-container {{
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 20px;
            padding: 20px;
            page-break-inside: avoid;
        }}
        .unit-header {{
            font-size: 1.5em;
            font-weight: bold;
            margin-bottom: 10px;
            color: #2c3e50;
            border-bottom: 1px solid #eee;
            padding-bottom: 10px;
        }}
        .hero-badge {{
            background-color: gold;
            color: black;
            padding: 2px 8px;
            border-radius: 10px;
            margin-left: 10px;
            font-weight: bold;
            font-size: 0.9em;
        }}
        .unit-stats {{
            display: flex;
            margin-bottom: 15px;
        }}
        .stat-badge {{
            background-color: #3498db;
            color: white;
            padding: 8px 12px;
            border-radius: 4px;
            margin-right: 10px;
            font-weight: bold;
            text-align: center;
            min-width: 80px;
        }}
        .stat-value {{
            font-size: 1.2em;
        }}
        .stat-label {{
            font-size: 0.8em;
            display: block;
            margin-bottom: 3px;
        }}
        .section-title {{
            font-weight: bold;
            margin: 15px 0 10px 0;
            color: #2c3e50;
            border-bottom: 1px solid #eee;
            padding-bottom: 5px;
        }}
        .weapon-table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 15px;
        }}
        .weapon-table th {{
            background-color: #f8f9fa;
            text-align: left;
            padding: 8px;
            border-bottom: 1px solid #ddd;
        }}
        .weapon-table td {{
            padding: 8px;
            border-bottom: 1px solid #eee;
        }}
        .rules-list {{
            margin: 10px 0;
        }}
        .special-rules {{
            font-style: italic;
            color: #555;
            margin-bottom: 15px;
        }}
        .unit-cost {{
            float: right;
            background-color: #3498db;
            color: white;
            padding: 5px 10px;
            border-radius: 4px;
            font-weight: bold;
        }}
        @media print {{
            .unit-container {{
                page-break-inside: avoid;
            }}
        }}
    </style>
</head>
<body>
    <h1 class="army-title">Liste d'armée OPR - {army_data['name']}</h1>
    <div class="army-info">
        <strong>Jeu:</strong> {army_data['game']} |
        <strong>Faction:</strong> {army_data['faction']} |
        <strong>Points:</strong> {army_data['total_cost']}/{army_data['points']}
    </div>
"""

        for unit in army_data['army_list']:
            rules = unit.get('rules', [])
            special_rules = ", ".join(rules) if rules else "Aucune"

            weapon_info = unit.get('weapon', {})
            if not isinstance(weapon_info, dict):
                weapon_info = {
                    "name": "Arme non spécifiée",
                    "attacks": "?",
                    "ap": "?",
                    "special": []
                }

            # Affichage du nom avec la taille FINAL de l'unité
            unit_name = f"{unit['name']} [{unit.get('size', 10)}]"
            unit_name = str(unit_name).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

            weapon_name = str(weapon_info['name']).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            weapon_attacks = str(weapon_info['attacks']).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            weapon_ap = str(weapon_info['ap']).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            weapon_special = ', '.join(weapon_info['special']) if weapon_info['special'] else '-'
            weapon_special = str(weapon_special).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

            # Badge héros si applicable
            hero_badge = ""
            if unit.get('type') == "hero":
                hero_badge = '<span class="hero-badge">HÉROS</span>'

            html_content += f"""
        <div class="unit-container">
            <div class="unit-header">
                {unit_name}
                {hero_badge}
                <span class="unit-cost">{unit['cost']} pts</span>
            </div>

            <div class="unit-stats">
                <div class="stat-badge">
                    <div class="stat-label">Qualité</div>
                    <div class="stat-value">{unit['quality']}+</div>
                </div>
                <div class="stat-badge">
                    <div class="stat-label">Défense</div>
                    <div class="stat-value">{unit['defense']}+</div>
                </div>
"""

            if unit.get('coriace'):
                html_content += f"""
                <div class="stat-badge">
                    <div class="stat-label">Coriace</div>
                    <div class="stat-value">{unit['coriace']}</div>
                </div>
"""

            html_content += """
            </div>
"""

            if rules:
                html_content += f'<div class="special-rules"><strong>Règles spéciales:</strong> {special_rules.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")}</div>'

            html_content += f"""
            <div class="section-title">Arme</div>
            <table class="weapon-table">
                <thead>
                    <tr>
                        <th>Nom</th>
                        <th>PORT</th>
                        <th>ATK</th>
                        <th>PA</th>
                        <th>SPE</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>{weapon_name}</td>
                        <td>-</td>
                        <td>{weapon_attacks}</td>
                        <td>{weapon_ap}</td>
                        <td>{weapon_special}</td>
                    </tr>
                </tbody>
            </table>
"""

            if 'options' in unit and unit['options']:
                for group_name, opts in unit['options'].items():
                    if isinstance(opts, list) and opts:
                        group_name_clean = str(group_name).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                        html_content += f'<div class="section-title">{group_name_clean}:</div>'
                        for opt in opts:
                            opt_name = str(opt.get("name", "")).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                            html_content += f'<div>• {opt_name}</div>'

            if 'mount' in unit and unit['mount']:
                mount_details = format_mount_details(unit["mount"])
                mount_details_clean = str(mount_details).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                html_content += f'<div class="section-title">Monture</div><p>{mount_details_clean}</p>'

            html_content += "</div>"

        html_content += """
    </body>
</html>
"""

        st.download_button(
            "Exporter en HTML",
            html_content,
            file_name=f"{st.session_state.list_name}.html",
            mime="text/html"
        )
