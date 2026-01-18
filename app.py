import json
import streamlit as st
from pathlib import Path
from datetime import datetime
import streamlit.components.v1 as components
import hashlib
import re  # Import nécessaire pour le calcul de Coriace

# ======================================================
# CONFIGURATION POUR SIMON
# ======================================================
st.set_page_config(
    page_title="OPR Army Builder FR - Simon Joinville Fouquet",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Chemins des fichiers (adapté pour GitHub)
BASE_DIR = Path(__file__).resolve().parent
FACTIONS_DIR = BASE_DIR / "lists" / "data" / "factions"
FACTIONS_DIR.mkdir(parents=True, exist_ok=True)  # Crée le dossier s'il n'existe pas

# ======================================================
# LOCAL STORAGE (version ultra-robuste pour GitHub)
# ======================================================
def generate_unique_key(base_key):
    """Génère une clé unique pour éviter les conflits"""
    return f"{base_key}_{hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()[:8]}"

def ls_get(key):
    """Récupère une valeur du LocalStorage avec gestion d'erreur complète"""
    try:
        unique_key = generate_unique_key(f"localstorage_{key}")
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
        st.error(f"Erreur de lecture LocalStorage: {e}")
        return None

def ls_set(key, value):
    """Stocke une valeur dans le LocalStorage avec échappement complet"""
    try:
        if not isinstance(value, str):
            value = json.dumps(value)

        # Double échappement pour éviter les problèmes
        escaped_value = value.replace("'", "\\'").replace('"', '\\"').replace("`", "\\`")
        components.html(
            f"""
            <script>
            localStorage.setItem("{key}", `{escaped_value}`);
            </script>
            """,
            height=0
        )
    except Exception as e:
        st.error(f"Erreur d'écriture LocalStorage: {e}")

# ======================================================
# GESTION DES FACTIONS (optimisé pour GitHub)
# ======================================================
@st.cache_data
def load_factions():
    """Charge les factions depuis les fichiers JSON dans lists/data/factions/"""
    factions = {}
    games = set()

    if not FACTIONS_DIR.exists():
        st.error(f"Dossier {FACTIONS_DIR} introuvable! Vérifiez que vous avez bien créé le dossier 'lists/data/factions/' dans votre dépôt GitHub.")
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
            st.warning(f"Erreur de chargement du fichier {fp.name}: {e}")

    return factions, sorted(games)

# Chargement initial des factions
factions_by_game, games = load_factions()

# ======================================================
# FONCTIONS UTILITAIRES POUR SIMON
# ======================================================
def format_special_rule(rule):
    """Formate les règles spéciales avec parenthèses si nécessaire"""
    if not isinstance(rule, str):
        return str(rule)
    if "(" in rule and ")" in rule:
        return rule
    match = re.search(r"(\D+)(\d+)", rule)
    if match:
        return f"{match.group(1)}({match.group(2)})"
    return rule

def calculate_coriace(rules):
    """Calcule la valeur de Coriace depuis les règles"""
    if not isinstance(rules, list):
        return 0
    total = 0
    for rule in rules:
        if isinstance(rule, str):
            match = re.search(r"Coriace\s*\(?(\d+)\)?", rule)
            if match:
                total += int(match.group(1))
    return total

def calculate_total_coriace(unit_data):
    """Calcule la Coriace totale pour une unité (inclut monture et améliorations)"""
    total = 0

    # 1. Règles de base de l'unité
    if 'special_rules' in unit_data:
        total += calculate_coriace(unit_data['special_rules'])

    # 2. Options de l'unité
    if 'options' in unit_data:
        for opts in unit_data['options'].values():
            if isinstance(opts, list):
                for opt in opts:
                    if isinstance(opt, dict) and 'special_rules' in opt:
                        total += calculate_coriace(opt['special_rules'])
            elif isinstance(opts, dict) and 'special_rules' in opts:
                total += calculate_coriace(opts['special_rules'])

    # 3. Monture (spécialement important pour les héros)
    if 'mount' in unit_data and isinstance(unit_data['mount'], dict):
        if 'special_rules' in unit_data['mount']:
            total += calculate_coriace(unit_data['mount']['special_rules'])

    # 4. Armes de l'unité
    if 'weapon' in unit_data and isinstance(unit_data['weapon'], dict):
        if 'special_rules' in unit_data['weapon']:
            total += calculate_coriace(unit_data['weapon']['special_rules'])

    return total if total > 0 else None

# ======================================================
# INITIALISATION DE LA SESSION
# ======================================================
if "page" not in st.session_state:
    st.session_state.page = "setup"
    st.session_state.army_list = []
    st.session_state.army_cost = 0
    st.session_state.current_player = "Simon"  # Nom par défaut pour Simon

# ======================================================
# PAGE 1 – CONFIGURATION
# ======================================================
if st.session_state.page == "setup":
    st.title("OPR Army Builder 🇫🇷")
    st.markdown("**Bienvenue Simon!** Créez ou chargez une liste d'armée pour One Page Rules.")

    if not games:
        st.error("Aucune faction trouvée. Vérifiez que vous avez bien placé vos fichiers JSON dans 'lists/data/factions/'")
        st.stop()

    # Sélection du jeu et de la faction
    game = st.selectbox("Jeu", games)
    faction = st.selectbox("Faction", factions_by_game[game].keys())
    points = st.number_input("Points", min_value=250, max_value=5000, value=1000, step=250)
    list_name = st.text_input("Nom de la liste", f"Liste_{datetime.now().strftime('%Y%m%d')}")

    # -------- IMPORT JSON --------
    st.divider()
    st.subheader("Importer une liste existante")

    uploaded = st.file_uploader("Sélectionnez un fichier JSON", type="json")
    if uploaded:
        try:
            data = json.load(uploaded)

            # Vérification minimale des données
            if not all(key in data for key in ["game", "faction", "army_list"]):
                st.error("Format JSON invalide. Le fichier doit contenir au moins: game, faction et army_list")
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
            st.error(f"Erreur de chargement du fichier: {e}")

    # -------- CRÉATION NOUVELLE LISTE --------
    st.divider()
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

    # -------- NAVIGATION --------
    if st.button("⬅ Retour à la configuration"):
        st.session_state.page = "setup"
        st.rerun()

    # -------- AJOUT D'UNITÉ --------
    st.divider()
    st.subheader("Ajouter une unité")

    unit = st.selectbox(
        "Unité disponible",
        st.session_state.units,
        format_func=lambda u: f"{u['name']} ({u['base_cost']} pts)"
    )

    # Initialisation des données de l'unité
    cost = unit["base_cost"]
    weapon = unit.get("weapons", [{}])[0]
    selected_options = {}
    mount = None
    combined = False

    # -------- UNITÉ COMBINÉE --------
    if unit.get("type", "").lower() != "hero":
        combined = st.checkbox("Unité combinée (+100% coût)", value=False)
        if combined:
            cost *= 2

    # -------- OPTIONS DE L'UNITÉ --------
    for group in unit.get("upgrade_groups", []):
        st.markdown(f"**{group['group']}**")

        if group["type"] == "weapon":
            # Choix d'arme (radio buttons)
            weapon_options = ["Arme de base"] + [
                f"{o['name']} (+{o['cost'] * (2 if combined else 1)} pts)" for o in group["options"]
            ]
            selected_weapon = st.radio(
                "Choix d'arme",
                weapon_options,
                key=f"{unit['name']}_weapon"
            )

            if selected_weapon != "Arme de base":
                opt_name = selected_weapon.split(" (+")[0]
                opt = next(o for o in group["options"] if o["name"] == opt_name)
                weapon = opt["weapon"]
                cost += opt["cost"] * (2 if combined else 1)

        elif group["type"] == "mount":
            # Choix de monture (radio buttons)
            mount_options = ["Aucune monture"] + [
                f"{o['name']} (+{o['cost'] * (2 if combined else 1)} pts)" for o in group["options"]
            ]
            selected_mount = st.radio(
                "Choix de monture",
                mount_options,
                key=f"{unit['name']}_mount"
            )

            if selected_mount != "Aucune monture":
                opt_name = selected_mount.split(" (+")[0]
                opt = next(o for o in group["options"] if o["name"] == opt_name)
                mount = opt
                cost += opt["cost"] * (2 if combined else 1)

        else:
            # Améliorations (radio buttons au lieu de checkbox)
            options = group.get("options", [])
            if options:
                option_names = ["Aucune amélioration"] + [
                    f"{o['name']} (+{o['cost'] * (2 if combined else 1)} pts)" for o in options
                ]
                selected_option = st.radio(
                    group["group"],
                    option_names,
                    key=f"{unit['name']}_{group['group']}"
                )

                if selected_option != "Aucune amélioration":
                    opt_name = selected_option.split(" (+")[0]
                    opt = next(o for o in options if o["name"] == opt_name)
                    if group["group"] not in selected_options:
                        selected_options[group["group"]] = []
                    selected_options[group["group"]].append(opt)
                    cost += opt["cost"] * (2 if combined else 1)

    # -------- CALCUL DE LA CORIACE --------
    total_coriace = 0
    if "special_rules" in unit:
        total_coriace += calculate_coriace(unit["special_rules"])

    if mount and "special_rules" in mount:
        total_coriace += calculate_coriace(mount["special_rules"])

    for opts in selected_options.values():
        if isinstance(opts, list):
            for opt in opts:
                if "special_rules" in opt:
                    total_coriace += calculate_coriace(opt["special_rules"])

    st.markdown(f"### 💰 Coût total : {cost} pts")
    if total_coriace > 0:
        st.markdown(f"### 🛡 Coriace totale : {total_coriace}")

    # -------- AJOUT À L'ARMÉE --------
    if st.button("➕ Ajouter à l'armée"):
        st.session_state.army_list.append({
            "name": unit["name"],
            "cost": cost,
            "quality": unit["quality"],
            "defense": unit["defense"],
            "rules": [format_special_rule(r) for r in unit.get("special_rules", [])],
            "weapon": weapon,
            "options": selected_options,
            "mount": mount,
            "coriace": total_coriace if total_coriace > 0 else None,
            "combined": combined if unit.get("type", "").lower() != "hero" else False
        })
        st.session_state.army_cost += cost
        st.rerun()

    # -------- LISTE DE L'ARMÉE --------
    st.divider()
    st.subheader("Liste de l'armée")

    if not st.session_state.army_list:
        st.info("Ajoutez des unités pour commencer")

    for i, u in enumerate(st.session_state.army_list):
        with st.container():
            st.markdown(f"### {u['name']} – {u['cost']} pts")
            if u.get("combined"):
                st.markdown("**Unité combinée** (x2 effectif)")

            c1, c2, c3 = st.columns(3)
            c1.metric("Qualité", f"{u['quality']}+")
            c2.metric("Défense", f"{u['defense']}+")
            if u.get("coriace"):
                c3.metric("Coriace", u["coriace"])

            if u["rules"]:
                st.markdown("**Règles spéciales**")
                st.caption(", ".join(u["rules"]))

            st.markdown("**Armes**")
            st.caption(
                f"{u['weapon'].get('name','-')} | "
                f"A{u['weapon'].get('attacks','?')} "
                f"PA({u['weapon'].get('armor_piercing','?')})"
            )

            if u["options"]:
                st.markdown("**Améliorations sélectionnées**")
                for group, opts in u["options"].items():
                    if isinstance(opts, list):
                        for o in opts:
                            st.caption(f"• {format_special_rule(o['name'])}")

            if u["mount"]:
                st.markdown("**Monture**")
                st.caption(u["mount"]["name"])
                if "special_rules" in u["mount"]:
                    st.caption(", ".join(u["mount"]["special_rules"]))

            if st.button("❌ Supprimer", key=f"del_{i}"):
                st.session_state.army_cost -= u["cost"]
                st.session_state.army_list.pop(i)
                st.rerun()

    # -------- SAUVEGARDE / EXPORT --------
    st.divider()
    col1, col2, col3 = st.columns(3)

    army_data = {
        "name": st.session_state.list_name,
        "game": st.session_state.game,
        "faction": st.session_state.faction,
        "points": st.session_state.points,
        "total_cost": st.session_state.army_cost,
        "army_list": st.session_state.army_list
    }

    with col1:
        if st.button("💾 Sauvegarder"):
            ls_set("opr_last_list", army_data)
            st.success("Liste sauvegardée dans le navigateur")

    with col2:
        st.download_button(
            "📁 Export JSON",
            json.dumps(army_data, indent=2, ensure_ascii=False),
            file_name=f"{st.session_state.list_name}.json",
            mime="application/json"
        )

    with col3:
        if st.button("♻ Réinitialiser"):
            st.session_state.army_list = []
            st.session_state.army_cost = 0
            st.rerun()
