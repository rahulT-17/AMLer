# # evaluate.py — measures accuracy of the compliance agent against ground truth

import asyncio
from collections import Counter
from sqlalchemy import select
from db import AsyncSessionLocal
from policy_rules_model import PolicyRule
from transaction_loader import load_transactions
from compliance.compliance_runner import run_compliance

async def evaluate() :
  
      # STEP 1 — load mixed sample with guaranteed laundering

      transactions = load_transactions(sample=1000)
      laundering_in_sample = sum(1 for t in transactions if t['is_laundering'] == 1)
      print(f"sample size: {len(transactions)}")
      print(f"laundering in sample: {laundering_in_sample}")

      async with AsyncSessionLocal() as session:
            
            # step 2 load rules from DB
            
            result = await session.execute(select(PolicyRule))
            rules = result.scalars().all()
        
            # eager load all attributes before session closes
            loaded_rules = []
            for rule in rules:
                await session.refresh(rule)
                loaded_rules.append(rule)

             # STEP 3 — run compliance INSIDE session
            alerts = await run_compliance(loaded_rules, transactions)

            # STEP 4 — deduplicate alerts by transaction
            # one transaction can be flagged by multiple rules
            # we count each transaction only once
            seen = set()
            unique_flagged = []
            for a in alerts:
                if not a.get("transaction"):
                    continue  # skip frequency alerts — no transaction attached
                txn_key = str(a['transaction'])
                if txn_key not in seen:
                    seen.add(txn_key)
                    unique_flagged.append(a)

            # STEP 5 — calculate metrics on deduplicated transactions
            tp = len([a for a in unique_flagged if a['transaction']['is_laundering'] == 1])
            fp = len([a for a in unique_flagged if a['transaction']['is_laundering'] == 0])
            total_flagged = len(unique_flagged)

            fp_rule_names = [a.get('rule_name', f'rule_{a["rule_id"]}') 
                 for a in unique_flagged 
                 if a['transaction']['is_laundering'] == 0]
            
            precision = tp / total_flagged if total_flagged else 0
            recall    = tp / laundering_in_sample if laundering_in_sample else 0
            f1        = 2 * (precision * recall) / (precision + recall) if (precision + recall) else 0

            print("=" * 50)
            print("COMPLIANCE AGENT EVALUATION REPORT")
            print("=" * 50)
            print(f"Total alerts fired:  {len(alerts)}")
            print(f"True positives:      {tp}")
            print(f"False positives:     {fp}")
            print(f"Precision:           {precision:.3f}")
            print(f"Recall:              {recall:.3f}")
            print(f"F1 Score:            {f1:.3f}")
            print("=" * 50)
            print("False positives by rule:")
            for rule_name, count in Counter(fp_rule_names).most_common():
                print(f"  {rule_name}: {count} false positives")
            print("=" * 50)

if __name__ == "__main__":
    asyncio.run(evaluate())


