# --- CODE IDENTIQUE AU TIEN ---
# (tout est inchangé sauf calculate_total_coriace)

def calculate_total_coriace(unit_data, combined=False):
    """
    Calcule la Coriace TOTALE d'une unité :
    - règles de base
    - monture (héros)
    - options
    - armes
    """
    total = 0

    # 1. règles de base
    if 'special_rules' in unit_data:
        total += calculate_coriace_from_rules(unit_data['special_rules'])

    # 2. monture (FIX ICI)
    if 'mount' in unit_data and unit_data['mount']:
        mount_data = unit_data['mount'].get('mount')
        if mount_data and 'special_rules' in mount_data:
            total += calculate_coriace_from_rules(mount_data['special_rules'])

    # 3. options
    if 'options' in unit_data:
        for opts in unit_data['options'].values():
            if isinstance(opts, list):
                for opt in opts:
                    if 'special_rules' in opt:
                        total += calculate_coriace_from_rules(opt['special_rules'])

    # 4. armes
    if 'weapon' in unit_data and 'special_rules' in unit_data['weapon']:
        total += calculate_coriace_from_rules(unit_data['weapon']['special_rules'])

    # 5. unité combinée (hors héros)
    if combined and unit_data.get('type', '').lower() != 'hero':
        total += calculate_coriace_from_rules(unit_data.get('special_rules', []))

    return total if total > 0 else None
