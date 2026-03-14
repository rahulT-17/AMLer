# Hackathon Session — Rule Schema Design
**VIT Code Apex 2.0 | Track 2, PS3: Data Policy Compliance Agent**
**Dataset: IBM AML HI-Small (financial transaction anomaly detection)**

---

## 1. The 8 AML Transaction Patterns

| # | Pattern | Structure | Key Trait |
|---|---------|-----------|-----------|
| 1 | FAN-OUT | A → B1, B2...BN | One sender, N distinct receivers |
| 2 | FAN-IN | A1, A2...AN → B | N distinct senders, one receiver |
| 3 | CYCLE | A → B → C → ... → A | Money returns to origin, currency changes each hop |
| 4 | SCATTER-GATHER | A → {B1..BN} → Z | Fan-out then fan-in, 1→N→1 diamond |
| 5 | GATHER-SCATTER | {A1..AN} → M → {Z1..ZK} | Fan-in then fan-out, M is the layering node |
| 6 | STACK | A1→B1→C1 / A2→B2→C2 ... | Parallel independent chains, coordinated |
| 7 | RANDOM | A → B → C → D... | Variable-length linear chain, 1–11 hops |
| 8 | BIPARTITE | A → B | Single transaction, often same entity |

---

## 2. Single-Transaction vs Multi-Transaction Detection

**Key question asked per pattern:** *"If I only see one transaction — can I make a call?"*

| Pattern | Single-txn detectable? | Minimum data unit needed |
|---------|------------------------|--------------------------|
| BIPARTITE | ✅ Yes | 1 row |
| FAN-OUT | ❌ No | All txns sharing sender in time window |
| FAN-IN | ❌ No | All txns sharing receiver in time window |
| CYCLE | ❌ No | Directed path A→B→...→A |
| SCATTER-GATHER | ❌ No | Diamond subgraph (path + list) |
| GATHER-SCATTER | ❌ No | Diamond subgraph (list + path) |
| STACK | ❌ No | Multiple independent chains compared together |
| RANDOM | ❌ No | Directed path of variable hops |

**Core insight:** 7 of 8 patterns require multi-row context. And the multi-row cases are NOT the same shape of data.

---

## 3. The 5 Data Shapes

| Shape | Patterns | Description |
|-------|----------|-------------|
| Single row | BIPARTITE | One transaction evaluated alone |
| Flat list | FAN-OUT, FAN-IN | All txns sharing an account within a time window |
| Directed path | CYCLE, RANDOM | Chain of hops followed sequentially |
| Diamond/subgraph | SCATTER-GATHER, GATHER-SCATTER | Fan-out + convergence combined |
| Coordinated multi-path | STACK | Multiple independent chains evaluated together for similarity |

---

## 4. Why Original 3 Rule Types Were Incomplete

Original schema had: **Threshold, Format, Frequency/Velocity**

These all operate on single transactions or flat aggregates. They have no concept of *structural shape* in the graph.

**Frequency/Velocity** does cover FAN-OUT and FAN-IN (it counts txns sharing an account in a window — same thing). But the remaining shapes have no coverage.

---

## 5. Final Rule Type System — 6 Types

| Type | Covers | What it does |
|------|--------|--------------|
| Threshold | BIPARTITE | Flags single transaction by value |
| Format | BIPARTITE | Flags single transaction by structure/format |
| Frequency/Velocity | FAN-OUT, FAN-IN | Counts txns sharing an account in a time window |
| **Chain** | CYCLE, RANDOM | Follows directed path hop by hop |
| **Graph** | SCATTER-GATHER, GATHER-SCATTER | Matches structural diamond shape in transaction network |
| **Correlation** | STACK | Detects coordination/similarity across independent chains |

---

## 6. Schema Design — Class Table Inheritance

**Why CTI?** Because base fields are universal but type-specific fields vary drastically per rule type. Flat model causes field leakage.

### Base Table — `PolicyRule`
```python
rule_id           # PK
rule_type         # Discriminator (SAEnum - determines child table)
source_text       # Human-readable rule description
severity          # Universal — every rule has consequences
time_window_hours # Most pattern detection is time-bounded
```

### Child Tables (each has FK → policy_rules.rule_id as PK)

```python
# ThresholdRule
field_target      # Which field to check (e.g. "amount")
operator          # How to compare (e.g. "greater_than")
threshold_value   # Value to compare against (e.g. 10000)

# FrequencyRule
group_by_field    # Which account field to group by (sender/receiver)
min_count         # Minimum N distinct accounts to trigger

# ChainRule
min_hops          # Minimum chain length
max_hops          # Maximum chain length
detect_cycle      # Boolean — True = must return to origin (CYCLE), False = RANDOM
amount_tolerance  # Acceptable % variation between hops

# GraphRule
min_intermediaries  # Minimum middle nodes in diamond
max_intermediaries  # Maximum middle nodes
pattern_shape       # "scatter_gather" or "gather_scatter"

# CorrelationRule
min_chains          # Minimum parallel chains to trigger
amount_tolerance    # How similar amounts must be across chains
time_gap_hours      # How close in time chains must occur
```

