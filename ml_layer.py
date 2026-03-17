# ml.layer.py : this file defines the ML layer which is using a isolation forest model to detect anomalies in the transactions and generate alerts based on the rules defined in the rules.py file

from datetime import datetime, timedelta

import pandas as pd
from sklearn.ensemble import IsolationForest


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def _parse_timestamp(value):
    if not value :
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M")
    except ValueError:
        return None

def _max_txns_in_24h (timestamps):
    timestamps = sorted(ts for ts in timestamps if ts is not None)
    best = 0
    left = 0

    for right in range(len(timestamps)):
        while timestamps[right] - timestamps[left] > timedelta(hours=24):
            left += 1
        best = max(best, right - left + 1)

    return best

def build_account_feature_frame(grouped):
    rows = []

    for account, result in grouped.items():
        txns = result.transactions
        amounts = [_safe_float(t.get("amount_paid")) for t in txns]
        timestamps = [_parse_timestamp(t.get("timestamp")) for t in txns]

        near_threshold_count = sum(1 for amt in amounts if 8000 <= amt <= 9999)
        ach_count = sum(1 for t in txns if t.get("payment_format") == "ACH")
        counterparties = {
            t.get("account.1")
            for t in txns
            if t.get("account.1")
        }

        rows.append({
            "account": account,
            "transaction_count": len(txns),
            "alert_count": len(result.alerts),
            "rule_count": len(result.rule_names_fired),
            "total_amount_flagged": result.total_amount_flagged,
            "avg_amount": sum(amounts) / len(amounts) if amounts else 0.0,
            "max_amount": max(amounts) if amounts else 0.0,
            "near_threshold_count": near_threshold_count,
            "near_threshold_ratio": near_threshold_count / len(txns) if txns else 0.0,
            "ach_count": ach_count,
            "ach_ratio": ach_count / len(txns) if txns else 0.0,
            "distinct_counterparties": len(counterparties),
            "max_txns_24h": _max_txns_in_24h(timestamps),
            "has_cycle": int("cycle_detection" in result.rule_names_fired),
            "has_fan_out": int("fan_out_detection" in result.rule_names_fired),
            "has_ach_rule": int("ach_format_detection" in result.rule_names_fired),
            "label": int(any(t.get("is_laundering") == 1 for t in txns)),
        })

    df = pd.DataFrame(rows).set_index("account")
    return df


def score_accounts_with_isolation_forest(feature_df, contamination=0.15, random_state=42):
    model_input = feature_df.drop(columns=["label"], errors="ignore")

    model = IsolationForest(
        n_estimators=200,
        contamination=contamination,
        random_state=random_state,
    )
    model.fit(model_input)

    raw_scores = -model.score_samples(model_input)
    score_series = pd.Series(raw_scores, index=model_input.index)

    min_score = score_series.min()
    max_score = score_series.max()

    if max_score > min_score:
        score_series = (score_series - min_score) / (max_score - min_score)
    else:
        score_series = score_series * 0

    return score_series.to_dict()


def derive_ml_reason_signals(result):
    signals = []

    txns = result.transactions

    if len(txns) >= 5:
        signals.append("many suspicious transaction count")

    near_threshold_count = 0
    ach_count = 0
    counterparties = set()

    for txn in txns:
        amount = _safe_float(txn.get("amount_paid"))
        if 8000 <= amount <= 9999:
            near_threshold_count += 1

        if txn.get("payment_format") == "ACH":
            ach_count += 1
        counterparty = txn.get("account.1")
        if txn.get("account.1"):
            counterparties.add(txn.get("account.1"))

    if near_threshold_count >= 3:
        signals.append("multiple transactions just under reporting threshold")

    if ach_count >= 3:
        signals.append("Heavy ACH transactions")

    if len(counterparties) >= 5:
        signals.append("many distinct counterparties")
    
    if "cycle_detection" in result.rule_names_fired:
        signals.append("possible cycle detected")

    return signals


def enrich_grouped_with_ml(grouped, contamination=0.15):
    
    if not grouped:
        return grouped                    # handle edge case 
    
    feature_df = build_account_feature_frame(grouped)

    scores = score_accounts_with_isolation_forest(
        feature_df, 
        contamination=contamination
    )

    for account, result in grouped.items():

        score = scores.get(account, 0.0)
        result.ml_anomaly_score = score

        if score > 0.75 :
            result.ml_priority = "HIGH"

        elif score > 0.45 :
            result.ml_priority = "MEDIUM"
        
        else:
            result.ml_priority = "LOW"

        result.ml_reason_signals = derive_ml_reason_signals(result)

    return grouped