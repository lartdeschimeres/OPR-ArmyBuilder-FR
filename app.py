import json
import copy
import streamlit as st
from pathlib import Path
from datetime import datetime
import re
import math
import base64

st.set_page_config(page_title="OPR ArmyBuilder FR", layout="wide", initial_sidebar_state="expanded")

st.markdown("""<style>
#MainMenu {visibility: hidden;} footer {visibility: hidden;} header {background: transparent;}
.stApp {background: #e9ecef; color: #212529;}
section[data-testid="stSidebar"] {background: #dee2e6; border-right: 1px solid #adb5bd; box-shadow: 2px 0 5px rgba(0,0,0,0.1);}
h1, h2, h3 {color: #202c45; letter-spacing: 0.04em; font-weight: 600;}
.stSelectbox, .stNumberInput, .stTextInput {background-color: white; border-radius: 6px; border: 1px solid #ced4da;}
button[kind="primary"] {background: linear-gradient(135deg, #2980b9, #1e5aa8) !important; color: white !important; font-weight: bold; border-radius: 6px;}
.badge {display: inline-block; padding: 0.35rem 0.75rem; border-radius: 4px; background: #2980b9; color: white; font-size: 0.8rem; margin-bottom: 0.75rem; font-weight: 600;}
.stButton>button {background-color: #f8f9fa; border: 1px solid #ced4da; border-radius: 6px; padding: 0.5rem 1rem; color: #212529; font-weight: 500;}
.stProgress > div > div > div {background-color: #2980b9 !important;}
</style>""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("<div style='height:1px;'></div>", unsafe_allow_html=True)
with st.sidebar:
    st.title("🛡️ OPR ArmyBuilder FR")
    st.subheader("📋 Armée")
    game = st.session_state.get("game", "—")
    faction = st.session_state.get("faction", "—")
    points = st.session_state.get("points", 0)
    army_cost = st.session_state.get("army_cost", 0)
    st.markdown(f"**Jeu :** {game}")
    st.markdown(f"**Faction :** {faction}")
    st.markdown(f"**Format :** {points} pts")
    if points > 0:
        st.progress(min(army_cost / points, 1.0))
        st.markdown(f"**Coût :** {army_cost} / {points} pts")
        if army_cost > points:
            st.error("⚠️ Dépassement de points")
        if st.session_state.get("page") == "army" and "army_list" in st.session_state:
            units_cap = math.floor(points / 150)
            heroes_cap = math.floor(points / 375)
            units_now = len([u for u in st.session_state.army_list if u.get("type") != "hero"])
            heroes_now = len([u for u in st.session_state.army_list if u.get("type") == "hero"])
            st.markdown(f"**Unités :** {units_now} / {units_cap}")
            st.markdown(f"**Héros :** {heroes_now} / {heroes_cap}")
    st.divider()

if "page" not in st.session_state: st.session_state.page = "setup"
if "army_list" not in st.session_state: st.session_state.army_list = []
if "army_cost" not in st.session_state: st.session_state.army_cost = 0
if "unit_selections" not in st.session_state: st.session_state.unit_selections = {}
if "draft_counter" not in st.session_state: st.session_state.draft_counter = 0
if "draft_unit_name" not in st.session_state: st.session_state.draft_unit_name = ""
if "game" not in st.session_state: st.session_state.game = None
if "faction" not in st.session_state: st.session_state.faction = None
if "points" not in st.session_state: st.session_state.points = 0
if "list_name" not in st.session_state: st.session_state.list_name = ""
if "units" not in st.session_state: st.session_state.units = []
if "faction_special_rules" not in st.session_state: st.session_state.faction_special_rules = []
if "faction_spells" not in st.session_state: st.session_state.faction_spells = {}

GAME_CONFIG = {
    "Age of Fantasy": {"min_points": 250, "max_points": 10000, "default_points": 1000, "hero_limit": 375, "unit_copy_rule": 750, "unit_max_cost_ratio": 0.35, "unit_per_points": 150},
    "Age of Fantasy: Regiments": {"min_points": 500, "max_points": 20000, "default_points": 2000, "hero_limit": 500, "unit_copy_rule": 1000, "unit_max_cost_ratio": 0.4, "unit_per_points": 200},
    "Grimdark Future": {"min_points": 250, "max_points": 10000, "default_points": 1000, "hero_limit": 375, "unit_copy_rule": 750, "unit_max_cost_ratio": 0.35, "unit_per_points": 150},
    "Grimdark Future: Firefight": {"min_points": 150, "max_points": 1000, "default_points": 300, "hero_limit": 300, "unit_copy_rule": 300, "unit_max_cost_ratio": 0.6, "unit_per_points": 100},
    "Age of Fantasy: Skirmish": {"min_points": 150, "max_points": 1000, "default_points": 300, "hero_limit": 300, "unit_copy_rule": 300, "unit_max_cost_ratio": 0.6, "unit_per_points": 100}
}

def check_hero_limit(army_list, army_points, game_config):
    max_heroes = math.floor(army_points / game_config["hero_limit"])
    hero_count = sum(1 for unit in army_list if unit.get("type") == "hero")
    if hero_count > max_heroes:
        st.error(f"Limite de héros dépassée! Max: {max_heroes} (1 héros/{game_config['hero_limit']} pts)")
        return False
    return True

def check_unit_max_cost(army_list, army_points, game_config, new_unit_cost=None):
    max_cost = army_points * game_config["unit_max_cost_ratio"]
    for unit in army_list:
        if unit["cost"] > max_cost:
            st.error(f"Unité {unit['name']} dépasse {int(max_cost)} pts (35% du total)")
            return False
    if new_unit_cost and new_unit_cost > max_cost:
        st.error(f"Cette unité dépasse {int(max_cost)} pts (35% du total)")
        return False
    return True

def check_unit_copy_rule(army_list, army_points, game_config):
    x_value = math.floor(army_points / game_config["unit_copy_rule"])
    max_copies = 1 + x_value
    unit_counts = {}
    for unit in army_list:
        name = unit["name"]
        unit_counts[name] = unit_counts.get(name, 0) + 1
    for unit_name, count in unit_counts.items():
        if count > max_copies:
            st.error(f"Trop de copies de {unit_name}! Max: {max_copies}")
            return False
    return True

def validate_army_rules(army_list, army_points, game):
    game_config = GAME_CONFIG.get(game, {})
    return (check_hero_limit(army_list, army_points, game_config) and
            check_unit_max_cost(army_list, army_points, game_config) and
            check_unit_copy_rule(army_list, army_points, game_config))

def check_weapon_conditions(unit_key, requires, unit=None):
    """
    Vérifie si les conditions d'une option sont remplies.
    Prend en compte :
    - Les sélections explicites dans session_state (armes de remplacement choisies)
    - Les armes de BASE de l'unité, actives quand aucun groupe type=weapon
      n'a de sélection explicite (= le joueur garde choices[0])
    """
    if not requires:
        return True
    current_weapons = []
    selections = st.session_state.unit_selections.get(unit_key, {})

    # 1. Sélections explicites (armes remplacées, conditionnelles choisies)
    for v in selections.values():
        if isinstance(v, str) and v not in ("Aucune amélioration", "Aucune arme", "Aucun rôle"):
            current_weapons.append({"name": v.split(" (")[0]})

    # 2. Armes de BASE — actives pour chaque groupe type=weapon
    #    où aucune sélection explicite n'est stockée (= choices[0] implicite)
    if unit is not None:
        for gi, g in enumerate(unit.get("upgrade_groups", [])):
            if g.get("type") != "weapon":
                continue
            g_key = f"group_{gi}"
            if g_key not in selections:
                # Aucune sélection explicite → les armes de base sont actives
                for w in unit.get("weapon", []):
                    if isinstance(w, dict):
                        current_weapons.append(w)

    for req in requires:
        if not any(w.get("name") == req or req in w.get("tags", []) for w in current_weapons):
            return False
    return True

def format_unit_option(u):
    name_part = u["name"] + (" [1]" if u.get("type") == "hero" else f" [{u.get('size', 10)}]")
    weapons = u.get("weapon", [])
    if isinstance(weapons, dict): weapons = [weapons]
    profiles = []
    for w in weapons:
        if isinstance(w, dict):
            sr = w.get("special_rules", [])
            # Formatage de la portée : entier → 'Xpouces', Mêlée → 'Mêlée'
            rng = w.get("range", "Mêlée")
            if rng in (None, "-", "mêlée", "Mêlée") or str(rng).lower() == "mêlée":
                rng_str = "Mêlée"
            elif isinstance(rng, (int, float)):
                rng_str = f'{int(rng)}"'
            else:
                s = str(rng).strip()
                rng_str = s if s.endswith('"') else f'{s}"'
            p = f"{w.get('name','Arme')} ({rng_str}/A{w.get('attacks','?')}/PA{w.get('armor_piercing','?')}"
            p += (f", {', '.join(sr)})" if sr else ")")
            profiles.append(p)
    weapon_text = ", ".join(profiles) if profiles else "Aucune"
    rules_text = ", ".join([r if isinstance(r, str) else r.get("name","") for r in u.get("special_rules", [])]) or "Aucune"
    # Ajout de Qual X+ devant Déf X+
    return f"{name_part} | Qual {u.get('quality','?')}+ | Déf {u.get('defense','?')}+ | {weapon_text} | {rules_text} | {u.get('base_cost',0)}pts"

def format_weapon_option(weapon, cost=0):
    if not weapon or not isinstance(weapon, dict): return "Aucune arme"
    profile = f"{weapon.get('name','Arme')} (A{weapon.get('attacks','?')}/PA{weapon.get('armor_piercing','?')}/{weapon.get('range','Mêlée')})"
    if cost > 0: profile += f" (+{cost} pts)"
    return profile

def format_mount_option(mount):
    if not mount or not isinstance(mount, dict): return "Aucune monture"
    name = mount.get("name", "Monture")
    cost = mount.get("cost", 0)
    mount_data = mount.get("mount", {})
    weapons = mount_data.get("weapon", [])
    if isinstance(weapons, dict): weapons = [weapons]
    coriace = mount_data.get("coriace_bonus", 0)
    stats = []
    for w in weapons:
        if isinstance(w, dict):
            p = f"{w.get('name','Arme')} A{w.get('attacks','?')}/PA{w.get('armor_piercing','?')}"
            sp = ", ".join(w.get("special_rules", []))
            if sp: p += f" ({sp})"
            stats.append(p)
    if coriace > 0: stats.append(f"Coriace+{coriace}")
    sr = mount_data.get("special_rules", [])
    if sr:
        rt = ", ".join([r for r in sr if not r.startswith(("Griffes", "Sabots"))])
        if rt: stats.append(rt)
    label = name
    if stats: label += f" ({', '.join(stats)})"
    return label + f" (+{cost} pts)"

# ======================================================
# EXPORT HTML — STYLE ARMYFORGE (VERSION FINALE CORRIGÉE)
# ======================================================
def export_html(army_list, army_name, army_limit):

    def esc(txt):
        if txt is None: return ""
        return str(txt).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")

    def get_priority(unit):
        d = unit.get("unit_detail", unit.get("type","unit"))
        order = {"named_hero": 1, "hero": 2, "unit": 3, "light_vehicle": 4, "vehicle": 5, "titan": 6}
        return order.get(d, 7)

    def fmt_range(rng):
        if rng in (None, "-", "mêlée", "Mêlée") or str(rng).lower() == "mêlée": return "-"
        if isinstance(rng, (int, float)): return f'{int(rng)}"'
        s = str(rng).strip()
        return s if s.endswith('"') else f'{s}"'

    def collect_weapons(unit):
        # unit["weapon"] contient DEJA toutes les armes consolidees par la page army
        # (armes de base, remplacements, armes de role). Ne PAS relire unit["options"]
        # pour eviter les doublons sur les roles avec weapon.
        result = []
        bw = unit.get("weapon", [])
        if isinstance(bw, dict): bw = [bw]
        for w in bw:
            if isinstance(w, dict):
                wc = w.copy(); wc.setdefault("range", "Mêlée")
                # Purger _count sur les armes de base (not _upgraded) :
                # _count ne doit exister que sur les armes ajoutées via slider.
                # Un résidu de cache ou de JSON corrompu sur une arme de base
                # fausserait le calcul de replaced_count dans group_weapons.
                if not wc.get("_upgraded") and "_count" in wc:
                    del wc["_count"]
                result.append(wc)
        # Armes de monture uniquement
        if unit.get("mount"):
            m = unit["mount"]
            if isinstance(m, dict):
                md = m.get("mount", {})
                if isinstance(md, dict):
                    mws = md.get("weapon", [])
                    if isinstance(mws, dict): mws = [mws]
                    for w in mws:
                        if isinstance(w, dict):
                            wc = w.copy(); wc.setdefault("range", "Mêlée"); wc["_mount_weapon"] = True; result.append(wc)
        return result

    def group_weapons(weapons, unit_size=1):
        # Agrège les armes par clé (même profil).
        # _count (slider) → utiliser _count comme quantité
        # Tout le reste → cnt=1 (arme de base, conditional, remplacement total)
        # La passe _replaces sert uniquement aux sliders (seuls cas avec _count).
        wmap = {}
        for w in weapons:
            if not isinstance(w, dict) or w.get("_mount_weapon"): continue
            wc = w.copy(); wc.setdefault("range","Mêlée")
            key = (wc.get("name",""), wc.get("range",""), wc.get("attacks",""),
                   wc.get("armor_piercing",""), tuple(sorted(wc.get("special_rules",[]))))
            cnt = wc.get("_count", 1) or 1
            if key not in wmap: wmap[key] = wc; wmap[key]["_display_count"] = cnt
            else: wmap[key]["_display_count"] += cnt
        # Soustraire les _replaces UNIQUEMENT pour les sliders (armes avec _count).
        # Les conditional_weapon (sans _count) n'affectent pas le count des armes de base.
        for w in weapons:
            if not isinstance(w, dict) or w.get("_mount_weapon"): continue
            if "_count" not in w: continue          # seulement les sliders
            replaces = w.get("_replaces", [])
            if not replaces: continue
            rc = w.get("_count", 1) or 1
            for replaced_name in replaces:
                for key, entry in wmap.items():
                    if entry.get("name") == replaced_name:
                        wmap[key]["_display_count"] -= rc
                        break
        return [v for v in wmap.values() if v.get("_display_count", 1) > 0]

    def get_rules(unit):
        rules = set()
        for r in unit.get("special_rules", []):
            if isinstance(r, str): rules.add(r)
        if "options" in unit and isinstance(unit["options"], dict):
            for group in unit["options"].values():
                opts = group if isinstance(group, list) else [group]
                for opt in opts:
                    if isinstance(opt, dict):
                        for r in opt.get("special_rules", []):
                            if isinstance(r, str): rules.add(r)
        if unit.get("mount"):
            m = unit["mount"]
            if isinstance(m, dict):
                md = m.get("mount", {})
                if isinstance(md, dict):
                    for r in md.get("special_rules", []):
                        if isinstance(r, str) and not r.startswith(("Griffes","Sabots")): rules.add(r)
        return sorted(rules)

    def render_weapon_rows(final_weapons, unit_size=1):
        # Règles d'affichage du préfixe :
        #   slider (_count > 1)                        → "Nx nom"
        #   conditional unique (_upgraded + _unique)   → "1x nom"  (amélioration d'une figurine)
        #   tout le reste                              → "nom"
        rows = ""
        for w in final_weapons:
            name      = esc(w.get("name","Arme"))
            cnt       = w.get("_display_count", 1) or 1
            has_count = "_count" in w
            upgraded  = w.get("_upgraded", False)
            unique    = w.get("_unique", False)

            if has_count and cnt > 1:
                nd = f"{cnt}x {name}"
            elif upgraded and unique:
                nd = f"1x {name}"
            else:
                nd = name

            rng = fmt_range(w.get("range","Mêlée"))
            att = w.get("attacks","-"); ap = w.get("armor_piercing","-")
            spe = ", ".join(w.get("special_rules",[])) or "-"
            rows += f"<tr><td class='weapon-name'>{nd}</td><td>{rng}</td><td>{att}</td><td>{ap}</td><td>{spe}</td></tr>"
        return rows

    def render_upgrade_rows(unit):
        upgrades = []
        if "options" in unit and isinstance(unit["options"], dict):
            for group_opts in unit["options"].values():
                opts = group_opts if isinstance(group_opts, list) else [group_opts]
                for opt in opts:
                    if not isinstance(opt, dict): continue
                    if opt.get("type") == "upgrade":
                        upgrades.append((opt.get("name","Amélioration"), ", ".join(opt.get("special_rules",[]))))
                    elif opt.get("type") == "role":
                        rules = ", ".join(opt.get("special_rules",[]))
                        if rules: upgrades.append((opt.get("name","Rôle"), rules))
        if not upgrades: return ""
        rows = "<tr><td colspan='2' style='font-weight:700;background:#f0f0f0;padding:6px 12px;border-top:2px solid #dee2e6;'>Upgrade</td><td colspan='3' style='font-weight:700;background:#f0f0f0;padding:6px 12px;border-top:2px solid #dee2e6;'>SPE</td></tr>"
        for n, r in upgrades:
            rows += f"<tr><td class='weapon-name' colspan='2'>{esc(n)}</td><td colspan='3'>{esc(r) if r else '-'}</td></tr>"
        return rows

    def render_mount_section(unit):
        if not unit.get("mount"): return ""
        mount = unit["mount"]
        if not isinstance(mount, dict) or "mount" not in mount: return ""
        md = mount["mount"]; mname = esc(mount.get("name","Monture")); mcost = mount.get("cost",0)
        mws = md.get("weapon",[]); 
        if isinstance(mws, dict): mws = [mws]
        wrows = ""
        for w in mws:
            if not isinstance(w, dict): continue
            spe = ", ".join(w.get("special_rules",[])) or "-"
            wrows += f"<tr><td class='weapon-name'>{esc(w.get('name','Arme'))}</td><td>{fmt_range(w.get('range','-'))}</td><td>{w.get('attacks','-')}</td><td>{w.get('armor_piercing','-')}</td><td>{spe}</td></tr>"
        mrules = [r for r in md.get("special_rules",[]) if not r.startswith(("Griffes","Sabots","Coriace"))]
        rhtml = " ".join(f'<span class="rule-tag">{esc(r)}</span>' for r in mrules) if mrules else ""
        return f"""<div class="mount-section"><div class="section-title">🐴 {mname} (+{mcost} pts)</div>
{('<div style="margin-bottom:8px;">' + rhtml + '</div>') if rhtml else ""}
<table class="weapon-table"><thead><tr><th>Arme</th><th>RNG</th><th>ATK</th><th>AP</th><th>SPE</th></tr></thead><tbody>{wrows}</tbody></table></div>"""

    sorted_units = sorted(army_list, key=get_priority)
    total_cost = sum(u.get("cost",0) for u in sorted_units)

    html = f"""<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8">
<title>Liste d'Armée OPR - {esc(army_name)}</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root{{--bg:#fff;--hdr:#f8f9fa;--accent:#3498db;--txt:#212529;--muted:#6c757d;--brd:#dee2e6;--red:#e74c3c;--rule:#e9ecef;--mount:#f3e5f5;--badge:#e9ecef;}}
body{{background:var(--bg);color:var(--txt);font-family:'Inter',sans-serif;margin:0;padding:20px;line-height:1.5;}}
.army{{max-width:1000px;margin:0 auto;}}
.army-title{{text-align:center;font-size:28px;font-weight:700;margin-bottom:20px;border-bottom:2px solid var(--accent);padding-bottom:10px;}}
.army-summary{{display:flex;justify-content:space-between;align-items:center;background:var(--hdr);padding:16px;border-radius:8px;margin:20px 0;border:1px solid var(--brd);}}
.summary-cost{{font-family:monospace;font-size:24px;font-weight:bold;color:var(--red);}}
.unit-card{{background:var(--bg);border:1px solid var(--brd);border-radius:8px;margin-bottom:20px;box-shadow:0 1px 3px rgba(0,0,0,.1);page-break-inside:avoid;}}
.unit-header{{padding:16px;background:var(--hdr);border-bottom:1px solid var(--brd);border-radius:8px 8px 0 0;}}
.unit-name-container{{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px;}}
.unit-name{{font-size:20px;font-weight:600;margin:0;}}
.unit-cost{{font-family:monospace;font-size:18px;font-weight:bold;color:var(--red);}}
.unit-stats{{display:flex;gap:12px;padding:12px;margin:0 16px 0;border-radius:6px;justify-content:center;flex-wrap:wrap;}}
.stat-badge{{background:var(--badge);padding:8px 12px;border-radius:20px;font-weight:600;display:flex;align-items:center;gap:6px;min-width:100px;justify-content:center;border:1px solid var(--brd);}}
.stat-value{{font-weight:bold;font-size:16px;}} .stat-label{{font-size:12px;color:var(--muted);}}
.section{{padding:0 16px 16px;}}
.section-title{{font-weight:600;margin:16px 0 8px;font-size:15px;display:flex;align-items:center;gap:8px;border-bottom:1px solid var(--brd);padding-bottom:4px;}}
.weapon-table{{width:100%;border-collapse:collapse;margin:0 0 12px;background:var(--hdr);border-radius:6px;overflow:hidden;border:1px solid var(--brd);}}
.weapon-table th{{background:var(--hdr);padding:8px 12px;text-align:left;font-weight:600;border-bottom:1px solid var(--brd);border-right:1px solid var(--brd);}}
.weapon-table th:last-child{{border-right:none;}}
.weapon-table td{{padding:8px 12px;border-bottom:1px solid var(--brd);border-right:1px solid var(--brd);vertical-align:top;}}
.weapon-table td:last-child{{border-right:none;}} .weapon-table tr:last-child td{{border-bottom:none;}}
.weapon-name{{font-weight:500;}}
.rules-section{{margin:12px 0 0;}} .rules-title{{font-weight:600;margin-bottom:6px;font-size:14px;}}
.rule-tag{{background:var(--rule);padding:4px 10px;border-radius:4px;font-size:13px;border:1px solid var(--brd);margin-right:6px;margin-bottom:6px;display:inline-block;}}
.mount-section{{background:var(--mount);border:1px solid var(--brd);border-radius:6px;padding:12px 16px;margin:12px 0;}}
.faction-rules{{margin-top:40px;padding:20px;border-radius:8px;border:1px solid var(--brd);}}
.rule-item{{margin-bottom:15px;padding-bottom:15px;border-bottom:1px solid var(--brd);}}
.rule-name{{color:var(--accent);font-weight:600;margin-bottom:5px;}}
@media print{{body{{background:white;}} .unit-card{{background:white;border:1px solid #ddd;page-break-inside:avoid;box-shadow:none;}}}}
</style></head><body><div class="army">
<div class="army-title">{esc(army_name)} - {total_cost}/{army_limit} pts</div>
<div class="army-summary">
  <div style="font-size:14px;"><span style="color:var(--muted);">Nombre d'unités :</span> <strong style="font-size:18px;">{len(sorted_units)}</strong></div>
  <div class="summary-cost">{total_cost}/{army_limit} pts</div>
</div>
"""

    for unit in sorted_units:
        if not isinstance(unit, dict): continue
        name = esc(unit.get("name","Unité")); cost = unit.get("cost",0)
        quality = esc(unit.get("quality","-")); defense = esc(unit.get("defense","-"))
        size = unit.get("size",10); coriace = unit.get("coriace",0)

        rules = get_rules(unit)
        rules_html = " ".join(f'<span class="rule-tag">{esc(r)}</span>' for r in rules) if rules else '<span class="rule-tag">Aucune</span>'

        weapons = collect_weapons(unit)
        final_weapons = group_weapons(weapons, unit_size=size)
        weapon_rows = render_weapon_rows(final_weapons, unit_size=size)
        upgrade_rows = render_upgrade_rows(unit)
        mount_section = render_mount_section(unit)

        html += f"""
<div class="unit-card">
  <div class="unit-header">
    <div class="unit-name-container">
      <div class="unit-name">{name}</div>
      <div class="unit-cost">{cost} pts</div>
    </div>
    <div class="unit-stats">
      <div class="stat-badge"><span class="stat-label">QUAL</span><span class="stat-value">{quality}+</span></div>
      <div class="stat-badge"><span class="stat-label">DÉF</span><span class="stat-value">{defense}+</span></div>
      <div class="stat-badge"><span class="stat-label">CORIACE</span><span class="stat-value">{coriace if coriace > 0 else '-'}</span></div>
      <div class="stat-badge"><span class="stat-label">TAILLE</span><span class="stat-value">{size}</span></div>
    </div>
  </div>
  <div class="section">
    <div class="rules-section">
      <div class="rules-title">Règles spéciales</div>
      <div style="margin-bottom:10px;">{rules_html}</div>
    </div>
    <div class="section-title">⚔️ Armes</div>
    <table class="weapon-table">
      <thead><tr><th>Arme</th><th>RNG</th><th>ATK</th><th>AP</th><th>SPE</th></tr></thead>
      <tbody>{weapon_rows}{upgrade_rows}</tbody>
    </table>
    {mount_section}
  </div>
</div>"""

    try:
        faction_rules = st.session_state.get("faction_special_rules", [])
        faction_spells = st.session_state.get("faction_spells", {})
        all_rules = [r for r in faction_rules if isinstance(r, dict)]
        if all_rules or faction_spells:
            html += """<div class="faction-rules">"""
            # Règles spéciales — texte compact (12px)
            if all_rules:
                html += """<h3 style="text-align:center;color:var(--accent);border-bottom:2px solid var(--accent);padding-bottom:8px;margin-bottom:16px;font-size:15px;">📜 Règles spéciales de la faction</h3>"""
                html += """<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px;margin-bottom:24px;">"""
                for rule in sorted(all_rules, key=lambda x: x.get("name","").lower()):
                    html += f'<div class="rule-item"><div class="rule-name" style="font-size:12px;">{esc(rule.get("name",""))}</div><div style="font-size:11px;line-height:1.4;color:#6c757d;">{esc(rule.get("description",""))}</div></div>'
                html += "</div>"
            # Sorts — même style compact
            if faction_spells:
                html += """<h3 style="text-align:center;color:var(--accent);border-bottom:2px solid var(--accent);padding-bottom:8px;margin-bottom:16px;font-size:15px;">✨ Sorts de la faction</h3>"""
                html += """<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px;">"""
                for spell_name, spell_data in faction_spells.items():
                    if isinstance(spell_data, dict):
                        cost = spell_data.get("cost","?")
                        desc = spell_data.get("description","")
                    else:
                        cost = "?"; desc = str(spell_data)
                    html += f'<div class="rule-item"><div class="rule-name" style="font-size:12px;">{esc(spell_name)} <span style="font-weight:400;color:#6c757d;">({cost} pts)</span></div><div style="font-size:11px;line-height:1.4;color:#6c757d;">{esc(desc)}</div></div>'
                html += "</div>"
            html += "</div>"
    except Exception as e:
        html += f'<div style="color:red;padding:10px;">Erreur règles faction : {esc(str(e))}</div>'

    html += f'<div style="text-align:center;margin-top:30px;font-size:12px;color:var(--muted);">Généré par OPR ArmyBuilder FR — {datetime.now().strftime("%d/%m/%Y %H:%M")}</div></div></body></html>'
    return html

@st.cache_data
def load_factions():
    factions = {}; games = set()
    try:
        FACTIONS_DIR = Path(__file__).resolve().parent / "frontend" / "public" / "factions"
        if not FACTIONS_DIR.exists():
            FACTIONS_DIR = Path(__file__).resolve().parent / "lists" / "data" / "factions"
        for fp in FACTIONS_DIR.glob("*.json"):
            try:
                with open(fp, encoding="utf-8") as f:
                    data = json.load(f)
                game = data.get("game"); faction = data.get("faction")
                if game and faction:
                    if game not in factions: factions[game] = {}
                    data.setdefault("faction_special_rules", []); data.setdefault("spells", {}); data.setdefault("units", [])
                    factions[game][faction] = data; games.add(game)
            except Exception as e:
                st.warning(f"Erreur chargement {fp.name}: {e}")
    except Exception as e:
        st.error(f"Erreur chargement des factions: {e}"); return {}, []
    return factions, sorted(games) if games else list(GAME_CONFIG.keys())

if st.session_state.page == "setup":
    game_images = {
        "Age of Fantasy": "assets/games/aof_cover.jpg", "Age of Fantasy Regiments": "assets/games/aofr_cover.jpg",
        "Grimdark Future": "assets/games/gf_cover.jpg", "Grimdark Future Firefight": "assets/games/gff_cover.jpg",
        "Age of Fantasy Skirmish": "assets/games/aofs_cover.jpg", "__default__": "https://i.imgur.com/DEFAULT_IMAGE.jpg"
    }
    current_game = st.session_state.get("game", "__default__")
    image_url = game_images.get("__default__")
    if current_game in game_images and current_game != "__default__":
        try:
            ip = game_images[current_game]
            if Path(ip).exists():
                with open(ip,"rb") as f: image_url = f"data:image/jpeg;base64,{base64.b64encode(f.read()).decode()}"
        except Exception: pass
    st.markdown(f"""<style>.game-bg{{background:linear-gradient(to bottom,rgba(0,0,0,.7) 0%,rgba(0,0,0,0) 100%),url('{image_url}');background-size:cover;background-position:center;padding:2rem;border-radius:10px;margin-bottom:2rem;min-height:200px;display:flex;align-items:center;justify-content:center;}}.game-bg .content{{position:relative;z-index:1;width:100%;text-align:center;}}.game-bg h2{{color:white;text-shadow:1px 1px 3px rgba(0,0,0,.8);}}.game-bg p{{color:rgba(255,255,255,.9);}}</style>""", unsafe_allow_html=True)
    st.markdown('<div class="game-bg"><div class="content">', unsafe_allow_html=True)
    st.markdown("## 🛡️ OPR ArmyBuilder FR")
    st.markdown("<p>Construisez, équilibrez et façonnez vos armées pour Age of Fantasy et Grimdark Future.</p>", unsafe_allow_html=True)
    st.markdown("</div></div>", unsafe_allow_html=True)
    st.markdown("---")
    factions_by_game, games = load_factions()
    if not games: st.error("Aucun jeu trouvé"); st.stop()
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("<span class='badge'>Jeu</span>", unsafe_allow_html=True)
        game = st.selectbox("Jeu", games, index=games.index(st.session_state.get("game")) if st.session_state.get("game") in games else 0, label_visibility="collapsed")
        if "game" not in st.session_state or game != st.session_state.game: st.session_state.game = game; st.rerun()
    with col2:
        st.markdown("<span class='badge'>Faction</span>", unsafe_allow_html=True)
        faction_options = list(factions_by_game.get(game, {}).keys())
        if not faction_options: st.error("Aucune faction disponible"); st.stop()
        faction = st.selectbox("Faction", faction_options, index=0, label_visibility="collapsed")
    with col3:
        st.markdown("<span class='badge'>Format</span>", unsafe_allow_html=True)
        gc = GAME_CONFIG.get(game, {})
        points = st.number_input("Points", min_value=gc.get("min_points",250), max_value=gc.get("max_points",10000), value=gc.get("default_points",1000), step=250, label_visibility="collapsed")
    st.markdown(""); colA, colB = st.columns([2, 1])
    with colA:
        st.markdown("<span class='badge'>Nom de la liste</span>", unsafe_allow_html=True)
        list_name = st.text_input("Nom", value=st.session_state.get("list_name", f"Liste_{datetime.now().strftime('%Y%m%d')}"), label_visibility="collapsed")
    with colB:
        st.markdown("<span class='badge'>Action</span>", unsafe_allow_html=True)
        st.markdown("<p>Prêt à forger votre armée ?</p>", unsafe_allow_html=True)
        if st.button("🔥 Construire l'armée", use_container_width=True, type="primary", disabled=not all([game, faction, points > 0, list_name.strip()]), key="build_army"):
            st.session_state.game = game; st.session_state.faction = faction; st.session_state.points = points; st.session_state.list_name = list_name
            fd = factions_by_game[game][faction]
            st.session_state.units = fd.get("units",[]); st.session_state.faction_special_rules = fd.get("faction_special_rules",[]); st.session_state.faction_spells = fd.get("spells",{})
            st.session_state.army_list = []; st.session_state.army_cost = 0; st.session_state.unit_selections = {}
            st.session_state.page = "army"; st.rerun()

if st.session_state.page == "army":
    required_keys = ["game","faction","points","list_name","units","faction_special_rules","faction_spells"]
    if not all(k in st.session_state for k in required_keys):
        st.error("Configuration incomplète.")
        if st.button("Retour", key="back1"): st.session_state.page = "setup"; st.rerun()
        st.stop()
    if not st.session_state.units:
        st.error("Aucune unité disponible pour cette faction.")
        if st.button("Retour", key="back2"): st.session_state.page = "setup"; st.rerun()
        st.stop()

    st.session_state.setdefault("list_name","Nouvelle Armée"); st.session_state.setdefault("army_cost",0)
    st.session_state.setdefault("army_list",[]); st.session_state.setdefault("unit_selections",{}); st.session_state.setdefault("unit_filter","Tous")

    st.title(f"{st.session_state.list_name} - {st.session_state.army_cost}/{st.session_state.points} pts")
    if st.button("⬅️ Retour à la configuration", key="back3"): st.session_state.page = "setup"; st.rerun()

    st.divider(); st.subheader("📤 Export/Import de la liste")
    colE1, colE2, colE3 = st.columns(3)
    with colE1:
        json_data = json.dumps({"game":st.session_state.game,"faction":st.session_state.faction,"points":st.session_state.points,"list_name":st.session_state.list_name,"army_list":st.session_state.army_list,"army_cost":st.session_state.army_cost}, indent=2, ensure_ascii=False)
        st.download_button("📄 Export JSON", data=json_data, file_name=f"{st.session_state.list_name}.json", mime="application/json", use_container_width=True, key="export_json")
    with colE2:
        html_data = export_html(st.session_state.army_list, st.session_state.list_name, st.session_state.points)
        st.download_button("🌐 Export HTML", data=html_data, file_name=f"{st.session_state.list_name}.html", mime="text/html", use_container_width=True, key="export_html_btn")
    with colE3:
        uploaded_file = st.file_uploader("📥 Importer", type=["json"], label_visibility="collapsed", key="import_file")
        if uploaded_file is not None:
            try:
                imported_data = json.loads(uploaded_file.getvalue().decode("utf-8"))
                if not isinstance(imported_data, dict) or "army_list" not in imported_data: st.error("Fichier invalide."); st.stop()
                st.session_state.list_name = imported_data.get("list_name", st.session_state.list_name)
                st.session_state.army_list = imported_data["army_list"]
                st.session_state.army_cost = imported_data.get("army_cost", sum(u["cost"] for u in imported_data["army_list"]))
                st.success(f"Liste importée ! ({len(imported_data['army_list'])} unités)"); st.rerun()
            except Exception as e: st.error(f"Erreur import: {e}")

    st.subheader("📊 Points de l'Armée")
    pu = st.session_state.army_cost; pt = st.session_state.points
    st.progress(min(pu/pt,1.0) if pt > 0 else 0)
    c1,c2=st.columns(2)
    with c1: st.markdown(f"**Points utilisés :** {pu} pts")
    with c2: st.markdown(f"**Points totaux :** {pt} pts")
    if pu > pt: st.error("⚠️ Dépassement du total de points autorisé")
    st.divider()

    gc = GAME_CONFIG.get(st.session_state.game, {})
    c1,c2,c3=st.columns(3)
    with c1:
        uc=math.floor(st.session_state.points/gc.get("unit_per_points",150)); un=len([u for u in st.session_state.army_list if u.get("type")!="hero"])
        st.progress(min(un/max(uc,1),1.0)); st.caption(f"Unités : {un} / {uc}")
    with c2:
        hc=math.floor(st.session_state.points/gc.get("hero_limit",375)); hn=len([u for u in st.session_state.army_list if u.get("type")=="hero"])
        st.progress(min(hn/max(hc,1),1.0)); st.caption(f"Héros : {hn} / {hc}")
    with c3:
        cc=1+math.floor(st.session_state.points/gc.get("unit_copy_rule",750))
        st.progress(min(cc/5,1.0)); st.caption(f"Copies max : {cc} / unité")
    st.divider()

    if st.session_state.faction_special_rules:
        with st.expander("📜 Règles spéciales de la faction", expanded=False):
            for rule in st.session_state.faction_special_rules:
                if isinstance(rule, dict): st.markdown(f"**{rule.get('name','Règle sans nom')}**: {rule.get('description','')}")
                else: st.markdown(f"- {rule}")
    if st.session_state.faction_spells:
        with st.expander("✨ Sorts de la faction", expanded=False):
            for sn, sd in st.session_state.faction_spells.items():
                if isinstance(sd, dict): st.markdown(f"**{sn}** ({sd.get('cost','?')} pts): {sd.get('description','')}")

    st.subheader("Liste de l'Armée")
    if not st.session_state.army_list:
        st.markdown("Aucune unité ajoutée pour le moment.")
    else:
        for i, ud in enumerate(st.session_state.army_list):
            with st.expander(f"{ud['name']} - {ud['cost']} pts", expanded=False):
                c1,c2,c3,c4=st.columns(4)
                with c1: st.markdown(f"**Type :** {ud.get('type','unit')}")
                with c2: st.markdown(f"**Qualité :** {ud.get('quality','?')}+")
                with c3: st.markdown(f"**Défense :** {ud.get('defense','?')}+")
                with c4:
                    cor=ud.get("coriace",0); st.markdown(f"**Coriace :** {cor if cor > 0 else '-'}"); st.markdown(f"**Taille :** {ud.get('size','?')}")
                weapons=ud.get("weapon",[])
                if weapons:
                    st.markdown("---"); st.markdown("**Armes :**")
                    ws=weapons if isinstance(weapons,list) else [weapons]
                    for w in ws:
                        if isinstance(w,dict):
                            rt=w.get("range","-"); rt=f'{rt}"' if isinstance(rt,(int,float)) else rt
                            st.markdown(f"- {w.get('name','Arme')} | {rt} | A{w.get('attacks','-')} | PA{w.get('armor_piercing','-')} | {', '.join(w.get('special_rules',[])) or '-'}")
                if ud.get("mount"):
                    m=ud["mount"]; md=m.get("mount",{}); st.markdown("---"); st.markdown(f"**Monture :** {m.get('name','Monture')}")
                    mws=md.get("weapon",[]); 
                    if mws:
                        st.markdown("**Armes de la monture :**")
                        if isinstance(mws,dict): mws=[mws]
                        for w in mws:
                            if isinstance(w,dict):
                                rt=w.get("range","-"); rt=f'{rt}"' if isinstance(rt,(int,float)) else rt
                                st.markdown(f"- {w.get('name','Arme')} | {rt} | A{w.get('attacks','-')} | PA{w.get('armor_piercing','-')} | {', '.join(w.get('special_rules',[])) or '-'}")
                if st.button(f"Supprimer {ud['name']}", key=f"delete_{i}"):
                    st.session_state.army_cost -= ud["cost"]; st.session_state.army_list.pop(i); st.rerun()

    st.divider(); st.subheader("Filtres par type d'unité")
    filter_categories = {"Tous":None,"Héros":["hero"],"Héros nommés":["named_hero"],"Unités de base":["unit"],"Véhicules légers / Petits monstres":["light_vehicle"],"Véhicules / Monstres":["vehicle"],"Titans":["titan"]}
    for cat in filter_categories:
        if st.button(cat, key=f"filter_{cat}", use_container_width=True): st.session_state.unit_filter = cat; st.rerun()

    fu = st.session_state.units if st.session_state.unit_filter == "Tous" else [u for u in st.session_state.units if u.get("unit_detail") in filter_categories[st.session_state.unit_filter]]
    st.markdown(f"<div style='text-align:center;margin:10px 0;color:#6c757d;font-size:.9em;'>{len(fu)} unités disponibles (filtre: {st.session_state.unit_filter})</div>", unsafe_allow_html=True)
    if not fu: st.warning(f"Aucune unité pour le filtre '{st.session_state.unit_filter}'."); st.stop()

    unit = st.selectbox("Unité disponible", fu, format_func=format_unit_option, key="unit_select")
    if not unit: st.error("Aucune unité sélectionnée."); st.stop()
    if "upgrade_groups" not in unit: unit["upgrade_groups"] = []

    # Chaque configuration d'unité a un key unique basé sur un compteur.
    # Quand l'unité change, on incrémente → pas de collision entre deux unités du même nom.
    if st.session_state.draft_unit_name != unit['name']:
        st.session_state.draft_counter += 1
        st.session_state.draft_unit_name = unit['name']
    unit_key = f"draft_{st.session_state.draft_counter}"
    st.session_state.unit_selections.setdefault(unit_key, {})
    weapons = copy.deepcopy(list(unit.get("weapon",[]))); selected_options = {}; mount = None
    weapon_cost = 0; mount_cost = 0; upgrades_cost = 0

    for g_idx, group in enumerate(unit.get("upgrade_groups",[])):
        g_key = f"group_{g_idx}"
        gtype = group.get("type","")
        hvo = (bool(group.get("options")) if gtype != "conditional_weapon"
               else any(not o.get("requires") or check_weapon_conditions(unit_key, o.get("requires",[]), unit) for o in group.get("options",[])))
        if not hvo: continue
        st.subheader(group.get("group","Améliorations"))

        if gtype == "weapon":
            bw = unit.get("weapon",[])
            if isinstance(bw,list) and bw:
                lbls=[w.get("name","Arme") for w in bw if isinstance(w,dict)]
                choices=[lbls[0] if len(lbls)==1 else " et ".join(lbls)]
            elif isinstance(bw,dict): choices=[format_weapon_option(bw)]
            else: choices=[]
            opt_map={}
            for o in group.get("options",[]):
                w=o.get("weapon",{})
                lbl=(" et ".join(x.get("name","Arme") for x in w)+f" (+{o['cost']} pts)") if isinstance(w,list) else format_weapon_option(w,o["cost"])
                choices.append(lbl); opt_map[lbl]=o
            if choices:
                cur=st.session_state.unit_selections[unit_key].get(g_key,choices[0])
                ch=st.radio("Sélection de l'arme",choices,index=choices.index(cur) if cur in choices else 0,key=f"{unit_key}_{g_key}_weapon")
                st.session_state.unit_selections[unit_key][g_key]=ch
                if ch!=choices[0]:
                    for ol,o in opt_map.items():
                        if ol==ch: weapon_cost+=o["cost"]; weapons=copy.deepcopy(o["weapon"] if isinstance(o["weapon"],list) else [o["weapon"]]); break

        elif gtype == "conditional_weapon":
            ao=[o for o in group.get("options",[]) if not o.get("requires") or check_weapon_conditions(unit_key,o.get("requires",[]),unit)]
            if not ao: st.markdown(f"<div style='color:#999;font-size:.9em;'>{group.get('description','')} <em>(Non disponible)</em></div>",unsafe_allow_html=True)
            else:
                choices=["Aucune amélioration"]; opt_map={}
                for o in ao:
                    lbl=f"{o.get('name','Amélioration')} (+{o.get('cost',0)} pts)"; choices.append(lbl); opt_map[lbl]=o
                cur=st.session_state.unit_selections[unit_key].get(g_key,choices[0])
                ch=st.radio(group.get("description","Sélectionnez une amélioration"),choices,index=choices.index(cur) if cur in choices else 0,key=f"{unit_key}_{g_key}_cond")
                st.session_state.unit_selections[unit_key][g_key]=ch
                if ch!=choices[0]:
                    opt=opt_map[ch]; upgrades_cost+=opt.get("cost",0)
                    if "weapon" in opt:
                        # conditional_weapon avec "requires" = amélioration d'une seule figurine → _unique=True
                        # conditional_weapon sans "requires" = toute l'unité → _unique absent
                        nw=opt["weapon"]
                        extra={"_upgraded":True}
                        if opt.get("requires"): extra["_unique"]=True
                        if isinstance(nw,dict): weapons.append({**nw,**extra})
                        elif isinstance(nw,list): weapons.extend({**w,**extra} for w in nw)

        elif gtype == "variable_weapon_count":
            st.markdown(f"<div style='margin-bottom:10px;color:#6c757d;'>{group.get('description','')}</div>",unsafe_allow_html=True)
            bw=copy.deepcopy(list(unit.get("weapon",[])) if isinstance(unit.get("weapon"),list) else [unit.get("weapon",{})])
            for oi,option in enumerate(group.get("options",[])):
                st.markdown(f"<h4 style='color:#3498db;'>{option['name']}</h4>",unsafe_allow_html=True)
                req=option.get("requires",[])
                if req and not check_weapon_conditions(unit_key,req,unit): st.markdown(f"<div style='color:#999;font-size:.9em;'>{option['name']} <em>(Non disponible)</em></div>",unsafe_allow_html=True); continue
                mc=unit.get("size",1)
                if "max_count" in option: mc=min(option["max_count"].get("value",mc),unit.get("size",1))
                cnt=st.number_input(f"Nombre de {option['name']} (0 – {mc})",min_value=option.get("min_count",0),max_value=mc,value=option.get("min_count",0),step=1,key=f"{unit_key}_{g_key}_cnt_{oi}")
                tc=cnt*option["cost"]; upgrades_cost+=tc
                st.markdown(f"<div style='margin:10px 0;padding:8px;background:#f8f9fa;border-radius:4px;'><strong>{option['name']}</strong> × {cnt} = <strong style='color:#e74c3c;'>{tc} pts</strong></div>",unsafe_allow_html=True)
                if cnt > 0:
                    fw=bw.copy(); nw=option["weapon"]
                    if isinstance(nw,dict): fw.append({**nw,"_count":cnt,"_replaces":option.get("replaces",[]),"_upgraded":True})
                    elif isinstance(nw,list): fw.extend({**w,"_count":cnt,"_replaces":option.get("replaces",[]),"_upgraded":True} for w in nw)
                    weapons=fw

        elif gtype == "role":
            choices=["Aucun rôle"]; opt_map={}
            for o in group.get("options",[]):
                sr=o.get("special_rules",[]); lbl=o.get("name","Rôle")
                if sr: lbl+=f" | {', '.join(sr)}"
                lbl+=f" (+{o.get('cost',0)} pts)"; choices.append(lbl); opt_map[lbl]=o
            cur=st.session_state.unit_selections[unit_key].get(g_key,choices[0])
            ch=st.radio(group.get("group","Rôle"),choices,index=choices.index(cur) if cur in choices else 0,key=f"{unit_key}_{g_key}_role",horizontal=len(choices)<=4)
            st.session_state.unit_selections[unit_key][g_key]=ch
            if ch!=choices[0]:
                opt=opt_map[ch]; upgrades_cost+=opt.get("cost",0); selected_options[group.get("group","Rôle")]=[opt]
                rw=opt.get("weapon",[])
                if isinstance(rw,list): weapons.extend(copy.deepcopy(rw))
                elif isinstance(rw,dict): weapons.append(copy.deepcopy(rw))

        elif gtype == "upgrades":
            for oi,o in enumerate(group.get("options",[])):
                ok=f"{unit_key}_{g_key}_{o['name']}_{oi}"
                # Afficher les special_rules entre parenthèses si présentes
                sr_label = o.get("special_rules", [])
                sr_str = f" ({', '.join(sr_label)})" if sr_label else ""
                chk=st.checkbox(f"{o['name']}{sr_str} (+{o['cost']} pts)",value=st.session_state.unit_selections[unit_key].get(ok,False),key=ok)
                st.session_state.unit_selections[unit_key][ok]=chk
                if chk: upgrades_cost+=o["cost"]; selected_options.setdefault(group.get("group","Options"),[]).append(o)

        elif gtype == "mount":
            choices=["Aucune monture"]; opt_map={}
            for o in group.get("options",[]): lbl=format_mount_option(o); choices.append(lbl); opt_map[lbl]=o
            cur=st.session_state.unit_selections[unit_key].get(g_key,choices[0])
            ch=st.radio("Monture",choices,index=choices.index(cur) if cur in choices else 0,key=f"{unit_key}_{g_key}_mount")
            st.session_state.unit_selections[unit_key][g_key]=ch
            if ch!="Aucune monture": mount=opt_map[ch]; mount_cost=mount["cost"]

    multiplier=1
    if unit.get("type")!="hero" and unit.get("size",1)>1:
        if st.checkbox("Unité combinée",key=f"{unit_key}_combined"): multiplier=2

    final_cost=(unit.get("base_cost",0)+weapon_cost)*multiplier+upgrades_cost+mount_cost
    st.subheader("Coût de l'unité sélectionnée"); st.markdown(f"**Coût total :** {final_cost} pts"); st.divider()

    # DEBUG temporaire — à supprimer après diagnostic
    with st.expander("🔍 Debug weapons (temporaire)", expanded=False):
        st.write(f"unit_key: {unit_key}")
        st.write(f"weapons ({len(weapons)}):")
        for _w in weapons:
            st.write(f"  - {_w.get('name')} | upgraded={_w.get('_upgraded')} | _count={_w.get('_count')} | _replaces={_w.get('_replaces')}")
    if st.button("➕ Ajouter à l'armée",key=f"{unit_key}_add"):
        if st.session_state.army_cost+final_cost>st.session_state.points:
            st.error(f"⛔ Dépassement : {st.session_state.army_cost+final_cost} / {st.session_state.points} pts"); st.stop()
        cor=unit.get("coriace",0); asr=unit.get("special_rules",[]).copy()
        if mount and "mount" in mount: cor+=mount["mount"].get("coriace_bonus",0)
        for g in unit.get("upgrade_groups",[]):
            gk=f"group_{unit.get('upgrade_groups',[]).index(g)}"
            so=st.session_state.unit_selections[unit_key].get(gk,"")
            if so and so not in ("Aucune amélioration","Aucun rôle"):
                for opt in g.get("options",[]):
                    if "special_rules" in opt and opt.get("name","") in so: asr.extend(opt["special_rules"])
        if mount:
            for r in mount.get("mount",{}).get("special_rules",[]):
                if not r.startswith(("Griffes","Sabots")) and "Coriace" not in r: asr.append(r)
        ud={"name":unit["name"],"type":unit.get("type","unit"),"cost":final_cost,"size":unit.get("size",10)*multiplier if unit.get("type")!="hero" else 1,"quality":unit.get("quality"),"defense":unit.get("defense"),"weapon":weapons,"options":selected_options,"mount":mount,"special_rules":list(set(asr)),"coriace":cor}
        if validate_army_rules(st.session_state.army_list+[ud],st.session_state.points,st.session_state.game):
            st.session_state.army_list.append(ud)
            st.session_state.army_cost += final_cost
            # Incrémenter le draft_counter → la prochaine unité (même nom) repart vierge
            st.session_state.draft_counter += 1
            st.session_state.draft_unit_name = ""
            st.rerun()
