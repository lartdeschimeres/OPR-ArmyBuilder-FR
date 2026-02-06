// frontend/src/pages/FactionSelection.jsx
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useArmy } from '../context/ArmyContext';
import { Button } from '../components/ui/button';

export default function FactionSelection() {
  const { state, setFaction } = useArmy();
  const [factions, setFactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    if (!state.selectedGame) {
      navigate('/');  // Redirige vers la sélection du jeu si aucun jeu n'est sélectionné
      return;
    }

    // 1. Charge l'index des factions
    fetch("/data/factions_index.json")
      .then((res) => res.json())
      .then((index) => {
        // 2. Charge chaque fichier de faction
        Promise.all(
          index.map((faction) =>
            fetch(`/data/factions/${faction.id}.json`).then((res) => res.json())
          )
        ).then((allFactions) => {
          // 3. Filtre les factions pour le jeu sélectionné
          const gameFactions = allFactions.filter(
            (f) => f.game === state.selectedGame.name
          );
          setFactions(gameFactions);
          setLoading(false);
        });
      });
  }, [state.selectedGame]);

  const handleFactionSelect = (faction) => {
    setFaction(faction);
    navigate('/builder');  // Redirige vers le builder après sélection
  };

  return (
    <div className="min-h-screen bg-[#2e2f2b]">
      <header className="border-b border-[#4b4d46] bg-[#3a3c36]/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <h1 className="font-headings text-2xl font-bold text-white uppercase tracking-wider">
            Sélectionnez une Faction
          </h1>
        </div>
      </header>

      <section className="py-16 px-6">
        <div className="max-w-7xl mx-auto">
          <h2 className="font-headings text-3xl font-bold text-white uppercase tracking-tight mb-8 text-center">
            {state.selectedGame.name}
          </h2>

          {loading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {[1, 2, 3].map((i) => (
                <div key={i} className="bg-[#3a3c36] rounded-lg h-32 animate-pulse" />
              ))}
            </div>
          ) : factions.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {factions.map((faction) => (
                <div
                  key={faction.id}
                  className="bg-[#3a3c36] rounded-lg overflow-hidden border-2 cursor-pointer transition-all hover:border-blue-500"
                  onClick={() => handleFactionSelect(faction)}
                >
                  <div className="p-6 text-center">
                    <h3 className="font-bold text-white uppercase tracking-wider">
                      {faction.faction}
                    </h3>
                    <p className="text-gray-400 text-sm mt-2">
                      {faction.description || "Aucune description disponible."}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-center text-gray-400">Aucune faction trouvée pour ce jeu.</p>
          )}
        </div>
      </section>
    </div>
  );
}
