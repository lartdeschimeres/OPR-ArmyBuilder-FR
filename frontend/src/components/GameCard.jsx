import React from 'react';

export const GameCard = ({ game, isSelected, onClick }) => {
  return (
    <div
      data-testid={`game-card-${game.id}`}
      onClick={onClick}
      className={`
        relative overflow-hidden rounded-lg cursor-pointer group
        border-2 transition-colors duration-200
        ${isSelected 
          ? 'border-blue-500 ring-2 ring-blue-500/30' 
          : 'border-transparent hover:border-blue-400/60'
        }
        bg-[#3a3c36]
      `}
    >
      <div className="relative h-48 overflow-hidden">
        <img
          src={game.image}
          alt={game.name}
          className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
          onError={(e) => {
            e.target.src = 'https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=800';
          }}
        />
        <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/40 to-transparent" />
      </div>
      
      <div className="absolute bottom-0 left-0 right-0 p-4">
        <h3 className="font-headings text-xl font-bold text-white uppercase tracking-wider">
          {game.name}
        </h3>
        <p className="text-sm text-gray-300 mt-1 line-clamp-2">
          {game.description}
        </p>
        <div className="mt-2 flex items-center gap-2">
          <span className="text-xs font-mono bg-blue-500/20 text-blue-400 px-2 py-0.5 rounded">
            {game.short_name}
          </span>
          {isSelected && (
            <span className="text-xs bg-green-500/20 text-green-400 px-2 py-0.5 rounded flex items-center gap-1">
              <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
              </svg>
              Sélectionné
            </span>
          )}
        </div>
      </div>
    </div>
  );
};
