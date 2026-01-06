import json
import streamlit as st
from pathlib import Path

# Helpers
def try_load(paths):
    for p in paths:
        try:
            with open(p, encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            continue
        except json.JSONDecodeError as e:
            st.error(f"JSON invalide dans {p}: {e}")
            st.stop()
    st.error(f"Aucun fichier trouvé parmi: {', '.join(paths)}")
    st.stop()

# Chemins possibles (compatible avec la structure du dépôt)
faction_paths = [
    'data/factions/sisters_blessed.json',
    'data/lists/data/factions/sisters_blessed.json'
]
rules_paths = [
    'data/rules/opr_limits.json',
    'data/lists/data/rules/opr_limits.json'
]
faction = try_load(faction_paths)
rules = try_load(rules_paths)

# --- Paramètres des jeux OPR ---
GAMES = [
    "Age of Fantasy",
    "Age of Fantasy Skirmish",
    "Age of Fantasy Regiment",
    "Grimdark Future",
    "Grimdark Future Firefight",
    "Warfleet",
]

# Valeurs par défaut (fallback) pour unit_per_points par jeu si non présentes dans rules
DEFAULT_UNIT_PER_POINTS_BY_GAME = {
    "Age of Fantasy": 200,
    "Age of Fantasy Skirmish": 100,
    "Age of Fantasy Regiment": 300,
    "Grimdark Future": 200,
    "Grimdark Future Firefight": 150,
    "Warfleet": 400,
}

DEFAULT_FALLBACK_UNIT_PER_POINTS = 200

st.title('OPR Army Builder 🇫🇷')

# Choix du jeu OPR
selected_game = st.selectbox('Variante OPR (jeu)', GAMES, index=0)

# Résolution de unit_per_points : priorité rules['unit_per_points_by_game'][game] -> rules['unit_per_points'] -> DEFAULT_UNIT_PER_POINTS_BY_GAME[game] -> DEFAULT_FALLBACK_UNIT_PER_POINTS
unit_per_points = None
if isinstance(rules, dict):
    upp_by_game = rules.get('unit_per_points_by_game')
    if isinstance(upp_by_game, dict):
        unit_per_points = upp_by_game.get(selected_game)
    if unit_per_points is None:
        unit_per_points = rules.get('unit_per_points')

if unit_per_points is None:
    unit_per_points = DEFAULT_UNIT_PER_POINTS_BY_GAME.get(selected_game, DEFAULT_FALLBACK_UNIT_PER_POINTS)

# Ensure integer
try:
    unit_per_points = int(unit_per_points)
except (TypeError, ValueError):
    unit_per_points = DEFAULT_FALLBACK_UNIT_PER_POINTS

# Affichage en en-tête
st.subheader(f"Faction : {faction.get('faction','Inconnue')}")
st.caption(f"Jeu sélectionné : {selected_game} — unit_per_points utilisé : {unit_per_points}")

# Initialisation
if 'army' not in st.session_state:
    st.session_state.army = []

# Sélection et ajout d'unité
units = faction.get('units', [])
if not isinstance(units, list) or not units:
    st.warning('Aucune unité disponible pour cette faction.')
else:
    unit_names = [u.get('name','Sans nom') for u in units]
    col1, col2 = st.columns([3,1])
    with col1:
        selected_unit = st.selectbox('Ajouter une unité', unit_names)
    with col2:
        if st.button('➕ Ajouter'):
            unit = next((u for u in units if u.get('name') == selected_unit), None)
            if unit:
                u_copy = dict(unit)
                # Normaliser le coût
                raw_cost = u_copy.get('base_cost', u_copy.get('cost', 0))
                try:
                    u_copy['base_cost'] = int(raw_cost)
                except (TypeError, ValueError):
                    u_copy['base_cost'] = 0
                st.session_state.army.append(u_copy)

# Affichage de l'armée avec possibilité de suppression
st.subheader('🧾 Liste actuelle')
if not st.session_state.army:
    st.info('Aucune unité ajoutée.')
else:
    for idx, u in enumerate(list(st.session_state.army)):
        cols = st.columns([6,1])
        with cols[0]:
            st.write(f"- {u.get('name','Sans nom')} ({u.get('base_cost',0)} pts)")
        with cols[1]:
            if st.button('🗑️', key=f'del_{idx}'):
                st.session_state.army.pop(idx)
                st.experimental_rerun()

# Budget et calculs
points_budget = st.number_input('Budget total de points', min_value=0, value=1000, step=50)

# Somme des points
total_points = sum(int(u.get('base_cost', 0)) for u in st.session_state.army)
st.markdown(f"### Total : **{total_points} pts**")

# Validation des règles (utilise unit_per_points résolu pour la variante)
if not isinstance(unit_per_points, int) or unit_per_points <= 0:
    st.warning("Règle 'unit_per_points' manquante ou invalide. Impossible de vérifier la limite d'unités.")
else:
    max_units = points_budget // unit_per_points
    if total_points > points_budget:
        st.error('❌ Coût total dépasse le budget de points')
    elif len(st.session_state.army) > max_units:
        st.error('❌ Trop d’unités selon les règles OPR (par rapport au budget)')
    else:
        st.success('✅ Liste valide')

# Afficher règles & debug utile (inclut maintenant le jeu sélectionné)
with st.expander('Règles (debug)'):
    st.write('Jeu sélectionné :', selected_game)
    st.write('unit_per_points appliqué :', unit_per_points)
    st.json(rules)
    st.write('Chemins testés pour faction:', faction_paths)
    st.write('Chemins testés pour règles:', rules_paths)
