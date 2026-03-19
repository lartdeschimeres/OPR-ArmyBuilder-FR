import streamlit as st


class SessionStateManager:
    DEFAULTS = {
        "page": "setup",
        "army_list": [],
        "army_cost": 0,
        "unit_selections": {},
        "draft_counter": 0,
        "draft_unit_name": "",
        "game": None,
        "faction": None,
        "points": 0,
        "list_name": "",
        "units": [],
        "faction_special_rules": [],
        "faction_spells": {},
        "unit_filter": "Tous",
    }

    def ensure_defaults(self) -> None:
        for key, value in self.DEFAULTS.items():
            st.session_state.setdefault(key, value)

    def reset_army_builder(self) -> None:
        st.session_state.army_list = []
        st.session_state.army_cost = 0
        st.session_state.unit_selections = {}

