import os
import csv
import glob
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

def load_faction_mapping(csv_path="data/factions_by_game.csv"):
    mapping = {}
    if not os.path.exists(csv_path):
        return mapping, f"Mapping non trouvé: {csv_path}"
    try:
        with open(csv_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Normaliser les clés (au cas où)
                game = (row.get('Game') or row.get('game') or '').strip()
                filep = (row.get('faction_file') or row.get('Faction_file') or '').strip()
                name = (row.get('faction_name') or row.get('faction') or row.get('Faction') or '').strip()
                if not game:
                    continue
                entry = {'file': filep if filep else None, 'name': name if name else None}
                mapping.setdefault(game, []).append(entry)
        return mapping, f"Mapping chargé depuis {csv_path}"
    except Exception as e:
        return {}, f"Erreur lecture mapping CSV: {e}"

def scan_faction_jsons(dirs=None):
    if dirs is None:
        dirs = ['data/lists/data/factions', 'data/factions']
    found = []
    for d in dirs:
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if not fn.lower().endswith('.json'):
                continue
            p = os.path.join(d, fn)
            try:
                with open(p, encoding='utf-8') as f:
                    j = json.load(f)
                    display = j.get('faction') or j.get('name') or os.path.splitext(fn)[0]
            except Exception:
                display = os.path.splitext(fn)[0]
            found.append({'file': p, 'name': display})
    return found

# Chemins possibles (compatible avec la structure du dépôt)
faction_paths = [
    #'data/factions/sisters_blessed.json',
    'data/lists/data/factions/sisters_blessed.json'
]
rules_paths = [
    'data/rules/opr_limits.json',
    'data/lists/data/rules/opr_limits.json'
]

# Charger rules & fallback faction initiale (gardées si aucun choix fait)
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

# Résolution de unit_per_points : priority rules['unit_per_points_by_game'][game] -> rules['unit_per_points'] -> DEFAULT_UNIT_PER_POINTS_BY_GAME[game] -> DEFAULT_FALLBACK_UNIT_PER_POINTS
unit_per_points = None
if isinstance(rules, dict):
    upp_by_game = rules.get('unit_per_points_by_game')
    if isinstance(upp_by_game, dict):
        unit_per_points = upp_by_game.get(selected_game)
    if unit_per_points is None:
        unit_per_points = rules.get('unit_per_points')
if unit_per_points is None:
    unit_per_points = DEFAULT_UNIT_PER_POINTS_BY_GAME.get(selected_game, DEFAULT_FALLBACK_UNIT_PER_POINTS)
try:
    unit_per_points = int(unit_per_points)
except (TypeError, ValueError):
    unit_per_points = DEFAULT_FALLBACK_UNIT_PER_POINTS

# Chargement du mapping CSV
mapping, mapping_status = load_faction_mapping("data/factions_by_game.csv")

# Construire la liste des options de factions pour le jeu sélectionné
faction_options = []  # list of dicts {name:<display>, file:<path or None>}
seen_names = set()
seen_files = set()

# 1) depuis le mapping CSV
for entry in mapping.get(selected_game, []):
    filep = entry.get('file')
    name = entry.get('name') or None
    if filep:
        # si le fichier existe, essayer de lire le nom depuis le JSON si name absent
        if os.path.exists(filep):
            try:
                with open(filep, encoding='utf-8') as f:
                    j = json.load(f)
                    json_name = j.get('faction') or j.get('name')
            except Exception:
                json_name = None
            display = name or json_name or os.path.splitext(os.path.basename(filep))[0]
            if display not in seen_names:
                faction_options.append({'name': display, 'file': filep})
                seen_names.add(display)
                seen_files.add(os.path.abspath(filep))
        else:
            # fichier référencé manquant : ajouter nom si présent, sinon skip
            if name:
                if name not in seen_names:
                    faction_options.append({'name': name, 'file': None})
                    seen_names.add(name)
    else:
        # pas de fichier fourni, on a juste un nom
        if name and name not in seen_names:
            faction_options.append({'name': name, 'file': None})
            seen_names.add(name)

# 2) fallback : scanner les dossiers JSON et ajouter ceux non listés
for found in scan_faction_jsons():
    absf = os.path.abspath(found['file'])
    if absf in seen_files or found['name'] in seen_names:
        continue
    faction_options.append({'name': found['name'], 'file': found['file']})
    seen_names.add(found['name'])
    seen_files.add(absf)

# Si aucune option, garder la faction actuelle (chargée par défaut)
if not faction_options:
    st.warning("Aucune faction trouvée pour ce jeu (mapping CSV et dossiers JSON vides). L'app utilisera la faction par défaut.")
    selected_faction_path = None
else:
    # Présenter selectbox avec les noms
    names = [e['name'] for e in faction_options]
    sel_idx = st.selectbox("Sélectionner la faction", names, index=0)
    selected_entry = faction_options[names.index(sel_idx)]
    selected_faction_path = selected_entry.get('file')

    # si on a un fichier JSON, le charger et remplacer la variable faction
    if selected_faction_path:
        if os.path.exists(selected_faction_path):
            try:
                with open(selected_faction_path, encoding='utf-8') as f:
                    faction = json.load(f)
            except Exception as e:
                st.error(f"Impossible de lire le fichier JSON de la faction: {selected_faction_path} — {e}")
        else:
            st.warning(f"Fichier JSON de la faction introuvable: {selected_faction_path}")

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

# Afficher règles & debug utile (inclut maintenant le jeu sélectionné et mapping)
with st.expander('Règles (debug)'):
    st.write('Mapping status:', mapping_status)
    st.write('Jeu sélectionné :', selected_game)
    st.write('unit_per_points appliqué :', unit_per_points)
    st.write('Faction selectionnée (file) :', selected_faction_path)
    st.write('Nombre d\'options de faction pour ce jeu:', len(faction_options))
    # afficher les 20 premières options pour debug si très nombreuses
    st.write('Options (extrait) :', [e['name'] for e in faction_options[:50]])
    st.json(rules)
    st.write('Chemins testés pour faction:', faction_paths)
    st.write('Chemins testés pour règles:', rules_paths)
