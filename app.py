import json
import copy
import streamlit as st
from pathlib import Path
from datetime import datetime
import re
import math
import base64

st.set_page_config(page_title="OPR ArmyBuilder FR", layout="wide", initial_sidebar_state="auto")

# Couleur d'accent par jeu
_GAME_COLORS = {
    "Age of Fantasy":            "#2980b9",
    "Age of Fantasy Regiments":  "#8e44ad",
    "Grimdark Future":           "#c0392b",
    "Grimdark Future Firefight": "#e67e22",
    "Age of Fantasy Skirmish":   "#27ae60",
}
_acc_color = _GAME_COLORS.get(st.session_state.get("game",""), "#2980b9")

st.markdown(f"""<style>
:root {{--acc: {_acc_color};}}
#MainMenu {{visibility: hidden;}} footer {{visibility: hidden;}} header {{background: transparent;}}
.stApp {{background: #e9ecef; color: #212529;}}
section[data-testid="stSidebar"] {{background: #dee2e6; border-right: 1px solid #adb5bd; box-shadow: 2px 0 5px rgba(0,0,0,0.1);}}
h1, h2, h3 {{color: #202c45; letter-spacing: 0.04em; font-weight: 600;}}
.stSelectbox, .stNumberInput, .stTextInput {{background-color: white; border-radius: 6px; border: 1px solid #ced4da;}}
button[kind="primary"] {{background: var(--acc) !important; color: white !important; font-weight: bold; border-radius: 6px;}}
.badge {{display: inline-block; padding: 0.35rem 0.75rem; border-radius: 4px; background: var(--acc); color: white; font-size: clamp(0.7rem,2vw,0.8rem); margin-bottom: 0.75rem; font-weight: 600;}}
.stButton>button {{background-color: #f8f9fa; border: 1px solid #ced4da; border-radius: 6px; padding: 0.5rem 1rem; color: #212529; font-weight: 500; min-height: 44px;}}
.stProgress > div > div > div {{background-color: var(--acc) !important;}}
.section-sep {{background: var(--acc); opacity:.12; height:2px; margin: 8px 0 12px; border-radius:1px;}}
.section-header {{font-size:clamp(10px,2.5vw,11px); font-weight:700; text-transform:uppercase; letter-spacing:.1em; color: var(--acc); margin: 16px 0 6px; padding: 4px 8px; background: rgba(0,0,0,.03); border-left: 3px solid var(--acc); border-radius: 0 4px 4px 0;}}
/* ── Responsive mobile ── */
@media (max-width: 640px) {{
  .stApp {{font-size: 14px;}}
  [data-testid="column"] {{width: 100% !important; flex: 1 1 100% !important; min-width: 100% !important;}}
  .stButton>button {{width: 100%; min-height: 48px; font-size: 15px;}}
  .stSelectbox label, .stNumberInput label, .stTextInput label {{font-size: 14px !important;}}
  section[data-testid="stSidebar"] {{box-shadow: none;}}
}}
@media (max-width: 480px) {{
  h1 {{font-size: clamp(1.2rem, 5vw, 1.8rem) !important;}}
  h2 {{font-size: clamp(1rem, 4vw, 1.4rem) !important;}}
  h3 {{font-size: clamp(0.9rem, 3.5vw, 1.2rem) !important;}}
}}
</style>""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("<div style='height:1px;'></div>", unsafe_allow_html=True)
with st.sidebar:
    st.title("🛡️ OPR ArmyBuilder FRA")
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
    "Age of Fantasy Regiments": {"min_points": 500, "max_points": 20000, "default_points": 2000, "hero_limit": 500, "unit_copy_rule": 1000, "unit_max_cost_ratio": 0.4, "unit_per_points": 200},
    "Grimdark Future": {"min_points": 250, "max_points": 10000, "default_points": 1000, "hero_limit": 375, "unit_copy_rule": 750, "unit_max_cost_ratio": 0.35, "unit_per_points": 150},
    "Grimdark Future Firefight": {"min_points": 150, "max_points": 1000, "default_points": 300, "hero_limit": 300, "unit_copy_rule": 300, "unit_max_cost_ratio": 0.6, "unit_per_points": 100},
    "Age of Fantasy Skirmish": {"min_points": 150, "max_points": 1000, "default_points": 300, "hero_limit": 300, "unit_copy_rule": 300, "unit_max_cost_ratio": 0.6, "unit_per_points": 100}
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
    Vérifie si les conditions d'un groupe ou d'une option sont remplies.

    Trois types de requires sont supportés :
    1. Nom d'une arme de base encore active (ex: "Bouclier de combat", "ACC")
       → on recalcule les armes actives en appliquant les replaces des groupes type=weapon choisis
    2. Nom d'une arme ajoutée via conditional_weapon (ex: "Fusil lourd de maître")
       → on vérifie si cette arme a été choisie dans un groupe conditional_weapon
    3. Nom d'une option choisie dans un autre groupe (ex: "Pistolet lourd de sergent + Épée énergétique")
       → on vérifie si cette option a été sélectionnée dans les selections
    """
    if not requires:
        return True

    selections = st.session_state.unit_selections.get(unit_key, {})

    # ── 1. Calculer les armes actives à partir des armes de base ───────────
    current_weapons = {w["name"] for w in unit.get("weapon", []) if isinstance(w, dict)} if unit else set()

    # Appliquer les remplacements des groupes type=weapon choisis
    if unit is not None:
        for gi, g in enumerate(unit.get("upgrade_groups", [])):
            if g.get("type") != "weapon":
                continue
            g_key = f"group_{gi}"
            selection = selections.get(g_key)
            if not selection:
                continue
            for o in g.get("options", []):
                w = o.get("weapon", {})
                if isinstance(w, list):
                    lbl = " et ".join(x.get("name", "") for x in w) + f" (+{o['cost']} pts)"
                else:
                    lbl = format_weapon_option(w, o["cost"])
                if lbl == selection:
                    # Retirer les armes remplacées
                    for r in o.get("replaces", []):
                        current_weapons.discard(r)
                    # Si pas de replaces explicite → remplacement total
                    if not o.get("replaces"):
                        current_weapons.clear()
                    # Ajouter les nouvelles armes
                    nw = o.get("weapon", {})
                    if isinstance(nw, list):
                        for w2 in nw:
                            if isinstance(w2, dict):
                                current_weapons.add(w2.get("name", ""))
                    elif isinstance(nw, dict):
                        current_weapons.add(nw.get("name", ""))
                    break

    # ── 2. Ajouter les armes choisies via conditional_weapon ───────────────
    # (ex: "Fusil lourd de maître" choisi dans "Remplacement Bouclier de combat")
    if unit is not None:
        for gi, g in enumerate(unit.get("upgrade_groups", [])):
            if g.get("type") != "conditional_weapon":
                continue
            g_key = f"group_{gi}"
            selection = selections.get(g_key)
            if not selection or selection == "Aucune amélioration":
                continue
            # Trouver l'option choisie et ajouter son arme à current_weapons
            for o in g.get("options", []):
                w_cond = o.get("weapon", {})
                if isinstance(w_cond, dict) and w_cond:
                    lbl = format_weapon_option(w_cond, o.get("cost", 0))
                else:
                    lbl = f"{o.get('name', '')} (+{o.get('cost', 0)} pts)"
                if lbl == selection:
                    nw = o.get("weapon", {})
                    if isinstance(nw, dict) and nw:
                        current_weapons.add(nw.get("name", ""))
                    elif isinstance(nw, list):
                        for w2 in nw:
                            if isinstance(w2, dict):
                                current_weapons.add(w2.get("name", ""))
                    break

    # ── 2b. Ajouter les armes choisies via variable_weapon_count ────────────
    # (ex: "Frappe" ajoutée avec le Lance-flamme béni rapide sur les marcheurs)
    # Les number_input sont stockés dans st.session_state sous la clé du widget
    if unit is not None:
        for gi, g in enumerate(unit.get("upgrade_groups", [])):
            if g.get("type") != "variable_weapon_count":
                continue
            for oi, option in enumerate(g.get("options", [])):
                widget_key = f"{unit_key}_group_{gi}_cnt_{oi}"
                cnt_val = st.session_state.get(widget_key, 0)
                if cnt_val and cnt_val > 0:
                    nw = option.get("weapon", {})
                    if isinstance(nw, dict) and nw:
                        current_weapons.add(nw.get("name", ""))
                    elif isinstance(nw, list):
                        for w2 in nw:
                            if isinstance(w2, dict):
                                current_weapons.add(w2.get("name", ""))

    # ── 3. Collecter les noms d'options choisies ───────────────────────────
    # Pour les requires du type "Pistolet lourd de sergent + Épée énergétique"
    selected_option_names = set()
    for sel in selections.values():
        if isinstance(sel, str) and sel not in ("Aucune amélioration", "Aucune arme", "Aucun rôle", "Aucune monture"):
            # Extraire le nom avant le " (+" du coût
            name_part = sel.split(" (+")[0].strip()
            selected_option_names.add(name_part)

    # ── 4. Vérifier chaque require ─────────────────────────────────────────
    for req in requires:
        if req not in current_weapons and req not in selected_option_names:
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
    return f"{name_part} | Qual {u.get('quality','?')}+ | Déf {u.get('defense','?')}+ | {weapon_text} | {rules_text} | {u.get('base_cost',0)}pts"

def format_weapon_option(weapon, cost=0):
    if not weapon or not isinstance(weapon, dict): return "Aucune arme"
    rng = weapon.get("range","Mêlée")
    if rng in (None,"-","mêlée","Mêlée") or str(rng).lower()=="mêlée": rng_str="Mêlée"
    elif isinstance(rng,(int,float)): rng_str=f'{int(rng)}"'
    else: s=str(rng).strip(); rng_str=s if s.endswith('"') else f'{s}"'
    sr = weapon.get("special_rules",[])
    profile_inner = f"{rng_str}/A{weapon.get('attacks','?')}/PA{weapon.get('armor_piercing','?')}"
    if sr: profile_inner += f", {', '.join(sr)}"
    profile = f"{weapon.get('name','Arme')} ({profile_inner})"
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
        result = []
        bw = unit.get("weapon", [])
        if isinstance(bw, dict): bw = [bw]
        for w in bw:
            if isinstance(w, dict):
                wc = w.copy(); wc.setdefault("range", "Mêlée")
                if not wc.get("_upgraded") and "_count" in wc:
                    del wc["_count"]
                result.append(wc)
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
        wmap = {}
        for w in weapons:
            if not isinstance(w, dict) or w.get("_mount_weapon"): continue
            wc = w.copy(); wc.setdefault("range","Mêlée")
            key = (wc.get("name",""), wc.get("range",""), wc.get("attacks",""),
                   wc.get("armor_piercing",""), tuple(sorted(wc.get("special_rules",[]))))
            cnt = wc.get("_count", 1) or 1
            if key not in wmap: wmap[key] = wc; wmap[key]["_display_count"] = cnt
            else: wmap[key]["_display_count"] += cnt
        for w in weapons:
            if not isinstance(w, dict) or w.get("_mount_weapon"): continue
            if "_count" not in w: continue
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
        return ""

    def render_upgrades_section(unit):
        upgrades = []
        if "options" in unit and isinstance(unit["options"], dict):
            for group_opts in unit["options"].values():
                opts = group_opts if isinstance(group_opts, list) else [group_opts]
                for opt in opts:
                    if not isinstance(opt, dict): continue
                    rules = ", ".join(opt.get("special_rules", []))
                    upgrades.append((opt.get("name","Amélioration"), rules))
        if not upgrades: return ""
        items = ""
        for n, r in upgrades:
            items += f'<span class="rule-tag" style="background:#e8f4fd;border-color:#b8d9f0;">{esc(n)}'
            if r: items += f' <span style="font-weight:400;color:#555;">({esc(r)})</span>'
            items += '</span>'
        return (
            '<div style="border-top:1px solid var(--brd);margin-top:8px;padding-top:8px;">'
            '<div class="rules-title">Améliorations</div>'
            f'<div style="margin-bottom:4px;">{items}</div>'
            '</div>'
        )

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
<table class="weapon-table"><thead><tr><th>Arme</th><th>Por</th><th>Att</th><th>PA</th><th>Spé</th></tr></thead><tbody>{wrows}</tbody></table></div>"""

    sorted_units = sorted(army_list, key=get_priority)
    total_cost = sum(u.get("cost",0) for u in sorted_units)

    html = f"""<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8">
<title>Liste d'Armée OPR - {esc(army_name)}</title>
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
.weapon-table td:last-child{{border-right:none;}} .weapon-table tr:last-child td{{border-bottom:none;}}
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
<div class="army-title">{esc(army_name)} — {total_cost}/{army_limit} pts</div>
<div class="army-summary">
  <div><span style="color:var(--muted);">Unités :</span> <strong>{len(sorted_units)}</strong></div>
  <div class="summary-cost">{total_cost}/{army_limit} pts</div>
</div>
<div class="units-grid">
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
        upgrade_rows     = render_upgrade_rows(unit)
        upgrades_section = render_upgrades_section(unit)
        mount_section    = render_mount_section(unit)

        detail_labels = {
            "named_hero":    "Héros nommé",
            "hero":          "Héros",
            "unit":          "Unité de base",
            "light_vehicle": "Véhicule léger / Petit monstre",
            "vehicle":       "Véhicule / Monstre",
            "titan":         "Titan",
        }
        detail_label = detail_labels.get(unit.get("unit_detail", unit.get("type","unit")), "")

        html += f"""<div class="unit-card">
  <div class="unit-header">
    <div class="unit-name-container">
      <div class="unit-name">{name}{'<div class="unit-type">' + detail_label + '</div>' if detail_label else ''}</div>
      <div class="unit-cost">{cost} pts</div>
    </div>
    <div class="unit-stats">
      <div class="stat-badge"><span class="stat-label">QUAL</span><span class="stat-value">{quality}+</span></div>
      <div class="stat-badge"><span class="stat-label">DÉF</span><span class="stat-value">{defense}+</span></div>
      {'<div class="stat-badge"><span class="stat-label">CORIACE</span><span class="stat-value">' + str(coriace) + '</span></div>' if coriace > 0 else ''}
      <div class="stat-badge"><span class="stat-label">TAILLE</span><span class="stat-value">{size}</span></div>
    </div>
  </div>
  <div class="section">
    <div class="rules-section">
      <div class="rules-title">Règles spéciales</div>
      <div style="margin-bottom:4px;">{rules_html}</div>
      {upgrades_section}
    </div>
    <div class="section-title">⚔️ Armes</div>
    <table class="weapon-table">
      <thead><tr><th>Arme</th><th>Por</th><th>Att</th><th>PA</th><th>Spé</th></tr></thead>
      <tbody>{weapon_rows}</tbody>
    </table>
    {mount_section}
  </div>
</div>"""

    html += "</div>\n"

    try:
        faction_rules = st.session_state.get("faction_special_rules", [])
        faction_spells = st.session_state.get("faction_spells", {})
        all_rules = [r for r in faction_rules if isinstance(r, dict)]
        if all_rules or faction_spells:
            html += """<div class="legend-page"><div class="faction-rules">"""
            html += """<div class="legend-title">📜 Règles spéciales &amp; Sorts</div>"""
            html += """<div style="columns:2;column-gap:16px;column-rule:1px solid #dee2e6;">"""

            if all_rules:
                for rule in sorted(all_rules, key=lambda x: x.get("name","").lower()):
                    html += (
                        f'<div class="rule-item" style="break-inside:avoid;">'
                        f'<div class="rule-name">{esc(rule.get("name",""))}</div>'
                        f'<div class="rule-desc">{esc(rule.get("description",""))}</div>'
                        f'</div>'
                    )

            if faction_spells:
                if all_rules:
                    html += '<div class="rule-item" style="break-inside:avoid;border-bottom:2px solid var(--accent);margin-bottom:8px;"><div style="font-size:10px;font-weight:700;color:var(--accent);">✨ Sorts</div></div>'
                for spell_name, spell_data in faction_spells.items():
                    if isinstance(spell_data, dict):
                        desc = spell_data.get("description","")
                    else:
                        desc = str(spell_data)
                    html += (
                        f'<div class="rule-item" style="break-inside:avoid;">'
                        f'<div class="rule-name">{esc(spell_name)}</div>'
                        f'<div class="rule-desc">{esc(desc)}</div>'
                        f'</div>'
                    )

            html += "</div></div></div>"
    except Exception as e:
        html += f'<div style="color:red;padding:10px;">Erreur règles faction : {esc(str(e))}</div>'

    import urllib.parse as _urlp
    _payload = json.dumps({
        "faction": army_name, "pts": army_limit,
        "units": [{"n": u.get("name",""), "c": u.get("cost",0)} for u in army_list]
    }, ensure_ascii=False, separators=(',',':'))

    _qr_img_tag = ""
    try:
        import qrcode as _qrc, io as _io, base64 as _b64
        _qr = _qrc.QRCode(version=None, error_correction=_qrc.constants.ERROR_CORRECT_M, box_size=4, border=2)
        _qr.add_data(_payload); _qr.make(fit=True)
        _img = _qr.make_image(fill_color="black", back_color="white")
        _buf = _io.BytesIO(); _img.save(_buf, format="PNG"); _buf.seek(0)
        _qr_b64 = _b64.b64encode(_buf.read()).decode()
        _qr_img_tag = f'<img src="data:image/png;base64,{_qr_b64}" style="width:96px;height:96px;display:block;margin:0 auto;border:1px solid var(--brd);border-radius:4px;" alt="QR code">'
    except Exception:
        _qr_url = "https://api.qrserver.com/v1/create-qr-code/?data=" + _urlp.quote(_payload) + "&size=96x96&margin=2"
        _qr_img_tag = f'<img src="{_qr_url}" style="width:96px;height:96px;display:block;margin:0 auto;border:1px solid var(--brd);border-radius:4px;" alt="QR code">'

    html += (
        '<div style="text-align:center;margin-top:28px;padding:16px 0;border-top:1px solid var(--brd);">'
        '<div style="font-size:10px;color:var(--muted);margin-bottom:8px;letter-spacing:.06em;text-transform:uppercase;">Scanner pour partager</div>'
        + _qr_img_tag +
        '</div>'
    )
    html += f'<div style="text-align:center;margin-top:16px;font-size:11px;color:var(--muted);">Généré par OPR ArmyBuilder FRA — {datetime.now().strftime("%d/%m/%Y %H:%M")}</div></div></body></html>'
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
    factions_by_game, games = load_factions()
    if not games: st.error("Aucun jeu trouvé"); st.stop()

    current_game = st.session_state.get("game", games[0] if games else "")

    game_meta = {
        "Age of Fantasy":            {"color": "#2980b9", "short": "AoF"},
        "Age of Fantasy Regiments": {"color": "#8e44ad", "short": "AoF:R"},
        "Grimdark Future":           {"color": "#c0392b", "short": "GDF"},
        "Grimdark Future Firefight":{"color": "#e67e22", "short": "GDF:FF"},
        "Age of Fantasy Skirmish":  {"color": "#27ae60", "short": "AoF:S"},
    }
    _BASE = Path(__file__).resolve().parent
    game_images = {
        "Age of Fantasy":            str(_BASE / "assets/games/aof_cover.jpg"),
        "Age of Fantasy Regiments": str(_BASE / "assets/games/aofr_cover.jpg"),
        "Grimdark Future":           str(_BASE / "assets/games/gf_cover.jpg"),
        "Grimdark Future Firefight":str(_BASE / "assets/games/gff_cover.jpg"),
        "Age of Fantasy Skirmish":  str(_BASE / "assets/games/aofs_cover.jpg"),
    }
    meta  = game_meta.get(current_game, {"color": "#2980b9", "short": "OPR"})
    acc   = meta["color"]
    short = meta["short"]

    vignette_html = ""
    img_path = game_images.get(current_game, "")
    if img_path and Path(img_path).exists():
        try:
            with open(img_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            vignette_html = f'<img src="data:image/jpeg;base64,{b64}" style="width:100%;height:100%;object-fit:cover;border-radius:8px;">'
        except Exception:
            pass
    if not vignette_html:
        vignette_html = f"""<svg width="64" height="64" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
          <polygon points="32,6 58,54 6,54" stroke="{acc}" stroke-width="2.5" fill="none"/>
          <polygon points="32,16 50,48 14,48" stroke="{acc}" stroke-width="1.5" fill="{acc}" fill-opacity=".12"/>
          <polygon points="32,28 42,44 22,44" fill="{acc}" fill-opacity=".7"/>
        </svg>"""

    game_subtitles = {
        "Age of Fantasy":             "Construisez vos armées pour les batailles fantastiques",
        "Age of Fantasy Regiments":  "Forgez vos régiments pour la guerre des âges",
        "Grimdark Future":            "Forgez vos escouades pour les guerres du futur",
        "Grimdark Future Firefight": "Constituez vos escouades pour les combats rapprochés",
        "Age of Fantasy Skirmish":   "Composez vos bandes pour l'escarmouche fantastique",
    }
    game_subtitle = game_subtitles.get(current_game, "Construisez et commandez vos armées")

    tri_svg = f"""<svg style="position:absolute;inset:0;width:100%;height:100%;opacity:.18;"
        viewBox="0 0 900 220" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <pattern id="tp" x="0" y="0" width="32" height="28" patternUnits="userSpaceOnUse">
          <polygon points="16,2 30,26 2,26" fill="none" stroke="white" stroke-width="1"/>
          <polygon points="0,28 14,4 28,28" fill="none" stroke="white" stroke-width=".6" opacity=".5"/>
        </pattern>
        <radialGradient id="rfade" cx="65%" cy="45%" r="58%">
          <stop offset="0%" stop-color="white" stop-opacity="1"/>
          <stop offset="55%" stop-color="white" stop-opacity=".25"/>
          <stop offset="100%" stop-color="white" stop-opacity="0"/>
        </radialGradient>
        <mask id="tm"><rect width="900" height="220" fill="url(#rfade)"/></mask>
      </defs>
      <rect width="900" height="220" fill="url(#tp)" mask="url(#tm)"/>
    </svg>"""

    st.markdown(f"""
<div style="background:#1a2332;border-radius:12px 12px 0 0;position:relative;
            overflow:hidden;height:clamp(130px,25vw,200px);display:flex;align-items:center;
            justify-content:center;margin-bottom:0;">
  {tri_svg}
  <div style="position:relative;z-index:2;text-align:center;padding:0 2rem;">
    <div style="display:flex;align-items:center;justify-content:center;gap:10px;margin-bottom:8px;">
    </div>
    <div style="font-size:clamp(24px,6vw,38px);font-weight:700;color:#fff;letter-spacing:.03em;line-height:1.1;">
      ArmyBuilder <span style="color:#002395;font-weight:700;">F</span><span style="color:#EDEDED;font-weight:700;text-shadow:0 0 2px rgba(0,0,0,.5);">R</span><span style="color:#ED2939;font-weight:700;">A</span>
    </div>
    <div style="font-size:12px;color:rgba(255,255,255,.45);margin-top:8px;letter-spacing:.04em;">Constructeur d'armée pour OPR en français</div>
    <div style="width:44px;height:3px;background:{acc};border-radius:2px;margin:9px auto 0;"></div>
  </div>
</div>
<div style="background:white;border:1px solid #dee2e6;border-top:none;
            border-radius:0 0 12px 12px;padding:16px;margin-bottom:1.5rem;">
  <div style="display:flex;gap:16px;align-items:flex-start;flex-wrap:wrap;">
    <div style="flex-shrink:0;width:min(130px,25vw);height:min(130px,25vw);border-radius:8px;
                overflow:hidden;border:1px solid {acc};
                display:flex;align-items:center;justify-content:center;
                background:#1a2332;">
      {vignette_html}
    </div>
    <div style="flex:1;padding-top:6px;line-height:1.7;">
      <div style="font-size:clamp(13px,3vw,15px);font-weight:600;color:#212529;margin-bottom:4px;">{short}</div>
      <div style="font-size:clamp(12px,2.5vw,13px);color:#6c757d;">{game_subtitle}</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("<span class='badge'>Jeu</span>", unsafe_allow_html=True)
        game = st.selectbox("Jeu", games, index=games.index(current_game) if current_game in games else 0, label_visibility="collapsed")
        if game != current_game: st.session_state.game = game; st.rerun()
    with col2:
        st.markdown("<span class='badge'>Faction</span>", unsafe_allow_html=True)
        faction_options = list(factions_by_game.get(game, {}).keys())
        if not faction_options: st.error("Aucune faction disponible"); st.stop()
        _cur_faction = st.session_state.get("faction", "")
        _faction_idx = faction_options.index(_cur_faction) if _cur_faction in faction_options else 0
        faction = st.selectbox("Faction", faction_options, index=_faction_idx, label_visibility="collapsed")
        if st.session_state.get("army_list") and faction != st.session_state.get("faction",""):
            st.warning("⚠️ Changer de faction réinitialisera l'armée en cours.")
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
        if st.button("🔥 Construire l'armée", use_container_width=True, type="primary", disabled=not all([game, faction, points > 0]), key="build_army"):
            _game_changed    = st.session_state.get("game")    != game
            _faction_changed = st.session_state.get("faction") != faction
            st.session_state.game = game; st.session_state.faction = faction; st.session_state.points = points
            st.session_state.list_name = list_name.strip() or f"Liste_{datetime.now().strftime('%Y%m%d')}"
            fd = factions_by_game[game][faction]
            st.session_state.units = fd.get("units",[]); st.session_state.faction_special_rules = fd.get("faction_special_rules",[]); st.session_state.faction_spells = fd.get("spells",{})
            if _game_changed or _faction_changed:
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
    _list_name = st.session_state.list_name
    _auto_name = bool(re.match(r'^Liste_[0-9]{8}$', _list_name))
    if _auto_name:
        _slug = re.sub(r'[^a-z0-9]+', '_', st.session_state.faction.lower()).strip('_')
        _base_name = f"{_slug}_{st.session_state.points}pts_{datetime.now().strftime('%Y%m%d')}"
    else:
        _base_name = re.sub(r'[^a-zA-Z0-9_ -]', '_', _list_name)

    colE1, colE2, colE3 = st.columns(3)
    with colE1:
        json_data = json.dumps({"game":st.session_state.game,"faction":st.session_state.faction,"points":st.session_state.points,"list_name":st.session_state.list_name,"army_list":st.session_state.army_list,"army_cost":st.session_state.army_cost,"exported_at":datetime.now().strftime("%Y-%m-%d %H:%M")}, indent=2, ensure_ascii=False)
        st.download_button("📄 Export JSON", data=json_data, file_name=f"{_base_name}.json", mime="application/json", use_container_width=True, key="export_json")
    with colE2:
        html_data = export_html(st.session_state.army_list, st.session_state.list_name, st.session_state.points)
        st.download_button("🌐 Export HTML", data=html_data, file_name=f"{_base_name}.html", mime="text/html", use_container_width=True, key="export_html_btn")
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
    gc = GAME_CONFIG.get(st.session_state.game, {})
    uc  = math.floor(pt / gc.get("unit_per_points", 150))
    un  = len([u for u in st.session_state.army_list if u.get("type") != "hero"])
    hc  = math.floor(pt / gc.get("hero_limit", 375))
    hn  = len([u for u in st.session_state.army_list if u.get("type") == "hero"])
    cc  = 1 + math.floor(pt / gc.get("unit_copy_rule", 750))
    pct = min(pu / pt * 100, 100) if pt > 0 else 0
    restants = pt - pu

    bar_color   = "#e74c3c" if pu >= pt else ("#f39c12" if pct >= 85 else "#2980b9")
    pts_color   = "#e74c3c" if pu >= pt else ("#f39c12" if pct >= 85 else "#212529")
    hero_color  = "#e74c3c" if hn >= hc else "#2980b9"
    hero_bg     = "#FCEBEB" if hn >= hc else "#E6F1FB"
    hero_txt    = "#791F1F" if hn >= hc else "#0C447C"
    hero_label  = f"Héros : {hn} / {hc}" + (" — LIMITE" if hn >= hc else "")
    reste_label = f"⚠️ {abs(restants)} pts de dépassement !" if pu > pt else f"{restants} pts restants"
    reste_color = "#e74c3c" if pu > pt else "#6c757d"

    st.markdown(f"""
<div style="margin-bottom:16px;">
  <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:6px;">
    <span style="font-size:clamp(18px,4vw,22px);font-weight:700;color:{pts_color};">{pu} pts</span>
    <span style="font-size:13px;color:#6c757d;">/ {pt} pts</span>
  </div>
  <div style="height:16px;background:#e9ecef;border-radius:8px;overflow:hidden;position:relative;margin-bottom:6px;">
    <div style="width:{pct:.1f}%;height:100%;background:{bar_color};border-radius:8px;transition:width .3s;"></div>
  </div>
  <div style="font-size:clamp(11px,2.5vw,12px);color:{reste_color};text-align:right;margin-bottom:12px;">{reste_label}</div>
  <div style="display:flex;gap:8px;flex-wrap:wrap;">
    <span style="padding:5px 10px;border-radius:6px;font-size:clamp(11px,2vw,12px);font-weight:500;background:#E6F1FB;color:#0C447C;">
      Unités : {un} / {uc}
    </span>
    <span style="padding:5px 12px;border-radius:6px;font-size:12px;font-weight:500;background:{hero_bg};color:{hero_txt};">
      {hero_label}
    </span>
    <span style="padding:5px 12px;border-radius:6px;font-size:12px;font-weight:500;background:#f0f0f0;color:#555;">
      Copies max : {cc} / unité
    </span>
  </div>
</div>
""", unsafe_allow_html=True)
    st.divider()

    if st.session_state.faction_special_rules:
        with st.expander("📜 Règles spéciales de la faction", expanded=False):
            for rule in st.session_state.faction_special_rules:
                if isinstance(rule, dict): st.markdown(f"**{rule.get('name','Règle sans nom')}**: {rule.get('description','')}")
                else: st.markdown(f"- {rule}")
    if st.session_state.faction_spells:
        with st.expander("✨ Sorts de la faction", expanded=False):
            for sn, sd in st.session_state.faction_spells.items():
                if isinstance(sd, dict): st.markdown(f"**{sn}**: {sd.get('description','')}")

    st.subheader("Liste de l'Armée")
    if not st.session_state.army_list:
        st.markdown("Aucune unité ajoutée pour le moment.")
    else:
        def fmt_rng(r):
            if r in (None,"-","mêlée","Mêlée") or str(r).lower()=="mêlée": return "Mêlée"
            return f'{int(r)}"' if isinstance(r,(int,float)) else str(r)
        def fmt_weapon_line(w):
            if not isinstance(w,dict): return ""
            sr=", ".join(w.get("special_rules",[])); rng=fmt_rng(w.get("range","Mêlée"))
            return f"{w.get('name','?')} ({rng}/A{w.get('attacks','?')}/PA{w.get('armor_piercing','?')}{', '+sr if sr else ''})"

        _section_labels = {
            "named_hero":   ("★ Héros nommés",    "⭐"),
            "hero":         ("Héros",              "🦸"),
            "unit":         ("Unités de base",     "⚔️"),
            "light_vehicle":("Véhicules légers",   "🐉"),
            "vehicle":      ("Véhicules / Monstres","🏰"),
            "titan":        ("Titans",             "💀"),
        }
        _current_section = None

        for i, ud in enumerate(st.session_state.army_list):
            _sec = ud.get("unit_detail", ud.get("type","unit"))
            if _sec != _current_section:
                _current_section = _sec
                _lbl, _ico = _section_labels.get(_sec, (_sec, "•"))
                st.markdown(f'<div class="section-header">{_ico} {_lbl}</div>', unsafe_allow_html=True)

            with st.expander(f"{ud['name']} — {ud['cost']} pts", expanded=False):
                cor=ud.get("coriace",0)
                stats_html = (
                    f"<span style='margin-right:12px;'>Qual <b>{ud.get('quality','?')}+</b></span>"
                    f"<span style='margin-right:12px;'>Déf <b>{ud.get('defense','?')}+</b></span>"
                    f"<span style='margin-right:12px;'>Taille <b>{ud.get('size','?')}</b></span>"
                    + (f"<span>Coriace <b>{cor}</b></span>" if cor else "")
                )
                st.markdown(f"<div style='font-size:clamp(12px,2vw,0.85em);color:#555;margin-bottom:6px;'>{stats_html}</div>", unsafe_allow_html=True)

                weapons=ud.get("weapon",[])
                ws=weapons if isinstance(weapons,list) else [weapons]
                armes=[fmt_weapon_line(w) for w in ws if isinstance(w,dict)]
                if armes:
                    st.markdown(
                        "<div style='font-size:clamp(12px,2vw,0.8em);color:#333;margin-bottom:4px;'>"
                        "<b>Armes :</b> " + " · ".join(armes) + "</div>",
                        unsafe_allow_html=True)

                upgrades_items=[]
                if "options" in ud and isinstance(ud["options"],dict):
                    for gopts in ud["options"].values():
                        opts=gopts if isinstance(gopts,list) else [gopts]
                        for opt in opts:
                            if not isinstance(opt,dict): continue
                            sr_upg=", ".join(opt.get("special_rules",[]))
                            label=opt.get("name","?")
                            upgrades_items.append(f"{label}" + (f" <span style='color:#888;'>({sr_upg})</span>" if sr_upg else ""))
                if upgrades_items:
                    st.markdown(
                        "<div style='font-size:clamp(12px,2vw,0.8em);color:#333;margin-bottom:4px;'>"
                        "<b>Améliorations :</b> " + " · ".join(upgrades_items) + "</div>",
                        unsafe_allow_html=True)

                if ud.get("mount"):
                    m=ud["mount"]; md=m.get("mount",{})
                    mws=md.get("weapon",[]); mws=mws if isinstance(mws,list) else [mws]
                    marmes=[fmt_weapon_line(w) for w in mws if isinstance(w,dict)]
                    msr=[r for r in md.get("special_rules",[]) if "Coriace" not in r]
                    mount_parts=[]
                    if marmes: mount_parts.append("Armes : "+" · ".join(marmes))
                    if msr: mount_parts.append(", ".join(msr))
                    st.markdown(
                        f"<div style='font-size:clamp(12px,2vw,0.8em);color:#333;margin-bottom:4px;'>"
                        f"<b>🐴 {m.get('name','Monture')}</b>"
                        + (f" — {' | '.join(mount_parts)}" if mount_parts else "")
                        + "</div>",
                        unsafe_allow_html=True)

                sr_unit=ud.get("special_rules",[])
                if sr_unit:
                    st.markdown(
                        "<div style='font-size:clamp(12px,2vw,0.78em);color:#666;margin-bottom:6px;'>"
                        + ", ".join(sr_unit) + "</div>",
                        unsafe_allow_html=True)

                _col1, _col2 = st.columns(2)
                with _col1:
                    if st.button("🗑 Supprimer", key=f"delete_{i}", type="secondary", use_container_width=True):
                        st.session_state.army_cost -= ud["cost"]; st.session_state.army_list.pop(i); st.rerun()
                with _col2:
                    if st.button("⧉ Dupliquer", key=f"dup_{i}", use_container_width=True):
                        import copy as _copy
                        _dup = _copy.deepcopy(ud)
                        st.session_state.army_list.insert(i+1, _dup)
                        st.session_state.army_cost += _dup["cost"]
                        st.rerun()

    st.divider(); st.subheader("Filtres par type d'unité")
    filter_categories = {"Tous":None,"Héros":["hero"],"Héros nommés":["named_hero"],"Unités de base":["unit"],"Véhicules légers / Petits monstres":["light_vehicle"],"Véhicules / Monstres":["vehicle"],"Titans":["titan"]}
    for cat in filter_categories:
        if st.button(cat, key=f"filter_{cat}", use_container_width=True): st.session_state.unit_filter = cat; st.rerun()

    fu = st.session_state.units if st.session_state.unit_filter == "Tous" else [u for u in st.session_state.units if u.get("unit_detail") in filter_categories[st.session_state.unit_filter]]

    _search = st.text_input("🔍 Rechercher une unité", value="", placeholder="Nom de l'unité…", label_visibility="collapsed", key="unit_search")
    if _search.strip():
        fu = [u for u in fu if _search.strip().lower() in u.get("name","").lower()]

    st.markdown(f"<div style='text-align:right;margin:4px 0 8px;color:#6c757d;font-size:.85em;'>{len(fu)} unité(s) — filtre : {st.session_state.unit_filter}</div>", unsafe_allow_html=True)
    if not fu: st.warning(f"Aucune unité trouvée."); st.stop()

    unit = st.selectbox("Unité disponible", fu, format_func=format_unit_option, key="unit_select")
    if not unit: st.error("Aucune unité sélectionnée."); st.stop()
    if "upgrade_groups" not in unit: unit["upgrade_groups"] = []

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

        # ── Vérifier si le groupe entier doit être affiché ──────────────────
        # Un groupe avec requires au niveau du groupe est conditionnel
        group_requires = group.get("requires", [])
        if group_requires and not check_weapon_conditions(unit_key, group_requires, unit):
            continue

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
                    w_cond=o.get("weapon",{})
                    if isinstance(w_cond,dict) and w_cond:
                        lbl=format_weapon_option(w_cond, o.get("cost",0))
                    else:
                        lbl=f"{o.get('name','Amélioration')} (+{o.get('cost',0)} pts)"
                    choices.append(lbl); opt_map[lbl]=o
                cur=st.session_state.unit_selections[unit_key].get(g_key,choices[0])
                ch=st.radio(group.get("description","Sélectionnez une amélioration"),choices,index=choices.index(cur) if cur in choices else 0,key=f"{unit_key}_{g_key}_cond")
                st.session_state.unit_selections[unit_key][g_key]=ch
                if ch!=choices[0]:
                    opt=opt_map[ch]; upgrades_cost+=opt.get("cost",0)
                    if "weapon" in opt:
                        nw=opt["weapon"]
                        opt_replaces=opt.get("replaces",[])
                        # Retirer les armes remplacées de la liste weapons
                        if opt_replaces:
                            weapons=[w for w in weapons if isinstance(w,dict) and w.get("name") not in opt_replaces]
                        extra={"_upgraded":True}
                        if opt.get("requires") and not opt_replaces: extra["_unique"]=True
                        if isinstance(nw,dict): weapons.append({**nw,**extra})
                        elif isinstance(nw,list): weapons.extend({**w2,**extra} for w2 in nw)

        elif gtype == "variable_weapon_count":
            st.markdown(f"<div style='margin-bottom:10px;color:#6c757d;'>{group.get('description','')}</div>",unsafe_allow_html=True)
            bw=copy.deepcopy(list(unit.get("weapon",[])) if isinstance(unit.get("weapon"),list) else [unit.get("weapon",{})])
            for oi,option in enumerate(group.get("options",[])):
                req=option.get("requires",[])
                if req and not check_weapon_conditions(unit_key,req,unit): st.markdown(f"<div style='color:#999;font-size:.9em;'>{option['name']} <em>(Non disponible)</em></div>",unsafe_allow_html=True); continue
                st.markdown(f"<h4 style='color:#3498db;'>{option['name']}</h4>",unsafe_allow_html=True)
                # max_count types :
                # "fixed"            → valeur absolue
                # "size_based"       → min(value, size)
                # "linked"           → valeur du slider d'un autre groupe (ex: nb de Frappess = nb de tirs choisis)
                # "linked_remainder" → total - valeur du slider source (ex: nb de Fléaux restants)
                mc_cfg=option.get("max_count",{})
                mc_type=mc_cfg.get("type","size_based")
                if mc_type == "fixed":
                    mc=mc_cfg.get("value",1)
                elif mc_type == "size_based":
                    mc=min(mc_cfg.get("value", unit.get("size",1)), unit.get("size",1))
                elif mc_type in ("linked", "linked_remainder"):
                    src_g=mc_cfg.get("source_group",0)
                    src_o=mc_cfg.get("source_option",0)
                    src_key=f"{unit_key}_group_{src_g}_cnt_{src_o}"
                    src_val=st.session_state.get(src_key,0) or 0
                    if mc_type == "linked":
                        mc=src_val
                    else:  # linked_remainder
                        mc=max(0, mc_cfg.get("total",2) - src_val)
                else:
                    mc=unit.get("size",1)
                cnt=st.number_input(f"Nombre de {option['name']} (0 – {mc})",min_value=option.get("min_count",0),max_value=mc,value=option.get("min_count",0),step=1,key=f"{unit_key}_{g_key}_cnt_{oi}")
                tc=cnt*option["cost"]; upgrades_cost+=tc
                st.markdown(f"<div style='margin:10px 0;padding:8px;background:#f8f9fa;border-radius:4px;'><strong>{option['name']}</strong> × {cnt} = <strong style='color:#e74c3c;'>{tc} pts</strong></div>",unsafe_allow_html=True)
                if cnt > 0:
                    fw=bw.copy(); nw=option["weapon"]
                    opt_replaces=option.get("replaces",[])
                    # Retirer les armes remplacées (proportionnellement au count)
                    if opt_replaces:
                        removed=0
                        new_fw=[]
                        for w in fw:
                            if isinstance(w,dict) and w.get("name") in opt_replaces and removed < cnt:
                                removed+=1
                            else:
                                new_fw.append(w)
                        fw=new_fw
                    if isinstance(nw,dict): fw.append({**nw,"_count":cnt,"_replaces":opt_replaces,"_upgraded":True})
                    elif isinstance(nw,list): fw.extend({**w2,"_count":cnt,"_replaces":opt_replaces,"_upgraded":True} for w2 in nw)
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
        ud={"name":unit["name"],"type":unit.get("type","unit"),"unit_detail":unit.get("unit_detail",unit.get("type","unit")),"cost":final_cost,"size":unit.get("size",10)*multiplier if unit.get("type")!="hero" else 1,"quality":unit.get("quality"),"defense":unit.get("defense"),"weapon":weapons,"options":selected_options,"mount":mount,"special_rules":list(set(asr)),"coriace":cor}
        if validate_army_rules(st.session_state.army_list+[ud],st.session_state.points,st.session_state.game):
            st.session_state.army_list.append(ud)
            st.session_state.army_cost += final_cost
            st.session_state.draft_counter += 1
            st.session_state.draft_unit_name = ""
            st.rerun()
