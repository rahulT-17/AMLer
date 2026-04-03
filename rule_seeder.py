# Rule seeder for AMLer
# This module contains functions to seed rules into the AMLer system.


import asyncio
from sqlalchemy import select
from policy_rules_model import PolicyRule
from core.db import AsyncSessionLocal 
from policy_rules_model import (
    BipartiteRule, PolicyRuleType, ThresholdRule, FormatRule, FrequencyRule, ChainRule
)

VALID_CURRENCIES =  (
    "US Dollar|Bitcoin|Euro|Australian Dollar|Yuan|"
    "Rupee|Mexican Peso|Yen|UK Pound|Ruble|"
    "Canadian Dollar|Swiss Franc|Brazil Real|Saudi Riyal|Shekel"
)

async def seed_rules() :
    async with AsyncSessionLocal() as session :
        
        result = await session.execute(select(PolicyRule.name))
        existing_rule_names = set(result.scalars().all())

        bipartite = BipartiteRule(
            name = "bipartite",
            rule_type=PolicyRuleType.BIPARTITE,
            source_text="Unusual relationship between sender and receiver accounts",
            severity="MEDIUM",
            time_window_hours=48,
            check_type= "both"
        )


        # rule 1 : THRESHOLD rule for transaction amount
        structuring_a  = ThresholdRule(
            name="structuring_lower_bound",
            rule_type=PolicyRuleType.THRESHOLD,
            source_text="Structuring â€” amount just under reporting threshold",
            severity="HIGH",
            field_target="amount_paid",
            operator=">=",
            threshold_value="8000"
        )

        structuring_b = ThresholdRule(
        name="structuring_upper_bound",
        rule_type=PolicyRuleType.THRESHOLD,
        source_text="Structuring â€” amount just under reporting threshold",
        severity="HIGH",
        field_target="amount_paid",
        operator="<=",
        threshold_value="9999"
)

        # rule 2 : ACH FORMAT rule 
        ach_format = FormatRule(
            name="ach_format_detection",
            rule_type=PolicyRuleType.FORMAT,
            source_text="ACH payment format flagged â€” primary laundering vector",
            severity="HIGH",
            time_window_hours=None,
            field_target="payment_currency",
            pattern=f"ACH$"
        )

        # rule 3 : FREQUENCY rule 
        frequency_rule = FrequencyRule(
            name="fan_out_detection",
            rule_type="FREQUENCY",
            source_text="Account sending to more than 4 distinct accounts within 24 hours",
            severity="HIGH",
            time_window_hours=24,
            group_by_field="account",
            min_count=4
        )

        # rule 4 : CHAIN rule (looking for cycles of money movement)
        chain =  ChainRule(
            name="cycle_detection",
            rule_type="CHAIN",
            source_text="Cycle detected â€” money returned to origin account",
            severity="HIGH",
            time_window_hours=72,
            min_hops=2,
            max_hops=12,
            detect_cycles=True,
            amount_tolerance=0.1
        )
        seed_rules = [structuring_a, structuring_b, ach_format, frequency_rule, bipartite, chain]

        new_rules = [rule for rule in seed_rules if rule.name not in existing_rule_names]

        if not new_rules:
            print("No new rules to seed.")
            return
        session.add_all(new_rules)
        await session.commit() 
        print(f"Seeded {len(new_rules)} new rules.")

if __name__ == "__main__":
    asyncio.run(seed_rules())
