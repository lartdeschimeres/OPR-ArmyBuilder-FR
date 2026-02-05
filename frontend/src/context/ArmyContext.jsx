import React, { createContext, useContext, useReducer, useCallback } from 'react';
import { v4 as uuidv4 } from 'uuid';

const ArmyContext = createContext(null);

const initialState = {
  selectedGame: null,
  selectedFaction: null,
  armyName: '',
  pointsLimit: 1000,
  units: [],
  totalPoints: 0,
  validation: {
    valid: true,
    errors: [],
    maxHeroCount: 2,
    currentHeroCount: 0
  }
};

function calculateUnitCost(unit, selectedUpgrades, isCombined) {
  let cost = unit.base_cost;
  
  // Add upgrade costs
  selectedUpgrades.forEach(upgrade => {
    cost += upgrade.cost;
  });
  
  // Double cost if combined unit (not for heroes)
  if (isCombined && unit.type !== 'hero') {
    cost *= 2;
  }
  
  return cost;
}

function validateArmy(state) {
  const errors = [];
  const { pointsLimit, units, totalPoints } = state;
  
  // Count heroes
  const heroCount = units.filter(u => u.unitType === 'hero').length;
  const maxHeroes = Math.floor(pointsLimit / 375);
  
  // Check hero limit
  if (heroCount > maxHeroes) {
    errors.push({
      type: 'error',
      message: `Trop de héros! Maximum ${maxHeroes} héros pour ${pointsLimit} pts (1 héros / 375 pts)`,
      unitId: null
    });
  }
  
  // Check 35% rule
  const maxUnitCost = Math.floor(pointsLimit * 0.35);
  units.forEach(unit => {
    if (unit.totalCost > maxUnitCost) {
      errors.push({
        type: 'error',
        message: `L'unité "${unit.unitName}" coûte ${unit.totalCost} pts, maximum: ${maxUnitCost} pts (35%)`,
        unitId: unit.id
      });
    }
  });
  
  // Check total points
  if (totalPoints > pointsLimit) {
    errors.push({
      type: 'error',
      message: `L'armée dépasse la limite! ${totalPoints}/${pointsLimit} pts`,
      unitId: null
    });
  }
  
  return {
    valid: errors.filter(e => e.type === 'error').length === 0,
    errors,
    maxHeroCount: maxHeroes,
    currentHeroCount: heroCount
  };
}

function armyReducer(state, action) {
  switch (action.type) {
    case 'SET_GAME': {
      return {
        ...initialState,
        selectedGame: action.payload
      };
    }
    
    case 'SET_FACTION': {
      return {
        ...state,
        selectedFaction: action.payload,
        units: [],
        totalPoints: 0,
        validation: validateArmy({ ...state, units: [], totalPoints: 0 })
      };
    }
    
    case 'SET_ARMY_NAME': {
      return {
        ...state,
        armyName: action.payload
      };
    }
    
    case 'SET_POINTS_LIMIT': {
      const newState = {
        ...state,
        pointsLimit: action.payload
      };
      return {
        ...newState,
        validation: validateArmy(newState)
      };
    }
    
    case 'ADD_UNIT': {
      const { unit } = action.payload;
      const newUnit = {
        id: uuidv4(),
        unitName: unit.name,
        unitType: unit.type,
        baseCost: unit.base_cost,
        unitData: unit,
        selectedUpgrades: [],
        combinedUnit: false,
        totalCost: unit.base_cost
      };
      
      const newUnits = [...state.units, newUnit];
      const newTotalPoints = newUnits.reduce((sum, u) => sum + u.totalCost, 0);
      const newState = {
        ...state,
        units: newUnits,
        totalPoints: newTotalPoints
      };
      
      return {
        ...newState,
        validation: validateArmy(newState)
      };
    }
    
    case 'REMOVE_UNIT': {
      const newUnits = state.units.filter(u => u.id !== action.payload);
      const newTotalPoints = newUnits.reduce((sum, u) => sum + u.totalCost, 0);
      const newState = {
        ...state,
        units: newUnits,
        totalPoints: newTotalPoints
      };
      
      return {
        ...newState,
        validation: validateArmy(newState)
      };
    }
    
    case 'UPDATE_UNIT_UPGRADES': {
      const { unitId, selectedUpgrades, combinedUnit } = action.payload;
      const newUnits = state.units.map(unit => {
        if (unit.id !== unitId) return unit;
        
        const totalCost = calculateUnitCost(
          unit.unitData,
          selectedUpgrades,
          combinedUnit
        );
        
        return {
          ...unit,
          selectedUpgrades,
          combinedUnit,
          totalCost
        };
      });
      
      const newTotalPoints = newUnits.reduce((sum, u) => sum + u.totalCost, 0);
      const newState = {
        ...state,
        units: newUnits,
        totalPoints: newTotalPoints
      };
      
      return {
        ...newState,
        validation: validateArmy(newState)
      };
    }
    
    case 'LOAD_ARMY': {
      const newState = {
        ...state,
        ...action.payload
      };
      return {
        ...newState,
        validation: validateArmy(newState)
      };
    }
    
    case 'RESET': {
      return initialState;
    }
    
    default:
      return state;
  }
}

export function ArmyProvider({ children }) {
  const [state, dispatch] = useReducer(armyReducer, initialState);
  
  const setGame = useCallback((game) => {
    dispatch({ type: 'SET_GAME', payload: game });
  }, []);
  
  const setFaction = useCallback((faction) => {
    dispatch({ type: 'SET_FACTION', payload: faction });
  }, []);
  
  const setArmyName = useCallback((name) => {
    dispatch({ type: 'SET_ARMY_NAME', payload: name });
  }, []);
  
  const setPointsLimit = useCallback((limit) => {
    dispatch({ type: 'SET_POINTS_LIMIT', payload: limit });
  }, []);
  
  const addUnit = useCallback((unit) => {
    dispatch({ type: 'ADD_UNIT', payload: { unit } });
  }, []);
  
  const removeUnit = useCallback((unitId) => {
    dispatch({ type: 'REMOVE_UNIT', payload: unitId });
  }, []);
  
  const updateUnitUpgrades = useCallback((unitId, selectedUpgrades, combinedUnit) => {
    dispatch({ 
      type: 'UPDATE_UNIT_UPGRADES', 
      payload: { unitId, selectedUpgrades, combinedUnit } 
    });
  }, []);
  
  const loadArmy = useCallback((armyData) => {
    dispatch({ type: 'LOAD_ARMY', payload: armyData });
  }, []);
  
  const resetArmy = useCallback(() => {
    dispatch({ type: 'RESET' });
  }, []);
  
  const value = {
    state,
    setGame,
    setFaction,
    setArmyName,
    setPointsLimit,
    addUnit,
    removeUnit,
    updateUnitUpgrades,
    loadArmy,
    resetArmy
  };
  
  return (
    <ArmyContext.Provider value={value}>
      {children}
    </ArmyContext.Provider>
  );
}

export function useArmy() {
  const context = useContext(ArmyContext);
  if (!context) {
    throw new Error('useArmy must be used within an ArmyProvider');
  }
  return context;
}
