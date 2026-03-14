# Compliance Runner : this will be the main class that runs all the evaluators and collects their results

from policy_rules_model import PolicyRuleType
from evaluators.registry import REGISTRY

SKIP_FOR_LARGE_SAMPLES = {PolicyRuleType.CHAIN}

async def run_compliance(rules, transactions) :

    """Main function to run all compliance checks.
    For each rule, it finds the appropriate evaluator from the registry,
      runs the evaluation, and collects all alerts."""

    all_alerts = []   # this will collect all alerts from all evaluators

    for rule in rules :
        
        if len(transactions) > 2000 and rule.rule_type in SKIP_FOR_LARGE_SAMPLES:
            continue # skip certain rules for large samples to save time
        evaluator = REGISTRY[rule.rule_type](rule)  # get the appropriate evaluator for this rule

        alerts = await evaluator.evaluate(transactions) # run the evaluation and collect alerts

        all_alerts.extend(alerts)  # aggregate alerts from all rules

    return all_alerts
    

    