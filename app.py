import json
import copy
import streamlit as st
from pathlib import Path
from datetime import datetime
import re
import math
import base64

st.set_page_config(page_title="OPR ArmyBuilder FR", layout="wide", initial_sidebar_state="auto")

# URL de l'app (pour le QR code de partage)
APP_URL = "https://armybuilder-fra.streamlit.app/"

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
  /* Colonnes Streamlit empilées sur mobile */
  [data-testid="column"] {{width: 100% !important; flex: 1 1 100% !important; min-width: 100% !important;}}
  /* Boutons pleine largeur sur mobile */
  .stButton>button {{width: 100%; min-height: 48px; font-size: 15px;}}
  /* Agrandir les labels de formulaire */
  .stSelectbox label, .stNumberInput label, .stTextInput label {{font-size: 14px !important;}}
  /* Supprimer les shadows lourdes sur mobile */
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

# ── Lecture du paramètre ?list= (QR code de partage) ────────────────────────
if not st.session_state.get("_qr_loaded"):
    st.session_state["_qr_loaded"] = True
    try:
        _qp = st.query_params.get("list", "")
        if _qp:
            import zlib as _z, base64 as _b64q, urllib.parse as _uq
            _raw  = _b64q.urlsafe_b64decode(_uq.unquote(_qp).encode() + b"==")
            _data = json.loads(_z.decompress(_raw).decode())
            # Pré-remplir jeu, faction et points directement dans session_state
            if _data.get("game"):    st.session_state["game"]    = _data["game"]
            if _data.get("faction"): st.session_state["faction"] = _data["faction"]
            if _data.get("pts"):     st.session_state["points"]  = _data["pts"]
            # Stocker army_list complète si présente
            if _data.get("army_list"):
                st.session_state["_qr_army_list"] = _data["army_list"]
                st.session_state["_qr_army_cost"] = _data.get("army_cost", 0)
            # Stocker pour le bandeau info
            st.session_state["_qr_game"]    = _data.get("game", "")
            st.session_state["_qr_faction"] = _data.get("faction", "")
            st.session_state["_qr_pts"]     = _data.get("pts", 1000)
            st.session_state["_qr_units"]   = _data.get("units", [])
            st.session_state["_qr_pending"] = True
            st.query_params.clear()
            st.rerun()
    except Exception:
        pass  # paramètre invalide → ignorer silencieusement
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

def weapon_profile_md(weapon):
    """Retourne une ligne de profil lisible pour l'UI : Mêlée | A2 | PA1 | Règles"""
    if not weapon or not isinstance(weapon, dict): return ""
    rng = weapon.get("range", "Mêlée")
    if rng in (None, "-", "mêlée", "Mêlée") or str(rng).lower() == "mêlée":
        rng_str = "Mêlée"
    elif isinstance(rng, (int, float)):
        rng_str = f'{int(rng)}"'
    else:
        s = str(rng).strip(); rng_str = s if s.endswith('"') else f'{s}"'
    att = weapon.get("attacks", "?")
    ap  = weapon.get("armor_piercing", "?")
    sr  = weapon.get("special_rules", [])
    parts = [f"{rng_str} | A{att} | PA{ap}"]
    if sr: parts.append(", ".join(sr))
    return " | ".join(parts)

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
        return ""   # remplacé par render_upgrades_section

    def render_upgrades_section(unit):
        """Bloc Améliorations sous les règles spéciales."""
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

/* ── Titre & résumé ── */
.army-title{{text-align:center;font-size:18px;font-weight:700;margin-bottom:8px;border-bottom:2px solid var(--accent);padding-bottom:6px;}}
.army-summary{{display:flex;justify-content:space-between;align-items:center;background:var(--hdr);padding:8px 12px;border-radius:6px;margin:8px 0 12px;border:1px solid var(--brd);font-size:12px;}}
.summary-cost{{font-family:monospace;font-size:16px;font-weight:bold;color:var(--red);}}

/* ── Grille 2 colonnes ── */
.units-grid{{display:grid;grid-template-columns:1fr 1fr;gap:8px;}}

/* ── Carte unité ── */
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

