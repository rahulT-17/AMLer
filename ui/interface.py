from pathlib import Path
import sys
import tempfile

# Streamlit runs this file from inside the ui/ folder context, so we add the
# project root explicitly to Python's import path. This keeps imports like
# `settings` and `policy_extraction` stable without requiring a manual
# PYTHONPATH export every time.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import requests
import streamlit as st
import streamlit.components.v1 as components
from pyvis.network import Network

from policy_extraction import extract_rules_from_clauses
from policy_ingestion_service import build_policy_clauses, extract_pdf_pages
from core.config import settings


API = settings.api_base_url
DEFAULT_SAMPLE_SIZE = settings.default_sample_size
LLM_ENABLED = settings.llm_enabled
PAGES = ["Run Analysis", "Transaction Feed", "Account Detail", "Evaluation", "Policy Ingestion"]


st.set_page_config(
    page_title="AMLer",
    page_icon="A",
    layout="wide",
)


def init_state():
    defaults = {
        "page": "Run Analysis",
        "analysis_data": None,
        "evaluation_data": None,
        "policy_data": None,
        "llm_account_summaries": {},
        "account_graphs": {},
        "selected_account": None,
        "sample_size": DEFAULT_SAMPLE_SIZE,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def inject_css():
    st.markdown(
        """
<style>
:root {
  --bg-page: #f6f7f9;
  --bg-panel: #ffffff;
  --bg-soft: #f3f4f6;
  --text-main: #161616;
  --text-secondary: #6b7280;
  --border-soft: #e5e7eb;
  --border-strong: #d8dce3;
  --radius-md: 10px;
  --radius-lg: 16px;
  --shadow-soft: 0 12px 30px rgba(15, 23, 42, 0.06);
}

* {
  box-sizing: border-box;
}

.stApp {
  background: linear-gradient(180deg, #faf8f3 0%, var(--bg-page) 100%);
  color: var(--text-main);
}

.block-container {
  max-width: 1360px;
  padding-top: 0.75rem;
  padding-bottom: 1.5rem;
}

header[data-testid="stHeader"] {
  height: 0;
  background: transparent !important;
}

[data-testid="stToolbar"],
[data-testid="stDecoration"],
#MainMenu {
  display: none !important;
}

[data-testid="stSidebar"] {
  background: rgba(255, 255, 255, 0.9);
  border-right: 1px solid var(--border-soft);
}

[data-testid="stSidebar"] .block-container {
  padding-top: 0.95rem;
}

div[data-testid="stVerticalBlockBorderWrapper"] {
  background: rgba(255, 255, 255, 0.93);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-soft);
  padding: 1.1rem 1.2rem;
}

.mock-shell {
  min-height: 580px;
}

.sidebar-brand {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.18rem;
  margin-bottom: 1rem;
  padding: 0.15rem 0.1rem 0.25rem;
}

.sidebar-brand-kicker {
  font-size: 0.64rem;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--text-secondary);
}

.sidebar-brand-title {
  font-size: 1.18rem;
  font-weight: 700;
  letter-spacing: 0.01em;
  line-height: 1;
  color: var(--text-main);
}

.sidebar-brand-subtitle {
  font-size: 0.72rem;
  color: var(--text-secondary);
  line-height: 1.35;
}

.nav-divider {
  border-top: 1px solid var(--border-soft);
  margin: 0.9rem 0 0.85rem;
}

.nav-last-run {
  font-size: 0.68rem;
  color: var(--text-secondary);
  letter-spacing: 0.06em;
  font-weight: 700;
  margin-bottom: 0.55rem;
}

.nav-summary {
  font-size: 0.78rem;
  color: var(--text-main);
  line-height: 1.6;
}

.section-title {
  font-size: 1.08rem;
  font-weight: 600;
  margin-bottom: 0.2rem;
}

.section-subtitle {
  font-size: 0.82rem;
  color: var(--text-secondary);
}

.metric-card {
  background: var(--bg-soft);
  border-radius: var(--radius-md);
  padding: 0.8rem 0.95rem;
  border: 1px solid rgba(0, 0, 0, 0.03);
}

.metric-label {
  font-size: 0.74rem;
  color: var(--text-secondary);
  margin-bottom: 0.22rem;
}

.metric-value {
  font-size: 1.35rem;
  font-weight: 600;
  color: var(--text-main);
}

.metric-value-sm {
  font-size: 1rem;
  font-weight: 600;
}

.badge {
  display: inline-block;
  padding: 0.16rem 0.58rem;
  border-radius: 999px;
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.02em;
  white-space: nowrap;
}

.badge-critical { background: #FCEBEB; color: #A32D2D; }
.badge-high { background: #FAEEDA; color: #854F0B; }
.badge-medium { background: #E6F1FB; color: #185FA5; }
.badge-low { background: #EAF3DE; color: #3B6D11; }
.badge-smurfing { background: #EEEDFE; color: #3C3489; }
.badge-structuring { background: #FAEEDA; color: #854F0B; }
.badge-layering { background: #FCEBEB; color: #A32D2D; }
.badge-placement { background: #E6F1FB; color: #185FA5; }
.badge-unknown { background: #EDF0F5; color: #465364; }
.badge-threshold { background: #EEEDFE; color: #3C3489; }
.badge-format { background: #E1F5EE; color: #0F6E56; }
.badge-frequency { background: #E6F1FB; color: #185FA5; }
.badge-chain { background: #FAEEDA; color: #854F0B; }

.rule-tag {
  display: inline-block;
  padding: 0.18rem 0.55rem;
  border-radius: 8px;
  border: 1px solid var(--border-soft);
  background: var(--bg-soft);
  font-size: 0.7rem;
  color: var(--text-secondary);
  margin: 0.12rem 0.15rem 0.12rem 0;
}

.feed-head {
  display: grid;
  grid-template-columns: 1.5fr 1fr 0.9fr 1fr;
  gap: 0.65rem;
  padding: 0.55rem 0.8rem;
  border-bottom: 1px solid var(--border-soft);
  font-size: 0.68rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text-secondary);
  font-weight: 700;
}

.account-row-selected {
  background: #f6f7fa;
  border-radius: 10px;
  box-shadow: inset 2px 0 0 #E24B4A;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}

.dot-critical { background: #E24B4A; }
.dot-high { background: #EF9F27; }
.dot-medium { background: #378ADD; }
.dot-low { background: #639922; }

.mono {
  font-family: "Consolas", "Courier New", monospace;
}

.account-code {
  font-family: "Consolas", "Courier New", monospace;
  font-size: 0.92rem;
  font-weight: 700;
}

.progress-wrap {
  background: #edf1f4;
  border-radius: 999px;
  height: 6px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  border-radius: 999px;
}

.empty-state {
  border: 1px dashed var(--border-soft);
  border-radius: var(--radius-lg);
  background: rgba(255, 255, 255, 0.7);
  padding: 1rem;
  color: var(--text-secondary);
}

.callout {
  border: 1px solid var(--border-soft);
  border-radius: 14px;
  background: linear-gradient(180deg, #fffdf8 0%, #f8f6ef 100%);
  padding: 0.95rem 1rem;
}

.callout-title {
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: #7a5d12;
  margin-bottom: 0.3rem;
}

.callout-body {
  font-size: 0.84rem;
  line-height: 1.6;
  color: #4b5563;
}

.policy-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.85rem;
}

.policy-card {
  border: 1px solid var(--border-soft);
  border-radius: 12px;
  background: #fbfbfc;
  padding: 0.85rem 0.9rem;
  margin-bottom: 0.75rem;
}

.policy-card-title {
  font-size: 0.82rem;
  font-weight: 700;
  margin-bottom: 0.3rem;
}

.policy-card-meta {
  font-size: 0.72rem;
  color: var(--text-secondary);
  margin-bottom: 0.45rem;
}

.policy-card-body {
  font-size: 0.82rem;
  line-height: 1.55;
  color: var(--text-main);
}

.policy-card-footer {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  margin-top: 0.6rem;
}

.detail-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  border-radius: 999px;
  border: 1px solid var(--border-soft);
  background: #ffffff;
  color: #485466;
  font-size: 0.72rem;
  padding: 0.22rem 0.55rem;
}

.detail-chip strong {
  color: var(--text-main);
}

.source-chip {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  background: #eef1f5;
  color: #485466;
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  padding: 0.24rem 0.56rem;
}

.section-kicker {
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.09em;
  text-transform: uppercase;
  color: var(--text-secondary);
  margin-bottom: 0.35rem;
}

.subtle-note {
  font-size: 0.76rem;
  color: var(--text-secondary);
}

.screen-gap {
  height: 0.6rem;
}

.stButton > button {
  border-radius: 10px !important;
  border: 1px solid var(--border-soft) !important;
  background: #ffffff !important;
  color: var(--text-main) !important;
  font-weight: 600 !important;
  font-size: 0.84rem !important;
  transition: all 0.18s ease !important;
  box-shadow: none !important;
}

.stButton > button:hover {
  background: #f7f8fa !important;
  border-color: #cfd5df !important;
}

.stButton > button[kind="primary"] {
  background: #161616 !important;
  color: #ffffff !important;
  border-color: #161616 !important;
}

[data-testid="stSidebar"] .stButton > button {
  justify-content: flex-start !important;
  text-align: left !important;
  min-height: 2.35rem !important;
  padding-left: 0.85rem !important;
  background: transparent !important;
}

[data-testid="stSidebar"] .stButton > button[kind="primary"] {
  background: #f3f4f6 !important;
  color: var(--text-main) !important;
  border-color: #e5e7eb !important;
}

.stSlider label,
.stCaption,
.stMarkdown p,
.stMarkdown li,
.stMarkdown strong {
  color: var(--text-main) !important;
}

.stMarkdown p {
  line-height: 1.55;
}
</style>
""",
        unsafe_allow_html=True,
    )


def priority_badge(value):
    mapping = {
        "CRITICAL": "badge-critical",
        "HIGH": "badge-high",
        "MEDIUM": "badge-medium",
        "LOW": "badge-low",
        "UNKNOWN": "badge-unknown",
    }
    label = (value or "LOW").upper()
    css_class = mapping.get(label, "badge-low")
    return f"<span class='badge {css_class}'>{label}</span>"


def typology_badge(value):
    mapping = {
        "SMURFING": "badge-smurfing",
        "STRUCTURING": "badge-structuring",
        "LAYERING": "badge-layering",
        "PLACEMENT": "badge-placement",
        "UNKNOWN": "badge-unknown",
    }
    label = (value or "UNKNOWN").upper()
    css_class = mapping.get(label, "badge-unknown")
    return f"<span class='badge {css_class}'>{label}</span>"


def rule_type_badge(value):
    mapping = {
        "THRESHOLD": "badge-threshold",
        "FORMAT": "badge-format",
        "FREQUENCY": "badge-frequency",
        "CHAIN": "badge-chain",
    }
    label = (value or "UNKNOWN").upper()
    css_class = mapping.get(label, "badge-unknown")
    return f"<span class='badge {css_class}'>{label}</span>"


def amount_text(value):
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return "$0"

    if abs(numeric) >= 1_000_000_000:
        return f"${numeric / 1_000_000_000:.1f}B"
    if abs(numeric) >= 1_000_000:
        return f"${numeric / 1_000_000:.1f}M"
    if abs(numeric) >= 1_000:
        return f"${numeric / 1_000:.1f}K"
    return f"${numeric:,.0f}"


def metric_card(label, value, accent=None):
    color_style = f"color:{accent};" if accent else ""
    return f"""
    <div class="metric-card">
      <div class="metric-label">{label}</div>
      <div class="metric-value" style="{color_style}">{value}</div>
    </div>
    """


def progress_bar(label, value, max_value, color, value_text=None):
    safe_max = max(max_value, 1)
    pct = min(max((value / safe_max) * 100, 0), 100)
    shown_value = value_text if value_text is not None else str(value)
    return f"""
    <div style="margin-bottom:0.8rem;">
      <div style="display:flex;justify-content:space-between;font-size:0.76rem;margin-bottom:0.25rem;">
        <span>{label}</span>
        <span class="subtle-note">{shown_value}</span>
      </div>
      <div class="progress-wrap">
        <div class="progress-fill" style="width:{pct:.2f}%; background:{color};"></div>
      </div>
    </div>
    """


def policy_rule_metric_card(label, value):
    return f"""
    <div class="metric-card">
      <div class="metric-label">{label}</div>
      <div class="metric-value-sm">{value}</div>
    </div>
    """


def callout_card(title, body):
    return f"""
    <div class="callout">
      <div class="callout-title">{title}</div>
      <div class="callout-body">{body}</div>
    </div>
    """


def sort_accounts(accounts):
    return sorted(
        accounts or [],
        key=lambda item: (
            item.get("ml_anomaly_score") if item.get("ml_anomaly_score") is not None else 0.0,
            item.get("total_flagged", 0),
        ),
        reverse=True,
    )


def get_selected_account(analysis_data):
    accounts = sort_accounts((analysis_data or {}).get("all_accounts", []))
    if not accounts:
        return None

    selected_id = st.session_state.get("selected_account")
    if selected_id:
        for account in accounts:
            if account.get("account") == selected_id:
                return account

    return accounts[0]


def get_high_priority_map(analysis_data):
    items = (analysis_data or {}).get("high_priority_accounts", [])
    return {item.get("account"): item for item in items}


def get_llm_account_summary_map():
    return st.session_state.get("llm_account_summaries", {})


def get_account_graph_map():
    return st.session_state.get("account_graphs", {})


def run_analysis_request(sample_size):
    response = requests.post(
        f"{API}/analyze",
        params={"sample": int(sample_size)},
        timeout=240,
    )
    response.raise_for_status()
    return response.json()


def run_evaluation_request():
    response = requests.get(f"{API}/evaluate", timeout=240)
    response.raise_for_status()
    return response.json()


def run_account_analysis_request(selected_account):
    # We send the already-ranked account summary back to the API so the detail
    # page can request an explanation on demand without rerunning the whole
    # analysis pipeline.
    payload = {
        "account": selected_account.get("account"),
        "typology": selected_account.get("typology"),
        "rules_fired": selected_account.get("rules_fired", []),
        "total_flagged": float(selected_account.get("total_flagged", 0) or 0),
        "alert_count": int(selected_account.get("alert_count", 0) or 0),
        "ml_anomaly_score": selected_account.get("ml_anomaly_score"),
        "ml_priority": selected_account.get("ml_priority"),
        "ml_reason_signals": selected_account.get("ml_reason_signals", []),
    }

    response = requests.post(
        f"{API}/account-analysis",
        json=payload,
        timeout=240,
    )
    response.raise_for_status()
    return response.json()


def run_account_graph_request(account_id, sample_size):
    response = requests.post(
        f"{API}/account-graph",
        json={
            "account": account_id,
            "sample": int(sample_size),
        },
        timeout=240,
    )
    response.raise_for_status()
    return response.json()


def render_account_graph(graph_data):
    focus_account = graph_data.get("account")
    net = Network(
        height="420px",
        width="100%",
        directed=True,
        bgcolor="#fbfbfc",
        font_color="#161616",
    )

    for node in graph_data.get("nodes", []):
        is_focus = node["id"] == focus_account
        net.add_node(
            node["id"],
            label=node["label"],
            title=node.get("title", ""),
            color=node.get("color", "#E24B4A" if is_focus else "#CBD5E1"),
            size=node.get("size", 28 if is_focus else 18),
            borderWidth=3 if is_focus else 1.5,
            shape="dot",
        )

    for edge in graph_data.get("edges", []):
        edge_value = edge.get("value", 1)
        scaled_width = min(max(edge_value / 5000, 1.25), 8)

        net.add_edge(
            edge["from"],
            edge["to"],
            label="",
            title=edge.get("title", ""),
            value=edge_value,
            width=scaled_width,
            color="#A7B1BF",
            arrows="to",
            font={"size": 9, "color": "#5B6574", "background": "#fbfbfc"},
        )

    net.set_options(
        """
        var options = {
          "nodes": {
            "font": {
              "face": "Georgia",
              "size": 13,
              "color": "#161616"
            },
            "shadow": {
              "enabled": true,
              "color": "rgba(15, 23, 42, 0.08)",
              "size": 12,
              "x": 0,
              "y": 4
            }
          },
          "edges": {
            "smooth": {
              "enabled": true,
              "type": "cubicBezier",
              "roundness": 0.18
            },
            "shadow": {
              "enabled": false
            }
          },
          "interaction": {
            "hover": true,
            "tooltipDelay": 120,
            "navigationButtons": false
          },
          "physics": {
            "barnesHut": {
              "gravitationalConstant": -2800,
              "springLength": 145,
              "springConstant": 0.05,
              "damping": 0.14
            },
            "minVelocity": 0.75
          }
        }
        """
    )
    return net.generate_html()


def build_policy_summary(clauses, rules):
    summary = {}
    extraction_mix = {"LLM": 0, "Fallback": 0}

    for rule in rules:
        rule_type = (rule.rule_type or "UNKNOWN").upper()
        summary[rule_type] = summary.get(rule_type, 0) + 1

        if (rule.metadata or {}).get("llm_reasoning"):
            extraction_mix["LLM"] += 1
        else:
            extraction_mix["Fallback"] += 1

    return {
        "total_clauses": len(clauses),
        "total_rules": len(rules),
        "rule_breakdown": summary,
        "extraction_mix": extraction_mix,
    }


def run_policy_ingestion(pdf_path: str):
    pages = extract_pdf_pages(pdf_path)
    clauses = build_policy_clauses(pdf_path, pages)
    rules = extract_rules_from_clauses(clauses)
    summary = build_policy_summary(clauses, rules)
    return {
        "pdf_path": pdf_path,
        "pages": pages,
        "clauses": clauses,
        "rules": rules,
        "summary": summary,
    }


def switch_page(page_name):
    st.session_state["page"] = page_name
    st.rerun()


def set_selected_account(account_id):
    st.session_state["selected_account"] = account_id
    st.session_state["page"] = "Account Detail"
    st.rerun()


def render_sidebar():
    st.sidebar.markdown(
        """
        <div class='sidebar-brand'>
          <div class='sidebar-brand-kicker'>Compliance Intelligence</div>
          <div class='sidebar-brand-title'>AMLer</div>
          <div class='sidebar-brand-subtitle'>Transaction monitoring workspace</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    for page in PAGES:
        button_type = "primary" if st.session_state.get("page") == page else "secondary"
        if st.sidebar.button(page, key=f"nav_{page}", use_container_width=True, type=button_type):
            switch_page(page)

    st.sidebar.markdown("<div class='nav-divider'></div>", unsafe_allow_html=True)
    st.sidebar.markdown("<div class='nav-last-run'>LAST RUN</div>", unsafe_allow_html=True)

    analysis = st.session_state.get("analysis_data")
    if not analysis:
        st.sidebar.markdown("<div class='nav-summary'>No analysis run yet.</div>", unsafe_allow_html=True)
        return

    sorted_accounts = sort_accounts(analysis.get("all_accounts", []))
    top_account = sorted_accounts[0] if sorted_accounts else None
    critical_count = sum(
        1 for account in sorted_accounts if (account.get("ml_priority") or "").upper() == "CRITICAL"
    )

    st.sidebar.markdown(
        f"""
        <div class='nav-summary'>
          {st.session_state.get('sample_size', DEFAULT_SAMPLE_SIZE):,} transactions<br>
          {analysis.get('total_suspicious_accounts', 0):,} suspicious accounts
        </div>
        """,
        unsafe_allow_html=True,
    )

    if critical_count:
        st.sidebar.markdown(priority_badge("CRITICAL"), unsafe_allow_html=True)
        st.sidebar.caption(f"{critical_count} critical accounts")

    if top_account:
        st.sidebar.caption(f"Top account: {top_account.get('account', 'N/A')}")


def render_header(title, subtitle):
    st.markdown(
        f"""
        <div style="margin-bottom:0.95rem;">
          <div class="section-title">{title}</div>
          <div class="section-subtitle">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def rule_extraction_source(rule):
    # LLM and heuristic fallback can both create draft rules. Surfacing the
    # source helps the user understand why a rule looks more semantic or more
    # template-like.
    if (rule.metadata or {}).get("llm_reasoning"):
        return "LLM"
    return "Fallback"


def rule_detail_chips(rule):
    chips = []

    if rule.field_target:
        chips.append(f"<span class='detail-chip'><strong>Field</strong> <span class='mono'>{rule.field_target}</span></span>")
    if rule.operator:
        chips.append(f"<span class='detail-chip'><strong>Operator</strong> <span class='mono'>{rule.operator}</span></span>")
    if rule.threshold_value:
        chips.append(f"<span class='detail-chip'><strong>Threshold</strong> <span class='mono'>{rule.threshold_value}</span></span>")
    if rule.pattern:
        chips.append(f"<span class='detail-chip'><strong>Pattern</strong> <span class='mono'>{rule.pattern}</span></span>")
    if rule.group_by_field:
        chips.append(f"<span class='detail-chip'><strong>Group by</strong> <span class='mono'>{rule.group_by_field}</span></span>")
    if rule.min_count is not None:
        chips.append(f"<span class='detail-chip'><strong>Min count</strong> <span class='mono'>{rule.min_count}</span></span>")
    if rule.time_window_hours is not None:
        chips.append(f"<span class='detail-chip'><strong>Window</strong> <span class='mono'>{rule.time_window_hours}h</span></span>")

    return chips


def render_run_analysis():
    analysis = st.session_state.get("analysis_data")

    render_header(
        "Run Compliance Analysis",
        "Load IBM AML dataset and detect suspicious transaction patterns",
    )

    with st.container(border=True):
        st.markdown("**Configuration**")
        sample_size = st.slider(
            "Sample size",
            min_value=1000,
            max_value=10000,
            step=500,
            key="sample_size",
        )
        st.caption(f"Sample size - {sample_size:,} transactions")

        st.markdown("**Evaluators to run**")
        st.markdown(
            """
            <div style="display:flex;flex-wrap:wrap;gap:6px;">
              <span class="rule-tag" style="background:#EEEDFE;color:#3C3489;border-color:#AFA9EC;">Threshold</span>
              <span class="rule-tag" style="background:#E1F5EE;color:#0F6E56;border-color:#5DCAA5;">Format (ACH)</span>
              <span class="rule-tag" style="background:#E6F1FB;color:#185FA5;border-color:#85B7EB;">Frequency</span>
              <span class="rule-tag" style="background:#FAEEDA;color:#854F0B;border-color:#EF9F27;">Chain (DFS)</span>
              <span class="rule-tag">Graph (stub)</span>
              <span class="rule-tag">Correlation (stub)</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button("Run Analysis", use_container_width=True, type="primary"):
            with st.spinner("Running compliance analysis..."):
                try:
                    analysis = run_analysis_request(sample_size)
                except requests.RequestException as exc:
                    st.error(f"Analysis request failed: {exc}")
                else:
                    st.session_state["analysis_data"] = analysis
                    st.session_state["evaluation_data"] = None
                    # Keep any precomputed top-account LLM summaries available in
                    # session state so the detail view can reuse them instantly.
                    st.session_state["llm_account_summaries"] = get_high_priority_map(analysis)
                    st.session_state["account_graphs"] = {}
                    sorted_accounts = sort_accounts(analysis.get("all_accounts", []))
                    st.session_state["selected_account"] = (
                        sorted_accounts[0]["account"] if sorted_accounts else None
                    )
                    st.success("Analysis completed successfully.")

    suspicious_accounts = analysis.get("total_suspicious_accounts", 0) if analysis else 0
    total_alerts = analysis.get("total_alerts", 0) if analysis else 0
    high_priority_count = len(analysis.get("high_priority_accounts", [])) if analysis else 0

    metric_cols = st.columns(3, gap="small")
    metric_cols[0].markdown(
        metric_card("Total transactions", f"{st.session_state.get('sample_size', DEFAULT_SAMPLE_SIZE):,}"),
        unsafe_allow_html=True,
    )
    metric_cols[1].markdown(
        metric_card("Suspicious accounts", f"{suspicious_accounts:,}", "#E24B4A"),
        unsafe_allow_html=True,
    )
    metric_cols[2].markdown(
        metric_card("LLM explained", f"{high_priority_count:,}", "#3B6D11"),
        unsafe_allow_html=True,
    )

    st.markdown("<div class='screen-gap'></div>", unsafe_allow_html=True)
    st.markdown(metric_card("Total alerts", f"{total_alerts:,}"), unsafe_allow_html=True)


def render_transaction_feed():
    analysis = st.session_state.get("analysis_data")
    if not analysis:
        st.markdown(
            "<div class='empty-state'>Run analysis first to populate the transaction feed.</div>",
            unsafe_allow_html=True,
        )
        return

    accounts = sort_accounts(analysis.get("all_accounts", []))
    typology_breakdown = analysis.get("typology_breakdown", {})

    render_header(
        "Transaction Feed",
        f"{analysis.get('total_suspicious_accounts', 0):,} suspicious accounts detected",
    )

    _, summary_col_right = st.columns([0.68, 0.32], gap="small")
    with summary_col_right:
        badges = []
        for typology, count in sorted(typology_breakdown.items(), key=lambda item: item[1], reverse=True)[:3]:
            badges.append(f"{typology_badge(typology)} <span class='subtle-note'>{count:,}</span>")
        st.markdown(
            "<div style='display:flex;justify-content:flex-end;gap:0.4rem;flex-wrap:wrap;'>"
            + "".join(f"<div>{item}</div>" for item in badges)
            + "</div>",
            unsafe_allow_html=True,
        )

    with st.container(border=True):
        st.markdown(
            "<div class='feed-head'><span>Account</span><span>Typology</span><span>Risk</span><span>Amount flagged</span></div>",
            unsafe_allow_html=True,
        )

        selected_id = st.session_state.get("selected_account")
        for account in accounts:
            priority = (account.get("ml_priority") or "LOW").upper()
            row_class = "account-row-selected" if account.get("account") == selected_id else ""
            st.markdown(f"<div class='{row_class}'>", unsafe_allow_html=True)

            dot_class = {
                "CRITICAL": "dot-critical",
                "HIGH": "dot-high",
                "MEDIUM": "dot-medium",
                "LOW": "dot-low",
            }.get(priority, "dot-low")

            cols = st.columns([0.08, 1.55, 1.0, 0.95, 1.0], gap="small")
            cols[0].markdown(
                f"<div style='padding-top:0.65rem;'><span class='dot {dot_class}'></span></div>",
                unsafe_allow_html=True,
            )
            if cols[1].button(
                account.get("account", "N/A"),
                key=f"feed_{account.get('account')}",
                use_container_width=True,
            ):
                set_selected_account(account.get("account"))
            cols[2].markdown(typology_badge(account.get("typology")), unsafe_allow_html=True)
            cols[3].markdown(priority_badge(priority), unsafe_allow_html=True)
            cols[4].markdown(
                f"<div class='mono' style='padding-top:0.35rem;text-align:right;'>{amount_text(account.get('total_flagged'))}</div>",
                unsafe_allow_html=True,
            )
            st.markdown(
                "<hr style='margin:0.15rem 0 0.35rem 0; border:0; border-top:1px solid #eceff3;'>",
                unsafe_allow_html=True,
            )
            st.markdown("</div>", unsafe_allow_html=True)


def render_account_detail():
    analysis = st.session_state.get("analysis_data")
    if not analysis:
        st.markdown(
            "<div class='empty-state'>Run analysis first to inspect an account in detail.</div>",
            unsafe_allow_html=True,
        )
        return

    selected = get_selected_account(analysis)
    if not selected:
        st.markdown(
            "<div class='empty-state'>No suspicious accounts are available in the latest analysis.</div>",
            unsafe_allow_html=True,
        )
        return

    llm_map = get_llm_account_summary_map()
    llm_details = llm_map.get(selected.get("account"))

    header_cols = st.columns([0.15, 0.85], gap="small")
    if header_cols[0].button("Back", key="back_to_feed"):
        switch_page("Transaction Feed")

    risk_source = (llm_details or {}).get("risk_level") or selected.get("ml_priority", "LOW")
    header_cols[1].markdown(
        f"""
        <div style="display:flex;align-items:center;gap:0.5rem;flex-wrap:wrap;">
          <span class="account-code">{selected.get('account', 'N/A')}</span>
          {typology_badge(selected.get("typology"))}
          {priority_badge(risk_source)}
        </div>
        <div class="section-subtitle">{selected.get('alert_count', 0):,} suspicious transactions - {amount_text(selected.get('total_flagged'))} flagged</div>
        """,
        unsafe_allow_html=True,
    )

    top_metrics = st.columns(4, gap="small")
    top_metrics[0].markdown(
        metric_card("Total flagged", amount_text(selected.get("total_flagged")), "#E24B4A"),
        unsafe_allow_html=True,
    )
    top_metrics[1].markdown(
        metric_card("Transactions", f"{selected.get('alert_count', 0):,}"),
        unsafe_allow_html=True,
    )
    top_metrics[2].markdown(
        metric_card("Rules fired", f"{len(selected.get('rules_fired', [])):,}"),
        unsafe_allow_html=True,
    )
    recommendation_value = (llm_details or {}).get("recommendation") or "MANUAL_REVIEW"
    top_metrics[3].markdown(
        f"""
        <div class="metric-card">
          <div class="metric-label">Recommendation</div>
          <div class="metric-value-sm" style="color:#A32D2D;">{recommendation_value.replace('_', ' ')}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    content_cols = st.columns(2, gap="large")

    with content_cols[0]:
        with st.container(border=True):
            st.markdown("**Rules fired**")
            rules_fired = selected.get("rules_fired", [])
            if rules_fired:
                for rule in rules_fired:
                    st.markdown(
                        f"<div style='display:flex;align-items:center;gap:0.45rem;margin:0.45rem 0;'><span class='dot dot-high'></span><span class='mono' style='font-size:0.78rem;'>{rule}</span></div>",
                        unsafe_allow_html=True,
                    )
            else:
                st.markdown(
                    "<div class='subtle-note'>No rule names available for this account.</div>",
                    unsafe_allow_html=True,
                )

    with content_cols[1]:
        with st.container(border=True):
            st.markdown("**Money trail**")

            graph_cache = get_account_graph_map()
            graph_data = graph_cache.get(selected.get("account"))

            if graph_data:
                graph_stats = st.columns(3, gap="small")
                graph_stats[0].markdown(
                    metric_card("Focus account", selected.get("account", "N/A")),
                    unsafe_allow_html=True,
                )
                graph_stats[1].markdown(
                    metric_card("Nodes", f"{len(graph_data.get('nodes', [])):,}", "#378ADD"),
                    unsafe_allow_html=True,
                )
                graph_stats[2].markdown(
                    metric_card("Paths", f"{len(graph_data.get('edges', [])):,}", "#854F0B"),
                    unsafe_allow_html=True,
                )
                st.markdown(
                    "<div class='subtle-note' style='margin:0.15rem 0 0.45rem;'>Nodes represent accounts. Edges represent aggregated suspicious transfer paths between accounts in the current analysis sample.</div>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    """
                    <div style="display:flex;align-items:center;gap:0.9rem;flex-wrap:wrap;margin:0.4rem 0 0.65rem;">
                      <div style="display:flex;align-items:center;gap:0.35rem;"><span class="dot dot-critical"></span><span class="subtle-note">Selected account</span></div>
                      <div style="display:flex;align-items:center;gap:0.35rem;"><span class="dot dot-medium"></span><span class="subtle-note">Counterparty accounts</span></div>
                      <div style="display:flex;align-items:center;gap:0.35rem;"><span class="dot dot-low"></span><span class="subtle-note">Edge width reflects total suspicious amount</span></div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                graph_html = render_account_graph(graph_data)
                components.html(graph_html, height=500, scrolling=False)
            else:
                st.markdown(
                    "<div class='empty-state'>No graph has been generated for this account yet.</div>",
                    unsafe_allow_html=True,
                )

                if st.button(
                    "Generate Money Trail",
                    key=f"generate_graph_{selected.get('account')}",
                    type="primary",
                ):
                    with st.spinner("Building account graph..."):
                        try:
                            graph_response = run_account_graph_request(
                                selected.get("account"),
                                st.session_state.get("sample_size", DEFAULT_SAMPLE_SIZE),
                            )
                        except requests.RequestException as exc:
                            st.error(f"Account graph request failed: {exc}")
                        else:
                            graph_cache[selected.get("account")] = graph_response
                            st.session_state["account_graphs"] = graph_cache
                            st.rerun()

            st.markdown(
                f"""
                <div style="margin-top:0.8rem;">
                  <div class="subtle-note">ML anomaly score</div>
                  <div class="metric-value-sm">{(selected.get('ml_anomaly_score') or 0):.4f}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            signals = selected.get("ml_reason_signals", [])
            if signals:
                st.markdown("**Signals**")
                for signal in signals:
                    st.markdown(f"- {signal}")
            else:
                st.markdown("<div class='subtle-note'>No ML reason signals available.</div>", unsafe_allow_html=True)
            st.caption("Money trail edges are built from suspicious transactions associated with the selected account in the current analysis sample.")

    with st.container(border=True):
        st.markdown("**LLM Analysis - Mistral 7B**")
        if llm_details:
            st.markdown(
                f"""
                <div style="margin-top:0.45rem;">
                  <div class="subtle-note" style="margin-bottom:0.55rem;">Risk level: {(llm_details.get("risk_level") or "UNKNOWN").upper()}</div>
                  <div style="font-size:0.88rem;line-height:1.7;color:#4b5563;margin-bottom:0.8rem;">{llm_details.get("reasoning", "No reasoning provided.")}</div>
                  <div><strong>Recommendation:</strong> {(llm_details.get("recommendation") or "MANUAL_REVIEW").replace("_", " ")}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            if not LLM_ENABLED:
                st.markdown(
                    "<div class='empty-state'>AI case summaries are disabled in this public demo deployment.</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    "<div class='empty-state'>No AI case summary has been generated for this account yet.</div>",
                    unsafe_allow_html=True,
                )
                if st.button("Generate AI Case Summary", key=f"generate_llm_{selected.get('account')}", type="primary"):
                    with st.spinner("Generating account summary..."):
                        try:
                            llm_response = run_account_analysis_request(selected)
                        except requests.RequestException as exc:
                            st.error(f"Account analysis request failed: {exc}")
                        else:
                            llm_cache = get_llm_account_summary_map()
                            llm_cache[selected.get("account")] = llm_response
                            st.session_state["llm_account_summaries"] = llm_cache
                            st.rerun()


def render_evaluation():
    render_header(
        "Evaluation Dashboard",
        "Accuracy metrics against IBM AML ground truth",
    )

    if st.button("Load Evaluation Metrics", key="load_eval"):
        with st.spinner("Running evaluation..."):
            try:
                st.session_state["evaluation_data"] = run_evaluation_request()
            except requests.RequestException as exc:
                st.error(f"Evaluation request failed: {exc}")

    evaluation = st.session_state.get("evaluation_data")
    if not evaluation:
        st.markdown(
            "<div class='empty-state'>Load evaluation metrics to populate this dashboard.</div>",
            unsafe_allow_html=True,
        )
        return

    metric_cols = st.columns(3, gap="small")
    metric_cols[0].markdown(
        metric_card("Precision", f"{evaluation.get('precision', 0):.3f}"),
        unsafe_allow_html=True,
    )
    metric_cols[0].markdown(
        progress_bar("Precision", evaluation.get("precision", 0), 1, "#378ADD", f"{evaluation.get('precision', 0):.3f}"),
        unsafe_allow_html=True,
    )
    metric_cols[1].markdown(
        metric_card("Recall", f"{evaluation.get('recall', 0):.3f}", "#3B6D11"),
        unsafe_allow_html=True,
    )
    metric_cols[1].markdown(
        progress_bar("Recall", evaluation.get("recall", 0), 1, "#639922", f"{evaluation.get('recall', 0):.3f}"),
        unsafe_allow_html=True,
    )
    metric_cols[2].markdown(
        metric_card("F1 Score", f"{evaluation.get('f1_score', 0):.3f}"),
        unsafe_allow_html=True,
    )
    metric_cols[2].markdown(
        progress_bar("F1 Score", evaluation.get("f1_score", 0), 1, "#EF9F27", f"{evaluation.get('f1_score', 0):.3f}"),
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        st.markdown("**Evaluation sample**")
        sample_cols = st.columns(3, gap="small")
        sample_cols[0].markdown(
            metric_card("Sample size", f"{evaluation.get('sample_size', 0):,}"),
            unsafe_allow_html=True,
        )
        sample_cols[1].markdown(
            metric_card("Laundering in sample", f"{evaluation.get('laundering_in_sample', 0):,}"),
            unsafe_allow_html=True,
        )
        sample_cols[2].markdown(
            metric_card("Total alerts", f"{evaluation.get('total_alerts', 0):,}"),
            unsafe_allow_html=True,
        )

    with st.container(border=True):
        st.markdown("**False positives by rule**")
        fp_breakdown = evaluation.get("false_positives_by_rule", {})
        if fp_breakdown:
            max_value = max(fp_breakdown.values())
            for rule_name, count in fp_breakdown.items():
                st.markdown(
                    progress_bar(rule_name, count, max_value, "#E24B4A", f"{count:,}"),
                    unsafe_allow_html=True,
                )
        else:
            st.markdown("<div class='subtle-note'>No false-positive breakdown is available.</div>", unsafe_allow_html=True)


def render_policy_ingestion():
    render_header(
        "Policy Ingestion",
        "Turn a policy PDF into traceable clauses and AI-generated draft compliance rules",
    )

    with st.container(border=True):
        control_col, guide_col = st.columns([1.15, 0.85], gap="large")

        with control_col:
            st.markdown("<div class='section-kicker'>Source</div>", unsafe_allow_html=True)
            st.markdown("**Choose a policy document**")
            if not LLM_ENABLED:
                st.markdown(
                    "<div class='subtle-note'>This deployment is running heuristic-only policy extraction (LLM disabled).</div>",
                    unsafe_allow_html=True,
                )

            raw_sample_options = {
                "Happy path sample": Path("sample_pdf") / "sample_policy.pdf",
                "Edge-case sample": Path("sample_pdf") / "sample_policy_edge_cases.pdf",
            }
            sample_options = {
                label: str(path) for label, path in raw_sample_options.items() if path.exists()
            }

            selected_sample = None
            if sample_options:
                selected_sample = st.selectbox(
                    "Choose a sample policy PDF",
                    options=list(sample_options.keys()),
                    index=min(1, len(sample_options) - 1),
                )
            else:
                st.markdown(
                    "<div class='subtle-note'>Bundled sample PDFs are not available here. Upload a text-based PDF to run ingestion.</div>",
                    unsafe_allow_html=True,
                )

            uploaded_file = st.file_uploader(
                "Or upload a text-based PDF",
                type=["pdf"],
                help="This MVP expects text-based PDFs rather than scanned image PDFs.",
            )

            pdf_path = sample_options.get(selected_sample) if selected_sample else None
            source_label = selected_sample or "Uploaded policy"

            if uploaded_file is not None:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
                    temp_pdf.write(uploaded_file.getbuffer())
                    pdf_path = temp_pdf.name
                source_label = uploaded_file.name

            if pdf_path:
                st.caption(f"Selected source: {pdf_path}")

            if st.button(
                "Run Policy Ingestion",
                key="run_policy_ingestion",
                type="primary",
                use_container_width=True,
                disabled=pdf_path is None,
            ):
                with st.spinner("Extracting clauses and candidate rules..."):
                    try:
                        policy_data = run_policy_ingestion(pdf_path)
                        policy_data["source_label"] = source_label
                        policy_data["source_mode"] = "upload" if uploaded_file is not None else "sample"
                        st.session_state["policy_data"] = policy_data
                    except Exception as exc:
                        st.error(f"Policy ingestion failed: {exc}")

        with guide_col:
            st.markdown(
                callout_card(
                    "Draft controls only",
                    "This page proposes candidate compliance controls from policy text. The extracted rules stay review-ready drafts and do not change the live AML detection engine.",
                ),
                unsafe_allow_html=True,
            )
            st.markdown("<div class='screen-gap'></div>", unsafe_allow_html=True)
            st.markdown(
                callout_card(
                    "How to read the output",
                    "Clauses preserve traceability back to the document. Candidate rules show the structured fields the system could reuse later, plus whether they came from the LLM or the heuristic fallback.",
                ),
                unsafe_allow_html=True,
            )

    policy_data = st.session_state.get("policy_data")
    if not policy_data:
        st.markdown(
            "<div class='empty-state'>Run policy ingestion to inspect extracted clauses and draft rules.</div>",
            unsafe_allow_html=True,
        )
        return

    summary = policy_data["summary"]
    summary_cols = st.columns(4, gap="small")
    summary_cols[0].markdown(
        metric_card("Pages", f"{len(policy_data['pages']):,}"),
        unsafe_allow_html=True,
    )
    summary_cols[1].markdown(
        metric_card("Clauses", f"{summary['total_clauses']:,}", "#378ADD"),
        unsafe_allow_html=True,
    )
    summary_cols[2].markdown(
        metric_card("Draft rules", f"{summary['total_rules']:,}", "#3B6D11"),
        unsafe_allow_html=True,
    )
    summary_cols[3].markdown(
        metric_card("Source", policy_data.get("source_label") or Path(policy_data["pdf_path"]).name),
        unsafe_allow_html=True,
    )

    st.markdown("<div class='screen-gap'></div>", unsafe_allow_html=True)

    mix_cols = st.columns(3, gap="small")
    extraction_mix = summary.get("extraction_mix", {})

    mix_cols[0].markdown(
        policy_rule_metric_card("LLM accepted", f"{extraction_mix.get('LLM', 0):,}"),
        unsafe_allow_html=True,
    )
    mix_cols[1].markdown(
        policy_rule_metric_card("Fallback rules", f"{extraction_mix.get('Fallback', 0):,}"),
        unsafe_allow_html=True,
    )
    mix_cols[2].markdown(
        policy_rule_metric_card(
            "Source mode",
            "Upload" if policy_data.get("source_mode") == "upload" else "Sample",
        ),
        unsafe_allow_html=True,
    )

    st.markdown("<div class='screen-gap'></div>", unsafe_allow_html=True)

    breakdown = summary["rule_breakdown"]
    if breakdown:
        st.markdown("**Rule breakdown**")
        breakdown_cols = st.columns(max(len(breakdown), 1), gap="small")
        for idx, (rule_type, count) in enumerate(sorted(breakdown.items())):
            breakdown_cols[idx].markdown(
                policy_rule_metric_card(rule_type, f"{count:,}"),
                unsafe_allow_html=True,
            )

    left_col, right_col = st.columns([1.15, 1.0], gap="large")

    with left_col:
        with st.container(border=True):
            st.markdown("<div class='section-kicker'>Traceability</div>", unsafe_allow_html=True)
            st.markdown("**Extracted clauses**")
            st.markdown(
                "<div class='subtle-note'>Each clause preserves the page and heading context used during extraction.</div>",
                unsafe_allow_html=True,
            )
            st.markdown("<div class='screen-gap'></div>", unsafe_allow_html=True)
            for clause in policy_data["clauses"]:
                st.markdown(
                    f"""
                    <div class="policy-card">
                      <div class="policy-card-title">{clause.clause_id}</div>
                      <div class="policy-card-meta">Page {clause.page_number} • {clause.section_heading or "No heading"}</div>
                      <div class="policy-card-body">{clause.text}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    with right_col:
        with st.container(border=True):
            st.markdown("<div class='section-kicker'>Review</div>", unsafe_allow_html=True)
            st.markdown("**Candidate rules**")
            st.markdown(
                "<div class='subtle-note'>These draft controls are shown separately from the active compliance rules used in runtime analysis.</div>",
                unsafe_allow_html=True,
            )
            st.markdown("<div class='screen-gap'></div>", unsafe_allow_html=True)
            if not policy_data["rules"]:
                st.markdown(
                    "<div class='empty-state'>No executable draft rules were extracted from the selected document.</div>",
                    unsafe_allow_html=True,
                )
            else:
                for rule in policy_data["rules"]:
                    details = rule_detail_chips(rule)
                    metadata_reason = (rule.metadata or {}).get("llm_reasoning") or (rule.metadata or {}).get("matched_family")
                    extraction_source = rule_extraction_source(rule)

                    st.markdown(
                        f"""
                        <div class="policy-card">
                          <div style="display:flex;justify-content:space-between;gap:0.6rem;align-items:center;flex-wrap:wrap;">
                            <div class="policy-card-title">{rule.name}</div>
                            <div style="display:flex;gap:0.35rem;align-items:center;flex-wrap:wrap;">
                              {rule_type_badge(rule.rule_type)}
                              <span class="source-chip">{extraction_source}</span>
                            </div>
                          </div>
                          <div class="policy-card-meta">Page {rule.page_number} • {rule.section_heading or "No heading"} • <span class="mono">{rule.status.value}</span></div>
                          <div class="policy-card-body">{rule.source_text}</div>
                          <div class="policy-card-footer">{"".join(details) if details else "<span class='subtle-note'>No structured fields extracted.</span>"}</div>
                          <div class="subtle-note" style="margin-top:0.55rem;">{metadata_reason or "No extraction reasoning available."}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )


def main():
    init_state()
    inject_css()
    render_sidebar()

    with st.container(border=True):
        page = st.session_state.get("page", "Run Analysis")

        if page == "Run Analysis":
            render_run_analysis()
        elif page == "Transaction Feed":
            render_transaction_feed()
        elif page == "Account Detail":
            render_account_detail()
        elif page == "Evaluation":
            render_evaluation()
        elif page == "Policy Ingestion":
            render_policy_ingestion()


if __name__ == "__main__":
    main()
