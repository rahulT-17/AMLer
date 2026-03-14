# Registry : this will maintain a registry of all the evaluators and their corresponding rules, and provide an interface to access them.
from policy_rules_model import PolicyRuleType
from .bipartite import BipartiteEvaluator
from .threshold import ThresholdEvaluator
from .format import FormatEvaluator
from .frequency import FrequencyEvaluator
from .chain import ChainEvaluator
from .graph import GraphEvaluator
from .correlation import CorrelationEvaluator

REGISTRY = {
    PolicyRuleType.BIPARTITE : BipartiteEvaluator,
    PolicyRuleType.THRESHOLD : ThresholdEvaluator,
    PolicyRuleType.FORMAT : FormatEvaluator,
    PolicyRuleType.FREQUENCY : FrequencyEvaluator,
    PolicyRuleType.CHAIN : ChainEvaluator,
    PolicyRuleType.GRAPH : GraphEvaluator,
    PolicyRuleType.CORRELATION : CorrelationEvaluator
}

