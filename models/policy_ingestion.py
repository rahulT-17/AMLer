"""These models define the policy-ingestion layer of the system.

PolicyClause stores raw traceable text extracted from a PDF policy document.

ExtractedPolicyRule stores the structured candidate rule derived from that clause.
We keep this separate from the live DB rule models so we can review, shadow-test,
and approve rules safely before they affect the main compliance engine. """

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

class PolicyRuleLifecycle(str, Enum) :
    DRAFT = "DRAFT"
    SHADOW = "SHADOW"
    ACTIVE = "ACTIVE"
    REJECTED = "REJECTED"

@dataclass
class PolicyClause :
   clause_id : str 
   text : str
   source_document : str
   page_number : Optional[int] = None
   section_heading : Optional[str] = None



@dataclass
class ExtractedPolicyRule:

    name : str 
    rule_type : str
    source_text : str
    source_document : str
    severity : Optional[str] = None
    status : PolicyRuleLifecycle = PolicyRuleLifecycle.DRAFT
    page_number : Optional[int] = None
    section_heading : Optional[str] = None
    
    
    # Threshold-specific fields
    field_target : Optional[str] = None
    operator : Optional[str] = None
    threshold_value : Optional[str] = None
    
    # Format-specific fields
    pattern : Optional[str] = None

    # Frequency-specific fields
    group_by_field : Optional[str] = None
    min_count : Optional[int] = None
    time_window_hours : Optional[int] = None

    # Chain-rule specific fields
    min_hops : Optional[int] = None
    max_hops : Optional[int] = None
    detect_cycles : Optional[bool] = None
    
    metadata: dict[str, Any] = field(default_factory=dict)