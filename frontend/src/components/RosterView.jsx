import React from 'react';
import { ScrollArea } from '../components/ui/scroll-area';
import { UnitCard } from './UnitCard';
import { useArmy } from '../context/ArmyContext';
import { Scroll, Users } from 'lucide-react';

export const RosterView = () => {
  const { state } = useArmy();
  const { units, totalPoints, pointsLimit, armyName } = state;
  
  const heroes = units.filter(u => u.unitType === 'hero');
  const regularUnits = units.filter(u => u.unitType !== 'hero');
  
  return (
    <div className="bg-[#3a3c36]/50 border border-[#4b4d46] rounded-lg overflow-hidden h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-[#4b4d46] bg-[#3a3c36]">
        <div className="flex justify-between items-center">
          <div className="flex items-center gap-3">
            <Scroll className="w-5 h-5 text-blue-400" />
            <div>
              <h2 className="font-headings text-lg font-bold uppercase tracking-wide text-white">
                {armyName || 'Nouvelle Armée'}
              </h2>
              <div className="text-xs text-gray-400">
                {units.length} unité{units.length !== 1 ? 's' : ''} • {heroes.length} héros
              </div>
            </div>
          </div>
          <div className="text-right">
            <div className={`font-mono text-2xl font-bold ${totalPoints > pointsLimit ? 'text-red-400' : 'text-yellow-400'}`}>
              {totalPoints}
              <span className="text-sm text-gray-400">/{pointsLimit} pts</span>
            </div>
          </div>
        </div>
        
        {/* Points Progress Bar */}
        <div className="mt-3">
          <div className="h-2 bg-[#2e2f2b] rounded-full overflow-hidden">
            <div 
              className={`h-full transition-all duration-300 ${totalPoints > pointsLimit ? 'bg-red-500' : 'bg-blue-500'}`}
              style={{ width: `${Math.min((totalPoints / pointsLimit) * 100, 100)}%` }}
            />
          </div>
        </div>
      </div>
      
      {/* Units List */}
      <ScrollArea className="flex-1">
        <div className="p-4">
          {units.length === 0 ? (
            <div className="text-center py-12">
              <Users className="w-12 h-12 text-gray-600 mx-auto mb-4" />
              <p className="text-gray-400 text-lg mb-2">Votre armée est vide</p>
              <p className="text-gray-500 text-sm">
                Ajoutez des unités depuis le panneau de gauche
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {heroes.length > 0 && (
                <div>
                  <h3 className="font-headings text-sm font-semibold uppercase text-yellow-400 mb-2">
                    Héros ({heroes.length})
                  </h3>
                  {heroes.map(unit => (
                    <UnitCard key={unit.id} rosterUnit={unit} />
                  ))}
                </div>
              )}
              
              {regularUnits.length > 0 && (
                <div>
                  <h3 className="font-headings text-sm font-semibold uppercase text-blue-400 mb-2">
                    Unités ({regularUnits.length})
                  </h3>
                  {regularUnits.map(unit => (
                    <UnitCard key={unit.id} rosterUnit={unit} />
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </ScrollArea>
    </div>
  );
};
