#!/usr/bin/env python3
"""
Progress monitoring script for the continuous improvement process.
Shows real-time progress on rule completion and estimates time remaining.
"""

import json
import time
import os
import subprocess
from datetime import datetime, timedelta

class ProgressMonitor:
    def __init__(self, rules_file: str = "rules.json"):
        self.rules_file = rules_file
        self.start_time = datetime.now()
        self.last_check_time = self.start_time
        self.last_completion_rate = 0.0
        self.completion_history = []
        
    def get_completion_stats(self):
        """Get current completion statistics"""
        try:
            with open(self.rules_file, 'r') as f:
                data = json.load(f)
            
            total_rules = len(data)
            completed_rules = sum(1 for value in data.values() if float(value) != 0.0)
            completion_rate = (completed_rules / total_rules) * 100 if total_rules > 0 else 0
            
            return {
                'total_rules': total_rules,
                'completed_rules': completed_rules,
                'zero_rules': total_rules - completed_rules,
                'completion_rate': completion_rate
            }
        except Exception as e:
            return {
                'total_rules': 0,
                'completed_rules': 0,
                'zero_rules': 0,
                'completion_rate': 0.0,
                'error': str(e)
            }
    
    def estimate_time_remaining(self, current_completion_rate):
        """Estimate time remaining based on progress rate"""
        if len(self.completion_history) < 2:
            return "Calculating..."
        
        # Calculate rate of progress (percentage per minute)
        recent_progress = self.completion_history[-5:]  # Last 5 measurements
        if len(recent_progress) < 2:
            return "Calculating..."
        
        time_diff = (recent_progress[-1]['time'] - recent_progress[0]['time']).total_seconds() / 60  # minutes
        completion_diff = recent_progress[-1]['completion'] - recent_progress[0]['completion']
        
        if time_diff <= 0 or completion_diff <= 0:
            return "Stalled"
        
        rate_per_minute = completion_diff / time_diff
        remaining_percentage = 100 - current_completion_rate
        
        if rate_per_minute > 0:
            minutes_remaining = remaining_percentage / rate_per_minute
            return f"{int(minutes_remaining)}m {int((minutes_remaining % 1) * 60)}s"
        else:
            return "Unknown"
    
    def check_process_running(self):
        """Check if the continuous improvement process is still running"""
        try:
            result = subprocess.run(['pgrep', '-f', 'continuous_improvement.py'], 
                                  capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False
    
    def display_progress(self):
        """Display current progress"""
        stats = self.get_completion_stats()
        current_time = datetime.now()
        elapsed = current_time - self.start_time
        
        # Store completion history
        self.completion_history.append({
            'time': current_time,
            'completion': stats['completion_rate']
        })
        
        # Keep only recent history
        if len(self.completion_history) > 20:
            self.completion_history = self.completion_history[-20:]
        
        # Clear screen for fresh display
        os.system('clear' if os.name == 'posix' else 'cls')
        
        print("🚀 Continuous Improvement Progress Monitor")
        print("=" * 50)
        print(f"Started: {self.start_time.strftime('%H:%M:%S')}")
        print(f"Elapsed: {elapsed}")
        print()
        
        if 'error' in stats:
            print(f"❌ Error reading rules file: {stats['error']}")
            return
        
        # Progress bar
        completion = stats['completion_rate']
        bar_width = 40
        filled = int(completion * bar_width / 100)
        bar = "█" * filled + "░" * (bar_width - filled)
        
        print(f"Progress: [{bar}] {completion:.1f}%")
        print()
        print(f"📊 Rules Status:")
        print(f"  Total rules:     {stats['total_rules']:,}")
        print(f"  Completed:       {stats['completed_rules']:,}")
        print(f"  Remaining:       {stats['zero_rules']:,}")
        print()
        
        # Time estimates
        time_remaining = self.estimate_time_remaining(completion)
        print(f"⏱️  Time Remaining: {time_remaining}")
        
        # Process status
        is_running = self.check_process_running()
        status = "🟢 RUNNING" if is_running else "🔴 STOPPED"
        print(f"📈 Process Status: {status}")
        
        if not is_running and completion < 95:
            print()
            print("⚠️  Process appears to have stopped!")
            print("   You may need to restart it:")
            print("   python continuous_improvement.py")
        
        # Recent progress
        if len(self.completion_history) >= 2:
            recent_change = completion - self.last_completion_rate
            if recent_change > 0:
                print(f"📈 Recent Progress: +{recent_change:.1f}% since last check")
            elif recent_change == 0:
                print("📊 Recent Progress: No change")
            else:
                print(f"📉 Recent Progress: {recent_change:.1f}% (possible restart)")
        
        self.last_completion_rate = completion
        
        print()
        print("Press Ctrl+C to stop monitoring")
    
    def run_monitor(self, interval: int = 30):
        """Run the monitoring loop"""
        try:
            while True:
                self.display_progress()
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n\n👋 Monitoring stopped.")
            stats = self.get_completion_stats()
            print(f"Final status: {stats['completion_rate']:.1f}% complete")

def main():
    import sys
    
    interval = 30  # Default 30 seconds
    if len(sys.argv) > 1:
        try:
            interval = int(sys.argv[1])
        except ValueError:
            print("Usage: python monitor_progress.py [interval_seconds]")
            sys.exit(1)
    
    monitor = ProgressMonitor()
    print(f"Starting progress monitor (checking every {interval} seconds)...")
    time.sleep(2)
    monitor.run_monitor(interval)

if __name__ == "__main__":
    main() 