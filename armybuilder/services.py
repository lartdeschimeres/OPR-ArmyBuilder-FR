import base64
import copy
import io
import json
import math
import re
import urllib.parse as urlparse
from datetime import datetime
from pathlib import Path

import streamlit as st

from repositories import JsonFactionRepository

from .config import GAME_CONFIG


class CatalogService:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = Path(base_dir)

    def load_factions(self) -> tuple[dict, list[str]]:
        repository = JsonFactionRepository(self.base_dir)
        factions, games = repository.load_catalog()
        return factions, sorted(games)


class OptionFormatter:
    @staticmethod
    def format_unit_option(unit: dict) -> str:
        name_part = unit["name"] + (" [1]" if unit.get("type") == "hero" else f" [{unit.get('size', 10)}]")
        weapons = unit.get("weapon", [])
        if isinstance(weapons, dict):
            weapons = [weapons]
        profiles = []
        for weapon in weapons:
            if not isinstance(weapon, dict):
                continue
            special_rules = weapon.get("special_rules", [])
            weapon_range = weapon.get("range", "Melee")
            if weapon_range in (None, "-", "melee", "Melee") or str(weapon_range).lower() == "melee":
                range_label = "Melee"
            elif isinstance(weapon_range, (int, float)):
                range_label = f'{int(weapon_range)}"'
            else:
                raw_range = str(weapon_range).strip()
                range_label = raw_range if raw_range.endswith('"') else f'{raw_range}"'
            profile = (
                f"{weapon.get('name', 'Arme')} ({range_label}/A{weapon.get('attacks', '?')}/"
                f"PA{weapon.get('armor_piercing', '?')}"
            )
            profile += f", {', '.join(special_rules)})" if special_rules else ")"
            profiles.append(profile)
        weapon_text = ", ".join(profiles) if profiles else "Aucune"
        rules_text = ", ".join([rule if isinstance(rule, str) else rule.get("name", "") for rule in unit.get("special_rules", [])]) or "Aucune"
        return (
            f"{name_part} | Qual {unit.get('quality', '?')}+ | Def {unit.get('defense', '?')}+ | "
            f"{weapon_text} | {rules_text} | {unit.get('base_cost', 0)}pts"
        )

    @staticmethod
    def format_weapon_option(weapon: dict, cost: int = 0) -> str:
        if not weapon or not isinstance(weapon, dict):
            return "Aucune arme"
        weapon_range = weapon.get("range", "Melee")
        if weapon_range in (None, "-", "melee", "Melee") or str(weapon_range).lower() == "melee":
            range_label = "Melee"
        elif isinstance(weapon_range, (int, float)):
            range_label = f'{int(weapon_range)}"'
        else:
            raw_range = str(weapon_range).strip()
            range_label = raw_range if raw_range.endswith('"') else f'{raw_range}"'
        special_rules = weapon.get("special_rules", [])
        profile = f"{weapon.get('name', 'Arme')} ({range_label}/A{weapon.get('attacks', '?')}/PA{weapon.get('armor_piercing', '?')}"
        if special_rules:
            profile += f", {', '.join(special_rules)}"
        profile += ")"
        if cost > 0:
            profile += f" (+{cost} pts)"
        return profile

    @staticmethod
    def format_mount_option(mount: dict) -> str:
        if not mount or not isinstance(mount, dict):
            return "Aucune monture"
        name = mount.get("name", "Monture")
        cost = mount.get("cost", 0)
        mount_data = mount.get("mount", {})
        weapons = mount_data.get("weapon", [])
        if isinstance(weapons, dict):
            weapons = [weapons]
        stats = []
        for weapon in weapons:
            if not isinstance(weapon, dict):
                continue
            profile = f"{weapon.get('name', 'Arme')} A{weapon.get('attacks', '?')}/PA{weapon.get('armor_piercing', '?')}"
            specials = ", ".join(weapon.get("special_rules", []))
            if specials:
                profile += f" ({specials})"
            stats.append(profile)
        coriace_bonus = mount_data.get("coriace_bonus", 0)
        if coriace_bonus > 0:
            stats.append(f"Coriace+{coriace_bonus}")
        mount_rules = mount_data.get("special_rules", [])
        if mount_rules:
            filtered = ", ".join([rule for rule in mount_rules if not rule.startswith(("Griffes", "Sabots"))])
            if filtered:
                stats.append(filtered)
        label = name
        if stats:
            label += f" ({', '.join(stats)})"
        return label + f" (+{cost} pts)"


