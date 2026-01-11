{
  "faction": "Disciples de la Guerre",
  "game": "Age of Fantasy",
  "units": [
    {
      "name": "Maître de la Guerre Élu",
      "type": "Hero",
      "base_cost": 60,
      "quality": 4,
      "defense": 4,
      "special_rules": ["Attaque versatile", "Héros", "Né pour la guerre"],
      "weapons": [
        {
          "name": "Paire d'armes à une main lourdes",
          "range": "-",
          "attacks": 4,
          "armor_piercing": 1
        }
      ],
      "upgrade_groups": [
        {
          "group": "Option",
          "type": "multiple",
          "options": [
            {
              "name": "Conquérant (Aura d'Éclaireur)",
              "cost": 15,
              "special_rules": ["Aura d'Éclaireur"]
            },
            {
              "name": "Marauder (Aura de combat imprévisible)",
              "cost": 10,
              "special_rules": ["Aura de combat imprévisible"]
            },
            {
              "name": "Manticore",
              "cost": 195,
              "mount": {
                "name": "Manticore",
                "special_rules": ["Vol", "Coriace (9)", "Peur", "Attaque mortelle"]
              }
            }
          ]
        }
      ]
    }
  ]
}
