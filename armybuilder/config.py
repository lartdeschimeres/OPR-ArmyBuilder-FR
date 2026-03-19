GAME_COLORS = {
    "Age of Fantasy": "#2980b9",
    "Age of Fantasy Regiments": "#8e44ad",
    "Grimdark Future": "#c0392b",
    "Grimdark Future Firefight": "#e67e22",
    "Age of Fantasy Skirmish": "#27ae60",
}

GAME_CONFIG = {
    "Age of Fantasy": {
        "min_points": 250,
        "max_points": 10000,
        "default_points": 1000,
        "hero_limit": 375,
        "unit_copy_rule": 750,
        "unit_max_cost_ratio": 0.35,
        "unit_per_points": 150,
    },
    "Age of Fantasy Regiments": {
        "min_points": 500,
        "max_points": 20000,
        "default_points": 2000,
        "hero_limit": 500,
        "unit_copy_rule": 1000,
        "unit_max_cost_ratio": 0.4,
        "unit_per_points": 200,
    },
    "Grimdark Future": {
        "min_points": 250,
        "max_points": 10000,
        "default_points": 1000,
        "hero_limit": 375,
        "unit_copy_rule": 750,
        "unit_max_cost_ratio": 0.35,
        "unit_per_points": 150,
    },
    "Grimdark Future Firefight": {
        "min_points": 150,
        "max_points": 1000,
        "default_points": 300,
        "hero_limit": 300,
        "unit_copy_rule": 300,
        "unit_max_cost_ratio": 0.6,
        "unit_per_points": 100,
    },
    "Age of Fantasy Skirmish": {
        "min_points": 150,
        "max_points": 1000,
        "default_points": 300,
        "hero_limit": 300,
        "unit_copy_rule": 300,
        "unit_max_cost_ratio": 0.6,
        "unit_per_points": 100,
    },
}

GAME_META = {
    "Age of Fantasy": {"color": "#2980b9", "short": "AoF"},
    "Age of Fantasy Regiments": {"color": "#8e44ad", "short": "AoF:R"},
    "Grimdark Future": {"color": "#c0392b", "short": "GDF"},
    "Grimdark Future Firefight": {"color": "#e67e22", "short": "GDF:FF"},
    "Age of Fantasy Skirmish": {"color": "#27ae60", "short": "AoF:S"},
}

GAME_SUBTITLES = {
    "Age of Fantasy": "Construisez vos armees pour les batailles fantastiques",
    "Age of Fantasy Regiments": "Forgez vos regiments pour la guerre des ages",
    "Grimdark Future": "Forgez vos escouades pour les guerres du futur",
    "Grimdark Future Firefight": "Constituez vos escouades pour les combats rapproches",
    "Age of Fantasy Skirmish": "Composez vos bandes pour l'escarmouche fantastique",
}

SECTION_LABELS = {
    "named_hero": ("Heros nommes", "★"),
    "hero": ("Heros", "🦸"),
    "unit": ("Unites de base", "⚔️"),
    "light_vehicle": ("Vehicules legers", "🐉"),
    "vehicle": ("Vehicules / Monstres", "🏰"),
    "titan": ("Titans", "💀"),
}

FILTER_CATEGORIES = {
    "Tous": None,
    "Heros": ["hero"],
    "Heros nommes": ["named_hero"],
    "Unites de base": ["unit"],
    "Vehicules legers / Petits monstres": ["light_vehicle"],
    "Vehicules / Monstres": ["vehicle"],
    "Titans": ["titan"],
}
