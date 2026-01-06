# OPR Army Builder (FR)

Outil Streamlit pour construire des listes d'armée OPR (version française).

## Description
Application simple permettant de sélectionner des unités d'une faction, calculer le coût total et vérifier des règles basiques (budget, nombre maximal d'unités selon les limitations OPR).

Les fichiers de données JSON se trouvent dans le dépôt (`data/...`). Le projet contient une faction d'exemple : *Sœurs Bénies*.

## Prérequis
- Python 3.8+
- Streamlit

Un fichier `requirements.txt` minimal est déjà présent :
```
streamlit
```

## Installation (locale)
1. Cloner le dépôt :
```bash
git clone https://github.com/lartdeschimeres/OPR-Army-Forge-FR.git
cd OPR-Army-Forge-FR
```

2. (Optionnel mais recommandé) créer et activer un environnement virtuel :
- macOS / Linux
```bash
python -m venv .venv
source .venv/bin/activate
```
- Windows (PowerShell)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3. Installer les dépendances :
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

## Lancer l'application
Depuis la racine du dépôt :
```bash
streamlit run app.py
```
L'application sera accessible par défaut sur : http://localhost:8501

Remarques :
- Le fichier principal s'appelle `app.py`. Si tu le renommes ou le déplaces, lance Streamlit avec le bon chemin.
- Le script recherche les JSON aux chemins suivants (dans cet ordre) :
  - `data/factions/sisters_blessed.json`
  - `data/lists/data/factions/sisters_blessed.json`
  - `data/rules/opr_limits.json`
  - `data/lists/data/rules/opr_limits.json`
  Assure-toi d'exécuter Streamlit depuis la racine du dépôt pour que ces chemins relatifs fonctionnent.

## Structure des données (exemples)
- `data/.../factions/*.json` : contient les factions et leurs unités (champs attendus : `faction`, `units[]` avec `name` et `base_cost`).
- `data/.../rules/opr_limits.json` : règles, par ex. `unit_per_points`.

## Fonctionnalités actuelles
- Ajouter/supprimer des unités
- Somme des points et affichage du total
- Vérification simple du respect du budget et du nombre maximal d'unités
- Expander de debug affichant les règles et les chemins testés

## Améliorations possibles
- Liste multiple de factions et sélection dynamique
- Sauvegarde/export de la liste (JSON/CSV)
- Validation plus riche des règles (types d'unités, limites par type, etc.)
- Tests unitaires

## Licence
Ajoute ici la licence souhaitée (ex. MIT) ou supprime cette section si non applicable.
