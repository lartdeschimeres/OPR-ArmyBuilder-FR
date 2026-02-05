// Export utilities for OPR Army Forge

export function generateFileName(armyName, extension) {
  const date = new Date();
  const dateStr = date.toISOString().slice(0, 10).replace(/-/g, '');
  const safeName = armyName.replace(/[^a-zA-Z0-9]/g, '_') || 'Liste';
  return `${safeName}_${dateStr}.${extension}`;
}

// Helper to extract Coriace (Tough) value from special rules
function extractToughValue(specialRules) {
  if (!specialRules || !Array.isArray(specialRules)) return 0;
  for (const rule of specialRules) {
    const match = rule.match(/[Cc]oriace\s*\((\d+)\)|[Tt]ough\s*\((\d+)\)/);
    if (match) {
      return parseInt(match[1] || match[2]);
    }
  }
  return 0;
}

export function exportToJSON(armyData) {
  const jsonString = JSON.stringify(armyData, null, 2);
  const blob = new Blob([jsonString], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  
  const link = document.createElement('a');
  link.href = url;
  link.download = generateFileName(armyData.armyName, 'json');
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export function exportToHTML(armyData, printFriendly = false) {
  const html = generateHTMLContent(armyData, printFriendly);
  const blob = new Blob([html], { type: 'text/html' });
  const url = URL.createObjectURL(blob);
  
  const link = document.createElement('a');
  link.href = url;
  const suffix = printFriendly ? '_print' : '';
  link.download = generateFileName(armyData.armyName + suffix, 'html');
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

// Calculate total Tough value (hero + mount)
function calculateTotalTough(unit) {
  const upgradeGroups = unit.unitData.upgrade_groups || [];
  const heroTough = extractToughValue(unit.unitData.special_rules);
  
  let mountTough = 0;
  let mountName = null;
  
  const mountGroups = upgradeGroups.filter(g => g.type === 'mount');
  mountGroups.forEach(group => {
    const selectedUpgrade = unit.selectedUpgrades.find(u => u.group === group.group);
    if (selectedUpgrade) {
      const option = group.options.find(o => o.name === selectedUpgrade.name);
      if (option && option.mount) {
        mountTough = extractToughValue(option.mount.special_rules);
        mountName = option.mount.name;
      }
    }
  });
  
  return {
    total: heroTough + mountTough,
    heroTough,
    mountTough,
    mountName
  };
}

// Calculate effective weapons based on selected upgrades
function calculateEffectiveWeapons(unit) {
  const upgradeGroups = unit.unitData.upgrade_groups || [];
  let weapons = [...(unit.unitData.weapons || [])];
  
  // Find weapon replacement upgrades
  const weaponGroups = upgradeGroups.filter(g => g.type === 'weapon');
  
  weaponGroups.forEach(group => {
    const selectedUpgrade = unit.selectedUpgrades.find(u => u.group === group.group);
    if (selectedUpgrade) {
      const option = group.options.find(o => o.name === selectedUpgrade.name);
      if (option && option.weapon) {
        // Check if this is a replacement or addition
        const isReplacement = group.description?.toLowerCase().includes('remplac');
        if (isReplacement) {
          weapons = [option.weapon];
        } else {
          weapons = [...weapons, option.weapon];
        }
      }
    }
  });
  
  // Find mount upgrades that add weapons
  const mountGroups = upgradeGroups.filter(g => g.type === 'mount');
  mountGroups.forEach(group => {
    const selectedUpgrade = unit.selectedUpgrades.find(u => u.group === group.group);
    if (selectedUpgrade) {
      const option = group.options.find(o => o.name === selectedUpgrade.name);
      if (option && option.mount) {
        const mountRules = option.mount.special_rules || [];
        mountRules.forEach(rule => {
          // Parse rules like "Griffes lourdes (A6, PA(1))"
          const match = rule.match(/^([^(]+)\s*\(([^)]+)\)/);
          if (match) {
            const weaponName = match[1].trim();
            const stats = match[2];
            const attackMatch = stats.match(/A(\d+)/);
            const paMatch = stats.match(/PA\((\d+)\)/);
            if (attackMatch) {
              weapons.push({
                name: `${weaponName} (${option.mount.name})`,
                range: '-',
                attacks: parseInt(attackMatch[1]),
                armor_piercing: paMatch ? parseInt(paMatch[1]) : '-',
                special_rules: []
              });
            }
          }
        });
      }
    }
  });
  
  return weapons;
}

// Calculate effective special rules based on selected upgrades
function calculateEffectiveRules(unit) {
  const upgradeGroups = unit.unitData.upgrade_groups || [];
  let rules = [...(unit.unitData.special_rules || [])];
  
  // Add rules from selected upgrades
  unit.selectedUpgrades.forEach(selectedUpgrade => {
    upgradeGroups.forEach(group => {
      const option = group.options.find(o => o.name === selectedUpgrade.name);
      if (option && option.special_rules) {
        rules = [...rules, ...option.special_rules];
      }
    });
  });
  
  // Add mount special rules (non-weapon ones)
  const mountGroups = upgradeGroups.filter(g => g.type === 'mount');
  mountGroups.forEach(group => {
    const selectedUpgrade = unit.selectedUpgrades.find(u => u.group === group.group);
    if (selectedUpgrade) {
      const option = group.options.find(o => o.name === selectedUpgrade.name);
      if (option && option.mount && option.mount.special_rules) {
        option.mount.special_rules.forEach(rule => {
          if (!rule.match(/\(A\d+/)) {
            rules.push(rule);
          }
        });
      }
    }
  });
  
  return [...new Set(rules)];
}

// Format upgrade option with details
function formatUpgradeWithDetails(upgrade, upgradeGroups) {
  for (const group of upgradeGroups) {
    const option = group.options.find(o => o.name === upgrade.name);
    if (option) {
      let details = '';
      if (group.type === 'weapon' && option.weapon) {
        const w = option.weapon;
        const parts = [];
        parts.push(w.range && w.range !== '-' ? `Portée ${w.range}` : 'Mêlée');
        parts.push(`A${w.attacks}`);
        if (w.armor_piercing && w.armor_piercing !== '-' && w.armor_piercing !== 0) {
          parts.push(`PA(${w.armor_piercing})`);
        }
        if (w.special_rules && w.special_rules.length > 0) {
          parts.push(w.special_rules.join(', '));
        }
        details = parts.join(', ');
      } else if (group.type === 'mount' && option.mount) {
        details = option.mount.special_rules?.join(', ') || '';
      } else if (option.special_rules && option.special_rules.length > 0) {
        details = option.special_rules.join(', ');
      }
      
      if (details) {
        return `${upgrade.name} (${details})`;
      }
    }
  }
  return upgrade.name;
}

function generateHTMLContent(armyData, printFriendly) {
  const bgColor = printFriendly ? '#ffffff' : '#2e2f2b';
  const cardBgColor = printFriendly ? '#f5f5f5' : '#3a3c36';
  const textColor = printFriendly ? '#1a1a1a' : '#e5e7eb';
  const borderColor = printFriendly ? '#cccccc' : '#4b4d46';
  const accentColor = printFriendly ? '#1a56db' : '#60a5fa';
  const costColor = printFriendly ? '#b45309' : '#fbbf24';
  const statsBgColor = printFriendly ? '#e5e5e5' : '#2e2f2b';
  const toughColor = printFriendly ? '#dc2626' : '#f87171';

  const unitsHTML = armyData.units.map(unit => {
    const upgradeGroups = unit.unitData.upgrade_groups || [];
    
    // Calculate effective weapons, rules, and tough value
    const effectiveWeapons = calculateEffectiveWeapons(unit);
    const effectiveRules = calculateEffectiveRules(unit);
    const toughData = calculateTotalTough(unit);
    
    // Format upgrades with details
    const upgradesHTML = unit.selectedUpgrades.length > 0
      ? `<div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid ${borderColor};">
          <div style="font-size: 12px; color: ${printFriendly ? '#666' : '#9ca3af'}; margin-bottom: 6px; font-weight: 600;">Améliorations sélectionnées:</div>
          ${unit.selectedUpgrades.map(u => `
            <div style="display: flex; justify-content: space-between; font-size: 12px; padding: 3px 0; align-items: flex-start;">
              <span style="flex: 1; color: ${textColor};">${formatUpgradeWithDetails(u, upgradeGroups)}</span>
              <span style="color: ${costColor}; font-family: 'JetBrains Mono', monospace; margin-left: 8px;">+${u.cost} pts</span>
            </div>
          `).join('')}
        </div>`
      : '';
    
    // Mount info with combined tough display
    const mountInfoHTML = toughData.mountName
      ? `<div style="margin-top: 12px; background: ${printFriendly ? '#f3e8ff' : 'rgba(168, 85, 247, 0.1)'}; border: 1px solid ${printFriendly ? '#c084fc' : 'rgba(168, 85, 247, 0.3)'}; border-radius: 4px; padding: 8px;">
          <div style="font-size: 12px; color: ${printFriendly ? '#7c3aed' : '#c084fc'}; display: flex; align-items: center; gap: 8px;">
            <span>🐴</span>
            <span style="font-weight: 600;">Monture: ${toughData.mountName}</span>
            ${toughData.total > 0 ? `<span style="color: ${printFriendly ? '#666' : '#9ca3af'};">(Coriace ${toughData.heroTough} + ${toughData.mountTough} = <span style="color: ${toughColor}; font-weight: bold;">${toughData.total}</span>)</span>` : ''}
          </div>
        </div>`
      : '';

    // All effective weapons
    const weaponsHTML = effectiveWeapons.length > 0
      ? `<div style="margin-top: 12px;">
          <div style="font-size: 12px; color: ${printFriendly ? '#666' : '#9ca3af'}; margin-bottom: 6px; font-weight: 600;">Armes:</div>
          <div style="background: ${statsBgColor}; padding: 10px; border-radius: 4px;">
            ${effectiveWeapons.map(w => `
              <div style="font-size: 12px; display: flex; justify-content: space-between; padding: 4px 0; border-bottom: 1px solid ${borderColor};">
                <span style="font-weight: 500; color: ${textColor};">${w.name}</span>
                <span style="color: ${printFriendly ? '#666' : '#9ca3af'};">
                  ${w.range && w.range !== '-' ? w.range : 'Mêlée'} | A${w.attacks} | PA(${w.armor_piercing && w.armor_piercing !== '-' ? w.armor_piercing : '0'})${w.special_rules && w.special_rules.length > 0 ? ` | ${w.special_rules.join(', ')}` : ''}
                </span>
              </div>
            `).join('')}
          </div>
        </div>`
      : '';

    // All effective rules (excluding Coriace if mount is selected - we show it separately)
    let filteredRules = effectiveRules;
    if (toughData.mountName && toughData.total > 0) {
      filteredRules = effectiveRules.filter(r => !r.match(/[Cc]oriace\s*\(\d+\)/));
    }
    
    const rulesHTML = filteredRules.length > 0
      ? `<div style="margin-top: 12px;">
          <div style="font-size: 12px; color: ${printFriendly ? '#666' : '#9ca3af'}; margin-bottom: 6px; font-weight: 600;">Règles spéciales:</div>
          <div style="color: ${accentColor}; font-size: 12px; line-height: 1.6;">${filteredRules.join(', ')}</div>
        </div>`
      : '';

    return `
      <div style="background: ${cardBgColor}; border: 1px solid ${borderColor}; border-radius: 8px; padding: 16px; margin-bottom: 16px; page-break-inside: avoid;">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
          <div>
            <div style="font-family: 'Barlow Condensed', Arial, sans-serif; font-size: 20px; font-weight: bold; text-transform: uppercase; color: ${textColor};">
              ${unit.unitName}
              ${unit.combinedUnit ? `<span style="font-size: 11px; background: ${printFriendly ? '#6b7280' : '#4b5563'}; color: white; padding: 2px 8px; border-radius: 4px; margin-left: 8px; text-transform: none;">COMBINÉE</span>` : ''}
              ${toughData.mountName ? `<span style="font-size: 11px; background: ${printFriendly ? '#7c3aed' : '#8b5cf6'}; color: white; padding: 2px 8px; border-radius: 4px; margin-left: 8px; text-transform: none;">🐴 ${toughData.mountName}</span>` : ''}
            </div>
            <div style="font-size: 12px; color: ${printFriendly ? '#666' : '#9ca3af'}; margin-top: 4px;">
              ${unit.unitType === 'hero' ? '⭐ Héros' : '🛡️ Unité'} | Taille: ${unit.unitData.size}${unit.combinedUnit ? ' ×2' : ''}
            </div>
          </div>
          <div style="font-family: 'JetBrains Mono', monospace; font-size: 22px; font-weight: bold; color: ${costColor};">
            ${unit.totalCost} pts
          </div>
        </div>
        
        <div style="display: grid; grid-template-columns: ${toughData.total > 0 ? 'repeat(5, 1fr)' : 'repeat(4, 1fr)'}; gap: 8px; background: ${statsBgColor}; padding: 12px; border-radius: 6px; text-align: center; font-size: 12px;">
          <div>
            <div style="color: ${printFriendly ? '#666' : '#9ca3af'}; font-size: 10px; text-transform: uppercase;">Qualité</div>
            <div style="font-weight: bold; font-size: 16px; color: ${textColor};">${unit.unitData.quality}+</div>
          </div>
          ${toughData.total > 0 ? `
          <div>
            <div style="color: ${printFriendly ? '#666' : '#9ca3af'}; font-size: 10px; text-transform: uppercase;">Coriace</div>
            <div style="font-weight: bold; font-size: 16px; color: ${toughColor};">${toughData.total}</div>
          </div>
          ` : ''}
          <div>
            <div style="color: ${printFriendly ? '#666' : '#9ca3af'}; font-size: 10px; text-transform: uppercase;">Défense</div>
            <div style="font-weight: bold; font-size: 16px; color: ${textColor};">${unit.unitData.defense}+</div>
          </div>
          <div>
            <div style="color: ${printFriendly ? '#666' : '#9ca3af'}; font-size: 10px; text-transform: uppercase;">Coût Base</div>
            <div style="font-weight: bold; font-size: 16px; color: ${textColor};">${unit.baseCost} pts</div>
          </div>
          <div>
            <div style="color: ${printFriendly ? '#666' : '#9ca3af'}; font-size: 10px; text-transform: uppercase;">Taille</div>
            <div style="font-weight: bold; font-size: 16px; color: ${textColor};">${unit.unitData.size}${unit.combinedUnit ? ' ×2' : ''}</div>
          </div>
        </div>
        
        ${mountInfoHTML}
        ${weaponsHTML}
        ${rulesHTML}
        ${upgradesHTML}
      </div>
    `;
  }).join('');

  return `<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${armyData.armyName || 'Liste OPR'} - OPR Army Forge</title>
  <link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@400;600;700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { 
      font-family: 'Inter', Arial, sans-serif; 
      background: ${bgColor}; 
      color: ${textColor}; 
      padding: 24px;
      line-height: 1.5;
    }
    @media print {
      body { padding: 12px; background: white; }
      @page { margin: 1cm; }
    }
  </style>
</head>
<body>
  <div style="max-width: 800px; margin: 0 auto;">
    <header style="margin-bottom: 24px; padding-bottom: 16px; border-bottom: 3px solid ${borderColor};">
      <h1 style="font-family: 'Barlow Condensed', Arial, sans-serif; font-size: 36px; font-weight: bold; text-transform: uppercase; margin-bottom: 8px; color: ${textColor};">
        ${armyData.armyName || 'Liste Sans Nom'}
      </h1>
      <div style="display: flex; gap: 24px; font-size: 14px; color: ${printFriendly ? '#666' : '#9ca3af'};">
        <span><strong style="color: ${textColor};">Jeu:</strong> ${armyData.selectedGame?.name || 'N/A'}</span>
        <span><strong style="color: ${textColor};">Faction:</strong> ${armyData.selectedFaction?.faction || 'N/A'}</span>
        <span><strong style="color: ${textColor};">Limite:</strong> ${armyData.pointsLimit} pts</span>
      </div>
    </header>
    
    <div style="display: flex; justify-content: space-between; align-items: center; background: ${cardBgColor}; padding: 16px; border-radius: 8px; margin-bottom: 24px; border: 1px solid ${borderColor};">
      <div style="font-size: 14px; color: ${textColor};">
        <span style="color: ${printFriendly ? '#666' : '#9ca3af'};">Nombre d'unités:</span>
        <strong style="margin-left: 8px; font-size: 18px;">${armyData.units.length}</strong>
      </div>
      <div style="font-family: 'JetBrains Mono', monospace; font-size: 28px; font-weight: bold; color: ${costColor};">
        ${armyData.totalPoints} / ${armyData.pointsLimit} pts
      </div>
    </div>
    
    <div>
      ${unitsHTML}
    </div>
    
    <footer style="margin-top: 32px; padding-top: 16px; border-top: 1px solid ${borderColor}; font-size: 12px; color: ${printFriendly ? '#999' : '#6b7280'}; text-align: center;">
      Généré par OPR Army Forge - ${new Date().toLocaleDateString('fr-FR')}
    </footer>
  </div>
</body>
</html>`;
}

export function importFromJSON(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const data = JSON.parse(e.target.result);
        resolve(data);
      } catch (error) {
        reject(new Error('Invalid JSON file'));
      }
    };
    reader.onerror = () => reject(new Error('Failed to read file'));
    reader.readAsText(file);
  });
}