/* ── Page de légende (règles + sorts) ── */
.legend-page{{page-break-before:always;break-before:page;padding:12px 0;}}
.faction-rules{{padding:8px;border-radius:6px;border:1px solid var(--brd);}}
.legend-title{{text-align:center;color:var(--accent);border-bottom:2px solid var(--accent);padding-bottom:6px;margin-bottom:12px;font-size:14px;font-weight:700;}}
.rule-item{{margin-bottom:4px;padding-bottom:4px;border-bottom:1px solid var(--brd);}}
.rule-item:last-child{{border-bottom:none;margin-bottom:0;padding-bottom:0;}}
.rule-name{{color:var(--accent);font-weight:600;font-size:8px;margin-bottom:1px;}}
.rule-desc{{font-size:7.5px;line-height:1.28;color:#555;}}

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

    html += "</div>\n"  # ferme .units-grid

    try:
        faction_rules = st.session_state.get("faction_special_rules", [])
        faction_spells = st.session_state.get("faction_spells", {})
        all_rules = [r for r in faction_rules if isinstance(r, dict)]
        if all_rules or faction_spells:
            # ── Page légende : règles + sorts en colonnes CSS auto-ajustées ──
            # columns: auto répartit le contenu sur plusieurs colonnes en remplissant
            # chaque colonne avant d'en créer une nouvelle → s'adapte à n'importe quel volume.
            html += """<div class="legend-page"><div class="faction-rules">"""
            html += """<div class="legend-title">📜 Règles spéciales &amp; Sorts</div>"""
            html += """<div style="columns:3;column-gap:12px;column-rule:1px solid #dee2e6;font-size:9px;">"""

            if all_rules:
                if faction_spells:
                    html += """<div style="break-after:column;"></div>""" if False else ""
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

            html += "</div></div></div>"  # ferme columns + faction-rules + legend-page
    except Exception as e:
        html += f'<div style="color:red;padding:10px;">Erreur règles faction : {esc(str(e))}</div>'

    # QR code : stratégie double
    # 1. qrcode[pil] installé → PNG base64 inline (offline)
    # 2. fallback → URL api.qrserver.com (requiert internet à l'ouverture)
    import urllib.parse as _urlp
    # QR code : URL vers l'app avec la liste encodée (compressée + base64)
    # Le téléphone ouvre directement l'app au scan
    import zlib as _zlib
    _list_data = json.dumps({
        "game": st.session_state.get("game",""),
        "faction": army_name, "pts": army_limit,
        "list_name": army_name,
        "army_list": army_list,
        "army_cost": sum(u.get("cost",0) for u in army_list),
        "units": [{"n": u.get("name",""), "c": u.get("cost",0)} for u in army_list]
    }, ensure_ascii=False, separators=(',',':'))
    _compressed = _zlib.compress(_list_data.encode(), level=9)
    import base64 as _b64u, urllib.parse as _urlp
    _b64_data = _b64u.urlsafe_b64encode(_compressed).decode()
    _payload = APP_URL + "?list=" + _urlp.quote(_b64_data)

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
        # Fallback URL externe (fonctionne si internet disponible à l'ouverture du HTML)
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
        FACTIONS_DIR = Path(__file__).resolve().parent / "repositories" / "data" / "factions"
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

    # ── Bandeau liste partagée reçue via QR ──────────────────────────────────
    if st.session_state.get("_qr_pending"):
        _qf = st.session_state.get("_qr_faction", "")
        _qg = st.session_state.get("_qr_game", "")
        _qu = st.session_state.get("_qr_units", [])
        _qp = st.session_state.get("_qr_pts", 0)
        _unit_lines = " · ".join(f"{u['n']} ({u['c']} pts)" for u in _qu)
        st.info(
            f"📲 **Liste reçue via QR code** — {_qg} / {_qf} / {_qp} pts\n\n"
            f"{_unit_lines}\n\n"
            f"Vérifiez le jeu et la faction puis cliquez **Construire l'armée**."
        )
        del st.session_state["_qr_pending"]

    # Jeu courant
    current_game = st.session_state.get("game", games[0] if games else "")

    # ── Couleurs et image par jeu ─────────────────────────────────────────────
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

    # Image vignette en base64 si disponible
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
        # Fallback : icône triangles SVG colorée par jeu
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
    # ── Hero banner ───────────────────────────────────────────────────────────
    # SVG triangles inline (motif géométrique, pas de fichier externe)
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
    <!-- Logo OPR SVG maison -->
    <div style="display:flex;align-items:center;justify-content:center;gap:10px;margin-bottom:8px;">
      <img src="data:image/png;base64,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"
           style="width:52px;height:52px;border-radius:50%;mix-blend-mode:screen;opacity:.92;"
           alt="OPR logo">
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

    # ── Formulaire ────────────────────────────────────────────────────────────
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
            # Réinitialiser l'armée seulement si jeu ou faction a changé
            if _game_changed or _faction_changed:
                st.session_state.army_list = []; st.session_state.army_cost = 0; st.session_state.unit_selections = {}
            # Si une liste QR est en attente, l'injecter
            if st.session_state.get("_qr_army_list"):
                st.session_state.army_list = st.session_state.pop("_qr_army_list")
                st.session_state.army_cost = st.session_state.pop("_qr_army_cost", 0)
                st.session_state.unit_selections = {}
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
    if st.button("⬅️ Retour à la configuration", key="back3"): st.session_state.page = "setup"; st.rerun()  # army_list conservée

    st.divider(); st.subheader("📤 Export/Import de la liste")
    # Nom de fichier intelligent : si nom auto (Liste_YYYYMMDD) → faction_Xpts_date
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

    # Couleurs selon état
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

        # Séparateurs de section par type
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
                # ── Ligne de stats ──────────────────────────────────────────
                cor=ud.get("coriace",0)
                stats_html = (
                    f"<span style='margin-right:12px;'>Qual <b>{ud.get('quality','?')}+</b></span>"
                    f"<span style='margin-right:12px;'>Déf <b>{ud.get('defense','?')}+</b></span>"
                    f"<span style='margin-right:12px;'>Taille <b>{ud.get('size','?')}</b></span>"
                    + (f"<span>Coriace <b>{cor}</b></span>" if cor else "")
                )
                st.markdown(f"<div style='font-size:clamp(12px,2vw,0.85em);color:#555;margin-bottom:6px;'>{stats_html}</div>", unsafe_allow_html=True)

                # ── Armes ───────────────────────────────────────────────────
                weapons=ud.get("weapon",[])
                ws=weapons if isinstance(weapons,list) else [weapons]
                armes=[fmt_weapon_line(w) for w in ws if isinstance(w,dict)]
                if armes:
                    st.markdown(
                        "<div style='font-size:clamp(12px,2vw,0.8em);color:#333;margin-bottom:4px;'>"
                        "<b>Armes :</b> " + " · ".join(armes) + "</div>",
                        unsafe_allow_html=True)

                # ── Améliorations (rôles, upgrades) ─────────────────────────
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

                # ── Monture ─────────────────────────────────────────────────
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

                # ── Règles spéciales ────────────────────────────────────────
                sr_unit=ud.get("special_rules",[])
                if sr_unit:
                    st.markdown(
                        "<div style='font-size:clamp(12px,2vw,0.78em);color:#666;margin-bottom:6px;'>"
                        + ", ".join(sr_unit) + "</div>",
                        unsafe_allow_html=True)

                # ── Boutons supprimer / dupliquer ───────────────────────────
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

    # Recherche par nom
    _search = st.text_input("🔍 Rechercher une unité", value="", placeholder="Nom de l'unité…", label_visibility="collapsed", key="unit_search")
    if _search.strip():
        fu = [u for u in fu if _search.strip().lower() in u.get("name","").lower()]

    st.markdown(f"<div style='text-align:right;margin:4px 0 8px;color:#6c757d;font-size:.85em;'>{len(fu)} unité(s) — filtre : {st.session_state.unit_filter}</div>", unsafe_allow_html=True)
    if not fu: st.warning(f"Aucune unité trouvée."); st.stop()

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
                if ch != choices[0] and ch in opt_map:
                    _ow = opt_map[ch].get("weapon", {})
                    if isinstance(_ow, list):
                        for _w in _ow:
                            if isinstance(_w, dict): st.caption(f"⚔️ {_w.get('name','')} — {weapon_profile_md(_w)}")
                    elif isinstance(_ow, dict) and _ow:
                        st.caption(f"⚔️ {_ow.get('name','')} — {weapon_profile_md(_ow)}")
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
                if ch != choices[0] and ch in opt_map:
                    _ow = opt_map[ch].get("weapon", {})
                    if isinstance(_ow, list):
                        for _w in _ow:
                            if isinstance(_w, dict): st.caption(f"⚔️ {_w.get('name','')} — {weapon_profile_md(_w)}")
                    elif isinstance(_ow, dict) and _ow:
                        st.caption(f"⚔️ {_ow.get('name','')} — {weapon_profile_md(_ow)}")
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
            for oi,option in enumerate(group.get("options",[])):
                req=option.get("requires",[])
                if req and not check_weapon_conditions(unit_key,req,unit):
                    st.markdown(f"<div style='color:#999;font-size:.9em;'>{option['name']} <em>(Non disponible)</em></div>",unsafe_allow_html=True); continue
                # Profil(s) de l'arme sous le titre
                _opt_nw = option.get("weapon", {})
                _profiles = []
                if isinstance(_opt_nw, list):
                    _profiles = [f"⚔️ **{_w.get('name','')}** — {weapon_profile_md(_w)}" for _w in _opt_nw if isinstance(_w, dict)]
                elif isinstance(_opt_nw, dict) and _opt_nw:
                    _profiles = [f"⚔️ **{_opt_nw.get('name','')}** — {weapon_profile_md(_opt_nw)}"]
                _profile_label = "  \n".join(_profiles)
                st.markdown(f"**{option['name']}**" + (f"  \n{_profile_label}" if _profile_label else ""))
                # ── BUG 1 FIX : max_count selon le type ──────────────────────
                mc_cfg  = option.get("max_count", {})
                mc_type = mc_cfg.get("type","size_based") if isinstance(mc_cfg,dict) else "size_based"
                if mc_type == "fixed":
                    mc = mc_cfg.get("value",1)
                elif mc_type == "size_based":
                    mc = min(mc_cfg.get("value", unit.get("size",1)), unit.get("size",1))
                elif mc_type == "count_in_weapons":
                    # Compter les exemplaires encore présents dans weapons (courant)
                    # _count pour les armes ajoutées par variable_weapon_count, count pour les armes de base
                    wn = mc_cfg.get("weapon_name","")
                    mc = sum(w.get("_count", w.get("count", 1)) for w in weapons if isinstance(w,dict) and w.get("name")==wn)
                else:
                    mc = unit.get("size",1)
                mc = max(mc, 0)
                cnt_key = f"{unit_key}_{g_key}_cnt_{oi}"
                prev = min(st.session_state.unit_selections[unit_key].get(cnt_key, option.get("min_count",0)), mc)
                cnt = st.number_input(f"Nombre de {option['name']} (0 – {mc})", min_value=option.get("min_count",0), max_value=max(mc, option.get("min_count",0)), value=prev, step=1, key=cnt_key)
                st.session_state.unit_selections[unit_key][cnt_key] = cnt
                tc=cnt*option["cost"]; upgrades_cost+=tc
                if cnt > 0 or tc > 0:
                    st.markdown(f"<div style='margin:10px 0;padding:8px;background:#f8f9fa;border-radius:4px;'><strong>{option['name']}</strong> × {cnt} = <strong style='color:#e74c3c;'>{tc} pts</strong></div>",unsafe_allow_html=True)
                if cnt > 0:
                    # BUG 2 FIX : fw repart de weapons COURANT (pas des armes de base)
                    fw = copy.deepcopy(weapons)
                    nw = option["weapon"]
                    opt_replaces = option.get("replaces",[])
                    # BUG 3 FIX : pour les armes avec count > 1, décrémenter count
                    if opt_replaces:
                        remaining = cnt
                        new_fw = []
                        for w in fw:
                            if not isinstance(w,dict): new_fw.append(w); continue
                            if w.get("name") in opt_replaces and remaining > 0:
                                # Lire _count OU count (armes ajoutées vs armes de base)
                                w_count = w.get("_count", w.get("count", 1))
                                if w_count > remaining:
                                    wc = w.copy()
                                    # Décrémenter le bon champ
                                    if "_count" in w: wc["_count"] = w_count - remaining
                                    else: wc["count"] = w_count - remaining
                                    new_fw.append(wc)
                                    remaining = 0
                                else:
                                    remaining -= w_count
                            else:
                                new_fw.append(w)
                        fw = new_fw
                    if isinstance(nw,dict): fw.append({**nw,"_count":cnt,"_replaces":opt_replaces,"_upgraded":True})
                    elif isinstance(nw,list): fw.extend({**w2,"_count":cnt,"_replaces":opt_replaces,"_upgraded":True} for w2 in nw)
                    weapons = fw
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
            # Incrémenter le draft_counter → la prochaine unité (même nom) repart vierge
            st.session_state.draft_counter += 1
            st.session_state.draft_unit_name = ""
            st.rerun()
