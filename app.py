def export_html(army_list, army_name, army_limit):
    # ... (les fonctions internes esc, format_weapon, get_special_rules restent inchangées)

    def get_french_type(unit):
        """Retourne le type français basé sur unit_detail"""
        if unit.get('type') == 'hero':
            return 'Héros'
        unit_detail = unit.get('unit_detail', 'unit')
        type_mapping = {
            'hero': 'Héros',
            'named_hero': 'Héros nommé',
            'unit': 'Unité de base',
            'light_vehicle': 'Véhicule léger',
            'vehicle': 'Véhicule/Monstre',
            'titan': 'Titan'
        }
        return type_mapping.get(unit_detail, 'Unité')

    # Trier la liste pour afficher les héros en premier
    sorted_army_list = sorted(army_list, key=lambda x: 0 if x.get("type") == "hero" else 1)

    html = f"""
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title>Liste d'Armée OPR - {esc(army_name)}</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
/* ... (le CSS reste inchangé) ... */
</style>
</head>
<body>
<div class="army">
  <!-- Titre de la liste -->
  <div class="army-title">
    {esc(army_name)} - {sum(unit['cost'] for unit in sorted_army_list)}/{army_limit} pts
  </div>

  <!-- Résumé de l'armée -->
  <div class="army-summary">
    <div style="font-size: 14px; color: var(--text-main);">
      <span style="color: var(--text-muted);">Nombre d'unités:</span>
      <strong style="margin-left: 8px; font-size: 18px;">{len(sorted_army_list)}</strong>
    </div>
    <div class="summary-cost">
      {sum(unit['cost'] for unit in sorted_army_list)}/{army_limit} pts
    </div>
  </div>
"""

    for unit in sorted_army_list:
