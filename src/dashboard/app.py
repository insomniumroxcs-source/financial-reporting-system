"""
Streamlit Dashboard — Slim Orchestrator
Fetches all data centrally, injects theme, dispatches to tab modules.
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import streamlit as st
from datetime import datetime

# ── Data layer ─────────────────────────────────────────────────────────────
from src.data_ingestion.api_client import (
    fetch_price_data, fetch_company_info, fetch_financials_yfinance,
)
from src.data_processing.cleaner import standardize_columns, enforce_schema
from src.data_processing.calculator import compute_all_ratios

# ── Theme & Components ─────────────────────────────────────────────────────
from src.dashboard.theme import inject_theme_css, TEXT_SECONDARY
from src.dashboard.components import ticker_sidebar, kpi_row, render_company_header

# ── Tab modules ────────────────────────────────────────────────────────────
from src.dashboard.tabs import (
    overview,
    fundamentals,
    technical,
    comparison,
    reports,
    statements_analysis,
    deal_insights,
    dcf_valuation,
    budget_variance,
)

# ── Page config & Theme injection ──────────────────────────────────────────
st.set_page_config(page_title="Financial Dashboard", page_icon="📊", layout="wide")
inject_theme_css()

# ── Curator Custom Top Navigation ─────────────────────────────────────────
top_nav_html = """
<div style="background-color: var(--color-surface); height: 64px; border-bottom: 1px solid var(--color-outline-variant); 
            display: flex; justify-content: space-between; align-items: center; padding: 0 24px; position: fixed; 
            top: 0; left: 0; width: 100%; z-index: 999999;">
    <div style="color: var(--color-primary); font-family: 'Manrope', sans-serif; font-weight: 900; font-size: 24px;">
        Curator Finance
    </div>
    <div style="display: flex; gap: 24px; font-family: 'Manrope', sans-serif; text-transform: uppercase; font-size: 12px; font-weight: 800; letter-spacing: 0.1em;">
        <span style="color: var(--color-primary); border-bottom: 2px solid var(--color-secondary); padding-bottom: 4px;">Dashboard</span>
        <span style="color: var(--color-on-surface-variant);">Markets</span>
        <span style="color: var(--color-on-surface-variant);">Portfolio</span>
    </div>
</div>
<div style="height: 64px;"></div> <!-- Spacer -->
"""
st.markdown(top_nav_html, unsafe_allow_html=True)

# ── Sidebar ────────────────────────────────────────────────────────────────
ticker, price_period, peers = ticker_sidebar()

# ── Cached data fetchers ───────────────────────────────────────────────────
@st.cache_data(ttl=600, show_spinner="Loading prices...")
def get_prices(t, p):
    return fetch_price_data(t, period=p)

@st.cache_data(ttl=3600, show_spinner="Loading info...")
def get_info(t):
    return fetch_company_info(t)

@st.cache_data(ttl=3600, show_spinner="Loading fundamentals...")
def get_fundamentals(t):
    raw = fetch_financials_yfinance(t)
    return {
        k: enforce_schema(standardize_columns(v))
        if v is not None and not v.empty else v
        for k, v in raw.items()
    }

# ── Fetch all data centrally ──────────────────────────────────────────────
try:
    info = get_info(ticker)
    prices = get_prices(ticker, price_period)
    fundamentals_data = get_fundamentals(ticker)
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

# Compute ratios once
inc = fundamentals_data.get("income_statement")
bal = fundamentals_data.get("balance_sheet")
cf = fundamentals_data.get("cash_flow")
ratios = compute_all_ratios(inc, bal, cf, ticker)

# ── Company header & KPI row ──────────────────────────────────────────────
render_company_header(ticker, info)
kpi_row(info)
st.markdown("---")

# ── Tab definitions ────────────────────────────────────────────────────────
TAB_LABELS = [
    "📈 Overview",
    "📊 Fundamentals",
    "📉 Technical",
    "🔄 Comparison",
    "📑 Statements",
    "📰 Deal Insights",
    "💰 DCF",
    "📋 Variance",
    "📥 Reports",
]

TAB_MODULES = [
    overview,
    fundamentals,
    technical,
    comparison,
    statements_analysis,
    deal_insights,
    dcf_valuation,
    budget_variance,
    reports,
]

tabs = st.tabs(TAB_LABELS)

# ── Dispatch to each tab's render() ───────────────────────────────────────
for tab_container, module in zip(tabs, TAB_MODULES):
    with tab_container:
        try:
            module.render(
                ticker=ticker,
                info=info,
                prices=prices,
                fundamentals=fundamentals_data,
                ratios=ratios,
                peers=peers,
                period=price_period,
            )
        except Exception as e:
            st.error(f"Error in {module.__name__}: {e}")

# ── Footer ─────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    f"<div style='text-align:center;color:{TEXT_SECONDARY};font-size:.8rem'>"
    f"Financial Dashboard • {datetime.now().strftime('%B %d, %Y')}</div>",
    unsafe_allow_html=True,
)
