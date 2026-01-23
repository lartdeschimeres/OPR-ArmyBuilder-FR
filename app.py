# ======================================================
# PAGE 1 – CONFIGURATION (modifiée)
# ======================================================
if st.session_state.page == "setup":
    st.title("OPR Army Forge FR")

    # Affichage des informations sur les jeux disponibles
    st.subheader("Jeux disponibles")
    for game_key, config in GAME_CONFIG.items():
        with st.expander(f"📖 {config['display_name']}"):
            st.markdown(f"""
            **Description**: {config['description']}
            - **Points**: {config['min_points']} à {config['max_points']} (défaut: {config['default_points']})
            """)

            if game_key == "Age of Fantasy":
                st.markdown(f"""
                **Règles spécifiques à Age of Fantasy:**
                - 1 Héros par tranche de {config['hero_limit']} pts d'armée
                - 1+X copies de la même unité (X=1 pour {config['unit_copy_rule']} pts d'armée)
                - Aucune unité ne peut valoir plus de {int(config['unit_max_cost_ratio']*100)}% du total des points
                - 1 unité maximum par tranche de {config['unit_per_points']} pts d'armée
                """)

    # Liste des listes sauvegardées
    st.subheader("Mes listes sauvegardées")

    # Chargement des listes sauvegardées
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
                            st.session_state.page = "army"
                            st.rerun()
        except Exception as e:
            st.error(f"Erreur chargement listes: {e}")

    if not games:
        st.error("Aucun jeu trouvé")
        st.stop()

    # Sélection du jeu
    game = st.selectbox("Jeu", games)
    game_config = GAME_CONFIG.get(game, GAME_CONFIG["Age of Fantasy"])

    # Sélection de la faction (ajouté ici)
    if game in factions_by_game and factions_by_game[game]:
        available_factions = list(factions_by_game[game].keys())
        faction = st.selectbox("Faction", available_factions)
    else:
        st.warning("Aucune faction disponible pour ce jeu")
        faction = None

    # Sélection des points
    points = st.number_input(
        "Points",
        min_value=game_config["min_points"],
        max_value=game_config["max_points"],
        value=game_config["default_points"],
        step=game_config["point_step"]
    )

    list_name = st.text_input("Nom de la liste", f"Liste_{datetime.now().strftime('%Y%m%d')}")

    # Affichage des règles spécifiques
    st.markdown(f"""
    **Règles pour {game_config['display_name']}:**
    - 1 Héros par tranche de {game_config['hero_limit']} pts
    - 1+X copies de la même unité (X=1 pour {game_config['unit_copy_rule']} pts)
    - Aucune unité ne peut valoir plus de {int(game_config['unit_max_cost_ratio']*100)}% du total des points
    - 1 unité maximum par tranche de {game_config['unit_per_points']} pts
    """)

    # Import JSON
    uploaded = st.file_uploader("Importer une liste JSON", type=["json"])
    if uploaded:
        try:
            data = json.load(uploaded)
            if not all(key in data for key in ["game", "faction", "army_list", "points"]):
                st.error("Format JSON invalide: les clés 'game', 'faction', 'army_list' et 'points' sont requises")
                st.stop()

            # Vérification que les points de la liste importée ne dépassent pas la limite
            total_cost = data.get("total_cost", sum(u["cost"] for u in data["army_list"]))
            if total_cost > data["points"]:
                st.error(f"La liste importée dépasse sa limite de points ({data['points']} pts). Total actuel: {total_cost} pts")
                st.stop()

            st.session_state.game = data["game"]
            st.session_state.faction = data["faction"]
            st.session_state.points = data["points"]
            st.session_state.list_name = data["name"]
            st.session_state.army_list = data["army_list"]
            st.session_state.army_cost = total_cost
            st.session_state.units = factions_by_game[data["game"]][data["faction"]]["units"]
            st.session_state.page = "army"
            st.rerun()
        except Exception as e:
            st.error(f"Erreur d'import: {str(e)}")

    if st.button("Créer une nouvelle liste"):
        if not faction:
            st.error("Veuillez sélectionner une faction")
        else:
            st.session_state.game = game
            st.session_state.faction = faction
            st.session_state.points = points
            st.session_state.list_name = list_name
            st.session_state.units = factions_by_game[game][faction]["units"]
            st.session_state.army_list = []
            st.session_state.army_cost = 0
            st.session_state.page = "army"
            st.rerun()
