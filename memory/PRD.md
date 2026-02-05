# OPR Army Forge - PRD

## Project Overview
**Application Name:** OPR Army Forge  
**Developer:** Simon Joinville Fouquet  
**Platform:** Web-based (React + FastAPI + MongoDB)  
**Primary Use Case:** OnePageRules (OPR) army list builder for tabletop wargames

## User Personas
1. **Tournament Player** - Needs validated army lists that comply with OPR rules
2. **Casual Gamer** - Wants easy-to-use interface for quick army building
3. **Collector** - Uses the app to track and plan miniature collections

## Core Requirements (Static)
- Game selection for all OPR systems (Grimdark Future, Age of Fantasy, Age of Fantasy Regiments)
- Faction-based unit browsing
- Unit customization with upgrades (radio for heroes, checkboxes for units)
- Combined Unit option for non-heroes
- Real-time validation:
  - 1 hero per 375 points limit
  - No unit can exceed 35% of total points
  - Total points cannot exceed limit
- Export to HTML (dark theme + print-friendly) and JSON
- Import from JSON

## What's Been Implemented (January 2026)

### Backend (FastAPI)
- [x] Games API (`/api/games`) - Returns all OPR game systems
- [x] Factions API (`/api/factions`) - Returns factions filtered by game
- [x] Armies API (`/api/armies`) - CRUD operations for saved armies
- [x] Validation API (`/api/validate`) - Server-side army validation
- [x] Sample faction data seeding (Sœurs Bénies, Disciples de la Guerre)
- [x] MongoDB integration for data persistence

### Frontend (React)
- [x] Game Selection Page with image cards
- [x] Army Builder 3-column layout:
  - Unit Browser (left) with search and filters
  - Roster View (center) with expandable unit cards
  - Validation Panel (right) with real-time feedback
- [x] Unit customization:
  - Radio buttons for hero upgrades
  - Checkboxes for unit upgrades
  - Combined Unit toggle for regular units
- [x] Export functionality (JSON, HTML dark, HTML print-friendly)
- [x] Import JSON functionality
- [x] Army name and points limit configuration
- [x] Dark theme UI (#2e2f2b background, #3a3c36 cards)

### Design
- [x] Barlow Condensed headings, Inter body font
- [x] Yellow accent for points/costs
- [x] Blue accent for primary actions
- [x] Responsive layout (mobile, tablet, desktop)

## Prioritized Backlog

### P0 (Critical) - COMPLETED
- ✅ Game selection
- ✅ Unit browser
- ✅ Army roster
- ✅ Validation
- ✅ Export/Import

### P1 (Important) - Next Phase
- [ ] Import user-provided JSON faction files from UI
- [ ] Persist armies to MongoDB with user session
- [ ] Unit count limits per army
- [ ] Spell selection for spellcaster units

### P2 (Nice to Have)
- [ ] Compare army lists side-by-side
- [ ] Print preview modal before export
- [ ] Share army via URL
- [ ] Army list templates
- [ ] User accounts with Google Auth

## Technical Architecture
```
Frontend (React 19)
├── Pages: GameSelection, ArmyBuilder
├── Components: GameCard, UnitBrowser, UnitCard, RosterView, ValidationPanel, ExportButtons
├── Context: ArmyContext (state management)
├── Utils: exportUtils.js
└── UI: Shadcn components + custom dark theme

Backend (FastAPI)
├── Routes: /api/games, /api/factions, /api/armies, /api/validate
├── Models: Pydantic models for Faction, Unit, Army
├── DB: MongoDB with Motor async driver
└── Data: Sample factions seeded on first request

Database (MongoDB)
├── Collection: factions
├── Collection: armies
└── Collection: status_checks
```

## Next Tasks
1. Add more faction data files via import endpoint
2. Implement spell selection for spellcaster heroes
3. Add unit limits validation per faction
4. User session management for army persistence