class ArmyValidationService:
    def __init__(self, formatter: OptionFormatter) -> None:
        self.formatter = formatter

    def check_hero_limit(self, army_list: list[dict], army_points: int, game_config: dict) -> bool:
        max_heroes = math.floor(army_points / game_config["hero_limit"])
        hero_count = sum(1 for unit in army_list if unit.get("type") == "hero")
        if hero_count > max_heroes:
            st.error(f"Limite de heros depassee! Max: {max_heroes} (1 heros/{game_config['hero_limit']} pts)")
            return False
        return True

    def check_unit_max_cost(self, army_list: list[dict], army_points: int, game_config: dict, new_unit_cost: int | None = None) -> bool:
        max_cost = army_points * game_config["unit_max_cost_ratio"]
        for unit in army_list:
            if unit["cost"] > max_cost:
                st.error(f"Unite {unit['name']} depasse {int(max_cost)} pts (35% du total)")
                return False
        if new_unit_cost and new_unit_cost > max_cost:
            st.error(f"Cette unite depasse {int(max_cost)} pts (35% du total)")
            return False
        return True

    def check_unit_copy_rule(self, army_list: list[dict], army_points: int, game_config: dict) -> bool:
        x_value = math.floor(army_points / game_config["unit_copy_rule"])
        max_copies = 1 + x_value
        unit_counts: dict[str, int] = {}
        for unit in army_list:
            name = unit["name"]
            unit_counts[name] = unit_counts.get(name, 0) + 1
        for unit_name, count in unit_counts.items():
            if count > max_copies:
                st.error(f"Trop de copies de {unit_name}! Max: {max_copies}")
                return False
        return True

    def validate_army_rules(self, army_list: list[dict], army_points: int, game: str) -> bool:
        game_config = GAME_CONFIG.get(game, {})
        return (
            self.check_hero_limit(army_list, army_points, game_config)
            and self.check_unit_max_cost(army_list, army_points, game_config)
            and self.check_unit_copy_rule(army_list, army_points, game_config)
        )

    def check_weapon_conditions(self, unit_key: str, requires: list[str], unit: dict | None = None) -> bool:
        if not requires:
            return True

        selections = st.session_state.unit_selections.get(unit_key, {})
        current_weapons = {weapon["name"] for weapon in unit.get("weapon", []) if isinstance(weapon, dict)} if unit else set()

        if unit is not None:
            for group_index, group in enumerate(unit.get("upgrade_groups", [])):
                if group.get("type") != "weapon":
                    continue
                group_key = f"group_{group_index}"
                selection = selections.get(group_key)
                if not selection:
                    continue
                for option in group.get("options", []):
                    weapon = option.get("weapon", {})
                    if isinstance(weapon, list):
                        label = " et ".join(item.get("name", "") for item in weapon) + f" (+{option['cost']} pts)"
                    else:
                        label = self.formatter.format_weapon_option(weapon, option["cost"])
                    if label != selection:
                        continue
                    for replaced in option.get("replaces", []):
                        current_weapons.discard(replaced)
                    if not option.get("replaces"):
                        current_weapons.clear()
                    new_weapon = option.get("weapon", {})
                    if isinstance(new_weapon, list):
                        for weapon_data in new_weapon:
                            if isinstance(weapon_data, dict):
                                current_weapons.add(weapon_data.get("name", ""))
                    elif isinstance(new_weapon, dict):
                        current_weapons.add(new_weapon.get("name", ""))
                    break

        if unit is not None:
            for group_index, group in enumerate(unit.get("upgrade_groups", [])):
                if group.get("type") != "conditional_weapon":
                    continue
                group_key = f"group_{group_index}"
                selection = selections.get(group_key)
                if not selection or selection == "Aucune amelioration":
                    continue
                for option in group.get("options", []):
                    conditional_weapon = option.get("weapon", {})
                    if isinstance(conditional_weapon, dict) and conditional_weapon:
                        label = self.formatter.format_weapon_option(conditional_weapon, option.get("cost", 0))
                    else:
                        label = f"{option.get('name', '')} (+{option.get('cost', 0)} pts)"
                    if label != selection:
                        continue
                    new_weapon = option.get("weapon", {})
                    if isinstance(new_weapon, dict) and new_weapon:
                        current_weapons.add(new_weapon.get("name", ""))
                    elif isinstance(new_weapon, list):
                        for weapon_data in new_weapon:
                            if isinstance(weapon_data, dict):
                                current_weapons.add(weapon_data.get("name", ""))
                    break

        if unit is not None:
            for group_index, group in enumerate(unit.get("upgrade_groups", [])):
                if group.get("type") != "variable_weapon_count":
                    continue
                for option_index, option in enumerate(group.get("options", [])):
                    widget_key = f"{unit_key}_group_{group_index}_cnt_{option_index}"
                    count_value = st.session_state.get(widget_key, 0)
                    if not count_value or count_value <= 0:
                        continue
                    new_weapon = option.get("weapon", {})
                    if isinstance(new_weapon, dict) and new_weapon:
                        current_weapons.add(new_weapon.get("name", ""))
                    elif isinstance(new_weapon, list):
                        for weapon_data in new_weapon:
                            if isinstance(weapon_data, dict):
                                current_weapons.add(weapon_data.get("name", ""))

        selected_option_names = set()
        for selection in selections.values():
            if isinstance(selection, str) and selection not in ("Aucune amelioration", "Aucune arme", "Aucun role", "Aucune monture"):
                selected_option_names.add(selection.split(" (+")[0].strip())

        for required in requires:
            if required not in current_weapons and required not in selected_option_names:
                return False
        return True


