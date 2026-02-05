from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import json
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone

ROOT_DIR = Path(__file__).parent
DATA_DIR = ROOT_DIR / 'data'
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ===== MODELS =====

class Weapon(BaseModel):
    name: str
    range: str = "-"
    attacks: int
    armor_piercing: Any = "-"
    special_rules: List[str] = []

class Mount(BaseModel):
    name: str
    special_rules: List[str] = []

class UpgradeOption(BaseModel):
    name: str
    cost: int
    weapon: Optional[Weapon] = None
    mount: Optional[Mount] = None
    special_rules: List[str] = []

class UpgradeGroup(BaseModel):
    group: str
    type: str  # "weapon", "upgrades", "mount"
    description: str = ""
    options: List[UpgradeOption] = []

class Unit(BaseModel):
    name: str
    original_name: Optional[str] = None
    type: str = "unit"  # "hero" or "unit"
    size: int = 1
    base_cost: int
    quality: int
    defense: int
    equipment: List[str] = []
    special_rules: List[str] = []
    weapons: List[Weapon] = []
    upgrade_groups: List[UpgradeGroup] = []

class Spell(BaseModel):
    cost: int
    description: str
    range: str = ""
    target: str = ""

class Faction(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    faction: str
    game: str
    version: str = ""
    status: str = "complete"
    description: str = ""
    special_rules_descriptions: Dict[str, str] = {}
    spells: Dict[str, Spell] = {}
    units: List[Unit] = []

class FactionCreate(BaseModel):
    faction: str
    game: str
    version: str = ""
    status: str = "complete"
    description: str = ""
    special_rules_descriptions: Dict[str, str] = {}
    spells: Dict[str, Any] = {}
    units: List[Dict[str, Any]] = []

# Army roster models
class SelectedUpgrade(BaseModel):
    group: str
    option_name: str
    cost: int

class RosterUnit(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    unit_name: str
    unit_type: str  # "hero" or "unit"
    base_cost: int
    selected_upgrades: List[SelectedUpgrade] = []
    combined_unit: bool = False
    total_cost: int = 0

class Army(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    game: str
    faction: str
    points_limit: int
    units: List[RosterUnit] = []
    total_points: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ArmyCreate(BaseModel):
    name: str
    game: str
    faction: str
    points_limit: int
    units: List[Dict[str, Any]] = []

class ArmyUpdate(BaseModel):
    name: Optional[str] = None
    points_limit: Optional[int] = None
    units: Optional[List[Dict[str, Any]]] = None

# Validation models
class ValidationError(BaseModel):
    type: str  # "error" or "warning"
    message: str
    unit_id: Optional[str] = None

class ValidationResult(BaseModel):
    valid: bool
    errors: List[ValidationError] = []
    total_points: int = 0
    max_hero_count: int = 0
    current_hero_count: int = 0

# ===== GAME DATA =====

GAMES = [
    {
        "id": "grimdark-future",
        "name": "Grimdark Future",
        "short_name": "GF",
        "description": "Sci-fi wargame in a dark future where there is only war",
        "image": "https://customer-assets.emergentagent.com/job_tabletop-roster/artifacts/4yhnbky1_gf_cover.jpg"
    },
    {
        "id": "grimdark-future-firefight",
        "name": "Grimdark Future Firefight",
        "short_name": "GFF",
        "description": "Small-scale skirmish battles in the grimdark future",
        "image": "https://customer-assets.emergentagent.com/job_tabletop-roster/artifacts/x3uaye60_gff_cover.jpg"
    },
    {
        "id": "grimdark-future-squad",
        "name": "Grimdark Future Squad",
        "short_name": "GFSQ",
        "description": "Squad-based tactical combat in the grimdark future",
        "image": "https://customer-assets.emergentagent.com/job_tabletop-roster/artifacts/n649vrml_gfsq_cover.jpg"
    },
    {
        "id": "age-of-fantasy",
        "name": "Age of Fantasy",
        "short_name": "AoF",
        "description": "Fantasy wargame with magic, monsters and epic battles",
        "image": "https://customer-assets.emergentagent.com/job_tabletop-roster/artifacts/ef8vm2eh_aof_cover.jpg"
    },
    {
        "id": "age-of-fantasy-regiments",
        "name": "Age of Fantasy Regiments",
        "short_name": "AoFR",
        "description": "Ranked combat fantasy wargame with massive armies",
        "image": "https://customer-assets.emergentagent.com/job_tabletop-roster/artifacts/egkkuekh_aofr_cover.jpg"
    },
    {
        "id": "age-of-fantasy-skirmish",
        "name": "Age of Fantasy Skirmish",
        "short_name": "AoFS",
        "description": "Small-scale skirmish battles in a fantasy world",
        "image": "https://customer-assets.emergentagent.com/job_tabletop-roster/artifacts/mnmh2se3_aofs_cover.jpg"
    },
    {
        "id": "age-of-fantasy-quest",
        "name": "Age of Fantasy Quest",
        "short_name": "AoFQ",
        "description": "Cooperative dungeon crawling adventure game",
        "image": "https://customer-assets.emergentagent.com/job_tabletop-roster/artifacts/00yl2v7x_aofq_cover.jpg"
    },
    {
        "id": "warfleets-ftl",
        "name": "Warfleets: FTL",
        "short_name": "FTL",
        "description": "Space fleet combat and interstellar warfare",
        "image": "https://customer-assets.emergentagent.com/job_tabletop-roster/artifacts/gk19bhic_ftl_cover.jpg"
    }
]

# Sample faction data to seed
SAMPLE_FACTIONS = [
    {
        "faction": "Disciples de la Guerre",
        "game": "Age of Fantasy",
        "version": "FR-3.5.2",
        "status": "complete",
        "description": "Les Disciples de la Guerre sont une faction brutale et impitoyable, composée de guerriers fanatiques et de monstres déchaînés.",
        "special_rules_descriptions": {
            "Warbound [Guerrier-né]": "Les ennemis qui lancent les dés pour bloquer les touches infligées par les armes de cette figurine subissent une blessure supplémentaire pour chaque résultat non modifié de 1 obtenu.",
            "Bloodthirsty Fighter [Combattant sanguinaire]": "Pour chaque résultat de 1 non modifié obtenu par les ennemis lorsqu'ils bloquent les touches portées par les armes de cette figurine en mêlée, cette figurine peut effectuer un jet d'attaque supplémentaire."
        },
        "spells": {
            "Terrifying Fury [Fureur terrifiante]": {"cost": 1, "description": "Choisissez une unité ennemie à 18\" ou moins, qui doit effectuer un Test de Moral.", "range": "18\"", "target": "1 unité ennemie"},
            "Flame of Destruction [Flammes de la destruction]": {"cost": 1, "description": "Choisissez une unité ennemie à 18\" ou moins, qui subit une touche avec Explosion (3).", "range": "18\"", "target": "1 unité ennemie"},
            "Fiery Protection [Protection ardente]": {"cost": 2, "description": "Choisissez jusqu'à deux unités amies à 12\" ou moins, qui obtiennent Esquive en mêlée.", "range": "12\"", "target": "jusqu'à 2 unités amies"},
            "Brutal Massacre [Massacre brutal]": {"cost": 2, "description": "Choisissez une unité ennemie à 6\" ou moins qui subit six touches avec Dislocation.", "range": "6\"", "target": "1 unité ennemie"},
            "War Boon [Bénédiction guerrière]": {"cost": 3, "description": "Choisissez jusqu'à trois unités amies à 12\" ou moins, qui bénéficient une fois de Boost de Guerrier-né.", "range": "12\"", "target": "jusqu'à 3 unités amies"},
            "Headtaker Strike [Décapitation]": {"cost": 3, "description": "Choisissez jusqu'à deux unités ennemies à 12\" ou moins, qui subissent chacune trois blessures avec PA (2).", "range": "12\"", "target": "jusqu'à 2 unités ennemies"}
        },
        "units": [
            {
                "name": "Maître du Ravage de la Guerre Élu",
                "type": "hero",
                "size": 1,
                "base_cost": 65,
                "quality": 3,
                "defense": 3,
                "special_rules": ["Attaque versatile", "Coriace (3)", "Héros", "Guerrier-né"],
                "weapons": [{"name": "Arme à une main lourde", "range": "-", "attacks": 3, "armor_piercing": 1}],
                "upgrade_groups": [
                    {
                        "group": "Améliorations de rôle",
                        "type": "upgrades",
                        "description": "Choisissez un rôle spécial pour ce héros (un seul choix possible)",
                        "options": [
                            {"name": "Conquérant (Aura d'Éclaireur)", "cost": 20, "special_rules": ["Aura d'Éclaireur"]},
                            {"name": "Marauder (Aura de Combattant imprévisible)", "cost": 30, "special_rules": ["Aura de Combattant imprévisible"]},
                            {"name": "Porteur de la bannière de l'armée (Effrayant (3))", "cost": 30, "special_rules": ["Effrayant (3)"]},
                            {"name": "Ensorceleur (Aura de Voile fluctuant)", "cost": 35, "special_rules": ["Aura de Voile fluctuant"]},
                            {"name": "Sorcier (Lanceur de sorts (2))", "cost": 40, "special_rules": ["Lanceur de sorts (2)"]},
                            {"name": "Seigneur de Guerre (Aura de Boost de Guerrier-né)", "cost": 50, "special_rules": ["Aura de Boost de Guerrier-né"]},
                            {"name": "Maître Sorcier (Lanceur de sorts (3))", "cost": 65, "special_rules": ["Lanceur de sorts (3)"]}
                        ]
                    },
                    {
                        "group": "Remplacement d'arme",
                        "type": "weapon",
                        "description": "Remplacez l'arme de base par:",
                        "options": [
                            {"name": "Hallebarde lourde", "cost": 5, "weapon": {"name": "Hallebarde lourde", "range": "-", "attacks": 3, "armor_piercing": 1, "special_rules": ["Perforant"]}},
                            {"name": "Paire d'armes à une main lourdes", "cost": 15, "weapon": {"name": "Paire d'armes à une main lourdes", "range": "-", "attacks": 4, "armor_piercing": 1}},
                            {"name": "Grande arme lourde", "cost": 15, "weapon": {"name": "Grande arme lourde", "range": "-", "attacks": 3, "armor_piercing": 3}},
                            {"name": "Lance lourde", "cost": 15, "weapon": {"name": "Lance lourde", "range": "-", "attacks": 3, "armor_piercing": 1, "special_rules": ["Percée"]}}
                        ]
                    },
                    {
                        "group": "Montures",
                        "type": "mount",
                        "description": "Ajoutez une monture",
                        "options": [
                            {"name": "Cheval", "cost": 15, "mount": {"name": "Cheval", "special_rules": ["Impact (1)", "Rapide"]}},
                            {"name": "Grande bête", "cost": 70, "mount": {"name": "Grande bête", "special_rules": ["Griffes lourdes (A1, PA(1))", "Coriace (3)", "Impact (2)", "Rapide"]}},
                            {"name": "Monture démoniaque", "cost": 80, "mount": {"name": "Monture démoniaque", "special_rules": ["Griffes lourdes (A1, PA(1))", "Coriace (3)", "Effrayant (1)", "Impact (2)", "Rapide"]}},
                            {"name": "Char", "cost": 125, "mount": {"name": "Char", "special_rules": ["Sabots (A2)", "Coriace (6)", "Impact (4)", "Rapide"]}},
                            {"name": "Char bestial", "cost": 140, "mount": {"name": "Char bestial", "special_rules": ["Griffes lourdes (A2, PA(1))", "Coriace (6)", "Effrayant (1)", "Impact (4)", "Rapide"]}},
                            {"name": "Manticore", "cost": 165, "mount": {"name": "Manticore", "special_rules": ["Griffes perforantes (A6, Perforant)", "Coriace (6)", "Effrayant (1)", "Volant"]}},
                            {"name": "Dragon du Ravage", "cost": 325, "mount": {"name": "Dragon du Ravage", "special_rules": ["Griffes lourdes (A6, PA(1))", "Piétinement (A4, PA(1))", "Attaque de souffle", "Coriace (12)", "Effrayant (2)", "Volant"]}}
                        ]
                    }
                ]
            },
            {
                "name": "Maître du Ravage de la Guerre",
                "type": "hero",
                "size": 1,
                "base_cost": 55,
                "quality": 3,
                "defense": 3,
                "special_rules": ["Coriace (3)", "Héros", "Guerrier-né"],
                "weapons": [{"name": "Arme à une main lourde", "range": "-", "attacks": 3, "armor_piercing": 1}],
                "upgrade_groups": [
                    {
                        "group": "Améliorations de rôle",
                        "type": "upgrades",
                        "description": "Choisissez un rôle spécial pour ce héros (un seul choix possible)",
                        "options": [
                            {"name": "Conquérant (Aura d'Éclaireur)", "cost": 20, "special_rules": ["Aura d'Éclaireur"]},
                            {"name": "Marauder (Aura de Combattant imprévisible)", "cost": 30, "special_rules": ["Aura de Combattant imprévisible"]},
                            {"name": "Porteur de la bannière de l'armée (Effrayant (3))", "cost": 30, "special_rules": ["Effrayant (3)"]},
                            {"name": "Ensorceleur (Aura de Voile fluctuant)", "cost": 35, "special_rules": ["Aura de Voile fluctuant"]},
                            {"name": "Sorcier (Lanceur de sorts (2))", "cost": 40, "special_rules": ["Lanceur de sorts (2)"]},
                            {"name": "Seigneur de Guerre (Aura de Boost de Guerrier-né)", "cost": 50, "special_rules": ["Aura de Boost de Guerrier-né"]},
                            {"name": "Maître Sorcier (Lanceur de sorts (3))", "cost": 65, "special_rules": ["Lanceur de sorts (3)"]}
                        ]
                    },
                    {
                        "group": "Remplacement d'arme",
                        "type": "weapon",
                        "description": "Remplacez l'arme de base par:",
                        "options": [
                            {"name": "Hallebarde lourde", "cost": 5, "weapon": {"name": "Hallebarde lourde", "range": "-", "attacks": 3, "armor_piercing": 1, "special_rules": ["Perforant"]}},
                            {"name": "Paire d'armes à une main lourdes", "cost": 10, "weapon": {"name": "Paire d'armes à une main lourdes", "range": "-", "attacks": 4, "armor_piercing": 1}},
                            {"name": "Grande arme lourde", "cost": 15, "weapon": {"name": "Grande arme lourde", "range": "-", "attacks": 3, "armor_piercing": 3}},
                            {"name": "Lance lourde", "cost": 15, "weapon": {"name": "Lance lourde", "range": "-", "attacks": 3, "armor_piercing": 1, "special_rules": ["Percée"]}}
                        ]
                    },
                    {
                        "group": "Montures",
                        "type": "mount",
                        "description": "Ajoutez une monture",
                        "options": [
                            {"name": "Cheval", "cost": 15, "mount": {"name": "Cheval", "special_rules": ["Impact (1)", "Rapide"]}},
                            {"name": "Grande bête", "cost": 65, "mount": {"name": "Grande bête", "special_rules": ["Griffes lourdes (A1, PA(1))", "Coriace (3)", "Impact (2)", "Rapide"]}},
                            {"name": "Monture démoniaque", "cost": 75, "mount": {"name": "Monture démoniaque", "special_rules": ["Griffes lourdes (A1, PA(1))", "Coriace (3)", "Effrayant (1)", "Impact (2)", "Rapide"]}},
                            {"name": "Char", "cost": 115, "mount": {"name": "Char", "special_rules": ["Sabots (A2)", "Coriace (6)", "Impact (4)", "Rapide"]}},
                            {"name": "Char bestial", "cost": 130, "mount": {"name": "Char bestial", "special_rules": ["Griffes lourdes (A2, PA(1))", "Coriace (6)", "Effrayant (1)", "Impact (4)", "Rapide"]}},
                            {"name": "Manticore", "cost": 145, "mount": {"name": "Manticore", "special_rules": ["Griffes perforantes (A6, Perforant)", "Coriace (6)", "Effrayant (1)", "Volant"]}},
                            {"name": "Dragon du Ravage", "cost": 295, "mount": {"name": "Dragon du Ravage", "special_rules": ["Griffes lourdes (A6, PA(1))", "Piétinement (A4, PA(1))", "Attaque de souffle", "Coriace (12)", "Effrayant (2)", "Volant"]}}
                        ]
                    }
                ]
            },
            {
                "name": "Champion Barbare de la Guerre",
                "type": "hero",
                "size": 1,
                "base_cost": 30,
                "quality": 5,
                "defense": 5,
                "special_rules": ["Coriace (3)", "Éclaireur", "Furieux", "Guerrier-né", "Héros"],
                "weapons": [{"name": "Arme à une main", "range": "-", "attacks": 3, "armor_piercing": "-"}],
                "upgrade_groups": [
                    {
                        "group": "Améliorations de rôle",
                        "type": "upgrades",
                        "description": "Choisissez un rôle spécial pour ce héros (un seul choix possible)",
                        "options": [
                            {"name": "Héraut (Aura de Lacération au tir)", "cost": 25, "special_rules": ["Aura de Lacération au tir"]},
                            {"name": "Marauder (Aura de Combattant imprévisible)", "cost": 30, "special_rules": ["Aura de Combattant imprévisible"]},
                            {"name": "Ensorceleur (Aura de Voile fluctuant)", "cost": 35, "special_rules": ["Aura de Voile fluctuant"]},
                            {"name": "Sorcier (Lanceur de sorts (2))", "cost": 40, "special_rules": ["Lanceur de sorts (2)"]},
                            {"name": "Seigneur de Guerre (Aura de Boost de Guerrier-né)", "cost": 50, "special_rules": ["Aura de Boost de Guerrier-né"]}
                        ]
                    },
                    {
                        "group": "Remplacement d'arme",
                        "type": "weapon",
                        "description": "Remplacez l'arme de base par:",
                        "options": [
                            {"name": "Paire d'armes à une main", "cost": 5, "weapon": {"name": "Paire d'armes à une main", "range": "-", "attacks": 4, "armor_piercing": "-"}},
                            {"name": "Hallebarde", "cost": 10, "weapon": {"name": "Hallebarde", "range": "-", "attacks": 3, "armor_piercing": "-", "special_rules": ["Perforant"]}},
                            {"name": "Lance", "cost": 10, "weapon": {"name": "Lance", "range": "-", "attacks": 3, "armor_piercing": "-", "special_rules": ["Percée"]}},
                            {"name": "Grande arme", "cost": 10, "weapon": {"name": "Grande arme", "range": "-", "attacks": 3, "armor_piercing": 2}}
                        ]
                    },
                    {
                        "group": "Améliorations d'arme",
                        "type": "weapon",
                        "description": "Améliorer avec une des options suivantes (un seul choix possible)",
                        "options": [
                            {"name": "Arc court", "cost": 10, "weapon": {"name": "Arc court", "range": "18", "attacks": 2, "armor_piercing": "-"}},
                            {"name": "Javelots barbelés", "cost": 10, "weapon": {"name": "Javelots barbelés", "range": "18", "attacks": 2, "armor_piercing": 1, "special_rules": ["Éclatement"]}}
                        ]
                    },
                    {
                        "group": "Montures",
                        "type": "mount",
                        "description": "Ajoutez une monture à ce héros",
                        "options": [
                            {"name": "Cheval", "cost": 15, "mount": {"name": "Cheval", "special_rules": ["Impact (1)", "Rapide"]}}
                        ]
                    }
                ]
            },
            {
                "name": "Pillards Barbares de la Guerre",
                "type": "unit",
                "size": 10,
                "base_cost": 95,
                "quality": 5,
                "defense": 5,
                "special_rules": ["Éclaireur", "Furieux", "Guerrier-né"],
                "weapons": [{"name": "Armes à une main", "range": "-", "attacks": 1, "armor_piercing": "-"}],
                "upgrade_groups": [
                    {
                        "group": "Remplacement d'armes",
                        "type": "weapon",
                        "description": "Remplacez toutes les armes de base par:",
                        "options": [
                            {"name": "Lance", "cost": 35, "weapon": {"name": "Lance", "range": "-", "attacks": 1, "armor_piercing": "-", "special_rules": ["Contre-charge"]}},
                            {"name": "Fléau", "cost": 20, "weapon": {"name": "Fléau", "range": "-", "attacks": 1, "armor_piercing": 1}}
                        ]
                    },
                    {
                        "group": "Améliorations d'unité",
                        "type": "upgrades",
                        "description": "Améliorations disponibles pour l'unité",
                        "options": [
                            {"name": "Icône du Ravage", "cost": 20, "special_rules": ["Aura de Défense versatile"]},
                            {"name": "Sergent", "cost": 5},
                            {"name": "Bannière", "cost": 5},
                            {"name": "Musicien", "cost": 10}
                        ]
                    }
                ]
            },
            {
                "name": "Guerriers de la Guerre",
                "type": "unit",
                "size": 5,
                "base_cost": 80,
                "quality": 3,
                "defense": 3,
                "special_rules": ["Guerrier-né"],
                "weapons": [{"name": "Armes à une main lourdes", "range": "-", "attacks": 1, "armor_piercing": 1}],
                "upgrade_groups": [
                    {
                        "group": "Améliorations d'unité",
                        "type": "upgrades",
                        "description": "Améliorations disponibles",
                        "options": [
                            {"name": "Sergent", "cost": 5},
                            {"name": "Bannière", "cost": 5},
                            {"name": "Musicien", "cost": 10}
                        ]
                    }
                ]
            },
            {
                "name": "Limiers du Ravage de la Guerre",
                "type": "unit",
                "size": 5,
                "base_cost": 70,
                "quality": 4,
                "defense": 5,
                "special_rules": ["Arpenteur", "Guerrier-né", "Rapide"],
                "weapons": [{"name": "Griffes perforantes", "range": "-", "attacks": 1, "armor_piercing": "-", "special_rules": ["Perforant"]}],
                "upgrade_groups": []
            }
        ]
    },
    {
        "faction": "Disciples de la Guerre",
        "game": "Age of Fantasy Regiments",
        "version": "FR-3.5.2",
        "status": "complete",
        "description": "Les Disciples de la Guerre - version Regiments.",
        "units": [
            {
                "name": "Maître du Ravage de la Guerre Élu",
                "type": "hero",
                "size": 1,
                "base_cost": 65,
                "quality": 3,
                "defense": 3,
                "special_rules": ["Attaque versatile", "Coriace (3)", "Héros", "Guerrier-né"],
                "weapons": [{"name": "Arme à une main lourde", "range": "-", "attacks": 3, "armor_piercing": 1}],
                "upgrade_groups": []
            },
            {
                "name": "Guerriers de la Guerre",
                "type": "unit",
                "size": 5,
                "base_cost": 80,
                "quality": 3,
                "defense": 3,
                "special_rules": ["Guerrier-né"],
                "weapons": [{"name": "Armes à une main lourdes", "range": "-", "attacks": 1, "armor_piercing": 1}],
                "upgrade_groups": []
            }
        ]
    },
    {
        "faction": "Sœurs Bénies",
        "game": "Grimdark Future",
        "version": "FR-0.1",
        "status": "complete",
        "description": "Les Sœurs Bénies sont des guerrières fanatiques.",
        "units": [
            {
                "name": "Chanoinesse",
                "type": "hero",
                "size": 1,
                "base_cost": 95,
                "quality": 3,
                "defense": 4,
                "equipment": ["Arme énergétique", "Pistolet"],
                "special_rules": ["Héroïne", "Foi"],
                "weapons": [
                    {"name": "Arme énergétique", "range": "-", "attacks": 4, "armor_piercing": 2},
                    {"name": "Pistolet", "range": "12\"", "attacks": 1, "armor_piercing": 0}
                ],
                "upgrade_groups": []
            },
            {
                "name": "Sœurs de Bataille",
                "type": "unit",
                "size": 5,
                "base_cost": 110,
                "quality": 4,
                "defense": 4,
                "equipment": ["Fusils", "Armure lourde"],
                "special_rules": ["Foi", "Zèle"],
                "weapons": [{"name": "Fusils", "range": "24\"", "attacks": 1, "armor_piercing": 0}],
                "upgrade_groups": [
                    {
                        "group": "Armes spéciales",
                        "type": "upgrades",
                        "description": "Ajoutez des armes spéciales",
                        "options": [
                            {"name": "Lance-flammes", "cost": 10, "weapon": {"name": "Lance-flammes", "range": "12\"", "attacks": 6, "armor_piercing": 0}},
                            {"name": "Fusil à plasma", "cost": 15, "weapon": {"name": "Fusil à plasma", "range": "24\"", "attacks": 1, "armor_piercing": 3}}
                        ]
                    }
                ]
            },
            {
                "name": "Sœurs d'Élite",
                "type": "unit",
                "size": 5,
                "base_cost": 150,
                "quality": 4,
                "defense": 3,
                "equipment": ["Fusils énergétiques", "Armure lourde"],
                "special_rules": ["Foi", "Zèle"],
                "weapons": [{"name": "Fusils énergétiques", "range": "24\"", "attacks": 2, "armor_piercing": 1}],
                "upgrade_groups": []
            },
            {
                "name": "Repentantes",
                "type": "unit",
                "size": 5,
                "base_cost": 120,
                "quality": 4,
                "defense": 5,
                "equipment": ["Armes lourdes de mêlée"],
                "special_rules": ["Frénésie", "Sans Peur"],
                "weapons": [{"name": "Armes lourdes de mêlée", "range": "-", "attacks": 2, "armor_piercing": 1}],
                "upgrade_groups": []
            },
            {
                "name": "Séraphines",
                "type": "unit",
                "size": 5,
                "base_cost": 160,
                "quality": 4,
                "defense": 4,
                "equipment": ["Pistolets jumelés", "Réacteurs dorsaux"],
                "special_rules": ["Vol", "Foi"],
                "weapons": [{"name": "Pistolets jumelés", "range": "12\"", "attacks": 4, "armor_piercing": 0}],
                "upgrade_groups": []
            },
            {
                "name": "Exorciste",
                "type": "unit",
                "size": 1,
                "base_cost": 220,
                "quality": 4,
                "defense": 2,
                "equipment": ["Missiles sacrés", "Blindage lourd"],
                "special_rules": ["Tir Indirect"],
                "weapons": [{"name": "Missiles sacrés", "range": "48\"", "attacks": 6, "armor_piercing": 2, "special_rules": ["Explosion(3)"]}],
                "upgrade_groups": []
            }
        ]
    }
]

# ===== ROUTES =====

@api_router.get("/")
async def root():
    return {"message": "OPR Army Forge API"}

@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

# Games routes
@api_router.get("/games")
async def get_games():
    """Get all available games"""
    return GAMES

@api_router.get("/games/{game_id}")
async def get_game(game_id: str):
    """Get a specific game by ID"""
    for game in GAMES:
        if game["id"] == game_id:
            return game
    raise HTTPException(status_code=404, detail="Game not found")

# Helper function to load factions from JSON files
async def seed_factions_from_files():
    """Load faction data from JSON files in /data directory"""
    if DATA_DIR.exists():
        for json_file in DATA_DIR.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    faction_data = json.load(f)
                    # Check if faction already exists
                    existing = await db.factions.find_one({
                        "faction": faction_data.get("faction"),
                        "game": faction_data.get("game")
                    })
                    if not existing:
                        faction_data["id"] = str(uuid.uuid4())
                        await db.factions.insert_one(faction_data)
                        logger.info(f"Loaded faction: {faction_data.get('faction')} ({faction_data.get('game')})")
            except Exception as e:
                logger.error(f"Error loading {json_file}: {e}")

# Factions routes
@api_router.get("/factions")
async def get_factions(game: Optional[str] = None):
    """Get all factions, optionally filtered by game"""
    query = {}
    if game:
        query["game"] = game
    
    factions = await db.factions.find(query, {"_id": 0}).to_list(1000)
    
    # If no factions exist, seed from JSON files first, then from SAMPLE_FACTIONS
    if not factions:
        await seed_factions_from_files()
        
        # Also seed from SAMPLE_FACTIONS for games not in files
        for faction_data in SAMPLE_FACTIONS:
            existing = await db.factions.find_one({
                "faction": faction_data.get("faction"),
                "game": faction_data.get("game")
            })
            if not existing:
                faction_obj = {**faction_data, "id": str(uuid.uuid4())}
                await db.factions.insert_one(faction_obj)
        
        factions = await db.factions.find(query, {"_id": 0}).to_list(1000)
    
    return factions

@api_router.get("/factions/{faction_id}")
async def get_faction(faction_id: str):
    """Get a specific faction by ID"""
    faction = await db.factions.find_one({"id": faction_id}, {"_id": 0})
    if not faction:
        raise HTTPException(status_code=404, detail="Faction not found")
    return faction

@api_router.post("/factions", response_model=dict)
async def create_faction(faction_data: FactionCreate):
    """Create a new faction"""
    faction_dict = faction_data.model_dump()
    faction_dict["id"] = str(uuid.uuid4())
    await db.factions.insert_one(faction_dict)
    return {"id": faction_dict["id"], "message": "Faction created successfully"}

@api_router.delete("/factions/{faction_id}")
async def delete_faction(faction_id: str):
    """Delete a faction"""
    result = await db.factions.delete_one({"id": faction_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Faction not found")
    return {"message": "Faction deleted successfully"}

# Import faction from JSON
@api_router.post("/factions/import")
async def import_faction(faction_data: dict):
    """Import a faction from raw JSON data"""
    # Check if faction already exists
    existing = await db.factions.find_one({
        "faction": faction_data.get("faction"),
        "game": faction_data.get("game")
    })
    if existing:
        # Update existing faction
        faction_data["id"] = existing["id"]
        await db.factions.replace_one({"id": existing["id"]}, faction_data)
        return {"id": existing["id"], "message": "Faction updated successfully"}
    else:
        faction_data["id"] = str(uuid.uuid4())
        await db.factions.insert_one(faction_data)
        return {"id": faction_data["id"], "message": "Faction imported successfully"}

# Upload faction JSON file
@api_router.post("/factions/upload")
async def upload_faction_file(file: UploadFile = File(...)):
    """Upload a faction JSON file"""
    if not file.filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="File must be a JSON file")
    
    try:
        content = await file.read()
        faction_data = json.loads(content.decode('utf-8'))
        
        # Validate basic structure
        if "faction" not in faction_data or "game" not in faction_data:
            raise HTTPException(status_code=400, detail="JSON must contain 'faction' and 'game' fields")
        
        # Check if faction already exists
        existing = await db.factions.find_one({
            "faction": faction_data.get("faction"),
            "game": faction_data.get("game")
        })
        
        if existing:
            faction_data["id"] = existing["id"]
            await db.factions.replace_one({"id": existing["id"]}, faction_data)
            return {
                "id": existing["id"], 
                "message": f"Faction '{faction_data['faction']}' updated successfully",
                "units_count": len(faction_data.get("units", []))
            }
        else:
            faction_data["id"] = str(uuid.uuid4())
            await db.factions.insert_one(faction_data)
            return {
                "id": faction_data["id"], 
                "message": f"Faction '{faction_data['faction']}' imported successfully",
                "units_count": len(faction_data.get("units", []))
            }
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Army routes
@api_router.get("/armies")
async def get_armies():
    """Get all armies"""
    armies = await db.armies.find({}, {"_id": 0}).to_list(1000)
    return armies

@api_router.get("/armies/{army_id}")
async def get_army(army_id: str):
    """Get a specific army by ID"""
    army = await db.armies.find_one({"id": army_id}, {"_id": 0})
    if not army:
        raise HTTPException(status_code=404, detail="Army not found")
    return army

@api_router.post("/armies", response_model=dict)
async def create_army(army_data: ArmyCreate):
    """Create a new army"""
    army_dict = army_data.model_dump()
    army_dict["id"] = str(uuid.uuid4())
    army_dict["created_at"] = datetime.now(timezone.utc).isoformat()
    army_dict["updated_at"] = datetime.now(timezone.utc).isoformat()
    army_dict["total_points"] = calculate_army_points(army_dict.get("units", []))
    
    await db.armies.insert_one(army_dict)
    return {"id": army_dict["id"], "message": "Army created successfully"}

@api_router.put("/armies/{army_id}")
async def update_army(army_id: str, army_update: ArmyUpdate):
    """Update an existing army"""
    update_data = {k: v for k, v in army_update.model_dump().items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    if "units" in update_data:
        update_data["total_points"] = calculate_army_points(update_data["units"])
    
    result = await db.armies.update_one({"id": army_id}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Army not found")
    
    return {"message": "Army updated successfully"}

@api_router.delete("/armies/{army_id}")
async def delete_army(army_id: str):
    """Delete an army"""
    result = await db.armies.delete_one({"id": army_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Army not found")
    return {"message": "Army deleted successfully"}

# Validation route
@api_router.post("/validate")
async def validate_army(army_data: dict):
    """Validate an army against OPR rules"""
    errors = []
    points_limit = army_data.get("points_limit", 1000)
    units = army_data.get("units", [])
    
    total_points = calculate_army_points(units)
    
    # Count heroes
    hero_count = sum(1 for u in units if u.get("unit_type") == "hero")
    max_heroes = points_limit // 375
    
    # Check hero limit
    if hero_count > max_heroes:
        errors.append({
            "type": "error",
            "message": f"Trop de héros! Maximum {max_heroes} héros pour {points_limit} pts (1 héros / 375 pts)",
            "unit_id": None
        })
    
    # Check 35% rule for each unit
    max_unit_cost = int(points_limit * 0.35)
    for unit in units:
        unit_cost = unit.get("total_cost", 0)
        if unit_cost > max_unit_cost:
            errors.append({
                "type": "error",
                "message": f"L'unité '{unit.get('unit_name', 'Unknown')}' coûte {unit_cost} pts, maximum autorisé: {max_unit_cost} pts (35% de {points_limit})",
                "unit_id": unit.get("id")
            })
    
    # Check total points
    if total_points > points_limit:
        errors.append({
            "type": "error",
            "message": f"L'armée dépasse la limite de points! {total_points}/{points_limit} pts",
            "unit_id": None
        })
    
    return {
        "valid": len([e for e in errors if e["type"] == "error"]) == 0,
        "errors": errors,
        "total_points": total_points,
        "max_hero_count": max_heroes,
        "current_hero_count": hero_count
    }

def calculate_army_points(units: List[dict]) -> int:
    """Calculate total points for an army"""
    total = 0
    for unit in units:
        total += unit.get("total_cost", unit.get("base_cost", 0))
    return total

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
