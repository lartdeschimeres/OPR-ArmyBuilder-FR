import json
import streamlit as st
from pathlib import Path
from datetime import datetime
import hashlib
import re
import copy
import math

# ======================================================
# CONFIGURATION POUR SIMON JOINVILLE FOUQUET
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
        "description": "Jeu de bataille dans un univers fantasy médiéval",
        "hero_limit": 375,
        "unit_copy_rule": 750,
        "unit_max_cost_ratio": 0.35,
        "unit_per_points": 150
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

def check_unit_copy_rule(army_list, army_points, game_config):
    """Vérifie la règle des copies d'unités"""
    if game_config.get("unit_copy_rule"):
        x_value = math.floor(army_points / game_config["unit_copy_rule"])
        max_copies = 1 + x_value
        unit_counts = {}
        for unit in army_list:
            unit_name = unit["name"]
            if unit_name in unit_counts:
                unit_counts[unit_name] += 1
            else:
                unit_counts[unit_name] = 1
        for unit_name, count in unit_counts.items():
            if count > max_copies:
                st.error(f"Trop de copies de l'unité! Maximum autorisé: {max_copies} (1+{x_value} pour {game_config['unit_copy_rule']} pts)")
                return False
    return True

def check_unit_max_cost(army_list, army_points, game_config, new_unit_cost=None):
    """Vérifie qu'aucune unité ne dépasse le ratio maximum de coût"""
    if not game_config.get("unit_max_cost_ratio"):
        return True
    max_cost = army_points * game_config["unit_max_cost_ratio"]
    for unit in army_list:
        if unit["cost"] > max_cost:
            st.error(f"L'unité {unit['name']} ({unit['cost']} pts) dépasse la limite de {int(max_cost)} pts")
            return False
    if new_unit_cost and new_unit_cost > max_cost:
        st.error(f"Cette unité ({new_unit_cost} pts) dépasse la limite de {int(max_cost)} pts")
        return False
    return True

def check_unit_per_points(army_list, army_points, game_config):
    """Vérifie le nombre maximum d'unités par tranche de points"""
    if game_config.get("unit_per_points"):
        max_units = math.floor(army_points / game_config["unit_per_points"])
        if len(army_list) > max_units:
            st.error(f"Trop d'unités! Maximum autorisé: {max_units} (1 unité par {game_config['unit_per_points']} pts)")
            return False
    return True

def validate_army_rules(army_list, army_points, game, new_unit_cost=None):
    """Valide toutes les règles spécifiques au jeu"""
    game_config = GAME_CONFIG.get(game, {})
    if game in GAME_CONFIG:
        return (check_hero_limit(army_list, army_points, game_config) and
                check_unit_copy_rule(army_list, army_points, game_config) and
                check_unit_max_cost(army_list, army_points, game_config, new_unit_cost) and
                check_unit_per_points(army_list, army_points, game_config))
    return True

# ======================================================
# FONCTIONS UTILITAIRES
# ======================================================
def format_special_rule(rule):
    """Formate les règles spéciales avec parenthèses"""
    if not isinstance(rule, str):
        return str(rule)
    if "(" in rule and ")" in rule:
        return rule
    match = re.search(r"(\D+)(\d+)", rule)
    if match:
        return f"{match.group(1)}({match.group(2)})"
    return rule

def extract_coriace_value(rule):
    """Extrait la valeur numérique de Coriace d'une règle"""
    if not isinstance(rule, str):
        return 0
    match = re.search(r"Coriace\s*\(?(\d+)\)?", rule)
    if match:
        return int(match.group(1))
    return 0

def get_coriace_from_rules(rules):
    """Calcule la Coriace depuis une liste de règles"""
    if not rules or not isinstance(rules, list):
        return 0
    total = 0
    for rule in rules:
        total += extract_coriace_value(rule)
    return total

def format_weapon_details(weapon):
    """Formate les détails d'une arme pour l'affichage"""
    if not weapon:
        return {
            "name": "Arme non spécifiée",
            "attacks": "?",
            "ap": "?",
            "special": []
        }
    return {
        "name": weapon.get('name', 'Arme non nommée'),
        "attacks": weapon.get('attacks', '?'),
        "ap": weapon.get('armor_piercing', '?'),
        "special": weapon.get('special_rules', [])
    }

