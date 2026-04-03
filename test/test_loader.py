# test/test_loader.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from transaction_loader import load_transactions

transactions = load_transactions(sample=1000)
print(transactions[5])
print(f"Total loaded: {len(transactions)}")
print(f"Columns: {list(transactions[0].keys())}")