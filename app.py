import json
import re
from pathlib import Path
from collections import defaultdict
import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime
import base64

# Configuration de base
st.set_page_config(page_title="OPR Army Builder FR", layout="centered")
BASE_DIR = Path(__file__).resolve().parent
FACTIONS_DIR = BASE_DIR / "lists" / "data" / "factions"
SAVE_DIR = BASE_DIR / "saves"
SAVE_DIR.mkdir(exist_ok=True)  # Crée le dossier s'il n'existe pas

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
if "page" not in st.session_state:
    st.session_state.page = "setup"

for key, default in {
    "game": None,
    "faction": None,
    "points": 1000,
    "list_name": "",
    "army_list": [],
    "army_total_cost": 0,
    "is_army_valid": True,
    "validation_errors": []
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# Chargement des factions
faction_files = list(FACTIONS_DIR.glob("*.json"))
factions = []

for fp in faction_files:
    try:
        with open(fp, encoding="utf-8") as f:
            data = json.load(f)
            factions.append({
                "name": data["faction"],
                "game": data["game"],
                "file": fp
            })
    except Exception as e:
        st.warning(f"Impossible de lire {fp.name} : {e}")

games = sorted(set(f["game"] for f in factions))

# Fonction pour valider la liste d'armée
def validate_army(army_list, game_rules, total_cost, total_points):
    errors = []

    if not army_list:
        errors.append("Aucune unité dans l'armée")
        return False, errors

    if game_rules == GAME_RULES["Age of Fantasy"]:
        # 1 héros par tranche de 375 pts
        heroes = sum(1 for u in army_list if u.get("type", "").lower() in ["hero", "héro"])
        max_heroes = max(1, total_points // game_rules["hero_per_points"])
        if heroes > max_heroes:
            errors.append(f"Trop de héros (max: {max_heroes} pour {total_points} pts)")

        # 1+X copies de la même unité (X=1 pour 750 pts)
        unit_counts = defaultdict(int)
        for unit in army_list:
            unit_counts[unit["name"]] += 1

        max_copies = 1 + (total_points // 750)
        for unit_name, count in unit_counts.items():
            if count > max_copies:
                errors.append(f"Trop de copies de '{unit_name}' (max: {max_copies})")

        # Aucune unité ne peut valoir plus de 35% du total des points de l'armée
        for unit in army_list:
            percentage = (unit["cost"] / total_points) * 100
            if percentage > game_rules["max_unit_percentage"]:
                errors.append(f"'{unit['name']}' ({unit['cost']} pts) dépasse {game_rules['max_unit_percentage']}% du total ({total_points} pts)")

        # 1 unité max par tranche de 150 pts
        max_units = total_points // game_rules["unit_per_points"]
        if len(army_list) > max_units:
            errors.append(f"Trop d'unités (max: {max_units} pour {total_points} pts)")

    return len(errors) == 0, errors

# Fonction pour sauvegarder la liste
def save_army():
    if not st.session_state.list_name:
        st.warning("Veuillez donner un nom à votre liste avant de sauvegarder")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{SAVE_DIR}/{st.session_state.list_name}_{timestamp}.json"

    data = {
        "game": st.session_state.game,
        "faction": st.session_state.faction,
        "points": st.session_state.points,
        "army_list": st.session_state.army_list,
        "total_cost": st.session_state.army_total_cost,
        "date": datetime.now().isoformat()
    }

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    st.success(f"Liste sauvegardée sous {filename}")

# Fonction pour générer un export HTML (alternative au PDF)
def export_to_html():
    if not st.session_state.army_list:
        st.warning("Aucune unité dans l'armée à exporter")
        return

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Liste d'armée OPR - {st.session_state.list_name}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1 {{ color: #4a89dc; }}
            .army-card {{ border: 1px solid #ccc; border-radius: 8px; padding: 15px; margin-bottom: 15px; background: #f9f9f9; }}
            .badge {{ display: inline-block; background: #4a89dc; color: white; padding: 6px 12px; border-radius: 15px; margin-right: 8px; margin-bottom: 5px; }}
            .title {{ font-weight: bold; color: #4a89dc; margin-top: 10px; }}
            .valid {{ border-left: 4px solid #2ecc71; }}
            .invalid {{ border-left: 4px solid #e74c3c; }}
        </style>
    </head>
    <body>
        <h1>Liste d'armée OPR - {st.session_state.list_name}</h1>
        <h2>{st.session_state.game} - {st.session_state.faction} - {st.session_state.army_total_cost}/{st.session_state.points} pts</h2>
    """

    for unit in st.session_state.army_list:
        html_content += f"""
        <div class="army-card {'valid' if st.session_state.is_army_valid else 'invalid'}">
            <h3>{unit['name']} - {unit['cost']} pts</h3>
            <div>
                <span class="badge">Qualité {unit['quality']}+</span>
                <span class="badge">Défense {unit['defense']}+</span>
                <span class="badge">Coriace {unit.get('coriace', 0)}</span>
            </div>
            <div class="title">Règles spéciales</div>
            <div>{', '.join(unit['base_rules'])}</div>
        """

        if 'current_weapon' in unit:
            weapon = unit['current_weapon']
            html_content += f"""
            <div class="title">Arme équipée</div>
            <div>
                {weapon.get('name', 'Arme de base')} | A{weapon.get('attacks', '?')} | PA({weapon.get('armor_piercing', '?')})
            </div>
            """

        if unit.get("options"):
            html_content += f"""
            <div class="title">Options sélectionnées</div>
            <div>
                {', '.join(o['name'] for o in unit['options'].values())}
            </div>
            """

        if unit.get("mount"):
            mount = unit['mount']
            html_content += f"""
            <div class="title">Monture</div>
            <div>
                <strong>{mount['name']}</strong> (+{mount.get('cost', 0)} pts)<br>
                {', '.join(mount.get('special_rules', []))}
            </div>
            """
        html_content += "</div>"

    html_content += """
    </body>
    </html>
    """

    # Sauvegarde du HTML
    filename = f"{st.session_state.list_name or 'army_list'}.html"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html_content)

    # Téléchargement
    with open(filename, "r", encoding="utf-8") as f:
        st.download_button(
            label="Télécharger le fichier HTML",
            data=f,
            file_name=filename,
            mime="text/html"
        )

    # Affichage dans l'interface
    components.html(html_content, height=600, scrolling=True)

# PAGE 1 — Configuration de la liste
if st.session_state.page == "setup":
    st.title("OPR Army Builder 🇫🇷")
    st.subheader("Créer une nouvelle liste")

    st.session_state.game = st.selectbox(
        "Jeu",
        games,
        index=games.index(st.session_state.game) if st.session_state.game else 0
    )

    available_factions = [f for f in factions if f["game"] == st.session_state.game]
    faction_names = [f["name"] for f in available_factions]

    st.session_state.faction = st.selectbox(
        "Faction",
        faction_names,
        index=faction_names.index(st.session_state.faction) if st.session_state.faction in faction_names else 0
    )

    st.session_state.points = st.number_input(
        "Format de la partie (points)",
        min_value=250,
        step=250,
        value=st.session_state.points
    )

    st.session_state.list_name = st.text_input(
        "Nom de la liste",
        value=st.session_state.list_name
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Sauvegarder la configuration"):
            st.success("Configuration sauvegardée")

    with col2:
        if st.button("➡️ Ma liste"):
            st.session_state.page = "army"
            st.rerun()

# PAGE 2 — Composition de l'armée
if st.session_state.page == "army":
    st.title(st.session_state.list_name or "Ma liste d'armée")
    st.caption(f"{st.session_state.game} — {st.session_state.faction} — {st.session_state.army_total_cost}/{st.session_state.points} pts")

    if st.button("⬅️ Retour configuration"):
        st.session_state.page = "setup"
        st.rerun()

    # Charger la faction
    faction_file = next(f["file"] for f in factions if f["name"] == st.session_state.faction)
    with open(faction_file, encoding="utf-8") as f:
        faction = json.load(f)

    units = faction.get("units", [])

    st.divider()
    st.subheader("Ajouter une unité")

    unit = st.selectbox(
        "Unité",
        units,
        format_func=lambda u: f"{u['name']} ({u['base_cost']} pts)",
    )

    total_cost = unit["base_cost"]
    base_rules = unit.get("special_rules", [])
    options_selected = {}
    mount_selected = None

    # Options
    for group in unit.get("upgrade_groups", []):
        choice = st.selectbox(
            group["group"],
            ["— Aucun —"] + [o["name"] for o in group["options"]],
            key=f"{unit['name']}_{group['group']}"
        )

        if choice != "— Aucun —":
            opt = next(o for o in group["options"] if o["name"] == choice)
            total_cost += opt.get("cost", 0)

            if group["type"] == "mount":
                mount_selected = opt
            else:
                options_selected[group["group"]] = opt

    # Calcul de la valeur de Coriace
    coriace_value = 0
    for rule in base_rules:
        match = re.search(r'Coriace \((\d+)\)', rule)
        if match:
            coriace_value += int(match.group(1))

    if mount_selected:
        for rule in mount_selected.get("special_rules", []):
            match = re.search(r'Coriace \(\+?(\d+)\)', rule)
            if match:
                coriace_value += int(match.group(1))

    st.markdown(f"### 💰 Coût : **{total_cost} pts**")
    st.markdown(f"**Coriace totale : {coriace_value}**")

    if st.button("➕ Ajouter à l'armée"):
        st.session_state.army_list.append({
            "name": unit["name"],
            "cost": total_cost,
            "quality": unit["quality"],
            "defense": unit["defense"],
            "coriace": coriace_value,
            "base_rules": base_rules,
            "options": options_selected,
            "mount": mount_selected,
            "type": unit.get("type", "Infantry")
        })
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

    # Affichage des erreurs de validation
    if not st.session_state.is_army_valid:
        st.warning("⚠️ La liste d'armée n'est pas valide :")
        for error in st.session_state.validation_errors:
            st.write(f"- {error}")

    # Liste de l'armée
    st.divider()
    st.subheader("Liste de l'armée")

    for i, u in enumerate(st.session_state.army_list):
        height = 260
        if u.get("mount"):
            height += 40
        if u.get("options"):
            height += 20 * len(u["options"])

        components.html(f"""
        <style>
        .card {{
            border:1px solid #ccc;
            border-radius:8px;
            padding:15px;
            margin-bottom:15px;
            background:#f9f9f9;
        }}
        .badge {{
            display:inline-block;
            background:#4a89dc;
            color:white;
            padding:6px 12px;
            border-radius:15px;
            margin-right:8px;
            margin-bottom: 5px;
        }}
        .title {{
            font-weight:bold;
            color:#4a89dc;
            margin-top:10px;
        }}
        .valid {{
            border-left: 4px solid #2ecc71;
        }}
        .invalid {{
            border-left: 4px solid #e74c3c;
        }}
        </style>

        <div class="card {'valid' if st.session_state.is_army_valid else 'invalid'}">
            <h4>{u['name']} — {u['cost']} pts</h4>

            <div style="margin-bottom: 10px;">
                <span class="badge">Qualité {u['quality']}+</span>
                <span class="badge">Défense {u['defense']}+</span>
                <span class="badge">Coriace {u['coriace']}</span>
            </div>

            <div class="title">Règles spéciales</div>
            <div style="margin-left: 15px; margin-bottom: 10px;">{", ".join(u["base_rules"])}</div>

            {f"""
            <div class="title">Arme équipée</div>
            <div style="margin-left: 15px; margin-bottom: 10px;">
                {u.get('current_weapon', {}).get('name', 'Arme de base')} |
                A{u.get('current_weapon', {}).get('attacks', '?')} |
                PA({u.get('current_weapon', {}).get('armor_piercing', '?')})
            </div>
            """ if 'current_weapon' in u else ''}

            {f"""
            <div class="title">Options sélectionnées</div>
            <div style="margin-left: 15px; margin-bottom: 10px;">
                {', '.join(o['name'] for o in u['options'].values())}
            </div>
            """ if u.get("options") else ''}

            {f"""
            <div class="title">Monture</div>
            <div style="margin-left: 15px; margin-bottom: 10px;">
                <strong>{u['mount']['name']}</strong> (+{u['mount'].get('cost', 0)} pts)<br>
                {', '.join(u['mount'].get('special_rules', []))}
            </div>
            """ if u.get("mount") else ''}
        </div>
        """, height=height)

        if st.button("❌ Supprimer", key=f"del_{i}"):
            st.session_state.army_total_cost -= u["cost"]
            st.session_state.army_list.pop(i)
            st.rerun()

    # Barre de progression et informations
    st.divider()
    progress = st.session_state.army_total_cost / st.session_state.points if st.session_state.points else 0
    st.progress(progress)
    st.markdown(f"**{st.session_state.army_total_cost} / {st.session_state.points} pts**")

    # Boutons de sauvegarde et d'export
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Sauvegarder la liste"):
            save_army()

    with col2:
        if st.button("📄 Exporter en HTML"):
            export_to_html()

    # Affichage des règles spécifiques au jeu
    if st.session_state.game in GAME_RULES:
        st.divider()
        st.subheader("Règles spécifiques à " + st.session_state.game)
        rules = GAME_RULES[st.session_state.game]
        st.markdown(f"""
        - **Héros** : 1 par tranche de {rules['hero_per_points']} pts
        - **Copies d'unités** : 1+X (X=1 pour {list(rules['unit_copies'].keys())[0]} pts)
        - **Unité max** : {rules['max_unit_percentage']}% du total des points de l'armée
        - **Nombre d'unités** : 1 par tranche de {rules['unit_per_points']} pts
        """)
