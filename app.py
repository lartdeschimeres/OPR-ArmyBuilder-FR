import json
import streamlit as st
from pathlib import Path
from datetime import datetime
import hashlib
import re
import base64
import math
import copy  # Ajout de l'import manquant

# [Toutes vos autres imports et configurations restent identiques...]

# ======================================================
# PAGE 2 – CONSTRUCTEUR D'ARMÉE (VERSION CORRIGÉE)
# ======================================================
elif st.session_state.page == "army":
    # Initialisation de l'historique si nécessaire
    if "history" not in st.session_state:
        st.session_state.history = []

    st.title(st.session_state.list_name)
    st.caption(f"{st.session_state.game} • {st.session_state.faction} • {st.session_state.army_cost}/{st.session_state.points} pts")

    # Boutons de contrôle en haut de page
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
            # Sauvegarder l'état actuel avant réinitialisation
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

    # Vérification des règles spécifiques au jeu
    game_config = GAME_CONFIG.get(st.session_state.game, GAME_CONFIG["Age of Fantasy"])

    # AFFICHAGE DES RÈGLES SPÉCIALES DE LA FACTION
    faction_data = factions_by_game[st.session_state.game][st.session_state.faction]
    display_faction_rules(faction_data)

    if not validate_army_rules(st.session_state.army_list, st.session_state.points, st.session_state.game):
        st.warning("⚠️ Certaines règles spécifiques ne sont pas respectées.")

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

    # Gestion des unités combinées - CORRECTION DÉFINITIVE POUR LES HÉROS
    if unit.get("type") == "hero":
        combined = False  # Les héros ne peuvent JAMAIS être combinés
    else:
        combined = st.checkbox("Unité combinée", value=False)

    # [Le reste de votre code pour les options d'unité reste identique...]

    # Calcul du coût final et de la taille
    if combined and unit.get("type") != "hero":
        final_cost = (base_cost + weapon_cost) * 2 + mount_cost + upgrades_cost
        unit_size = base_size * 2
    else:
        final_cost = base_cost + weapon_cost + mount_cost + upgrades_cost
        unit_size = base_size

    # Vérification finale du coût maximum
    if not check_unit_max_cost(st.session_state.army_list, st.session_state.points, game_config, final_cost):
        st.stop()

    # Affichage des informations
    if unit.get("type") == "hero":
        st.markdown(f"**Taille finale: 1** (les héros sont toujours des unités individuelles)")
    else:
        st.markdown(f"**Taille finale: {unit_size}** {'(x2 combinée)' if combined else ''}")
    st.markdown(f"**Coût total: {final_cost} pts**")

    if st.button("Ajouter à l'armée"):
        try:
            # Sauvegarder l'état actuel avant l'ajout
            st.session_state.history.append({
                "army_list": copy.deepcopy(st.session_state.army_list),
                "army_cost": st.session_state.army_cost
            })

            # [Votre code existant pour créer unit_data...]

            # Vérification des règles avant d'ajouter
            test_army = copy.deepcopy(st.session_state.army_list)
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
            # [Votre code existant pour afficher les unités...]

            if st.button(f"Supprimer {u['name']}", key=f"del_{i}"):
                # Sauvegarder l'état avant suppression
                st.session_state.history.append({
                    "army_list": copy.deepcopy(st.session_state.army_list),
                    "army_cost": st.session_state.army_cost
                })
                st.session_state.army_cost -= u["cost"]
                st.session_state.army_list.pop(i)
                st.rerun()

    # Sauvegarde/Export (votre code existant est correct)
    # [Votre code existant pour la sauvegarde et l'export...]
