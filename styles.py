"""
Professional Enterprise Theme and Styling for Industrial Decision Intelligence.
Applies a modern industrial executive dark palette (Midnight Navy, Slate, Cyan/Azure).
"""

import streamlit as st


def apply_custom_theme():
    """Injects high-end enterprise CSS into the Streamlit application."""
    css = """
    <style>
    /* ========== Global Font & Reset ========== */
    html, body, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }
    
    /* ========== Main App Background ========== */
    .stApp {
        background: radial-gradient(circle at 15% 15%, #0d1829 0%, #080d1a 100%) !important;
        color: #F8FAFC;
    }

    /* Top decoration bar */
    .stApp::before {
        content: "";
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: linear-gradient(90deg, #0284C7, #38BDF8, #2563EB, #06B6D4);
        z-index: 999999;
    }

    /* ========== Metric Cards Styling ========== */
    [data-testid="stMetric"] {
        background: linear-gradient(145deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.85) 100%) !important;
        border: 1px solid rgba(148, 163, 184, 0.15) !important;
        border-radius: 12px !important;
        padding: 16px 20px !important;
        box-shadow: 0 4px 18px rgba(0, 0, 0, 0.35) !important;
        transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease !important;
    }
    [data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        border-color: rgba(56, 189, 248, 0.4) !important;
        box-shadow: 0 8px 24px rgba(2, 132, 199, 0.2) !important;
    }
    [data-testid="stMetricLabel"] p {
        font-size: 0.82rem !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.06em !important;
        color: #94A3B8 !important;
    }
    [data-testid="stMetricValue"] div {
        font-size: 1.9rem !important;
        font-weight: 700 !important;
        color: #F8FAFC !important;
    }

    /* ========== Modern Tabs Styling ========== */
    [data-baseweb="tab-list"] {
        background: rgba(15, 23, 42, 0.6) !important;
        border-radius: 12px !important;
        padding: 6px !important;
        border: 1px solid rgba(148, 163, 184, 0.12) !important;
        gap: 4px !important;
    }
    button[data-baseweb="tab"] {
        border-radius: 8px !important;
        color: #94A3B8 !important;
        font-weight: 600 !important;
        font-size: 0.92rem !important;
        padding: 8px 16px !important;
        border: none !important;
        transition: all 0.2s ease !important;
    }
    button[data-baseweb="tab"]:hover {
        background: rgba(51, 65, 85, 0.4) !important;
        color: #E2E8F0 !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        background: linear-gradient(135deg, rgba(2, 132, 199, 0.25) 0%, rgba(37, 99, 235, 0.35) 100%) !important;
        color: #38BDF8 !important;
        border: 1px solid rgba(56, 189, 248, 0.4) !important;
        box-shadow: 0 2px 10px rgba(2, 132, 199, 0.25) !important;
    }

    /* ========== Buttons Styling ========== */
    .stButton > button {
        border-radius: 8px !important;
        font-weight: 600 !important;
        letter-spacing: 0.02em !important;
        transition: all 0.2s ease !important;
        border: 1px solid rgba(148, 163, 184, 0.2) !important;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #0284C7 0%, #2563EB 100%) !important;
        color: #FFFFFF !important;
        border: 1px solid #38BDF8 !important;
        box-shadow: 0 4px 14px rgba(2, 132, 199, 0.35) !important;
    }
    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #0369A1 0%, #1D4ED8 100%) !important;
        box-shadow: 0 6px 20px rgba(2, 132, 199, 0.5) !important;
        transform: translateY(-1px);
    }
    .stButton > button[kind="secondary"] {
        background: #1E293B !important;
        color: #F1F5F9 !important;
        border: 1px solid #334155 !important;
    }
    .stButton > button[kind="secondary"]:hover {
        background: #334155 !important;
        border-color: #64748B !important;
    }

    /* ========== Forms, Inputs & Selectboxes ========== */
    .stTextInput input, .stSelectbox [data-baseweb="select"], .stNumberInput input, .stDateInput input {
        background-color: #151F32 !important;
        color: #F8FAFC !important;
        border: 1px solid #334155 !important;
        border-radius: 8px !important;
    }
    .stTextInput input:focus, .stNumberInput input:focus, .stDateInput input:focus {
        border-color: #38BDF8 !important;
        box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.25) !important;
    }

    /* ========== Expanders ========== */
    .streamlit-expanderHeader {
        background: rgba(30, 41, 59, 0.5) !important;
        border-radius: 8px !important;
        border: 1px solid rgba(148, 163, 184, 0.12) !important;
        font-weight: 600 !important;
    }

    /* ========== DataFrames ========== */
    [data-testid="stDataFrame"] {
        border: 1px solid rgba(148, 163, 184, 0.15) !important;
        border-radius: 10px !important;
        overflow: hidden !important;
        background: #0F172A !important;
    }

    /* ========== Alert / Status Boxes ========== */
    .stAlert {
        border-radius: 10px !important;
        background: rgba(15, 23, 42, 0.8) !important;
        border-left-width: 5px !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2) !important;
    }

    /* ========== Custom Header Banner Component ========== */
    .industrial-header {
        background: linear-gradient(135deg, rgba(15, 23, 42, 0.95) 0%, rgba(30, 41, 59, 0.85) 100%);
        border: 1px solid rgba(56, 189, 248, 0.25);
        border-radius: 14px;
        padding: 22px 28px;
        margin-bottom: 24px;
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.45);
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 16px;
    }
    .industrial-title-group h1 {
        margin: 0;
        font-size: 1.85rem;
        font-weight: 800;
        background: linear-gradient(90deg, #FFFFFF 0%, #E2E8F0 50%, #38BDF8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -0.02em;
    }
    .industrial-title-group p {
        margin: 4px 0 0 0;
        font-size: 0.92rem;
        color: #94A3B8;
        font-weight: 500;
    }
    .industrial-badges {
        display: flex;
        gap: 10px;
        align-items: center;
        flex-wrap: wrap;
    }
    .badge-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-size: 0.78rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        padding: 6px 12px;
        border-radius: 9999px;
    }
    .badge-live {
        background: rgba(16, 185, 129, 0.15);
        color: #34D399;
        border: 1px solid rgba(16, 185, 129, 0.35);
    }
    .badge-pulse {
        width: 8px;
        height: 8px;
        background-color: #34D399;
        border-radius: 50%;
        box-shadow: 0 0 8px #34D399;
        animation: pulse 2s infinite;
    }
    @keyframes pulse {
        0% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.4; transform: scale(0.85); }
        100% { opacity: 1; transform: scale(1); }
    }
    .badge-ai {
        background: rgba(2, 132, 199, 0.15);
        color: #38BDF8;
        border: 1px solid rgba(56, 189, 248, 0.35);
    }
    .badge-user {
        background: rgba(99, 102, 241, 0.15);
        color: #A5B4FC;
        border: 1px solid rgba(99, 102, 241, 0.35);
    }

    /* ========== Quick Prompt Pill / Chips ========== */
    .prompt-chip {
        display: inline-block;
        background: rgba(30, 41, 59, 0.8);
        border: 1px solid rgba(148, 163, 184, 0.2);
        color: #E2E8F0;
        font-size: 0.85rem;
        padding: 7px 14px;
        border-radius: 8px;
        margin: 4px 6px 6px 0;
        cursor: pointer;
        transition: all 0.2s ease;
    }
    .prompt-chip:hover {
        background: rgba(2, 132, 199, 0.25);
        border-color: #38BDF8;
        color: #38BDF8;
        transform: translateY(-1px);
    }

    /* ========== Assistant Message Bubble ========== */
    .assistant-card {
        background: linear-gradient(135deg, rgba(21, 31, 50, 0.95) 0%, rgba(15, 23, 42, 0.98) 100%);
        border: 1px solid rgba(56, 189, 248, 0.25);
        border-left: 4px solid #38BDF8;
        border-radius: 12px;
        padding: 18px 22px;
        margin: 12px 0;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
    }
    .user-card {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.9) 0%, rgba(51, 65, 85, 0.8) 100%);
        border: 1px solid rgba(148, 163, 184, 0.2);
        border-right: 4px solid #818CF8;
        border-radius: 12px;
        padding: 16px 20px;
        margin: 12px 0;
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


def render_header(full_name="Administrator", role="ADMIN"):
    """Renders a sleek top-tier industrial enterprise banner."""
    header_html = f"""
    <div class="industrial-header">
        <div class="industrial-title-group">
            <h1>🏭 INDUSTRIAL DECISION INTELLIGENCE</h1>
            <p>Autonomous Industrial Monitoring, Predictive Diagnostics & Risk Mitigation System</p>
        </div>
        <div class="industrial-badges">
            <span class="badge-pill badge-live">
                <span class="badge-pulse"></span> LIVE TELEMETRY
            </span>
            <span class="badge-pill badge-ai">
                🤖 AI COPILOT READY
            </span>
            <span class="badge-pill badge-user">
                👤 {full_name} ({role})
            </span>
        </div>
    </div>
    """
    st.markdown(header_html, unsafe_allow_html=True)
