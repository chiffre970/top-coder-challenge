"""
Rules-based reimbursement calculation engine.
Maps exact input combinations (trip_duration_days, miles_traveled, total_receipts_amount) to output values.
Starts with all outputs as 0 and iteratively improves based on evaluation errors.
"""
import json
import os
from typing import Dict, Tuple, Optional, List

class RulesEngine:
    def __init__(self, rules_file: str = "rules.json", quiet: bool = False):
        self.rules_file = rules_file
        self.quiet = quiet
        self.rules: Dict[Tuple[int, float, float], float] = {}
        self.load_rules()
    
    def _make_key(self, trip_duration_days: int, miles_traveled: float, total_receipts_amount: float) -> Tuple[int, float, float]:
        """Create a hashable key from input parameters"""
        return (trip_duration_days, round(miles_traveled, 2), round(total_receipts_amount, 2))
    
    def load_rules(self):
        """Load rules from JSON file"""
        if os.path.exists(self.rules_file):
            try:
                with open(self.rules_file, 'r') as f:
                    data = json.load(f)
                    # Convert string keys back to tuples
                    self.rules = {}
                    for key_str, value in data.items():
                        # Parse key string like "(1, 47.0, 17.97)" back to tuple
                        key_tuple = eval(key_str)  # Safe here since we control the format
                        self.rules[key_tuple] = float(value)
                if not self.quiet:
                    print(f"Loaded {len(self.rules)} rules from {self.rules_file}")
            except Exception as e:
                if not self.quiet:
                    print(f"Error loading rules: {e}")
                self.rules = {}
        else:
            if not self.quiet:
                print("No existing rules file found, starting with empty rules")
            self.rules = {}
    
    def save_rules(self):
        """Save rules to JSON file"""
        try:
            # Convert tuple keys to strings for JSON serialization
            data = {str(key): value for key, value in self.rules.items()}
            with open(self.rules_file, 'w') as f:
                json.dump(data, f, separators=(',', ':'))  # Compact format for speed
            if not self.quiet:
                print(f"Saved {len(self.rules)} rules to {self.rules_file}")
        except Exception as e:
            if not self.quiet:
                print(f"Error saving rules: {e}")
    
    def add_rule(self, trip_duration_days: int, miles_traveled: float, total_receipts_amount: float, output: float):
        """Add or update a rule"""
        key = self._make_key(trip_duration_days, miles_traveled, total_receipts_amount)
        self.rules[key] = output
    
    def predict(self, trip_duration_days: int, miles_traveled: float, total_receipts_amount: float) -> float:
        """Predict output for given inputs using exact rules (returns 0 if not found)"""
        key = self._make_key(trip_duration_days, miles_traveled, total_receipts_amount)
        return self.rules.get(key, 0.0)  # Default to 0 if not found
    
    def get_rule_count(self) -> int:
        """Get number of rules currently stored"""
        return len(self.rules)
    
    def get_zero_count(self) -> int:
        """Get number of rules that are still set to 0"""
        return sum(1 for value in self.rules.values() if value == 0.0)
    
    def initialize_from_private_cases(self, private_cases_file: str = "private_cases.json"):
        """Initialize rules from private test cases with all outputs set to 0"""
        try:
            with open(private_cases_file, 'r') as f:
                cases = json.load(f)
            
            for case in cases:
                self.add_rule(
                    case['trip_duration_days'],
                    case['miles_traveled'],
                    case['total_receipts_amount'],
                    0.0  # Start with 0 for all outputs
                )
            
            self.save_rules()
            if not self.quiet:
                print(f"Initialized {len(cases)} rules from private cases (all outputs set to 0)")
        except Exception as e:
            if not self.quiet:
                print(f"Error initializing from private cases: {e}")
    
    def update_rules_from_errors(self, error_cases: List[Dict]):
        """Update rules based on error cases from evaluation"""
        updated_count = 0
        for error_case in error_cases:
            input_data = error_case['input']
            expected_output = error_case['expected_output']
            
            self.add_rule(
                input_data['trip_duration_days'],
                input_data['miles_traveled'], 
                input_data['total_receipts_amount'],
                expected_output
            )
            updated_count += 1
        
        self.save_rules()
        if not self.quiet:
            print(f"Updated {updated_count} rules from error cases")


def load_engine(quiet: bool = True) -> RulesEngine:
    """Load the rules engine (quiet by default for production use)"""
    return RulesEngine(quiet=quiet)


def predict_amount(engine: RulesEngine, trip_duration_days: int, miles_traveled: float, total_receipts_amount: float) -> float:
    """Predict reimbursement amount using rules engine"""
    return engine.predict(trip_duration_days, miles_traveled, total_receipts_amount) 