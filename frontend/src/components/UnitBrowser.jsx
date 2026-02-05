import React, { useState } from 'react';
import { Plus, Search, Shield, Sword, User, Users } from 'lucide-react';
import { Input } from '../components/ui/input';
import { Button } from '../components/ui/button';
import { ScrollArea } from '../components/ui/scroll-area';
import { useArmy } from '../context/ArmyContext';

export const UnitBrowser = () => {
  const { state, addUnit } = useArmy();
  const [searchQuery, setSearchQuery] = useState('');
  const [filter, setFilter] = useState('all'); // 'all', 'hero', 'unit'
  
  const faction = state.selectedFaction;
  
  if (!faction) {
    return (
      <div className="bg-[#3a3c36] border border-[#4b4d46] rounded-lg p-6 h-full flex items-center justify-center">
        <p className="text-gray-400 text-center">
          Sélectionnez une faction pour voir les unités disponibles
        </p>
      </div>
    );
  }
  
  const units = faction.units || [];
  
  const filteredUnits = units.filter(unit => {
    const matchesSearch = unit.name.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesFilter = filter === 'all' || unit.type === filter;
    return matchesSearch && matchesFilter;
  });
  
  const heroes = filteredUnits.filter(u => u.type === 'hero');
  const regularUnits = filteredUnits.filter(u => u.type !== 'hero');
  
  return (
    <div className="bg-[#3a3c36] border border-[#4b4d46] rounded-lg overflow-hidden h-full flex flex-col">
      <div className="p-4 border-b border-[#4b4d46]">
        <h2 className="font-headings text-lg font-bold uppercase tracking-wide text-white mb-3">
          Unités Disponibles
        </h2>
        
        <div className="relative mb-3">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <Input
            data-testid="unit-search-input"
            placeholder="Rechercher..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9 bg-[#2e2f2b] border-[#4b4d46] text-white placeholder:text-gray-500"
          />
        </div>
        
        <div className="flex gap-2">
          <Button
            data-testid="filter-all-btn"
            variant={filter === 'all' ? 'default' : 'secondary'}
            size="sm"
            onClick={() => setFilter('all')}
            className={filter === 'all' ? 'bg-blue-500 hover:bg-blue-600' : 'bg-[#4b5563] hover:bg-[#586270]'}
          >
            Tous
          </Button>
          <Button
            data-testid="filter-heroes-btn"
            variant={filter === 'hero' ? 'default' : 'secondary'}
            size="sm"
            onClick={() => setFilter('hero')}
            className={filter === 'hero' ? 'bg-blue-500 hover:bg-blue-600' : 'bg-[#4b5563] hover:bg-[#586270]'}
          >
            <User className="w-3 h-3 mr-1" />
            Héros
          </Button>
          <Button
            data-testid="filter-units-btn"
            variant={filter === 'unit' ? 'default' : 'secondary'}
            size="sm"
            onClick={() => setFilter('unit')}
            className={filter === 'unit' ? 'bg-blue-500 hover:bg-blue-600' : 'bg-[#4b5563] hover:bg-[#586270]'}
          >
            <Users className="w-3 h-3 mr-1" />
            Unités
          </Button>
        </div>
      </div>
      
      <ScrollArea className="flex-1">
        <div className="p-4 space-y-4">
          {heroes.length > 0 && (
            <div>
              <h3 className="font-headings text-sm font-semibold uppercase text-yellow-400 mb-2 flex items-center gap-2">
                <User className="w-4 h-4" />
                Héros ({heroes.length})
              </h3>
              <div className="space-y-2">
                {heroes.map((unit, idx) => (
                  <UnitBrowserItem key={`hero-${idx}`} unit={unit} onAdd={() => addUnit(unit)} />
                ))}
              </div>
            </div>
          )}
          
          {regularUnits.length > 0 && (
            <div>
              <h3 className="font-headings text-sm font-semibold uppercase text-blue-400 mb-2 flex items-center gap-2">
                <Users className="w-4 h-4" />
                Unités ({regularUnits.length})
              </h3>
              <div className="space-y-2">
                {regularUnits.map((unit, idx) => (
                  <UnitBrowserItem key={`unit-${idx}`} unit={unit} onAdd={() => addUnit(unit)} />
                ))}
              </div>
            </div>
          )}
          
          {filteredUnits.length === 0 && (
            <p className="text-gray-400 text-center py-8">
              Aucune unité trouvée
            </p>
          )}
        </div>
      </ScrollArea>
    </div>
  );
};

const UnitBrowserItem = ({ unit, onAdd }) => {
  const isHero = unit.type === 'hero';
  
  return (
    <div
      data-testid={`unit-browser-item-${unit.name.replace(/\s+/g, '-').toLowerCase()}`}
      className="bg-[#2e2f2b] border border-[#4b4d46] rounded-md p-3 hover:border-gray-500 transition-colors group"
    >
      <div className="flex justify-between items-start">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="font-bold text-sm text-white truncate">{unit.name}</span>
            {isHero && (
              <span className="text-xs bg-yellow-500/20 text-yellow-400 px-1.5 py-0.5 rounded">
                Héros
              </span>
            )}
          </div>
          
          <div className="flex items-center gap-3 text-xs text-gray-400">
            <span className="flex items-center gap-1">
              <Sword className="w-3 h-3" />
              Q{unit.quality}+
            </span>
            <span className="flex items-center gap-1">
              <Shield className="w-3 h-3" />
              D{unit.defense}+
            </span>
            <span>Taille: {unit.size}</span>
          </div>
        </div>
        
        <div className="flex items-center gap-2 ml-2">
          <span className="font-mono text-sm font-bold text-yellow-400">
            {unit.base_cost} pts
          </span>
          <Button
            data-testid={`add-unit-btn-${unit.name.replace(/\s+/g, '-').toLowerCase()}`}
            size="sm"
            onClick={onAdd}
            className="bg-blue-500 hover:bg-blue-600 text-white h-7 w-7 p-0 opacity-0 group-hover:opacity-100 transition-opacity"
          >
            <Plus className="w-4 h-4" />
          </Button>
        </div>
      </div>
      
      {unit.special_rules && unit.special_rules.length > 0 && (
        <div className="mt-2 text-xs text-blue-400 truncate">
          {unit.special_rules.slice(0, 3).join(', ')}
          {unit.special_rules.length > 3 && '...'}
        </div>
      )}
    </div>
  );
};
