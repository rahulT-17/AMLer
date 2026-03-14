# PolicyRules / this file will hold the schema for policy rules and the database model 

import enum
from sqlalchemy import  Boolean, Column, Integer, Float, ForeignKey, Text , Enum as SAEnum
from db import Base

class PolicyRuleType(enum.Enum) :
    BIPARTITE = "BIPARTITE"
    THRESHOLD = "THRESHOLD"
    FORMAT = "FORMAT"
    FREQUENCY = "FREQUENCY"
    CHAIN = "CHAIN"
    GRAPH = "GRAPH"
    CORRELATION = "CORRELATION"

class PolicyRule(Base) :
    __tablename__ = "policy_rules"

    __mapper_args__ = {
    "polymorphic_on": "rule_type",
    "polymorphic_identity": "policy_rule"
   }
    name = Column(Text, nullable=False, default="Unnamed Rule") # human readable name for the rule
    rule_id = Column(Integer, primary_key=True, index=True)
    rule_type = Column(SAEnum(PolicyRuleType), nullable=False) # discriminator for the type of rule

    source_text = Column(Text) # human readable description of the rule
    severity = Column(Text)     # univseral severity level for the rule (e.g. LOW, MEDIUM, HIGH)
  
    time_window_hours = Column(Integer)      # Most pattern detection is rule-based

class BipartiteRule(PolicyRule) :  
    __tablename__ = "bipartite_rules"

    __mapper_args__ = {
    "polymorphic_identity": PolicyRuleType.BIPARTITE
    }

    rule_id = Column(Integer, ForeignKey('policy_rules.rule_id'), primary_key=True)
    check_type = Column(Text, nullable=False) 
    
class ThresholdRule(PolicyRule) :

    __tablename__ = "threshold_rules"
    __mapper_args__ = {
    "polymorphic_identity": PolicyRuleType.THRESHOLD
    }
    rule_id = Column(Integer, ForeignKey('policy_rules.rule_id'), primary_key=True)

    field_target = Column(Text, nullable=False) # which field to checl (eg.amount, transaction count, etc) 

    operator = Column(Text, nullable=False) # How to compare the field to the threshold (e.g. >, <, >=, <=, ==, !=)

    threshold_value = Column(Text, nullable=False) # Value to compare againt

class FormatRule(PolicyRule) :
    __tablename__ = "format_rules"
    __mapper_args__ = {
    "polymorphic_identity": PolicyRuleType.FORMAT
    }

    rule_id = Column(Integer, ForeignKey('policy_rules.rule_id'), primary_key=True)
    field_target = Column(Text, nullable=False) # which field validate against
    pattern = Column(Text, nullable=False) # regex pattern to expected format

class FrequencyRule(PolicyRule) :

    __tablename__ = "frequency_rules"
    __mapper_args__ = {
    "polymorphic_identity": PolicyRuleType.FREQUENCY
    }

    rule_id = Column(Integer, ForeignKey('policy_rules.rule_id'), primary_key=True)
    group_by_field = Column(Text, nullable=False)   # Which account field to group by (sender/receiver)
    min_count = Column(Integer, nullable=False)     # Minimum N distinct accounts to trigger

class ChainRule(PolicyRule) :

    __tablename__ = "chain_rules"
    __mapper_args__ = {
    "polymorphic_identity": PolicyRuleType.CHAIN
    }

    rule_id = Column(Integer, ForeignKey('policy_rules.rule_id'), primary_key=True)
    min_hops = Column(Integer, nullable=False)   # Minimun chain length to trigger
    max_hops = Column(Integer, nullable=False)   # Maximum chain length to trigger
    detect_cycles = Column(Boolean, nullable=False, default=False)    # Boolean — True = must return to origin (CYCLE), False = RANDOM
    amount_tolerance = Column(Float)  # # Acceptable % variation between hops

class GraphRule(PolicyRule) :

    __tablename__ = "graph_rules"

    __mapper_args__ = {
    "polymorphic_identity": PolicyRuleType.GRAPH 
    }

    rule_id = Column(Integer, ForeignKey('policy_rules.rule_id'), primary_key=True)
    min_intermediaries = Column(Integer, nullable=False) # minimum middle nodes in diamond 
    max_intermediaries = Column(Integer, nullable=False) # maximum middle nodes 
    pattern_shape = Column(Text, nullable=False)  # scatter gather or gather scatter

class CorrelationRule(PolicyRule) :

    __tablename__ = "correlation_rules"

    __mapper_args__ = {
    "polymorphic_identity": PolicyRuleType.CORRELATION
    }

    rule_id = Column(Integer, ForeignKey('policy_rules.rule_id'), primary_key=True)
    min_chains = Column(Integer, nullable=False)      # minimum parallel chains to trigger
    amount_tolerance = Column(Float)   # How similar the amounts must be across chains (e.g. 10% variation allowed)
    time_gap_hours = Column(Integer)   # How close in time the chains must occur (e.g. within 24 hours)
