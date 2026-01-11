# OPR Army Builder FR 🇫🇷

**Un outil complet pour créer et gérer vos listes d'armées pour les jeux One Page Rules (OPR)**

*Auteur : Simon Joinville Fouquet*

---

## 📋 Fonctionnalités principales

✅ **Création de listes d'armées** pour tous les jeux OPR
✅ **Validation automatique** des règles spécifiques à chaque jeu
✅ **Système de comptes joueurs** pour sauvegarder et retrouver vos listes
✅ **Export HTML** pour partager ou imprimer vos listes
✅ **Calcul automatique** des valeurs de Coriace et autres statistiques
✅ **Interface intuitive** avec visualisation claire des unités

---

## 🛠️ Prérequis

- Python 3.7 ou supérieur
- Streamlit

---

## 🚀 Installation et lancement

Clonez ce dépôt :
bash
Copier

git clone https://github.com/votre-utilisateur/opr-army-forge-fr.git
cd opr-army-forge-fr


Installez les dépendances :
bash
Copier

pip install -r requirements.txt


Lancez l'application :
bash
Copier

streamlit run app.py

---

## 📂 Structure du projet
Copier

opr-army-forge-fr/
├── app.py                  # Code principal
├── lists/
│   └── data/
│       └── factions/       # Fichiers JSON des factions
├── players/                # Comptes joueurs (créé automatiquement)
├── saves/                  # Listes sauvegardées
└── README.md               # Ce fichier


---

## 🎮 Utilisation pas à pas

Créez un compte (ou connectez-vous si vous en avez déjà un)
Configurez une nouvelle liste :

Sélectionnez un jeu (Age of Fantasy, etc.)
Choisissez une faction
Définissez le format de points

Composez votre armée :

Ajoutez des unités avec leurs options
Visualisez les statistiques en temps réel
Vérifiez la validation des règles

Sauvegardez votre liste pour la retrouver plus tard
Exportez en HTML pour partager ou imprimer

---

## 📜 Règles spécifiques implémentées
Pour Age of Fantasy :

1 héros par tranche de 375 pts
1+X copies de la même unité (X=1 pour 750 pts)
Aucune unité ne peut valoir plus de 35% du total des points
1 unité max par tranche de 150 pts

---

## 🔧 Personnalisation


Ajouter de nouvelles factions :

Créez des fichiers JSON dans lists/data/factions/


Modifier les règles :

Éditez le dictionnaire GAME_RULES dans le code


Adapter le style :

Modifiez le CSS dans les composants HTML


---

## 📦 Déploiement (Streamlit Cloud)

Créez un compte sur Streamlit Community Cloud
Liez votre dépôt GitHub
Configurez les paramètres de déploiement

---

## 🤝 Contribution
Les contributions sont bienvenues ! Pour contribuer :

Fork le projet
Créez une branche (git checkout -b feature/ma-fonctionnalité)
Commitez vos changements
Poussez vers la branche
Ouvrez une Pull Request

---

## 📜 Licence
Ce projet est sous licence MIT.

---

## 🙏 Remerciements

À la communauté OPR pour les règles et l'univers
À tous les testeurs et contributeurs
Dernière mise à jour : 11/01/2026
Version : 1.0


```bash
pip install streamlit