def format_mount_details(mount):
    """Formate les détails d'une monture pour l'affichage"""
    if not mount:
        return "Aucune monture"
    mount_name = mount.get('name', 'Monture non nommée')
    mount_data = mount['mount'] if 'mount' in mount else mount
    details = mount_name
    if 'quality' in mount_data or 'defense' in mount_data:
        details += " ("
        if 'quality' in mount_data:
            details += f"Qua{mount_data['quality']}+"
        if 'defense' in mount_data:
            details += f" Déf{mount_data['defense']}+"
        details += ")"
    if 'special_rules' in mount_data and mount_data['special_rules']:
        details += " | " + ", ".join(mount_data['special_rules'])
    if 'weapons' in mount_data and mount_data['weapons']:
        for weapon in mount_data['weapons']:
            weapon_details = format_weapon_details(weapon)
            details += f" | {weapon.get('name', 'Arme')} (A{weapon_details['attacks']}, PA({weapon_details['ap']})"
            if weapon_details['special']:
                details += ", " + ", ".join(weapon_details['special'])
            details += ")"
    return details

def format_unit_option(u):
    """Formate l'affichage des unités dans la liste déroulante"""
    name_part = f"{u['name']}"
    if u.get('type') == "hero":
        name_part += " [1]"
    else:
        name_part += f" [{u.get('size', 10)}]"
    qua_def = f"Qua {u['quality']}+ / Déf {u.get('defense', '?')}"
    coriace = get_coriace_from_rules(u.get('special_rules', []))
    if 'mount' in u and u['mount']:
        _, mount_coriace = get_mount_details(u['mount'])
        coriace += mount_coriace
    if coriace > 0:
        qua_def += f" / Coriace {coriace}"
    weapons_part = ""
    if 'weapons' in u and u['weapons']:
        weapons = []
        for weapon in u['weapons']:
            weapon_details = format_weapon_details(weapon)
            weapons.append(f"{weapon.get('name', 'Arme')} (A{weapon_details['attacks']}, PA({weapon_details['ap']}){', ' + ', '.join(weapon_details['special']) if weapon_details['special'] else ''})")
        weapons_part = " | ".join(weapons)
    rules_part = ", ".join(u['special_rules']) if 'special_rules' in u and u['special_rules'] else ""
    return f"{name_part} - {qua_def} - {weapons_part} - {rules_part} {u['base_cost']}pts"

# ======================================================
# LOCAL STORAGE
# ======================================================
def ls_get(key):
    """Récupère une valeur du LocalStorage"""
    try:
        unique_key = f"{key}_{hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()[:8]}"
        st.markdown(f"""
        <script>
        const value = localStorage.getItem("{key}");
        const input = document.createElement("input");
        input.type = "hidden";
        input.id = "{unique_key}";
        input.value = value || "";
        document.body.appendChild(input);
        </script>
        """, unsafe_allow_html=True)
        return st.text_input("", key=unique_key, label_visibility="collapsed")
    except Exception as e:
        st.error(f"Erreur LocalStorage: {e}")
        return None

