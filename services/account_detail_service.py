# services/account_detail_services.py : 

# import libraries:
from sqlalchemy import select
from collections import defaultdict

# import models and services:
from core.db import AsyncSessionLocal
from policy_rules_model import PolicyRule
from transaction_loader import load_transactions
from compliance.compliance_runner import run_compliance

# Additional imports for typology and ML enrichment:
from typology import group_alerts_by_account
from ml_layer import enrich_grouped_with_ml


async def load_grouped_results(sample: int):
    transactions = load_transactions(sample=sample)

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(PolicyRule))
        rules = result.scalars().all()
        loaded_rules = []
        for rule in rules:
            await session.refresh(rule)
            loaded_rules.append(rule)

        alerts = await run_compliance(loaded_rules, transactions)

    grouped = group_alerts_by_account(alerts)
    grouped = enrich_grouped_with_ml(grouped)

    return grouped


def build_account_graph_payload(result):
    selected_account = result.account
    nodes = {}
    edge_groups = defaultdict(lambda: {"count": 0, "total_amount": 0.0, "timestamps": []})

    nodes[selected_account] = {
        "id": selected_account,
        "label": selected_account,
        "title": "Selected suspicious account",
        "color": "#E24B4A",
        "size": 30
    }

    for txn in result.transactions:
        sender = txn.get("account")
        receiver = txn.get("account.1")
        amount = txn.get("amount_paid", 0)
        timestamp = txn.get("timestamp", "Unknown time")

        if not sender or not receiver:
            continue

        if sender not in nodes:
            nodes[sender] = {
                "id": sender,
                "label": sender,
                "title": f"Account: {sender}",
                "color": "#CBD5E1",
                "size": 10
            }

        if receiver not in nodes:
            nodes[receiver] = {
                "id": receiver,
                "label": receiver,
                "title": f"Account: {receiver}",
                "color": "#CBD5E1",
                "size": 10
            }
        
        try:
            numeric_amount = float(amount)
        except (TypeError, ValueError):
            numeric_amount = 0.0

        edge_key = (sender, receiver)
        edge_groups[edge_key]["count"] += 1
        edge_groups[edge_key]["total_amount"] += numeric_amount
        edge_groups[edge_key]["timestamps"].append(timestamp)

    edges = []
    for (sender, receiver), edge_data in edge_groups.items():
        latest_timestamp = edge_data["timestamps"][-1] if edge_data["timestamps"] else "Unknown time"
        transfer_count = edge_data["count"]
        total_amount = edge_data["total_amount"]

        edges.append(
            {
                "from": sender,
                "to": receiver,
                "label": f"{transfer_count} txns",
                "title": (
                    f"Suspicious transfers: {transfer_count} | "
                    f"Total amount: ${total_amount:,.2f} | "
                    f"Latest time: {latest_timestamp}"
                ),
                "value": max(total_amount, 1),
                "transaction_count": transfer_count,
                "total_amount": total_amount,
            }
        )

    return {
        "account": selected_account,
        "nodes": list(nodes.values()),
        "edges": edges,
    }
