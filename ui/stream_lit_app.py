# stream_lit app.py : this file defines the stream lit app which is used to run the compliance agent and display the results

import streamlit as st
import requests
import pandas as pd
import streamlit.components.v1 as components


API = "http://localhost:8000"

st.set_page_config(
    page_title="AMLer",
    page_icon="ðŸ”",
    layout="wide"
)

# custom CSS
st.markdown("""
<style>

/* Global font */
html, body, [class*="css"] {
    font-family: "Inter", sans-serif;
}

/* Dark dashboard background */
.stApp { 
    background-color: #0f1117; 
}

/* Metric cards */
.metric-card { 
    background: #1c1f2e; 
    padding: 16px; 
    border-radius: 8px;
    border: 1px solid #2d3147;
}

/* Sidebar navigation text */
section[data-testid="stSidebar"] label {
    font-size: 18px;
    font-weight: 500;
}

/* Sidebar spacing */
section[data-testid="stSidebar"] {
    padding-top: 25px;
}

/* Headings */
h1, h2, h3 {
    font-weight: 600;
}

</style>
""", unsafe_allow_html=True)

st.title("ðŸ” AMLer")
st.caption("IBM AML HI-Small Dataset Â· Mistral 7B Â· Real-time detection")

page = st.sidebar.radio(
    "Navigation",
    ["Run Analysis", "Transaction Feed", "Account Detail", "Evaluation"]
)

if page == "Run Analysis":

    st.header("Run AML Detection")

    st.write(
        "Execute the AML compliance engine on the IBM HI-Small transaction dataset."
    )

    st.divider()

    col1, col2 = st.columns([2,1])

    with col1:

        st.subheader("Start Analysis")

        if st.button("Run Analysis", use_container_width=True):

            with st.spinner("Running compliance detection..."):

                response = requests.post(f"{API}/analyze")

            if response.status_code == 200:

                alerts = response.json()

                st.session_state["alerts"] = alerts

                st.success(f"Analysis completed â€” {len(alerts)} alerts detected")

            else:

                st.error("Failed to run analysis")

    with col2:

        st.subheader("Detection Pipeline")

        st.info("""
Transactions  
â†“  
Rule Engine  
â†“  
Typology Detection  
â†“  
AI Reasoning  
â†“  
Investigation Alerts
""")
