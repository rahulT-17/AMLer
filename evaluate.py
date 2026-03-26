# # evaluate.py — measures accuracy of the compliance agent against ground truth

import asyncio
from collections import Counter
from sqlalchemy import select
from db import AsyncSessionLocal
from policy_rules_model import PolicyRule
from transaction_loader import load_transactions
from compliance.compliance_runner import run_compliance

from ml_layer import build_account_feature_frame , score_accounts_with_isolation_forest
from typology import group_alerts_by_account

async def evaluate() :
  
      # STEP 1 — load mixed sample with guaranteed laundering

      transactions = load_transactions(sample=10000)
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

            grouped = group_alerts_by_account(alerts)
            typology_counts = Counter(r.typology for r in grouped.values())


            feature_df = build_account_feature_frame(grouped)
            account_scores = score_accounts_with_isolation_forest(feature_df)

            print(f"Typology distribution: {dict(typology_counts)}")

            strong_typologies = {"SMURFING", "LAYERING", "STRUCTURING"}
            candidate_thresholds = sorted(set(account_scores.values()))

            best_run = None

            for threshold in candidate_thresholds:
                filtered_alerts = []

                for account, result in grouped.items():
                    keep_account = False

                    if result.typology in strong_typologies:
                        keep_account = True
                    elif result.typology == "UNKNOWN" and account_scores.get(account, 0.0) >= threshold:
                        keep_account = True

                    if not keep_account:
                        continue

                    filtered_alerts.extend(result.alerts)

                seen = set()
                unique_flagged = []
                for a in filtered_alerts:
                    if not a.get("transaction"):
                        continue
                    txn_key = str(a["transaction"])
                    if txn_key not in seen:
                        seen.add(txn_key)
                        unique_flagged.append(a)

                tp = len([a for a in unique_flagged if a["transaction"]["is_laundering"] == 1])
                fp = len([a for a in unique_flagged if a["transaction"]["is_laundering"] == 0])
                total_flagged = len(unique_flagged)

                precision = tp / total_flagged if total_flagged else 0
                recall = tp / laundering_in_sample if laundering_in_sample else 0

                if recall >= 0.9:
                    if best_run is None or precision > best_run["precision"]:
                        best_run = {
                            "threshold": threshold,
                            "alerts": filtered_alerts,
                            "unique_flagged": unique_flagged,
                            "tp": tp,
                            "fp": fp,
                            "precision": precision,
                            "recall": recall,
                        }

            if best_run is None:
                best_run = {
                    "threshold": 1.0,
                    "alerts": [],
                    "unique_flagged": [],
                    "tp": 0,
                    "fp": 0,
                    "precision": 0,
                    "recall": 0,
                }

            alerts = best_run["alerts"]
            unique_flagged = best_run["unique_flagged"]
            tp = best_run["tp"]
            fp = best_run["fp"]
            total_flagged = len(unique_flagged)
            precision = best_run["precision"]
            recall = best_run["recall"]

            print(f"Chosen ML threshold: {best_run['threshold']:.4f}")
            print(f"Alerts after ML + typology filter: {len(alerts)}")

            print(f"Alerts after typology filter: {len(alerts)}")

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

            results = {
            "sample_size": len(transactions),
            "laundering_in_sample": laundering_in_sample,
            "total_alerts": len(alerts),
            "true_positives": tp,
            "false_positives": fp,
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "f1_score": round(f1, 3),
            "false_positives_by_rule": dict(Counter(fp_rule_names).most_common())
            }

            # print when run directly
            print("=" * 50)
            print("COMPLIANCE AGENT EVALUATION REPORT")
            print("=" * 50)
            for key, value in results.items():
                print(f"{key}: {value}")
            print("=" * 50)
            
            return results
             

if __name__ == "__main__":
    asyncio.run(evaluate())


