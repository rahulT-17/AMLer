# typology : this file defines the typology classification logic based on the rules that were triggered for a transaction
from datetime import datetime, timedelta   
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
            transactions=[a['transaction'] for a in account_alerts if a.get('transaction')],
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
    
    # SMURFING — tighteng structuring definition with ACH + fan-out to multiple accounts
    if "ach_format_detection" in rules and "fan_out_detection" in rules:
        return "SMURFING"
    
    # STRUCTURING — multiple transactions just under reporting threshold within short time window

    # creating a list of transactions that triggered structuring rules, sorted by timestamp:
    band_txns = []

    
    for txn in result.transactions:       # loop through all transactions that triggered alerts for this account
        try :
            amount = float(txn.get('amount_paid', 0))    # if amount is missing or not a number, skip this transaction
        except (ValueError, TypeError):
            continue

        if 8000 <= amount <= 9999:                      # if amount is just under reporting threshold, consider it for structuring typology
            timestamp_str = txn.get('timestamp')         # if timestamp is missing, skip this transaction as we cannot determine if they are within the time window for structuring
            if not timestamp_str:
                continue
            
            try:
                timestamp = datetime.strptime(timestamp_str, "%Y/%m/%d %H:%M")      # parse transaction timestamp
            except ValueError:
                continue

            band_txns.append((timestamp, txn))

    band_txns.sort(key=lambda x: x[0])      # sort transactions by timestamp

    window_size = 3                         # we need at least 3 transactions just under the threshold within the time window to consider it structuring
    time_window = timedelta(hours=24)

    for i in range(len(band_txns) - window_size + 1):        # slide a window of size 3 over the transactions and check if they are within the time window for structuring
        
        start_time = band_txns[i][0]                           # timestamp of the first transaction in the window
        end_time = band_txns[i + window_size - 1][0]           # timestamp of the last transaction in the window

        if end_time - start_time <= time_window:
            return "STRUCTURING"
        
    # PLACEMENT — ACH alone, direct placement into financial system
    #if "ach_format_detection" in rules :
        #sif result.total_amount_flagged > 5000:  # arbitrary threshold for weak signal
            return "PLACEMENT"
    
    
    
    return "UNKNOWN"



# STRUCTURING - both bounds + ACH + minimum 3 transactions :
    if ("structuring_lower_bound" in rules and 
        "structuring_upper_bound" in rules and 
        "ach_format_detection" in rules) :
        structuring_count = sum(1 for a in result.alerts if a.get('rule_name') 
                                in ["structuring_lower_bound", "structuring_upper_bound"]
        )

        if structuring_count >= 3:
            return "STRUCTURING"
        
    # WEAK STRUCTURING — both bounds triggered, amount just under reporting threshold
    if "structuring_lower_bound" in rules and "structuring_upper_bound" in rules:
        return "STRUCTURING"