# calculate_reimbursement.py
#
# Wrapper the evaluator will run:
#   python calculate_reimbursement.py <days> <miles> <receipts>

import sys
from pathlib import Path
# Use the rules engine
from rules_engine import load_engine, predict_amount

def main() -> None:
    if len(sys.argv) != 4:
        print("Usage: calculate_reimbursement.py <days> <miles> <receipts>", file=sys.stderr)
        sys.exit(1)

    try:
        days     = int(sys.argv[1])
        miles    = float(sys.argv[2])
        receipts = float(sys.argv[3])
    except ValueError:
        print("All three arguments must be numeric.", file=sys.stderr)
        sys.exit(2)

    # Load the rules engine and make prediction
    engine = load_engine()
    amount = predict_amount(engine, days, miles, receipts)
    print(f"{amount:.2f}")          # ← single number, no extra text

if __name__ == "__main__":
    main()