def ls_set(key, value):
    """Stocke une valeur dans le LocalStorage"""
    try:
        if not isinstance(value, str):
            value = json.dumps(value)
        escaped_value = value.replace("'", "\\'").replace('"', '\\"')
        st.markdown(f"""
        <script>
        localStorage.setItem("{key}", `{escaped_value}`);
        </script>
        """, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Erreur LocalStorage: {e}")

# ======================================================
# CHARGEMENT DES FACTIONS
# ======================================================
@st.cache_data
def load_factions():
    """Charge les factions depuis les fichiers JSON"""
    factions = {}
    games = set()

    # Faction par défaut
    default_faction = {
        "game": "Age of Fantasy",
        "faction": "Disciples de la Guerre",
        "special_rules_descriptions": {
            "Éclaireur": "Déplacement facilité en terrain difficile.",
            "Furieux": "Relance les 1 en attaque.",
            "Né pour la guerre": "Relance les 1 en test de moral.",
            "Héros": "Personnage inspirant.",
            "Coriace(1)": "Ignore 1 point de dégât par phase.",
            "Magique(1)": "Ignore 1 point de défense.",
            "Contre-charge": "+1 aux jets de dégât lors d'une charge.",
            "Attaque venimeuse": "Les blessures infligées ne peuvent pas être régénérées.",
            "Perforant": "Ignore 1 point de défense supplémentaire.",
            "Volant": "Peut voler par-dessus les obstacles et les unités.",
            "Effrayant(1)": "Les unités ennemies à 6\" doivent passer un test de moral ou reculer de 3\".",
            "Lanceur de sorts (3)": "Peut lancer 3 sorts par tour."
        },
        "units": [
            {
                "name": "Maître de la Guerre Élu",
                "type": "hero",
                "size": 1,
                "base_cost": 150,
                "quality": 3,
                "defense": 5,
                "special_rules": ["Héros", "Éclaireur", "Furieux", "Né pour la guerre"],
                "weapons": [{
                    "name": "Arme héroïque",
                    "attacks": 2,
                    "armor_piercing": 1,
                    "special_rules": ["Magique(1)"]
                }],
                "upgrade_groups": [
                    {
                        "group": "Montures",
                        "type": "mount",
                        "options": [
                            {
                                "name": "Dragon du Ravage",
                                "cost": 155,
                                "mount": {
                                    "name": "Dragon du Ravage",
                                    "quality": 4,
                                    "defense": 4,
                                    "special_rules": ["Volant", "Effrayant(1)", "Coriace(6)"],
                                    "weapons": [
                                        {
                                            "name": "Griffes et crocs",
                                            "attacks": 6,
                                            "armor_piercing": 1,
                                            "special_rules": ["Perforant"]
                                        },
                                        {
                                            "name": "Souffle de feu",
                                            "attacks": 1,
                                            "armor_piercing": 0,
                                            "special_rules": ["Attaque de souffle"]
                                        }
                                    ]
                                }
                            }
                        ]
                    },
                    {
                        "group": "Améliorations de rôle",
                        "type": "upgrades",
                        "options": [
                            {
                                "name": "Porteur de la bannière de l'armée",
                                "cost": 60,
                                "special_rules": ["Effrayant(3)"]
                            }
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
                "special_rules": ["Éclaireur", "Furieux", "Né pour la guerre"],
                "weapons": [{
                    "name": "Armes à une main",
                    "attacks": 1,
                    "armor_piercing": 0,
                    "special_rules": []
                }],
                "upgrade_groups": [
                    {
                        "group": "Remplacement d'armes",
                        "type": "weapon",
                        "options": [
                            {
                                "name": "Lance",
                                "cost": 35,
                                "weapon": {
                                    "name": "Lance",
                                    "attacks": 1,
                                    "armor_piercing": 0,
                                    "special_rules": ["Contre-charge"]
                                }
                            },
                            {
                                "name": "Fléau",
                                "cost": 20,
                                "weapon": {
                                    "name": "Fléau",
                                    "attacks": 1,
                                    "armor_piercing": 1,
                                    "special_rules": []
                                }
                            }
                        ]
                    },
                    {
                        "group": "Améliorations d'unité",
                        "type": "upgrades",
                        "options": [
                            {
                                "name": "Icône du Ravage",
                                "cost": 20,
                                "special_rules": ["Aura de Défense versatile"]
                            },
                            {
                                "name": "Sergent",
                                "cost": 5,
                                "special_rules": []
                            },
                            {
                                "name": "Bannière",
                                "cost": 5,
                                "special_rules": []
                            },
                            {
                                "name": "Musicien",
                                "cost": 10,
                                "special_rules": []
                            }
                        ]
                    }
                ]
            }
        ]
    }

    # Chargement des fichiers existants
    if FACTIONS_DIR.exists():
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
                st.warning(f"Erreur chargement {fp.name}: {e}")

    # Ajout de la faction par défaut si nécessaire
    factions.setdefault("Age of Fantasy", {})["Disciples de la Guerre"] = default_faction
    games.add("Age of Fantasy")

    return factions, sorted(games) if games else ["Age of Fantasy"]

# ======================================================
# INITIALISATION
# ======================================================
factions_by_game, games = load_factions()

if "page" not in st.session_state:
    st.session_state.page = "setup"
    st.session_state.army_list = []
    st.session_state.army_cost = 0
    st.session_state.history = []  # Historique pour l'annulation

# ======================================================
# PAGE 1 – CONFIGURATION
# ======================================================
if st.session_state.page == "setup":
    st.title("OPR Army Forge FR")

    # Sélection du jeu
    game = st.selectbox("Jeu", games)
    game_config = GAME_CONFIG.get(game, GAME_CONFIG["Age of Fantasy"])

    # Points
    points = st.number_input(
        "Points",
        min_value=game_config["min_points"],
        max_value=game_config["max_points"],
        value=game_config["default_points"],
        step=game_config["point_step"]
    )

    list_name = st.text_input("Nom de la liste", f"Liste_{datetime.now().strftime('%Y%m%d')}")

    # Chargement des listes sauvegardées
    st.subheader("Mes listes sauvegardées")
    saved_lists = ls_get("opr_saved_lists")
    if saved_lists:
        try:
            saved_lists = json.loads(saved_lists)
            if isinstance(saved_lists, list):
                for i, saved_list in enumerate(saved_lists):
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.markdown(f"**{saved_list.get('name', 'Liste sans nom')}**")
                        st.caption(f"{saved_list.get('game', 'Inconnu')} • {saved_list.get('faction', 'Inconnue')} • {saved_list.get('total_cost', 0)}/{saved_list.get('points', 0)} pts")
                    with col2:
                        if st.button(f"Charger", key=f"load_{i}"):
                            st.session_state.game = saved_list["game"]
                            st.session_state.faction = saved_list["faction"]
                            st.session_state.points = saved_list["points"]
                            st.session_state.list_name = saved_list["name"]
                            st.session_state.army_list = saved_list["army_list"]
                            st.session_state.army_cost = saved_list["total_cost"]
                            st.session_state.units = factions_by_game[saved_list["game"]][saved_list["faction"]]["units"]
                            st.session_state.history = []  # Réinitialiser l'historique
                            st.session_state.page = "army"
                            st.rerun()
        except Exception as e:
            st.error(f"Erreur chargement listes: {e}")

    if st.button("Créer une nouvelle liste"):
        st.session_state.game = game
        st.session_state.faction = st.selectbox("Faction", factions_by_game[game].keys())
        st.session_state.points = points
        st.session_state.list_name = list_name
        st.session_state.units = factions_by_game[game][st.session_state.faction]["units"]
        st.session_state.army_list = []
        st.session_state.army_cost = 0
        st.session_state.history = []  # Initialiser l'historique
        st.session_state.page = "army"
        st.rerun()

# ======================================================
# PAGE 2 – CONSTRUCTEUR D'ARMÉE
# ======================================================
elif st.session_state.page == "army":
    st.title(st.session_state.list_name)
    st.caption(f"{st.session_state.game} • {st.session_state.faction} • {st.session_state.army_cost}/{st.session_state.points} pts")

    # Boutons de contrôle
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        undo_disabled = len(st.session_state.history) == 0
        if st.button("↩ Annuler la dernière action", disabled=undo_disabled):
            if st.session_state.history:
                previous_state = st.session_state.history.pop()
                st.session_state.army_list = copy.deepcopy(previous_state["army_list"])
                st.session_state.army_cost = previous_state["army_cost"]
                st.rerun()

    with col2:
        if st.button("🗑 Réinitialiser la liste"):
            st.session_state.history.append({
                "army_list": copy.deepcopy(st.session_state.army_list),
                "army_cost": st.session_state.army_cost
            })
            st.session_state.army_list = []
            st.session_state.army_cost = 0
            st.rerun()

    with col3:
        if st.button("⬅ Retour"):
            st.session_state.page = "setup"
            st.rerun()

    # Vérification des règles
    game_config = GAME_CONFIG.get(st.session_state.game, GAME_CONFIG["Age of Fantasy"])
    if not validate_army_rules(st.session_state.army_list, st.session_state.points, st.session_state.game):
        st.warning("⚠️ Certaines règles ne sont pas respectées.")

    # Ajout d'une unité
    st.divider()
    st.subheader("Ajouter une unité")

    unit = st.selectbox(
        "Unité disponible",
        st.session_state.units,
        format_func=format_unit_option,
        index=0,
        key="unit_select"
    )

    base_size = unit.get('size', 10)
    base_cost = unit["base_cost"]

    # Vérification du coût maximum
    max_cost = st.session_state.points * game_config["unit_max_cost_ratio"]
    if unit["base_cost"] > max_cost:
        st.error(f"Cette unité ({unit['base_cost']} pts) dépasse la limite de {int(max_cost)} pts")
        st.stop()

    weapon = unit.get("weapons", [{}])[0]
    selected_options = {}
    mount = None
    weapon_cost = 0
    mount_cost = 0
    upgrades_cost = 0

    # Gestion des unités combinées (désactivé pour les héros)
    if unit.get("type") == "hero":
        combined = False
    else:
        combined = st.checkbox("Unité combinée", value=False)

    # Options de l'unité
    for group in unit.get("upgrade_groups", []):
        st.markdown(f"**{group['group']}**")

        if group["type"] == "weapon":
            weapon_options = ["Arme de base"]
            for o in group["options"]:
                weapon_details = format_weapon_details(o["weapon"])
                weapon_options.append(f"{o['name']} (+{o['cost']} pts)")
            selected_weapon = st.radio("Arme", weapon_options, key=f"{unit['name']}_weapon")
            if selected_weapon != "Arme de base":
                opt = next((o for o in group["options"] if o["name"] == selected_weapon.split(" (+")[0]), None)
                if opt:
                    weapon = opt["weapon"]
                    weapon_cost = opt["cost"]

        elif group["type"] == "mount":
            mount_options = ["Aucune monture"]
            mount_map = {}
            for o in group["options"]:
                mount_details = format_mount_details(o)
                mount_options.append(f"{mount_details} (+{o['cost']} pts)")
                mount_map[mount_details] = o
            selected_mount = st.radio("Monture", mount_options, key=f"{unit['name']}_mount")
            if selected_mount != "Aucune monture":
                mount = mount_map[selected_mount.split(" (+")[0]]
                mount_cost = mount["cost"]

        else:  # Améliorations
            options = ["Aucune"] + [f"{o['name']} (+{o['cost']} pts)" for o in group["options"]]
            selected = st.radio(group["group"], options, key=f"{unit['name']}_{group['group']}")
            if selected != "Aucune":
                opt = next((o for o in group["options"] if o["name"] == selected.split(" (+")[0]), None)
                if opt:
                    if group["group"] not in selected_options:
                        selected_options[group["group"]] = []
                    selected_options[group["group"]].append(opt)
                    upgrades_cost += opt["cost"]

    # Calcul du coût final
    if combined and unit.get("type") != "hero":
        final_cost = (base_cost + weapon_cost) * 2 + mount_cost + upgrades_cost
        unit_size = base_size * 2
    else:
        final_cost = base_cost + weapon_cost + mount_cost + upgrades_cost
        unit_size = base_size

    st.markdown(f"**Taille finale: {unit_size}** {'(x2 combinée)' if combined and unit.get('type') != 'hero' else ''}")
    st.markdown(f"**Coût total: {final_cost} pts**")

    if st.button("Ajouter à l'armée"):
        # Sauvegarder l'état actuel
        st.session_state.history.append({
            "army_list": copy.deepcopy(st.session_state.army_list),
            "army_cost": st.session_state.army_cost
        })

        # Calcul de la coriace
        total_coriace = get_coriace_from_rules(unit.get("special_rules", []))
        if mount:
            _, mount_coriace = get_mount_details(mount)
            total_coriace += mount_coriace
        if selected_options:
            for opts in selected_options.values():
                if isinstance(opts, list):
                    for opt in opts:
                        total_coriace += get_coriace_from_rules(opt.get("special_rules", []))
        if 'special_rules' in weapon:
            total_coriace += get_coriace_from_rules(weapon["special_rules"])
        if combined and unit.get('type') != "hero":
            total_coriace += get_coriace_from_rules(unit.get('special_rules', []))

        unit_data = {
            "name": unit["name"],
            "type": unit.get("type", "unit"),
            "cost": final_cost,
            "size": unit_size,
            "quality": unit["quality"],
            "defense": unit["defense"],
            "rules": [format_special_rule(r) for r in unit.get("special_rules", [])],
            "weapon": format_weapon_details(weapon),
            "options": selected_options,
            "mount": mount,
            "coriace": total_coriace if total_coriace > 0 else None
        }

        # Vérification des règles
        test_army = copy.deepcopy(st.session_state.army_list)
        test_army.append(unit_data)
        if not validate_army_rules(test_army, st.session_state.points, st.session_state.game, final_cost):
            st.error("Cette unité ne peut pas être ajoutée (règles violées)")
        else:
            st.session_state.army_list.append(unit_data)
            st.session_state.army_cost += final_cost
            st.rerun()

    # Liste de l'armée
    st.divider()
    st.subheader("Liste de l'armée")

    if not st.session_state.army_list:
        st.info("Ajoutez des unités pour commencer")

    for i, u in enumerate(st.session_state.army_list):
        with st.container():
            qua_def = f"Qua {u['quality']}+ / Déf {u['defense']}+"
            if u.get("coriace"):
                qua_def += f" / Coriace {u['coriace']}"

            unit_header = f"### {u['name']} [{u['size']}] ({u['cost']} pts) | {qua_def}"
            if u.get("type") == "hero":
                unit_header += " | 🌟 Héros"
            st.markdown(unit_header)

            if u.get("rules"):
                st.markdown(f"**Règles spéciales:** {', '.join(u['rules'])}")

            if 'weapon' in u:
                w = u['weapon']
                st.markdown(f"**Arme:** {w['name']} (A{w['attacks']}, PA({w['ap']}){', ' + ', '.join(w['special']) if w['special'] else ''})")

            if u.get("options"):
                for group, opts in u["options"].items():
                    st.markdown(f"**{group}:**")
                    for opt in opts:
                        st.markdown(f"• {opt['name']}")

            if u.get("mount"):
                st.markdown(f"**Monture:** {format_mount_details(u['mount'])}")

            if st.button(f"Supprimer {u['name']}", key=f"del_{i}"):
                st.session_state.history.append({
                    "army_list": copy.deepcopy(st.session_state.army_list),
                    "army_cost": st.session_state.army_cost
                })
                st.session_state.army_cost -= u["cost"]
                st.session_state.army_list.pop(i)
                st.rerun()

    # Export
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
        # Génération de l'HTML
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Liste OPR - {army_data['name']}</title>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .unit {{ margin-bottom: 20px; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
                .hero {{ background-color: #fffde7; }}
                .stats {{ display: flex; gap: 10px; margin-bottom: 10px; }}
                .stat {{ background: #e3f2fd; padding: 5px 10px; border-radius: 3px; }}
                .rules {{ margin: 10px 0; font-style: italic; }}
                table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <h1>Liste d'armée: {army_data['name']}</h1>
            <p><strong>Faction:</strong> {army_data['faction']} |
               <strong>Points:</strong> {army_data['total_cost']}/{army_data['points']}</p>

            <h2>Règles de la faction</h2>
            <div class="faction-rules">
        """

        # Ajout des règles de faction
        faction_data = factions_by_game[army_data['game']][army_data['faction']]
        if 'special_rules_descriptions' in faction_data:
            for rule, desc in faction_data['special_rules_descriptions'].items():
                html_content += f"""
                <details>
                    <summary><strong>{rule}:</strong></summary>
                    <p>{desc}</p>
                </details>
                """
        else:
            html_content += "<p>Aucune règle spéciale définie pour cette faction.</p>"

        html_content += """
            </div>

            <h2>Unités</h2>
        """

        for unit in army_data['army_list']:
            html_content += f"""
            <div class="unit {'hero' if unit.get('type') == 'hero' else ''}">
                <h3>{unit['name']} [{unit['size']}] ({unit['cost']} pts)
                {' <span style="color: gold;">🌟 Héros</span>' if unit.get('type') == 'hero' else ''}</h3>

                <div class="stats">
                    <div class="stat"><strong>Qualité:</strong> {unit['quality']}+</div>
                    <div class="stat"><strong>Défense:</strong> {unit['defense']}+</div>
                    {'<div class="stat"><strong>Coriace:</strong> ' + str(unit['coriace']) + '</div>' if unit.get('coriace') else ''}
                </div>

                {'<div class="rules"><strong>Règles spéciales:</strong> ' + ', '.join(unit['rules']) + '</div>' if unit.get('rules') else ''}

                <h4>Arme principale</h4>
                <table>
                    <tr>
                        <th>Nom</th>
                        <th>ATK</th>
                        <th>PA</th>
                        <th>Règles spéciales</th>
                    </tr>
                    <tr>
                        <td>{unit['weapon']['name']}</td>
                        <td>{unit['weapon']['attacks']}</td>
                        <td>{unit['weapon']['ap']}</td>
                        <td>{', '.join(unit['weapon']['special']) if unit['weapon']['special'] else 'Aucune'}</td>
                    </tr>
                </table>
            """

            if unit.get('options'):
                for group, opts in unit['options'].items():
                    html_content += f"<h4>{group}</h4><ul>"
                    for opt in opts:
                        html_content += f"<li>{opt['name']}</li>"
                    html_content += "</ul>"

            if unit.get('mount'):
                html_content += f"""
                <h4>Monture</h4>
                <p>{format_mount_details(unit['mount'])}</p>
                """

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
