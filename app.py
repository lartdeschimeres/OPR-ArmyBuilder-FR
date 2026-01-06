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

# Initialisation
if 'army' not in st.session_state:
    st.session_state.army = []

st.title('OPR Army Builder 🇫🇷')
st.subheader(f"Faction : {faction.get('faction','Inconnue')}")

# Sélection et ajout d'unité
units = faction.get('units', [])
if not isinstance(units, list) or not units:
    st.warning('Aucune unité disponible pour cette faction.')
else:
    unit_names = [u.get('name','Sans nom') for u in units]
    col1, col2 = st.columns([3,1])
    with col1:
        selected = st.selectbox('Ajouter une unité', unit_names)
    with col2:
        if st.button('➕ Ajouter'):
            unit = next((u for u in units if u.get('name') == selected), None)
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
unit_per_points = rules.get('unit_per_points')

# Somme des points
total_points = sum(int(u.get('base_cost', 0)) for u in st.session_state.army)
st.markdown(f"### Total : **{total_points} pts**")

# Validation des règles
if not isinstance(unit_per_points, int) or unit_per_points <= 0:
    st.warning("Règle 'unit_per_points' manquante ou invalide dans les règles. Impossible de vérifier la limite d'unités.")
else:
    max_units = points_budget // unit_per_points
    if total_points > points_budget:
        st.error('❌ Coût total dépasse le budget de points')
    elif len(st.session_state.army) > max_units:
        st.error('❌ Trop d’unités selon les règles OPR (par rapport au budget)')
    else:
        st.success('✅ Liste valide')

# Afficher règles & debug utile
with st.expander('Règles (debug)'):
    st.json(rules)
    st.write('Chemins testés pour faction:', faction_paths)
    st.write('Chemins testés pour règles:', rules_paths)
