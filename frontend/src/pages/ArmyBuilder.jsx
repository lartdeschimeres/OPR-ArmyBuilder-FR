import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { UnitBrowser } from '../components/UnitBrowser';
import { RosterView } from '../components/RosterView';
import { ValidationPanel } from '../components/ValidationPanel';
import { ExportButtons } from '../components/ExportButtons';
import { FactionImport } from '../components/FactionImport';
import { useArmy } from '../context/ArmyContext';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Button } from '../components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import { ArrowLeft, Sword, RotateCcw } from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const POINTS_OPTIONS = [500, 750, 1000, 1500, 2000, 2500, 3000];

export default function ArmyBuilder() {
  const navigate = useNavigate();
  const { state, setFaction, setArmyName, setPointsLimit, resetArmy } = useArmy();
  const [factions, setFactions] = useState([]);
  const [loadingFactions, setLoadingFactions] = useState(true);

  // Redirect if no game selected
  useEffect(() => {
    if (!state.selectedGame) {
      navigate('/');
    }
  }, [state.selectedGame, navigate]);

  // Fetch factions for selected game
  const fetchFactions = useCallback(async () => {
    if (!state.selectedGame) return;
    
    setLoadingFactions(true);
    try {
      // Map game ID to game name for API
      const gameNameMap = {
        'grimdark-future': 'Grimdark Future',
        'age-of-fantasy': 'Age of Fantasy',
        'age-of-fantasy-regiments': 'Age of Fantasy Regiments'
      };
      const gameName = gameNameMap[state.selectedGame.id] || state.selectedGame.name;
      
      const response = await axios.get(`${API}/factions`, {
        params: { game: gameName }
      });
      setFactions(response.data);
    } catch (err) {
      console.error('Error fetching factions:', err);
      toast.error('Erreur lors du chargement des factions');
    } finally {
      setLoadingFactions(false);
    }
  }, [state.selectedGame]);

  useEffect(() => {
    fetchFactions();
  }, [fetchFactions]);

  const handleFactionChange = (factionId) => {
    const faction = factions.find(f => f.id === factionId);
    if (faction) {
      setFaction(faction);
    }
  };

  const handleReset = () => {
    if (state.units.length > 0) {
      if (window.confirm('Voulez-vous vraiment réinitialiser l\'armée? Toutes les unités seront supprimées.')) {
        resetArmy();
        toast.success('Armée réinitialisée');
      }
    } else {
      resetArmy();
    }
  };

  if (!state.selectedGame) {
    return null;
  }

  return (
    <div className="min-h-screen bg-[#2e2f2b]">
      {/* Header */}
      <header className="border-b border-[#4b4d46] bg-[#3a3c36]/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-[1800px] mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button
                data-testid="back-to-games-btn"
                variant="ghost"
                size="sm"
                onClick={() => navigate('/')}
                className="text-gray-400 hover:text-white"
              >
                <ArrowLeft className="w-4 h-4 mr-2" />
                Jeux
              </Button>
              
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-blue-500/20 flex items-center justify-center">
                  <Sword className="w-5 h-5 text-blue-400" />
                </div>
                <div>
                  <h1 className="font-headings text-lg font-bold text-white uppercase tracking-wider">
                    OPR Army Forge
                  </h1>
                  <p className="text-xs text-gray-400">{state.selectedGame.name}</p>
                </div>
              </div>
            </div>
            
            <div className="flex items-center gap-4">
              <ExportButtons />
              
              <Button
                data-testid="reset-army-btn"
                variant="ghost"
                size="sm"
                onClick={handleReset}
                className="text-gray-400 hover:text-red-400"
              >
                <RotateCcw className="w-4 h-4 mr-2" />
                Reset
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Configuration Bar */}
      <div className="border-b border-[#4b4d46] bg-[#3a3c36]/50">
        <div className="max-w-[1800px] mx-auto px-4 py-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {/* Army Name */}
            <div className="space-y-2">
              <Label htmlFor="army-name" className="text-sm text-gray-400">
                Nom de l'Armée
              </Label>
              <Input
                id="army-name"
                data-testid="army-name-input"
                placeholder="Ma Liste..."
                value={state.armyName}
                onChange={(e) => setArmyName(e.target.value)}
                className="bg-[#2e2f2b] border-[#4b4d46] text-white placeholder:text-gray-500"
              />
            </div>
            
            {/* Faction Selector */}
            <div className="space-y-2">
              <Label className="text-sm text-gray-400">Faction</Label>
              <Select
                value={state.selectedFaction?.id || ''}
                onValueChange={handleFactionChange}
                disabled={loadingFactions}
              >
                <SelectTrigger 
                  data-testid="faction-select"
                  className="bg-[#2e2f2b] border-[#4b4d46] text-white"
                >
                  <SelectValue placeholder={loadingFactions ? "Chargement..." : "Sélectionner une faction"} />
                </SelectTrigger>
                <SelectContent className="bg-[#3a3c36] border-[#4b4d46]">
                  {factions.map((faction) => (
                    <SelectItem 
                      key={faction.id} 
                      value={faction.id}
                      className="text-white hover:bg-[#4b4d46]"
                    >
                      {faction.faction}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            {/* Points Limit */}
            <div className="space-y-2">
              <Label className="text-sm text-gray-400">Limite de Points</Label>
              <Select
                value={String(state.pointsLimit)}
                onValueChange={(val) => setPointsLimit(Number(val))}
              >
                <SelectTrigger 
                  data-testid="points-limit-select"
                  className="bg-[#2e2f2b] border-[#4b4d46] text-white"
                >
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-[#3a3c36] border-[#4b4d46]">
                  {POINTS_OPTIONS.map((pts) => (
                    <SelectItem 
                      key={pts} 
                      value={String(pts)}
                      className="text-white hover:bg-[#4b4d46]"
                    >
                      {pts} pts
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            {/* Points Summary */}
            <div className="space-y-2">
              <Label className="text-sm text-gray-400">Points Utilisés</Label>
              <div className="h-10 bg-[#2e2f2b] border border-[#4b4d46] rounded-md flex items-center px-3">
                <span className={`font-mono text-lg font-bold ${state.totalPoints > state.pointsLimit ? 'text-red-400' : 'text-yellow-400'}`}>
                  {state.totalPoints}
                </span>
                <span className="text-gray-500 mx-2">/</span>
                <span className="text-gray-400">{state.pointsLimit} pts</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content - 3 Column Layout */}
      <main className="max-w-[1800px] mx-auto px-4 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6" style={{ minHeight: 'calc(100vh - 220px)' }}>
          {/* Unit Browser - Left */}
          <div className="lg:col-span-3">
            <UnitBrowser />
          </div>
          
          {/* Roster View - Center */}
          <div className="lg:col-span-6">
            <RosterView />
          </div>
          
          {/* Validation Panel - Right */}
          <div className="lg:col-span-3">
            <ValidationPanel />
          </div>
        </div>
      </main>
    </div>
  );
}
