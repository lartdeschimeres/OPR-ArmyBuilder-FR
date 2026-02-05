// Export utilities for OPR Army Forge

export function generateFileName(armyName, extension) {
  const date = new Date();
  const dateStr = date.toISOString().slice(0, 10).replace(/-/g, '');
  const safeName = armyName.replace(/[^a-zA-Z0-9]/g, '_') || 'Liste';
  return `${safeName}_${dateStr}.${extension}`;
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

function generateHTMLContent(armyData, printFriendly) {
  const bgColor = printFriendly ? '#ffffff' : '#2e2f2b';
  const cardBgColor = printFriendly ? '#f5f5f5' : '#3a3c36';
  const textColor = printFriendly ? '#1a1a1a' : '#e5e7eb';
  const borderColor = printFriendly ? '#cccccc' : '#4b4d46';
  const accentColor = printFriendly ? '#1a56db' : '#60a5fa';
  const costColor = printFriendly ? '#b45309' : '#fbbf24';

  const unitsHTML = armyData.units.map(unit => {
    const upgradesHTML = unit.selectedUpgrades.length > 0
      ? `<div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid ${borderColor};">
          <div style="font-size: 12px; color: ${printFriendly ? '#666' : '#9ca3af'}; margin-bottom: 4px;">Améliorations:</div>
          ${unit.selectedUpgrades.map(u => `
            <div style="display: flex; justify-content: space-between; font-size: 13px; padding: 2px 0;">
              <span>${u.name}</span>
              <span style="color: ${costColor};">+${u.cost} pts</span>
            </div>
          `).join('')}
        </div>`
      : '';

    const weaponsHTML = unit.unitData.weapons && unit.unitData.weapons.length > 0
      ? `<div style="margin-top: 8px; background: ${printFriendly ? '#e5e5e5' : '#2e2f2b'}; padding: 8px; border-radius: 4px;">
          <div style="font-size: 11px; color: ${printFriendly ? '#666' : '#9ca3af'}; margin-bottom: 4px;">Armes:</div>
          ${unit.unitData.weapons.map(w => `
            <div style="font-size: 12px; display: flex; gap: 8px;">
              <span style="font-weight: 500;">${w.name}</span>
              <span style="color: ${printFriendly ? '#666' : '#9ca3af'};">
                ${w.range !== '-' ? `Portée: ${w.range}` : 'Mêlée'} | 
                A${w.attacks} | 
                PA${w.armor_piercing !== '-' ? w.armor_piercing : '0'}
              </span>
            </div>
          `).join('')}
        </div>`
      : '';

    const rulesHTML = unit.unitData.special_rules && unit.unitData.special_rules.length > 0
      ? `<div style="margin-top: 8px; font-size: 12px;">
          <span style="color: ${printFriendly ? '#666' : '#9ca3af'};">Règles: </span>
          <span style="color: ${accentColor};">${unit.unitData.special_rules.join(', ')}</span>
        </div>`
      : '';

    return `
      <div style="background: ${cardBgColor}; border: 1px solid ${borderColor}; border-radius: 6px; padding: 16px; margin-bottom: 12px;">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
          <div>
            <div style="font-family: 'Barlow Condensed', Arial, sans-serif; font-size: 18px; font-weight: bold; text-transform: uppercase;">
              ${unit.unitName}
              ${unit.combinedUnit ? '<span style="font-size: 12px; background: #4b5563; padding: 2px 6px; border-radius: 4px; margin-left: 8px;">COMBINÉE</span>' : ''}
            </div>
            <div style="font-size: 12px; color: ${printFriendly ? '#666' : '#9ca3af'};">
              ${unit.unitType === 'hero' ? 'Héros' : 'Unité'} | Taille: ${unit.unitData.size}${unit.combinedUnit ? ' x2' : ''}
            </div>
          </div>
          <div style="font-family: 'JetBrains Mono', monospace; font-size: 18px; font-weight: bold; color: ${costColor};">
            ${unit.totalCost} pts
          </div>
        </div>
        
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; background: ${printFriendly ? '#e5e5e5' : '#2e2f2b'}; padding: 8px; border-radius: 4px; text-align: center; font-size: 12px;">
          <div>
            <div style="color: ${printFriendly ? '#666' : '#9ca3af'};">Qualité</div>
            <div style="font-weight: bold;">${unit.unitData.quality}+</div>
          </div>
          <div>
            <div style="color: ${printFriendly ? '#666' : '#9ca3af'};">Défense</div>
            <div style="font-weight: bold;">${unit.unitData.defense}+</div>
          </div>
          <div>
            <div style="color: ${printFriendly ? '#666' : '#9ca3af'};">Coût Base</div>
            <div style="font-weight: bold;">${unit.baseCost} pts</div>
          </div>
          <div>
            <div style="color: ${printFriendly ? '#666' : '#9ca3af'};">Taille</div>
            <div style="font-weight: bold;">${unit.unitData.size}${unit.combinedUnit ? ' x2' : ''}</div>
          </div>
        </div>
        
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
      body { padding: 12px; }
    }
  </style>
</head>
<body>
  <div style="max-width: 800px; margin: 0 auto;">
    <header style="margin-bottom: 24px; padding-bottom: 16px; border-bottom: 2px solid ${borderColor};">
      <h1 style="font-family: 'Barlow Condensed', Arial, sans-serif; font-size: 32px; font-weight: bold; text-transform: uppercase; margin-bottom: 8px;">
        ${armyData.armyName || 'Liste Sans Nom'}
      </h1>
      <div style="display: flex; gap: 24px; font-size: 14px; color: ${printFriendly ? '#666' : '#9ca3af'};">
        <span><strong>Jeu:</strong> ${armyData.selectedGame?.name || 'N/A'}</span>
        <span><strong>Faction:</strong> ${armyData.selectedFaction?.faction || 'N/A'}</span>
        <span><strong>Limite:</strong> ${armyData.pointsLimit} pts</span>
      </div>
    </header>
    
    <div style="display: flex; justify-content: space-between; align-items: center; background: ${cardBgColor}; padding: 16px; border-radius: 8px; margin-bottom: 24px;">
      <div style="font-size: 14px;">
        <span style="color: ${printFriendly ? '#666' : '#9ca3af'};">Nombre d'unités:</span>
        <strong style="margin-left: 8px;">${armyData.units.length}</strong>
      </div>
      <div style="font-family: 'JetBrains Mono', monospace; font-size: 24px; font-weight: bold; color: ${costColor};">
        ${armyData.totalPoints} / ${armyData.pointsLimit} pts
      </div>
    </div>
    
    <div>
      ${unitsHTML}
    </div>
    
    <footer style="margin-top: 24px; padding-top: 16px; border-top: 1px solid ${borderColor}; font-size: 12px; color: ${printFriendly ? '#999' : '#6b7280'}; text-align: center;">
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
