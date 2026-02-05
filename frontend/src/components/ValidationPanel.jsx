import React from 'react';
import { AlertTriangle, CheckCircle2, Info, XCircle, Users, User, Copy, Shield } from 'lucide-react';
import { useArmy } from '../context/ArmyContext';

export const ValidationPanel = () => {
  const { state } = useArmy();
  const { validation, totalPoints, pointsLimit } = state;
  
  const remainingPoints = pointsLimit - totalPoints;
  const percentUsed = Math.round((totalPoints / pointsLimit) * 100);
  
  const errors = validation.errors.filter(e => e.type === 'error');
  const warnings = validation.errors.filter(e => e.type === 'warning');
  
  // Calculate limits for display
  const maxUnitCost = Math.floor(pointsLimit * 0.35);
  
  return (
    <div className="bg-[#3a3c36]/80 backdrop-blur-sm border border-[#4b4d46] rounded-lg overflow-hidden sticky top-4">
      {/* Status Header */}
      <div className={`p-4 ${validation.valid ? 'bg-green-500/10' : 'bg-red-500/10'}`}>
        <div className="flex items-center gap-3">
          {validation.valid ? (
            <CheckCircle2 className="w-6 h-6 text-green-400" />
          ) : (
            <XCircle className="w-6 h-6 text-red-400" />
          )}
          <div>
            <div className={`font-headings font-bold uppercase ${validation.valid ? 'text-green-400' : 'text-red-400'}`}>
              {validation.valid ? 'Armée Valide' : 'Armée Invalide'}
            </div>
            <div className="text-xs text-gray-400">
              {errors.length} erreur{errors.length !== 1 ? 's' : ''} • {warnings.length} avertissement{warnings.length !== 1 ? 's' : ''}
            </div>
          </div>
        </div>
      </div>
      
      {/* Points Summary */}
      <div className="p-4 border-t border-[#4b4d46]">
        <h3 className="font-headings text-sm font-semibold uppercase text-gray-400 mb-3">
          Résumé des Points
        </h3>
        
        <div className="space-y-3">
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-400">Total</span>
            <span className={`font-mono font-bold ${totalPoints > pointsLimit ? 'text-red-400' : 'text-white'}`}>
              {totalPoints} pts
            </span>
          </div>
          
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-400">Limite</span>
            <span className="font-mono font-bold text-white">{pointsLimit} pts</span>
          </div>
          
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-400">Restant</span>
            <span className={`font-mono font-bold ${remainingPoints < 0 ? 'text-red-400' : 'text-green-400'}`}>
              {remainingPoints} pts
            </span>
          </div>
          
          <div className="h-2 bg-[#2e2f2b] rounded-full overflow-hidden">
            <div 
              className={`h-full transition-all duration-300 ${percentUsed > 100 ? 'bg-red-500' : percentUsed > 90 ? 'bg-yellow-500' : 'bg-green-500'}`}
              style={{ width: `${Math.min(percentUsed, 100)}%` }}
            />
          </div>
          <div className="text-xs text-gray-500 text-center">{percentUsed}% utilisé</div>
        </div>
      </div>
      
      {/* Army Composition Limits */}
      <div className="p-4 border-t border-[#4b4d46]">
        <h3 className="font-headings text-sm font-semibold uppercase text-gray-400 mb-3">
          Limites de Composition
        </h3>
        
        <div className="space-y-3">
          {/* Hero Limit */}
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-400 flex items-center gap-2">
              <User className="w-4 h-4" />
              Héros
            </span>
            <span className={`font-mono font-bold ${validation.currentHeroCount > validation.maxHeroCount ? 'text-red-400' : 'text-white'}`}>
              {validation.currentHeroCount} / {validation.maxHeroCount}
            </span>
          </div>
          
          {/* Total Units Limit */}
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-400 flex items-center gap-2">
              <Users className="w-4 h-4" />
              Unités totales
            </span>
            <span className={`font-mono font-bold ${(validation.currentUnitCount || 0) > (validation.maxTotalUnits || 999) ? 'text-red-400' : 'text-white'}`}>
              {validation.currentUnitCount || 0} / {validation.maxTotalUnits || Math.floor(pointsLimit / 150)}
            </span>
          </div>
          
          {/* Max Copies */}
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-400 flex items-center gap-2">
              <Copy className="w-4 h-4" />
              Copies max/unité
            </span>
            <span className="font-mono font-bold text-white">
              {validation.maxCopies || (1 + Math.floor(pointsLimit / 750))}
            </span>
          </div>
          
          {/* Max Unit Cost */}
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-400 flex items-center gap-2">
              <Shield className="w-4 h-4" />
              Coût max/unité
            </span>
            <span className="font-mono font-bold text-white">
              {maxUnitCost} pts
            </span>
          </div>
        </div>
      </div>
      
      {/* Unit Copies Count */}
      {validation.unitCounts && Object.keys(validation.unitCounts).length > 0 && (
        <div className="p-4 border-t border-[#4b4d46]">
          <h3 className="font-headings text-sm font-semibold uppercase text-gray-400 mb-3">
            Copies par Unité
          </h3>
          <div className="space-y-1">
            {Object.entries(validation.unitCounts).map(([unitName, count]) => {
              const isOverLimit = count > (validation.maxCopies || 2);
              return (
                <div key={unitName} className="flex justify-between items-center text-sm">
                  <span className={`truncate pr-2 ${isOverLimit ? 'text-red-400' : 'text-gray-400'}`}>
                    {unitName}
                  </span>
                  <span className={`font-mono ${isOverLimit ? 'text-red-400 font-bold' : 'text-white'}`}>
                    {count}x
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}
      
      {/* Errors */}
      {errors.length > 0 && (
        <div className="p-4 border-t border-[#4b4d46]">
          <h3 className="font-headings text-sm font-semibold uppercase text-red-400 mb-3 flex items-center gap-2">
            <XCircle className="w-4 h-4" />
            Erreurs ({errors.length})
          </h3>
          <div className="space-y-2">
            {errors.map((error, idx) => (
              <div key={idx} className="flex items-start gap-2 text-red-400 text-sm py-1">
                <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                <span>{error.message}</span>
              </div>
            ))}
          </div>
        </div>
      )}
      
      {/* Warnings */}
      {warnings.length > 0 && (
        <div className="p-4 border-t border-[#4b4d46]">
          <h3 className="font-headings text-sm font-semibold uppercase text-yellow-400 mb-3 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4" />
            Avertissements ({warnings.length})
          </h3>
          <div className="space-y-2">
            {warnings.map((warning, idx) => (
              <div key={idx} className="flex items-start gap-2 text-yellow-400 text-sm py-1">
                <Info className="w-4 h-4 mt-0.5 flex-shrink-0" />
                <span>{warning.message}</span>
              </div>
            ))}
          </div>
        </div>
      )}
      
      {/* Rules Info */}
      <div className="p-4 border-t border-[#4b4d46] bg-[#2e2f2b]/50">
        <h3 className="font-headings text-sm font-semibold uppercase text-gray-400 mb-2 flex items-center gap-2">
          <Info className="w-4 h-4" />
          Règles OPR
        </h3>
        <ul className="text-xs text-gray-500 space-y-1">
          <li>• 1 héros par tranche de 375 pts</li>
          <li>• 1+X copies de même unité (X = pts/750)</li>
          <li>• 1 unité max par tranche de 150 pts</li>
          <li>• Aucune unité &gt; 35% du total</li>
        </ul>
      </div>
    </div>
  );
};
