# typology : this file defines the typology classification logic based on the rules that were triggered for a transaction

from models.transaction_result import TransactionResult

# group alerts by account and classify typology based on the combination of rules triggered :

def group_alerts_by_account(alerts) -> dict[str, TransactionResult] :

   # PART 1 — build groups
    account_groups = {}
    for alert in alerts:
        transaction = alert.get('transaction')

        if transaction :
            # threshold, format, chain, bipartite alerts
           account = transaction.get('account')
        else:
           # frequency alerts have account directly
           account = alert.get('account')

        if not account:
            continue

        if account not in account_groups:
            account_groups[account] = []
        account_groups[account].append(alert)

    # PART 2 — convert to TransactionResult
    results = {}
    for account, account_alerts in account_groups.items():
        result = TransactionResult(
            account=account,
            alerts=account_alerts,
            rule_names_fired=list(set(
                a.get('rule_name', '') for a in account_alerts
            )),
            total_amount_flagged=sum(
                a['transaction'].get('amount_paid', 0)
                for a in account_alerts
                if a.get('transaction')
            )
        )
        result.typology = detect_typology(result)
        results[account] = result

    print(f"account_groups size: {len(account_groups)}")
    print(f"results size: {len(results)}")

    return results


def detect_typology(result: TransactionResult) -> str :
    """Detect typology based on the combination of rules triggered for this transaction"""

    rules = set(result.rule_names_fired)

    # LAYERING — cycle detected, money moving in circles
    if "cycle_detection" in rules:
        return "LAYERING"
    
    # SMURFING — fan out + ACH, classic placement through multiple accounts
    if "ach_format_detection" in rules and "fan_out_detection" in rules:
        return "SMURFING"
    
    # STRUCTURING — both bounds triggered, amount just under reporting threshold
    if "structuring_lower_bound" in rules and "structuring_upper_bound" in rules:
        return "STRUCTURING"
    
    # PLACEMENT — ACH alone, direct placement into financial system
    if "ach_format_detection" in rules:
        return "PLACEMENT"
    
    # STRUCTURING — only one bound triggered, weaker signal
    if "structuring_lower_bound" in rules or "structuring_upper_bound" in rules:
        return "STRUCTURING"
    
    return "UNKNOWN"