class HtmlExportService:
    def export_html(self, army_list: list[dict], army_name: str, army_limit: int) -> str:
        def esc(text):
            if text is None:
                return ""
            return (
                str(text)
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
            )

        def get_priority(unit):
            detail = unit.get("unit_detail", unit.get("type", "unit"))
            order = {"named_hero": 1, "hero": 2, "unit": 3, "light_vehicle": 4, "vehicle": 5, "titan": 6}
            return order.get(detail, 7)

        def fmt_range(value):
            if value in (None, "-", "melee", "Melee") or str(value).lower() == "melee":
                return "-"
            if isinstance(value, (int, float)):
                return f'{int(value)}"'
            raw = str(value).strip()
            return raw if raw.endswith('"') else f'{raw}"'

        def collect_weapons(unit):
            result = []
            base_weapons = unit.get("weapon", [])
            if isinstance(base_weapons, dict):
                base_weapons = [base_weapons]
            for weapon in base_weapons:
                if isinstance(weapon, dict):
                    weapon_copy = weapon.copy()
                    weapon_copy.setdefault("range", "Melee")
                    if not weapon_copy.get("_upgraded") and "_count" in weapon_copy:
                        del weapon_copy["_count"]
                    result.append(weapon_copy)
            if unit.get("mount"):
                mount = unit["mount"]
                if isinstance(mount, dict):
                    mount_data = mount.get("mount", {})
                    if isinstance(mount_data, dict):
                        mount_weapons = mount_data.get("weapon", [])
                        if isinstance(mount_weapons, dict):
                            mount_weapons = [mount_weapons]
                        for weapon in mount_weapons:
                            if isinstance(weapon, dict):
                                weapon_copy = weapon.copy()
                                weapon_copy.setdefault("range", "Melee")
                                weapon_copy["_mount_weapon"] = True
                                result.append(weapon_copy)
            return result

        def group_weapons(weapons):
            weapons_map = {}
            for weapon in weapons:
                if not isinstance(weapon, dict) or weapon.get("_mount_weapon"):
                    continue
                weapon_copy = weapon.copy()
                weapon_copy.setdefault("range", "Melee")
                key = (
                    weapon_copy.get("name", ""),
                    weapon_copy.get("range", ""),
                    weapon_copy.get("attacks", ""),
                    weapon_copy.get("armor_piercing", ""),
                    tuple(sorted(weapon_copy.get("special_rules", []))),
                )
                count = weapon_copy.get("_count", 1) or 1
                if key not in weapons_map:
                    weapons_map[key] = weapon_copy
                    weapons_map[key]["_display_count"] = count
                else:
                    weapons_map[key]["_display_count"] += count
            for weapon in weapons:
                if not isinstance(weapon, dict) or weapon.get("_mount_weapon"):
                    continue
                if "_count" not in weapon:
                    continue
                replaces = weapon.get("_replaces", [])
                if not replaces:
                    continue
                replace_count = weapon.get("_count", 1) or 1
                for replaced_name in replaces:
                    for key, entry in weapons_map.items():
                        if entry.get("name") == replaced_name:
                            weapons_map[key]["_display_count"] -= replace_count
                            break
            return [weapon for weapon in weapons_map.values() if weapon.get("_display_count", 1) > 0]

        def get_rules(unit):
            rules = set()
            for rule in unit.get("special_rules", []):
                if isinstance(rule, str):
                    rules.add(rule)
            if "options" in unit and isinstance(unit["options"], dict):
                for group in unit["options"].values():
                    options = group if isinstance(group, list) else [group]
                    for option in options:
                        if isinstance(option, dict):
                            for rule in option.get("special_rules", []):
                                if isinstance(rule, str):
                                    rules.add(rule)
            if unit.get("mount"):
                mount = unit["mount"]
                if isinstance(mount, dict):
                    mount_data = mount.get("mount", {})
                    if isinstance(mount_data, dict):
                        for rule in mount_data.get("special_rules", []):
                            if isinstance(rule, str) and not rule.startswith(("Griffes", "Sabots")):
                                rules.add(rule)
            return sorted(rules)

        def render_weapon_rows(final_weapons):
            rows = ""
            for weapon in final_weapons:
                name = esc(weapon.get("name", "Arme"))
                count = weapon.get("_display_count", 1) or 1
                has_count = "_count" in weapon
                upgraded = weapon.get("_upgraded", False)
                unique = weapon.get("_unique", False)
                if has_count and count > 1:
                    name_display = f"{count}x {name}"
                elif upgraded and unique:
                    name_display = f"1x {name}"
                else:
                    name_display = name
                special = ", ".join(weapon.get("special_rules", [])) or "-"
                rows += (
                    f"<tr><td class='weapon-name'>{name_display}</td><td>{fmt_range(weapon.get('range', 'Melee'))}</td>"
                    f"<td>{weapon.get('attacks', '-')}</td><td>{weapon.get('armor_piercing', '-')}</td><td>{special}</td></tr>"
                )
            return rows

        def render_upgrades_section(unit):
            upgrades = []
            if "options" in unit and isinstance(unit["options"], dict):
                for group_options in unit["options"].values():
                    options = group_options if isinstance(group_options, list) else [group_options]
                    for option in options:
                        if not isinstance(option, dict):
                            continue
                        upgrades.append((option.get("name", "Amelioration"), ", ".join(option.get("special_rules", []))))
            if not upgrades:
                return ""
            items = ""
            for name, rules in upgrades:
                items += f'<span class="rule-tag" style="background:#e8f4fd;border-color:#b8d9f0;">{esc(name)}'
                if rules:
                    items += f' <span style="font-weight:400;color:#555;">({esc(rules)})</span>'
                items += "</span>"
            return (
                '<div style="border-top:1px solid var(--brd);margin-top:8px;padding-top:8px;">'
                '<div class="rules-title">Ameliorations</div>'
                f"<div style=\"margin-bottom:4px;\">{items}</div>"
                "</div>"
            )

        def render_mount_section(unit):
            if not unit.get("mount"):
                return ""
            mount = unit["mount"]
            if not isinstance(mount, dict) or "mount" not in mount:
                return ""
            mount_data = mount["mount"]
            mount_name = esc(mount.get("name", "Monture"))
            mount_cost = mount.get("cost", 0)
            mount_weapons = mount_data.get("weapon", [])
            if isinstance(mount_weapons, dict):
                mount_weapons = [mount_weapons]
            rows = ""
            for weapon in mount_weapons:
                if not isinstance(weapon, dict):
                    continue
                special = ", ".join(weapon.get("special_rules", [])) or "-"
                rows += (
                    f"<tr><td class='weapon-name'>{esc(weapon.get('name', 'Arme'))}</td><td>{fmt_range(weapon.get('range', '-'))}</td>"
                    f"<td>{weapon.get('attacks', '-')}</td><td>{weapon.get('armor_piercing', '-')}</td><td>{special}</td></tr>"
                )
            mount_rules = [rule for rule in mount_data.get("special_rules", []) if not rule.startswith(("Griffes", "Sabots", "Coriace"))]
            rules_html = " ".join(f'<span class="rule-tag">{esc(rule)}</span>' for rule in mount_rules) if mount_rules else ""
            rules_block = f'<div style="margin-bottom:8px;">{rules_html}</div>' if rules_html else ""
            return (
                f"<div class=\"mount-section\"><div class=\"section-title\">Monture {mount_name} (+{mount_cost} pts)</div>"
                f"{rules_block}"
                f"<table class=\"weapon-table\"><thead><tr><th>Arme</th><th>Por</th><th>Att</th><th>PA</th><th>Spe</th></tr></thead><tbody>{rows}</tbody></table></div>"
            )

        sorted_units = sorted(army_list, key=get_priority)
        total_cost = sum(unit.get("cost", 0) for unit in sorted_units)
        html = f"""<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8">
<title>Liste d'Armee OPR - {esc(army_name)}</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root{{--bg:#fff;--hdr:#f8f9fa;--accent:#3498db;--txt:#212529;--muted:#6c757d;--brd:#dee2e6;--red:#e74c3c;--rule:#e9ecef;--mount:#f3e5f5;--badge:#e9ecef;}}
*{{box-sizing:border-box;}}
body{{background:var(--bg);color:var(--txt);font-family:'Inter',sans-serif;margin:0;padding:12px;line-height:1.3;font-size:12px;}}
.army{{max-width:210mm;margin:0 auto;}}
.army-title{{text-align:center;font-size:18px;font-weight:700;margin-bottom:8px;border-bottom:2px solid var(--accent);padding-bottom:6px;}}
.army-summary{{display:flex;justify-content:space-between;align-items:center;background:var(--hdr);padding:8px 12px;border-radius:6px;margin:8px 0 12px;border:1px solid var(--brd);font-size:12px;}}
.summary-cost{{font-family:monospace;font-size:16px;font-weight:bold;color:var(--red);}}
.units-grid{{display:grid;grid-template-columns:1fr 1fr;gap:8px;}}
.unit-card{{background:var(--bg);border:1px solid var(--brd);border-radius:6px;break-inside:avoid;page-break-inside:avoid;font-size:11px;}}
.unit-header{{padding:6px 8px 4px;background:var(--hdr);border-bottom:1px solid var(--brd);border-radius:6px 6px 0 0;}}
.unit-name-container{{display:flex;justify-content:space-between;align-items:flex-start;}}
.unit-name{{font-size:13px;font-weight:700;margin:0;line-height:1.2;}}
.unit-cost{{font-family:monospace;font-size:12px;font-weight:700;color:var(--red);white-space:nowrap;margin-left:6px;}}
.unit-type{{font-size:10px;color:var(--muted);margin-top:1px;}}
.unit-stats{{display:flex;gap:6px;padding:4px 0 2px;flex-wrap:wrap;}}
.stat-badge{{background:var(--badge);padding:2px 7px;border-radius:12px;font-weight:600;display:flex;align-items:center;gap:4px;border:1px solid var(--brd);}}
.stat-value{{font-weight:700;font-size:11px;}}
.stat-label{{font-size:9px;color:var(--muted);}}
.section{{padding:4px 8px 6px;}}
.section-title{{font-weight:600;margin:4px 0 3px;font-size:11px;display:flex;align-items:center;gap:5px;border-bottom:1px solid var(--brd);padding-bottom:2px;color:var(--accent);}}
.weapon-table{{width:100%;border-collapse:collapse;margin:0 0 4px;font-size:10px;}}
.weapon-table th{{background:var(--hdr);padding:2px 5px;text-align:left;font-weight:600;border-bottom:1px solid var(--brd);border-right:1px solid var(--brd);font-size:9px;color:var(--muted);}}
.weapon-table th:last-child{{border-right:none;}}
.weapon-table td{{padding:2px 5px;border-bottom:1px solid var(--brd);border-right:1px solid var(--brd);vertical-align:top;line-height:1.3;}}
.weapon-table td:last-child{{border-right:none;}}
.weapon-table tr:last-child td{{border-bottom:none;}}
.weapon-name{{font-weight:600;}}
.rules-section{{margin:3px 0 0;}}
.rules-title{{font-weight:600;margin-bottom:3px;font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.03em;}}
.rule-tag{{background:var(--rule);padding:1px 6px;border-radius:3px;font-size:9px;border:1px solid var(--brd);margin-right:3px;margin-bottom:3px;display:inline-block;line-height:1.5;}}
.mount-section{{background:var(--mount);border:1px solid var(--brd);border-radius:4px;padding:4px 8px;margin:4px 0;font-size:10px;}}
.mount-section .section-title{{font-size:10px;}}
.legend-page{{page-break-before:always;break-before:page;padding:12px 0;}}
.faction-rules{{padding:8px;border-radius:6px;border:1px solid var(--brd);}}
.legend-title{{text-align:center;color:var(--accent);border-bottom:2px solid var(--accent);padding-bottom:6px;margin-bottom:12px;font-size:14px;font-weight:700;}}
.rule-item{{margin-bottom:8px;padding-bottom:8px;border-bottom:1px solid var(--brd);}}
.rule-item:last-child{{border-bottom:none;margin-bottom:0;padding-bottom:0;}}
.rule-name{{color:var(--accent);font-weight:600;font-size:9px;margin-bottom:1px;}}
.rule-desc{{font-size:8.5px;line-height:1.35;color:#555;}}
@media print{{
  body{{padding:6px;}}
  .army{{max-width:100%;}}
  .unit-card{{border:0.5px solid #ccc;box-shadow:none;background:white;}}
  .faction-rules{{border:0.5px solid #ccc;}}
  .legend-page{{page-break-before:always;}}
}}
</style></head><body><div class="army">
<div class="army-title">{esc(army_name)} - {total_cost}/{army_limit} pts</div>
<div class="army-summary">
  <div><span style="color:var(--muted);">Unites :</span> <strong>{len(sorted_units)}</strong></div>
  <div class="summary-cost">{total_cost}/{army_limit} pts</div>
</div>
<div class="units-grid">
"""
        for unit in sorted_units:
            final_weapons = group_weapons(collect_weapons(unit))
            rules = get_rules(unit)
            rules_html = " ".join(f'<span class="rule-tag">{esc(rule)}</span>' for rule in rules)
            html += f"""
<div class="unit-card">
  <div class="unit-header">
    <div class="unit-name-container">
      <div>
        <div class="unit-name">{esc(unit.get("name", "Unite"))}</div>
        <div class="unit-type">{esc(unit.get("unit_detail", unit.get("type", "unit")))}</div>
      </div>
      <div class="unit-cost">{unit.get("cost", 0)} pts</div>
    </div>
    <div class="unit-stats">
      <div class="stat-badge"><span class="stat-label">Qual</span><span class="stat-value">{unit.get("quality", "?")}+</span></div>
      <div class="stat-badge"><span class="stat-label">Def</span><span class="stat-value">{unit.get("defense", "?")}+</span></div>
      <div class="stat-badge"><span class="stat-label">Taille</span><span class="stat-value">{unit.get("size", "?")}</span></div>
      {f'<div class="stat-badge"><span class="stat-label">Coriace</span><span class="stat-value">{unit.get("coriace", 0)}</span></div>' if unit.get("coriace", 0) else ''}
    </div>
  </div>
  <div class="section">
    <div class="section-title">Armes</div>
    <table class="weapon-table"><thead><tr><th>Arme</th><th>Por</th><th>Att</th><th>PA</th><th>Spe</th></tr></thead><tbody>{render_weapon_rows(final_weapons)}</tbody></table>
    {render_mount_section(unit)}
    {render_upgrades_section(unit)}
    {('<div class="rules-section"><div class="rules-title">Regles</div>' + rules_html + '</div>') if rules_html else ''}
  </div>
</div>
"""
        html += "</div>"
        faction_rules = []
        seen_rules = set()
        for unit in sorted_units:
            for rule in unit.get("special_rules", []):
                if isinstance(rule, str) and rule not in seen_rules:
                    seen_rules.add(rule)
                    faction_rules.append({"name": rule, "description": ""})
        if faction_rules:
            html += '<div class="legend-page"><div class="legend-title">Reference des regles</div><div class="faction-rules">'
            for rule in faction_rules:
                html += (
                    '<div class="rule-item">'
                    f'<div class="rule-name">{esc(rule.get("name", ""))}</div>'
                    f'<div class="rule-desc">{esc(rule.get("description", ""))}</div>'
                    "</div>"
                )
            html += "</div></div>"

        payload = json.dumps(
            {
                "name": army_name,
                "limit": army_limit,
                "total": total_cost,
                "units": sorted_units,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )
        try:
            import qrcode

            qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=4, border=2)
            qr.add_data(payload)
            qr.make(fit=True)
            image = qr.make_image(fill_color="black", back_color="white")
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            buffer.seek(0)
            qr_b64 = base64.b64encode(buffer.read()).decode()
            qr_img_tag = (
                f'<img src="data:image/png;base64,{qr_b64}" '
                'style="width:96px;height:96px;display:block;margin:0 auto;border:1px solid var(--brd);border-radius:4px;" alt="QR code">'
            )
        except Exception:
            qr_url = "https://api.qrserver.com/v1/create-qr-code/?data=" + urlparse.quote(payload) + "&size=96x96&margin=2"
            qr_img_tag = (
                f'<img src="{qr_url}" style="width:96px;height:96px;display:block;margin:0 auto;'
                'border:1px solid var(--brd);border-radius:4px;" alt="QR code">'
            )
        html += (
            '<div style="text-align:center;margin-top:28px;padding:16px 0;border-top:1px solid var(--brd);">'
            '<div style="font-size:10px;color:var(--muted);margin-bottom:8px;letter-spacing:.06em;text-transform:uppercase;">Scanner pour partager</div>'
            + qr_img_tag
            + "</div>"
        )
        html += f'<div style="text-align:center;margin-top:16px;font-size:11px;color:var(--muted);">Genere par OPR ArmyBuilder FRA - {datetime.now().strftime("%d/%m/%Y %H:%M")}</div></div></body></html>'
        return html
