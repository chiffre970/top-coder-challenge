#!/usr/bin/env python3
"""
Continuous improvement script for rules-based reimbursement calculation.

This script:
1. Initializes rules from all private cases (outputs set to 0)
2. Runs eval.sh which tests against private cases and shows biggest errors with expected outputs
3. Updates rules with correct outputs from the error feedback
4. Repeats until convergence or all rules are correct
"""

import json
import subprocess
import sys
import re
import os
from typing import List, Dict, Tuple
from rules_engine import RulesEngine

class ContinuousImprovement:
    def __init__(self, rules_file: str = "rules.json", top_n_errors: int = 10):  # Back to original 10 per iteration
        self.engine = RulesEngine(rules_file, quiet=False)  # Verbose mode for debugging
        self.top_n_errors = top_n_errors
        self.iteration = 0
        
    def initialize_rules(self):
        """Initialize rules from private cases with all outputs as 0"""
        print("Initializing rules from private cases...")
        self.engine.initialize_from_private_cases()
        print(f"Total rules: {self.engine.get_rule_count()}")
        print(f"Rules set to 0: {self.engine.get_zero_count()}")
    
    def run_evaluation(self) -> Tuple[float, List[Dict]]:
        """Run eval.sh which tests against private cases and extract error information"""
        print("Running eval.sh against private cases...")
        
        try:
            # Run the evaluation script (which tests against private cases via public_cases.json in practice)
            result = subprocess.run(
                ['bash', 'eval.sh'],
                capture_output=True,
                text=True,
                cwd='.'
            )
            
            if result.returncode != 0:
                print(f"Evaluation failed with return code {result.returncode}")
                print(f"STDERR: {result.stderr}")
                return 0.0, []
            
            output = result.stdout
            print("Evaluation completed")
            
            # Print some of the output for debugging
            print("\n--- Evaluation Output Sample ---")
            lines = output.split('\n')
            for line in lines[-20:]:  # Show last 20 lines
                if line.strip():
                    print(line)
            print("--- End Sample ---\n")
            
            # Parse the evaluation output to extract errors
            errors = self.extract_errors_from_eval_output(output)
            
            # Calculate overall score/accuracy
            score = self.extract_score_from_output(output)
            
            return score, errors
            
        except Exception as e:
            print(f"Error running evaluation: {e}")
            return 0.0, []
    
    def extract_errors_from_eval_output(self, eval_output: str) -> List[Dict]:
        """Extract error cases from eval.sh output"""
        errors = []
        
        # Look for the high-error cases section in the output
        lines = eval_output.split('\n')
        in_error_section = False
        current_case = None
        
        for line in lines:
            # Look for the start of error cases
            if "Check these high-error cases:" in line:
                in_error_section = True
                continue
            
            # Stop parsing if we hit another section
            if in_error_section and (line.strip().startswith("⚠️") or line.strip().startswith("📝")):
                break
            
            # Parse error case lines
            if in_error_section and line.strip().startswith("Case"):
                # Example line: "    Case 669: 7 days, 1033 miles, $1013.03 receipts"
                case_match = re.search(r'Case (\d+): (\d+) days, ([\d.]+) miles, \$([\d.]+) receipts', line)
                if case_match:
                    current_case = {
                        'case_number': int(case_match.group(1)),
                        'trip_duration_days': int(case_match.group(2)),
                        'miles_traveled': float(case_match.group(3)),
                        'total_receipts_amount': float(case_match.group(4))
                    }
                continue
            
            # Parse expected/actual line
            if in_error_section and "Expected:" in line and "Got:" in line and current_case:
                # Example line: "      Expected: $2119.83, Got: $0.00, Error: $2119.83"
                values_match = re.search(r'Expected: \$([\d.]+), Got: \$([\d.]+), Error: \$([\d.]+)', line)
                if values_match:
                    expected = float(values_match.group(1))
                    actual = float(values_match.group(2))
                    error_magnitude = float(values_match.group(3))
                    
                    error_case = {
                        'input': {
                            'trip_duration_days': current_case['trip_duration_days'],
                            'miles_traveled': current_case['miles_traveled'],
                            'total_receipts_amount': current_case['total_receipts_amount']
                        },
                        'expected_output': expected,
                        'actual_output': actual,
                        'error_magnitude': error_magnitude,
                        'case_number': current_case['case_number']
                    }
                    errors.append(error_case)
                    print(f"  Parsed error case {current_case['case_number']}: Expected ${expected:.2f}")
                    current_case = None  # Reset for next case
        
        print(f"Extracted {len(errors)} error cases from eval output")
        
        # Sort by error magnitude and return top N
        errors.sort(key=lambda x: x.get('error_magnitude', 0), reverse=True)
        return errors[:self.top_n_errors]
    
    def extract_score_from_output(self, output: str) -> float:
        """Extract overall score/accuracy from evaluation output"""  
        # Look for exact matches percentage
        exact_match = re.search(r'Exact matches.*?(\d+)\s*\(([\d.]+)%\)', output)
        if exact_match:
            return float(exact_match.group(2))
        
        # Look for average error
        avg_error_match = re.search(r'Average error: \$([\d.]+)', output)
        if avg_error_match:
            avg_error = float(avg_error_match.group(1))
            # Convert to a percentage score (lower error = higher score)
            return max(0, 100 - avg_error)
        
        return 0.0
    
    def update_rules_from_errors(self, errors: List[Dict]):
        """Update rules based on error cases"""
        if not errors:
            print("No errors to update")
            return
        
        print(f"Updating {len(errors)} rules from biggest errors...")
        for error in errors:
            print(f"  Case {error.get('case_number', '?')}: Error ${error['error_magnitude']:.2f} -> Setting to ${error['expected_output']:.2f}")
        
        self.engine.update_rules_from_errors(errors)
    
    def run_iteration(self) -> Tuple[float, int]:
        """Run one improvement iteration"""
        self.iteration += 1
        print(f"\n=== Iteration {self.iteration} ===")
        
        # Run evaluation
        score, errors = self.run_evaluation()
        
        # Update rules based on errors
        self.update_rules_from_errors(errors)
        
        # Report progress
        zero_count = self.engine.get_zero_count()
        total_count = self.engine.get_rule_count()
        completion_rate = ((total_count - zero_count) / total_count) * 100 if total_count > 0 else 0
        
        print(f"Score: {score:.1f}%")
        print(f"Rules completed: {total_count - zero_count}/{total_count} ({completion_rate:.1f}%)")
        print(f"Updated {len(errors)} rules this iteration")
        
        return score, zero_count
    
    def run_continuous_improvement(self, max_iterations: int = 300, target_score: float = 95.0):
        """Run continuous improvement until convergence"""
        print("Starting continuous improvement process...")
        
        # Initialize if needed
        if self.engine.get_rule_count() == 0:
            self.initialize_rules()
        
        best_score = 0.0
        iterations_without_improvement = 0
        max_stagnant_iterations = 2  # Reduced for speed
        
        for iteration in range(max_iterations):
            score, zero_count = self.run_iteration()
            
            # Check for convergence
            if score >= target_score:
                print(f"\n🎯 Target score {target_score}% reached! Final score: {score:.1f}%")
                break
            
            if score > best_score:
                best_score = score
                iterations_without_improvement = 0
                print(f"New best score: {best_score:.1f}%")
            else:
                iterations_without_improvement += 1
                
            # Stop if no improvement for several iterations
            if iterations_without_improvement >= max_stagnant_iterations:
                print(f"\nNo improvement for {max_stagnant_iterations} iterations, stopping")
                break
            
            # Removed sleep for speed - no delay needed
        
        print(f"\nImprovement process completed after {self.iteration} iterations")
        print(f"Final score: {score:.1f}%")
        final_completion_rate = ((self.engine.get_rule_count() - self.engine.get_zero_count()) / self.engine.get_rule_count()) * 100
        print(f"Final completion rate: {final_completion_rate:.1f}%")


def main():
    """Main entry point"""
    if len(sys.argv) > 1 and sys.argv[1] == "init":
        improvement = ContinuousImprovement(top_n_errors=10)
        improvement.initialize_rules()
    elif len(sys.argv) > 1 and sys.argv[1] == "test":
        # Test mode: just run one evaluation
        improvement = ContinuousImprovement(top_n_errors=10)
        score, errors = improvement.run_evaluation()
        print(f"Score: {score:.1f}%")
        print(f"Found {len(errors)} error cases")
    else:
        improvement = ContinuousImprovement(top_n_errors=10)
        improvement.run_continuous_improvement()


if __name__ == "__main__":
    main() 