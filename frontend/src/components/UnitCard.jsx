import React, { useState, useCallback } from 'react';
import { Trash2, ChevronDown, ChevronUp, Shield, Sword } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Checkbox } from '../components/ui/checkbox';
import { RadioGroup, RadioGroupItem } from '../components/ui/radio-group';
import { Label } from '../components/ui/label';
import { Switch } from '../components/ui/switch';
import { useArmy } from '../context/ArmyContext';

export const UnitCard = ({ rosterUnit }) => {
  const { removeUnit, updateUnitUpgrades, state } = useArmy();
  const [isExpanded, setIsExpanded] = useState(true);
  
  const unit = rosterUnit.unitData;
  const isHero = rosterUnit.unitType === 'hero';
  
  // Group upgrades by type
  const upgradeGroups = unit.upgrade_groups || [];
  
  // Find selected upgrade for a radio group
  const getSelectedRadio = (groupName) => {
    const found = rosterUnit.selectedUpgrades.find(u => u.group === groupName);
    return found ? found.name : '';
  };
  
  // Check if a checkbox upgrade is selected
  const isCheckboxSelected = (groupName, optionName) => {
    return rosterUnit.selectedUpgrades.some(
      u => u.group === groupName && u.name === optionName
    );
  };
  
  // Handle radio selection (single choice)
  const handleRadioChange = useCallback((groupName, option) => {
    const otherUpgrades = rosterUnit.selectedUpgrades.filter(u => u.group !== groupName);
    
    if (option) {
      const newUpgrades = [
        ...otherUpgrades,
        { group: groupName, name: option.name, cost: option.cost }
      ];
      updateUnitUpgrades(rosterUnit.id, newUpgrades, rosterUnit.combinedUnit);
    } else {
      updateUnitUpgrades(rosterUnit.id, otherUpgrades, rosterUnit.combinedUnit);
    }
  }, [rosterUnit, updateUnitUpgrades]);
  
  // Handle checkbox toggle (multi choice)
  const handleCheckboxChange = useCallback((groupName, option, checked) => {
    let newUpgrades;
    if (checked) {
      newUpgrades = [
        ...rosterUnit.selectedUpgrades,
        { group: groupName, name: option.name, cost: option.cost }
      ];
    } else {
      newUpgrades = rosterUnit.selectedUpgrades.filter(
        u => !(u.group === groupName && u.name === option.name)
      );
    }
    updateUnitUpgrades(rosterUnit.id, newUpgrades, rosterUnit.combinedUnit);
  }, [rosterUnit, updateUnitUpgrades]);
  
  // Handle combined unit toggle
  const handleCombinedToggle = useCallback((checked) => {
    updateUnitUpgrades(rosterUnit.id, rosterUnit.selectedUpgrades, checked);
  }, [rosterUnit, updateUnitUpgrades]);
  
  // Check if unit exceeds 35% limit
  const maxCost = Math.floor(state.pointsLimit * 0.35);
  const exceedsLimit = rosterUnit.totalCost > maxCost;
  
  return (
    <div
      data-testid={`roster-unit-${rosterUnit.id}`}
      className={`
        bg-[#3a3c36] border rounded-md overflow-hidden mb-3
        transition-colors animate-scaleIn
        ${exceedsLimit ? 'border-red-500/50' : 'border-[#4b4d46] hover:border-gray-500'}
      `}
    >
      {/* Header */}
      <div 
        className="p-4 cursor-pointer"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex justify-between items-start">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <h4 className="font-headings font-bold text-lg text-white">
                {rosterUnit.unitName}
              </h4>
              {isHero && (
                <span className="text-xs bg-yellow-500/20 text-yellow-400 px-2 py-0.5 rounded">
                  Héros
                </span>
              )}
              {rosterUnit.combinedUnit && (
                <span className="text-xs bg-purple-500/20 text-purple-400 px-2 py-0.5 rounded">
                  Combinée
                </span>
              )}
            </div>
            
            <div className="flex items-center gap-4 text-xs text-gray-400">
              <span className="flex items-center gap-1">
                <Sword className="w-3 h-3" />
                Qualité {unit.quality}+
              </span>
              <span className="flex items-center gap-1">
                <Shield className="w-3 h-3" />
                Défense {unit.defense}+
              </span>
              <span>
                Taille: {unit.size}{rosterUnit.combinedUnit ? ' x2' : ''}
              </span>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            <span className={`font-mono text-lg font-bold ${exceedsLimit ? 'text-red-400' : 'text-yellow-400'}`}>
              {rosterUnit.totalCost} pts
            </span>
            <Button
              data-testid={`remove-unit-btn-${rosterUnit.id}`}
              variant="ghost"
              size="sm"
              onClick={(e) => {
                e.stopPropagation();
                removeUnit(rosterUnit.id);
              }}
              className="text-red-400 hover:text-red-300 hover:bg-red-500/10 h-8 w-8 p-0"
            >
              <Trash2 className="w-4 h-4" />
            </Button>
            {isExpanded ? (
              <ChevronUp className="w-5 h-5 text-gray-400" />
            ) : (
              <ChevronDown className="w-5 h-5 text-gray-400" />
            )}
          </div>
        </div>
      </div>
      
      {/* Expanded Content */}
      {isExpanded && (
        <div className="px-4 pb-4 border-t border-[#4b4d46]">
          {/* Stats Grid */}
          <div className="grid grid-cols-4 gap-2 text-xs text-gray-300 bg-[#2e2f2b] p-2 rounded mt-3 mb-3">
            <div className="text-center">
              <div className="text-gray-500">Qualité</div>
              <div className="font-bold">{unit.quality}+</div>
            </div>
            <div className="text-center">
              <div className="text-gray-500">Défense</div>
              <div className="font-bold">{unit.defense}+</div>
            </div>
            <div className="text-center">
              <div className="text-gray-500">Coût Base</div>
              <div className="font-bold">{unit.base_cost} pts</div>
            </div>
            <div className="text-center">
              <div className="text-gray-500">Taille</div>
              <div className="font-bold">{unit.size}</div>
            </div>
          </div>
          
          {/* Weapons */}
          {unit.weapons && unit.weapons.length > 0 && (
            <div className="mb-3">
              <div className="text-xs text-gray-500 mb-1">Armes:</div>
              <div className="space-y-1">
                {unit.weapons.map((weapon, idx) => (
                  <div key={idx} className="text-xs bg-[#2e2f2b] p-2 rounded flex justify-between">
                    <span className="font-medium text-white">{weapon.name}</span>
                    <span className="text-gray-400">
                      {weapon.range !== '-' ? `${weapon.range}"` : 'Mêlée'} | 
                      A{weapon.attacks} | 
                      PA{weapon.armor_piercing !== '-' ? weapon.armor_piercing : '0'}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
          
          {/* Special Rules */}
          {unit.special_rules && unit.special_rules.length > 0 && (
            <div className="mb-3">
              <div className="text-xs text-gray-500 mb-1">Règles spéciales:</div>
              <div className="flex flex-wrap gap-1">
                {unit.special_rules.map((rule, idx) => (
                  <span key={idx} className="text-xs bg-blue-500/20 text-blue-400 px-2 py-0.5 rounded">
                    {rule}
                  </span>
                ))}
              </div>
            </div>
          )}
          
          {/* Combined Unit Toggle (only for non-heroes) */}
          {!isHero && (
            <div className="flex items-center justify-between py-3 border-t border-[#4b4d46]">
              <div>
                <Label htmlFor={`combined-${rosterUnit.id}`} className="text-sm text-white">
                  Unité Combinée
                </Label>
                <p className="text-xs text-gray-500">Double la taille et le coût</p>
              </div>
              <Switch
                id={`combined-${rosterUnit.id}`}
                data-testid={`combined-switch-${rosterUnit.id}`}
                checked={rosterUnit.combinedUnit}
                onCheckedChange={handleCombinedToggle}
              />
            </div>
          )}
          
          {/* Upgrade Groups */}
          {upgradeGroups.map((group, groupIdx) => (
            <div key={groupIdx} className="pt-3 border-t border-[#4b4d46]">
              <div className="text-sm font-semibold text-white mb-1">{group.group}</div>
              {group.description && (
                <div className="text-xs text-gray-500 mb-2">{group.description}</div>
              )}
              
              {/* Single choice (weapon, mount) - Radio buttons for heroes */}
              {(group.type === 'weapon' || group.type === 'mount' || (isHero && group.type === 'upgrades')) ? (
                <RadioGroup
                  value={getSelectedRadio(group.group)}
                  onValueChange={(value) => {
                    const option = group.options.find(o => o.name === value);
                    handleRadioChange(group.group, option);
                  }}
                  className="space-y-2"
                >
                  <div className="flex items-center space-x-2">
                    <RadioGroupItem 
                      value="" 
                      id={`${rosterUnit.id}-${groupIdx}-none`}
                      className="border-gray-500"
                    />
                    <Label 
                      htmlFor={`${rosterUnit.id}-${groupIdx}-none`}
                      className="text-sm text-gray-400 cursor-pointer"
                    >
                      Aucun
                    </Label>
                  </div>
                  {group.options.map((option, optIdx) => (
                    <div key={optIdx} className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <RadioGroupItem 
                          value={option.name} 
                          id={`${rosterUnit.id}-${groupIdx}-${optIdx}`}
                          data-testid={`radio-${rosterUnit.id}-${option.name.replace(/\s+/g, '-').toLowerCase()}`}
                          className="border-gray-500 data-[state=checked]:border-blue-500"
                        />
                        <Label 
                          htmlFor={`${rosterUnit.id}-${groupIdx}-${optIdx}`}
                          className="text-sm text-gray-300 cursor-pointer"
                        >
                          {option.name}
                        </Label>
                      </div>
                      <span className="text-xs font-mono text-yellow-400">
                        +{option.cost} pts
                      </span>
                    </div>
                  ))}
                </RadioGroup>
              ) : (
                /* Multi choice (upgrades for units) - Checkboxes */
                <div className="space-y-2">
                  {group.options.map((option, optIdx) => (
                    <div key={optIdx} className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <Checkbox 
                          id={`${rosterUnit.id}-${groupIdx}-${optIdx}`}
                          data-testid={`checkbox-${rosterUnit.id}-${option.name.replace(/\s+/g, '-').toLowerCase()}`}
                          checked={isCheckboxSelected(group.group, option.name)}
                          onCheckedChange={(checked) => 
                            handleCheckboxChange(group.group, option, checked)
                          }
                          className="border-gray-500 data-[state=checked]:bg-blue-500"
                        />
                        <Label 
                          htmlFor={`${rosterUnit.id}-${groupIdx}-${optIdx}`}
                          className="text-sm text-gray-300 cursor-pointer"
                        >
                          {option.name}
                        </Label>
                      </div>
                      <span className="text-xs font-mono text-yellow-400">
                        +{option.cost} pts
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
