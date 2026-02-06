import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { GameCard } from '../components/GameCard';
import { useArmy } from '../context/ArmyContext';
import { Sword, Shield, Scroll, ChevronRight } from 'lucide-react';
import { Button } from '../components/ui/button';

export default function GameSelection() {
  const navigate = useNavigate();
  const { state, setGame } = useArmy();
  const [games, setGames] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch("/data/games.json")
      .then(res => {
        if (!res.ok) throw new Error("Impossible de charger les jeux");
        return res.json();
      })
      .then(data => {
        setGames(data);
        setError(null);
      })
      .catch(err => {
        console.error(err);
        setError("Impossible de charger les jeux");
      })
      .finally(() => setLoading(false));
  }, []);

  const handleGameSelect = (game) => {
    setGame(game);
  };

  const handleContinue = () => {
    if (state.selectedGame) {
      navigate('/builder');
    }
  };

  return (
    <div className="min-h-screen bg-[#2e2f2b]">
      {/* Header */}
      <header className="border-b border-[#4b4d46] bg-[#3a3c36]/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-blue-500/20 flex items-center justify-center">
                <Sword className="w-6 h-6 text-blue-400" />
              </div>
              <div>
                <h1 className="font-headings text-2xl font-bold text-white uppercase tracking-wider">
                  OPR Army Forge
                </h1>
                <p className="text-xs text-gray-400">OnePageRules Army Builder</p>
              </div>
            </div>
            
            {state.selectedGame && (
              <Button
                data-testid="continue-to-builder-btn"
                onClick={handleContinue}
                className="bg-blue-500 hover:bg-blue-600 text-white font-bold shadow-lg shadow-blue-500/20"
              >
                Continuer vers le Builder
                <ChevronRight className="w-4 h-4 ml-2" />
              </Button>
            )}
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="py-16 px-6">
        <div className="max-w-7xl mx-auto text-center">
          <div className="flex justify-center gap-6 mb-8">
            <div className="w-16 h-16 rounded-xl bg-yellow-500/10 flex items-center justify-center">
              <Shield className="w-8 h-8 text-yellow-400" />
            </div>
            <div className="w-16 h-16 rounded-xl bg-blue-500/10 flex items-center justify-center">
              <Sword className="w-8 h-8 text-blue-400" />
            </div>
            <div className="w-16 h-16 rounded-xl bg-green-500/10 flex items-center justify-center">
              <Scroll className="w-8 h-8 text-green-400" />
            </div>
          </div>
          
          <h2 className="font-headings text-4xl md:text-5xl font-bold text-white uppercase tracking-tight mb-4">
            Sélectionnez Votre Jeu
          </h2>
          <p className="text-lg text-gray-400 max-w-2xl mx-auto">
            Choisissez un système de jeu OnePageRules pour commencer à construire votre armée.
            Créez, validez et exportez vos listes en quelques clics.
          </p>
        </div>
      </section>

      {/* Games Grid */}
      <section className="pb-16 px-6">
        <div className="max-w-7xl mx-auto">
          {loading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {[1, 2, 3].map((i) => (
                <div key={i} className="bg-[#3a3c36] rounded-lg h-64 animate-pulse" />
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {games.map((game, idx) => (
                <div 
                  key={game.id} 
                  className="animate-slideUp"
                  style={{ animationDelay: `${idx * 0.1}s` }}
                >
                  <GameCard
                    game={game}
                    isSelected={state.selectedGame?.id === game.id}
                    onClick={() => handleGameSelect(game)}
                  />
                </div>
              ))}
            </div>
          )}
        </div>
      </section>

      {/* Features */}
      <section className="py-16 px-6 border-t border-[#4b4d46]">
        <div className="max-w-7xl mx-auto">
          <h3 className="font-headings text-2xl font-bold text-white uppercase text-center mb-12">
            Fonctionnalités
          </h3>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="bg-[#3a3c36] border border-[#4b4d46] rounded-lg p-6 text-center">
              <div className="w-12 h-12 rounded-lg bg-blue-500/20 flex items-center justify-center mx-auto mb-4">
                <Shield className="w-6 h-6 text-blue-400" />
              </div>
              <h4 className="font-headings font-bold text-white uppercase mb-2">Validation OPR</h4>
              <p className="text-sm text-gray-400">
                Vérification automatique des règles de construction d'armée OPR
              </p>
            </div>
            
            <div className="bg-[#3a3c36] border border-[#4b4d46] rounded-lg p-6 text-center">
              <div className="w-12 h-12 rounded-lg bg-yellow-500/20 flex items-center justify-center mx-auto mb-4">
                <Sword className="w-6 h-6 text-yellow-400" />
              </div>
              <h4 className="font-headings font-bold text-white uppercase mb-2">Personnalisation</h4>
              <p className="text-sm text-gray-400">
                Configurez chaque unité avec des armes, montures et améliorations
              </p>
            </div>
            
            <div className="bg-[#3a3c36] border border-[#4b4d46] rounded-lg p-6 text-center">
              <div className="w-12 h-12 rounded-lg bg-green-500/20 flex items-center justify-center mx-auto mb-4">
                <Scroll className="w-6 h-6 text-green-400" />
              </div>
              <h4 className="font-headings font-bold text-white uppercase mb-2">Export</h4>
              <p className="text-sm text-gray-400">
                Exportez en HTML ou JSON pour l'impression ou la sauvegarde
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-[#4b4d46] py-8 px-6">
        <div className="max-w-7xl mx-auto text-center">
          <p className="text-sm text-gray-500">
            OPR Army Forge • OnePageRules Army List Builder
          </p>
          <p className="text-xs text-gray-600 mt-1">
            Développé par Simon Joinville Fouquet
          </p>
        </div>
      </footer>
    </div>
  );
}
