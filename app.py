# Dans la partie EXPORT HTML, remplacez la section des règles de faction par :

html_content += """
    <!-- AFFICHAGE DES RÈGLES SPÉCIALES DE LA FACTION DANS L'EXPORT HTML -->
    <div class="faction-rules">
        <h2>Règles Spéciales de la Faction</h2>
        <style>
        .faction-rules {
            background-color: #f8f9fa;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 20px;
        }
        .rule-accordion {
            border-bottom: 1px solid #eee;
            margin-bottom: 5px;
        }
        .rule-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 0;
            cursor: pointer;
            font-weight: bold;
            color: #2c3e50;
        }
        .rule-header:hover {
            color: #3498db;
        }
        .rule-content {
            padding: 0 0 10px 0;
            display: none;
            color: #555;
            font-size: 0.9em;
        }
        .expand-icon {
            transition: transform 0.2s;
        }
        .expand-icon.expanded {
            transform: rotate(180deg);
        }
        </style>
        <script>
        function toggleRule(id) {
            const content = document.getElementById('rule-content-' + id);
            const icon = document.getElementById('rule-icon-' + id);

            if (content.style.display === 'block') {
                content.style.display = 'none';
                icon.style.transform = 'rotate(0deg)';
            } else {
                content.style.display = 'block';
                icon.style.transform = 'rotate(180deg)';
            }
        }
        </script>
"""

if 'special_rules_descriptions' in faction_data:
    rule_id = 0
    for rule_name, description in faction_data['special_rules_descriptions'].items():
        rule_id += 1
        html_content += f"""
        <div class="rule-accordion">
            <div class="rule-header" onclick="toggleRule({rule_id})">
                <span>{rule_name}</span>
                <span id="rule-icon-{rule_id}" class="expand-icon" style="display: inline-block;">▼</span>
            </div>
            <div id="rule-content-{rule_id}" class="rule-content" style="display: none;">
                {description}
            </div>
        </div>
"""
else:
    html_content += "<p>Aucune règle spéciale pour cette faction.</p>"

html_content += """
    </div>
"""
