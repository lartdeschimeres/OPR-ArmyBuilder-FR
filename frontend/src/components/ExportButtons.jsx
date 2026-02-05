import React, { useRef } from 'react';
import { Download, FileJson, FileText, Upload, Printer } from 'lucide-react';
import { Button } from '../components/ui/button';
import { useArmy } from '../context/ArmyContext';
import { exportToJSON, exportToHTML, importFromJSON } from '../utils/exportUtils';
import { toast } from 'sonner';

export const ExportButtons = () => {
  const { state, loadArmy } = useArmy();
  const fileInputRef = useRef(null);
  
  const handleExportJSON = () => {
    if (state.units.length === 0) {
      toast.error('Aucune unité à exporter');
      return;
    }
    
    const exportData = {
      armyName: state.armyName || 'Liste Sans Nom',
      selectedGame: state.selectedGame,
      selectedFaction: state.selectedFaction ? { 
        faction: state.selectedFaction.faction,
        game: state.selectedFaction.game 
      } : null,
      pointsLimit: state.pointsLimit,
      totalPoints: state.totalPoints,
      units: state.units.map(u => ({
        id: u.id,
        unitName: u.unitName,
        unitType: u.unitType,
        baseCost: u.baseCost,
        totalCost: u.totalCost,
        combinedUnit: u.combinedUnit,
        selectedUpgrades: u.selectedUpgrades,
        unitData: u.unitData
      })),
      exportedAt: new Date().toISOString()
    };
    
    exportToJSON(exportData);
    toast.success('Liste exportée en JSON');
  };
  
  const handleExportHTML = (printFriendly = false) => {
    if (state.units.length === 0) {
      toast.error('Aucune unité à exporter');
      return;
    }
    
    const exportData = {
      armyName: state.armyName || 'Liste Sans Nom',
      selectedGame: state.selectedGame,
      selectedFaction: state.selectedFaction,
      pointsLimit: state.pointsLimit,
      totalPoints: state.totalPoints,
      units: state.units
    };
    
    exportToHTML(exportData, printFriendly);
    toast.success(printFriendly ? 'Liste exportée (version imprimable)' : 'Liste exportée en HTML');
  };
  
  const handleImport = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    
    try {
      const data = await importFromJSON(file);
      
      // Validate basic structure
      if (!data.units || !Array.isArray(data.units)) {
        throw new Error('Format de fichier invalide');
      }
      
      loadArmy({
        armyName: data.armyName || '',
        pointsLimit: data.pointsLimit || 1000,
        selectedGame: data.selectedGame || null,
        selectedFaction: data.selectedFaction || null,
        units: data.units,
        totalPoints: data.totalPoints || 0
      });
      
      toast.success('Liste importée avec succès');
    } catch (error) {
      toast.error(`Erreur d'import: ${error.message}`);
    }
    
    // Reset file input
    event.target.value = '';
  };
  
  return (
    <div className="flex flex-wrap gap-2">
      <input
        ref={fileInputRef}
        type="file"
        accept=".json"
        onChange={handleImport}
        className="hidden"
      />
      
      <Button
        data-testid="import-json-btn"
        variant="secondary"
        size="sm"
        onClick={() => fileInputRef.current?.click()}
        className="bg-[#4b5563] hover:bg-[#586270] text-white"
      >
        <Upload className="w-4 h-4 mr-2" />
        Importer JSON
      </Button>
      
      <Button
        data-testid="export-json-btn"
        variant="secondary"
        size="sm"
        onClick={handleExportJSON}
        className="bg-[#4b5563] hover:bg-[#586270] text-white"
        disabled={state.units.length === 0}
      >
        <FileJson className="w-4 h-4 mr-2" />
        Exporter JSON
      </Button>
      
      <Button
        data-testid="export-html-btn"
        size="sm"
        onClick={() => handleExportHTML(false)}
        className="bg-blue-500 hover:bg-blue-600 text-white"
        disabled={state.units.length === 0}
      >
        <FileText className="w-4 h-4 mr-2" />
        Exporter HTML
      </Button>
      
      <Button
        data-testid="export-print-btn"
        size="sm"
        onClick={() => handleExportHTML(true)}
        className="bg-green-600 hover:bg-green-700 text-white"
        disabled={state.units.length === 0}
      >
        <Printer className="w-4 h-4 mr-2" />
        Version Imprimable
      </Button>
    </div>
  );
};