### SQLAlchemy CTI Setup
```python
# Base model
__mapper_args__ = {
    "polymorphic_on": rule_type,
    "polymorphic_identity": "policy_rule"
}

# Each child model
__mapper_args__ = {
    "polymorphic_identity": "threshold"  # or "frequency", "chain", "graph", "correlation"
}

# Child FK (in every child table)
rule_id = Column(Integer, ForeignKey("policy_rules.rule_id"), primary_key=True)
```

---

## 7. Key Concepts Learned This Session

- **Data vs Metadata distinction** — transaction fields (amount, sender_id) are *data*. Schema fields (field_target, operator) are *metadata* — they describe how to evaluate data.
- **Shape taxonomy** — not all multi-row rules need the same kind of data. A flat list ≠ a directed path ≠ a subgraph.
- **Field leakage** — putting type-specific fields in the base model is a design smell. CTI solves this cleanly.
- **Discriminator column** — `rule_type` doubles as the SQLAlchemy polymorphic discriminator. No need for a separate column.

---

## 8. Parked Questions (Next Session)

1. How does the evaluation engine route rules to the correct detection strategy per type?
2. How do we measure accuracy of the compliance agent against the IBM AML dataset?
   - These are two separate problems: **routing** and **evaluation**.

---

## Next Step
Write the full SQLAlchemy schema — base `PolicyRule` model first, then all 5 child models.


## Progress uptill now : 10-03-2026

**Progress Report:**
```
PHASE 1 — SCHEMA DESIGN ✅ COMPLETE
=====================================
[✅] Analyzed 8 AML transaction patterns
[✅] Classified single vs multi-transaction detection
[✅] Identified 5 distinct data shapes
[✅] Designed 6 rule types from scratch
[✅] Decided CTI architecture with justification
[✅] Wrote all 7 SQLAlchemy models
[✅] Built db.py + init_db.py
[✅] Tables live in PostgreSQL

PHASE 2 — DETECTION ENGINE 🔄 STARTING NOW
============================================
[⬜] BaseEvaluator abstract class
[⬜] 6 concrete evaluators (one per rule type)
[⬜] Evaluator registry
[⬜] Transaction loader (read IBM dataset)
[⬜] Rule loader (seed rules into DB)
[⬜] Compliance runner (apply rules → transactions)

PHASE 3 — AGENT LAYER ⬜ NOT STARTED
======================================
[⬜] Violation reporter
[⬜] FastAPI endpoints
[⬜] End-to-end test on IBM dataset
[⬜] Demo prep

# Architecture :

┌─────────────────────────────────────────────────────┐
│                   COMPLIANCE AGENT                   │
├─────────────────────────────────────────────────────┤
│                                                      │
│   CSV Loader          Rule Loader                    │
│   (IBM dataset)       (PostgreSQL)                   │
│       │                    │                         │
│       └──────────┬─────────┘                        │
│                  ▼                                   │
│          Compliance Runner                           │
│          (loads rules + transactions,                │
│           routes each rule to evaluator)             │
│                  │                                   │
│                  ▼                                   │
│         Evaluator Registry                           │
│         ┌────────────────────────┐                  │
│         │ THRESHOLD → Evaluator  │                  │
│         │ FORMAT    → Evaluator  │                  │
│         │ FREQUENCY → Evaluator  │                  │
│         │ CHAIN     → Evaluator  │                  │
│         │ GRAPH     → Evaluator  │                  │
│         │ CORRELATION→ Evaluator │                  │
│         └────────────────────────┘                  │
│                  │                                   │
│                  ▼                                   │
│         Violation Reporter                           │
│         (flags + severity output)                    │
│                  │                                   │
│                  ▼                                   │
│         FastAPI Endpoints                            │
│         (demo interface)                             │
└─────────────────────────────────────────────────────┘

update 13-03-2026 :
DONE
[✅] Schema design
[✅] Database models  
[✅] Tables in PostgreSQL
[✅] ThresholdEvaluator
[✅] FrequencyEvaluator
[✅] ChainEvaluator
[✅] FormatEvaluator
[✅] Graph + Correlation stubs
[✅] Registry
[✅] Transaction loader

REMAINING
[⬜] Compliance runner     ← writing now (30 mins)
[⬜] Rule seeder           ← inserts test rules into DB (30 mins)
[⬜] LLM layer             ← reasons over violations (1 hour)
[⬜] FastAPI endpoints     ← exposes everything (45 mins)
[⬜] End to end test       ← full pipeline on IBM data (1 hour)
[⬜] Demo prep             ← (30 mins)


bugs faced during the test the compliance runner and main :
