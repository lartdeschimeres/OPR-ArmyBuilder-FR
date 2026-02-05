#!/usr/bin/env python3

import requests
import sys
import json
from datetime import datetime

class OPRArmyForgeAPITester:
    def __init__(self, base_url="https://tabletop-roster.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name, success, details=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
        
        result = {
            "test": name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {name}")
        if details:
            print(f"    {details}")

    def run_test(self, name, method, endpoint, expected_status=200, data=None, params=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=10)

            success = response.status_code == expected_status
            details = f"Status: {response.status_code}, Expected: {expected_status}"
            
            if not success:
                try:
                    error_data = response.json()
                    details += f", Response: {error_data}"
                except:
                    details += f", Response: {response.text[:200]}"
            
            self.log_test(name, success, details)
            
            return success, response.json() if success and response.content else {}

        except Exception as e:
            self.log_test(name, False, f"Exception: {str(e)}")
            return False, {}

    def test_health_endpoints(self):
        """Test basic health endpoints"""
        print("\n🔍 Testing Health Endpoints...")
        
        # Test root endpoint
        self.run_test("Root endpoint", "GET", "", 200)
        
        # Test health check
        self.run_test("Health check", "GET", "health", 200)

    def test_games_endpoints(self):
        """Test games endpoints"""
        print("\n🎮 Testing Games Endpoints...")
        
        # Get all games
        success, games_data = self.run_test("Get all games", "GET", "games", 200)
        
        if success and games_data:
            # Verify games structure
            expected_games = ["grimdark-future", "age-of-fantasy", "age-of-fantasy-regiments"]
            found_games = [game.get("id") for game in games_data]
            
            all_found = all(game_id in found_games for game_id in expected_games)
            self.log_test("Games structure validation", all_found, 
                         f"Expected: {expected_games}, Found: {found_games}")
            
            # Test individual game retrieval
            if games_data:
                first_game = games_data[0]
                game_id = first_game.get("id")
                if game_id:
                    self.run_test(f"Get game by ID ({game_id})", "GET", f"games/{game_id}", 200)
        
        # Test non-existent game
        self.run_test("Get non-existent game", "GET", "games/non-existent", 404)

    def test_factions_endpoints(self):
        """Test factions endpoints"""
        print("\n⚔️ Testing Factions Endpoints...")
        
        # Get all factions (should seed database)
        success, factions_data = self.run_test("Get all factions", "GET", "factions", 200)
        
        if success and factions_data:
            # Test faction filtering by game
            games = ["Age of Fantasy", "Grimdark Future", "Age of Fantasy Regiments"]
            for game in games:
                success, filtered = self.run_test(
                    f"Get factions for {game}", 
                    "GET", 
                    "factions", 
                    200, 
                    params={"game": game}
                )
                
                if success and filtered:
                    # Verify all returned factions belong to the requested game
                    correct_game = all(f.get("game") == game for f in filtered)
                    self.log_test(f"Faction filtering for {game}", correct_game,
                                f"Found {len(filtered)} factions")
            
            # Test individual faction retrieval
            if factions_data:
                first_faction = factions_data[0]
                faction_id = first_faction.get("id")
                if faction_id:
                    self.run_test(f"Get faction by ID", "GET", f"factions/{faction_id}", 200)
        
        # Test non-existent faction
        self.run_test("Get non-existent faction", "GET", "factions/non-existent", 404)

    def test_army_validation(self):
        """Test army validation endpoint"""
        print("\n✅ Testing Army Validation...")
        
        # Test valid army
        valid_army = {
            "points_limit": 1000,
            "units": [
                {
                    "id": "test-unit-1",
                    "unit_name": "Test Hero",
                    "unit_type": "hero",
                    "base_cost": 100,
                    "total_cost": 100,
                    "selected_upgrades": [],
                    "combined_unit": False
                },
                {
                    "id": "test-unit-2", 
                    "unit_name": "Test Unit",
                    "unit_type": "unit",
                    "base_cost": 200,
                    "total_cost": 200,
                    "selected_upgrades": [],
                    "combined_unit": False
                }
            ]
        }
        
        success, validation = self.run_test("Validate valid army", "POST", "validate", 200, valid_army)
        
        if success and validation:
            is_valid = validation.get("valid", False)
            total_points = validation.get("total_points", 0)
            self.log_test("Valid army validation result", is_valid, 
                         f"Total points: {total_points}")
        
        # Test army with too many heroes
        invalid_army = {
            "points_limit": 500,  # Only allows 1 hero (500/375 = 1.33 -> 1)
            "units": [
                {
                    "id": "hero-1",
                    "unit_name": "Hero 1",
                    "unit_type": "hero",
                    "base_cost": 100,
                    "total_cost": 100,
                    "selected_upgrades": [],
                    "combined_unit": False
                },
                {
                    "id": "hero-2",
                    "unit_name": "Hero 2", 
                    "unit_type": "hero",
                    "base_cost": 100,
                    "total_cost": 100,
                    "selected_upgrades": [],
                    "combined_unit": False
                }
            ]
        }
        
        success, validation = self.run_test("Validate army with too many heroes", "POST", "validate", 200, invalid_army)
        
        if success and validation:
            is_valid = validation.get("valid", False)
            errors = validation.get("errors", [])
            hero_errors = [e for e in errors if "héros" in e.get("message", "").lower()]
            self.log_test("Hero limit validation", not is_valid and len(hero_errors) > 0,
                         f"Valid: {is_valid}, Hero errors: {len(hero_errors)}")
        
        # Test army with unit exceeding 35% limit
        expensive_army = {
            "points_limit": 1000,
            "units": [
                {
                    "id": "expensive-unit",
                    "unit_name": "Expensive Unit",
                    "unit_type": "unit", 
                    "base_cost": 400,  # 40% of 1000 points
                    "total_cost": 400,
                    "selected_upgrades": [],
                    "combined_unit": False
                }
            ]
        }
        
        success, validation = self.run_test("Validate army with 35% rule violation", "POST", "validate", 200, expensive_army)
        
        if success and validation:
            is_valid = validation.get("valid", False)
            errors = validation.get("errors", [])
            cost_errors = [e for e in errors if "35%" in e.get("message", "")]
            self.log_test("35% rule validation", not is_valid and len(cost_errors) > 0,
                         f"Valid: {is_valid}, Cost errors: {len(cost_errors)}")

    def test_army_crud_operations(self):
        """Test army CRUD operations"""
        print("\n📝 Testing Army CRUD Operations...")
        
        # Create army
        army_data = {
            "name": "Test Army",
            "game": "Age of Fantasy",
            "faction": "Test Faction",
            "points_limit": 1000,
            "units": []
        }
        
        success, create_response = self.run_test("Create army", "POST", "armies", 200, army_data)
        
        army_id = None
        if success and create_response:
            army_id = create_response.get("id")
            self.log_test("Army creation response", bool(army_id), f"Army ID: {army_id}")
        
        if army_id:
            # Get army by ID
            success, army = self.run_test(f"Get army by ID", "GET", f"armies/{army_id}", 200)
            
            if success and army:
                # Verify army data
                name_match = army.get("name") == army_data["name"]
                game_match = army.get("game") == army_data["game"]
                self.log_test("Army data verification", name_match and game_match,
                             f"Name: {army.get('name')}, Game: {army.get('game')}")
            
            # Update army
            update_data = {
                "name": "Updated Test Army",
                "points_limit": 1500
            }
            
            self.run_test("Update army", "PUT", f"armies/{army_id}", 200, update_data)
            
            # Delete army
            self.run_test("Delete army", "DELETE", f"armies/{army_id}", 200)
            
            # Verify deletion
            self.run_test("Get deleted army", "GET", f"armies/{army_id}", 404)
        
        # Get all armies
        self.run_test("Get all armies", "GET", "armies", 200)

    def run_all_tests(self):
        """Run all test suites"""
        print("🚀 Starting OPR Army Forge API Tests...")
        print(f"Testing against: {self.base_url}")
        
        try:
            self.test_health_endpoints()
            self.test_games_endpoints()
            self.test_factions_endpoints()
            self.test_army_validation()
            self.test_army_crud_operations()
            
        except KeyboardInterrupt:
            print("\n⚠️ Tests interrupted by user")
        except Exception as e:
            print(f"\n💥 Unexpected error: {e}")
        
        # Print summary
        print(f"\n📊 Test Summary:")
        print(f"Tests run: {self.tests_run}")
        print(f"Tests passed: {self.tests_passed}")
        print(f"Tests failed: {self.tests_run - self.tests_passed}")
        print(f"Success rate: {(self.tests_passed/self.tests_run*100):.1f}%" if self.tests_run > 0 else "0%")
        
        return self.tests_passed == self.tests_run

def main():
    tester = OPRArmyForgeAPITester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())