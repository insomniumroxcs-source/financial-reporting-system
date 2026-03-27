"""
Tab: Financial Modelling & Forecasting
Build 3-statement financial model with interactive assumptions.
"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np

from src.dashboard.theme import plotly_theme, section_header, metric_card, BLUE, GREEN, RED, TEXT_SECONDARY
from src.data_processing.forecaster import build_three_statement_model, compute_historical_averages


def render(ticker, info, prices, fundamentals, ratios, peers, period):
    section_header("Financial Modelling & Forecasting",
                   "Build a 3-statement financial model with custom growth assumptions")

    inc = fundamentals.get("income_statement") if fundamentals else None
    bal = fundamentals.get("balance_sheet") if fundamentals else None
    cf = fundamentals.get("cash_flow") if fundamentals else None

    if inc is None or inc.empty:
        st.info("No historical financial data available to build a model.")
        return

    # ── Historical Averages ──────────────────────────────────────────────
    hist_avg = compute_historical_averages(inc, bal, cf)

    # ── Assumptions Panel ────────────────────────────────────────────────
    with st.expander("Model Assumptions", expanded=True):
        st.caption("Adjust the sliders to change projection assumptions. Defaults are based on historical averages.")

        # Reset button
        if st.button("Reset to Historical Averages", key="reset_model"):
            for key in list(st.session_state.keys()):
                if key.startswith(f"model_{ticker}_"):
                    del st.session_state[key]
            st.rerun()

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("**Revenue Growth Rates**")
            growth_rates = []
            default_growth = hist_avg.get("revenue_cagr", 0.05)
            for yr in range(1, 6):
                key = f"model_{ticker}_growth_{yr}"
                g = st.slider(f"Year {yr} Growth", min_value=-0.20, max_value=0.30,
                              value=float(min(0.30, max(-0.20, default_growth))),
                              step=0.01, format="%.0f%%", key=key)
                growth_rates.append(g)

        with col2:
            st.markdown("**Cost Structure**")
            cogs_pct = st.slider("COGS % of Revenue", 0.10, 0.95,
                                 value=float(hist_avg.get("cogs_pct", 0.60)),
                                 step=0.01, format="%.0f%%", key=f"model_{ticker}_cogs")
            opex_pct = st.slider("OpEx % of Revenue", 0.05, 0.50,
                                 value=float(hist_avg.get("opex_pct_revenue", 0.25)),
                                 step=0.01, format="%.0f%%", key=f"model_{ticker}_opex")
            tax_rate = st.number_input("Tax Rate %", 0.0, 50.0,
                                       value=float(hist_avg.get("tax_rate", 0.21)) * 100,
                                       step=1.0, key=f"model_{ticker}_tax") / 100

        with col3:
            st.markdown("**Capital & Working Capital**")
            capex_pct = st.slider("CapEx % of Revenue", 0.01, 0.20,
                                  value=float(hist_avg.get("capex_pct_revenue", 0.05)),
                                  step=0.01, format="%.0f%%", key=f"model_{ticker}_capex")
            depr_pct = st.number_input("Depreciation % of Assets", 1.0, 15.0,
                                        value=float(hist_avg.get("depreciation_pct_assets", 0.03)) * 100,
                                        step=0.5, key=f"model_{ticker}_depr") / 100
            ar_days = st.number_input("A/R Days", 5, 120,
                                       value=int(hist_avg.get("ar_days", 30)),
                                       key=f"model_{ticker}_ar")
            inv_days = st.number_input("Inventory Days", 5, 180,
                                        value=int(hist_avg.get("inventory_days", 45)),
                                        key=f"model_{ticker}_inv")
            ap_days = st.number_input("A/P Days", 5, 120,
                                       value=int(hist_avg.get("ap_days", 30)),
                                       key=f"model_{ticker}_ap")

    # ── Build Model ──────────────────────────────────────────────────────
    assumptions = {
        "revenue_growth_rates": growth_rates,
        "cogs_pct": cogs_pct,
        "opex_pct_revenue": opex_pct,
        "tax_rate": tax_rate,
        "capex_pct_revenue": capex_pct,
        "depreciation_pct_assets": depr_pct,
        "ar_days": ar_days,
        "inventory_days": inv_days,
        "ap_days": ap_days,
    }

    try:
        model = build_three_statement_model(fundamentals, assumptions, n_years=5)
    except Exception as e:
        st.error(f"Model computation failed: {e}")
        return

    proj_inc = model["projected_income"]
    proj_bal = model["projected_balance"]
    proj_cf = model["projected_cashflow"]

    # ── Summary Metrics ──────────────────────────────────────────────────
    st.subheader("Projection Summary")
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        terminal_rev = proj_inc["revenue"].iloc[-1]
        st.markdown(metric_card("Terminal Revenue", f"${terminal_rev/1e9:.1f}B" if terminal_rev >= 1e9 else f"${terminal_rev/1e6:.0f}M"),
                    unsafe_allow_html=True)
    with m2:
        terminal_ni = proj_inc["net_income"].iloc[-1]
        st.markdown(metric_card("Terminal Net Income", f"${terminal_ni/1e9:.1f}B" if abs(terminal_ni) >= 1e9 else f"${terminal_ni/1e6:.0f}M"),
                    unsafe_allow_html=True)
    with m3:
        terminal_margin = proj_inc["net_income"].iloc[-1] / proj_inc["revenue"].iloc[-1] * 100 if proj_inc["revenue"].iloc[-1] != 0 else 0
        st.markdown(metric_card("Terminal Net Margin", f"{terminal_margin:.1f}%"), unsafe_allow_html=True)
    with m4:
        terminal_fcf = proj_cf["free_cash_flow"].iloc[-1]
        st.markdown(metric_card("Terminal FCF", f"${terminal_fcf/1e9:.1f}B" if abs(terminal_fcf) >= 1e9 else f"${terminal_fcf/1e6:.0f}M"),
                    unsafe_allow_html=True)

    # ── Revenue & Net Income Chart ───────────────────────────────────────
    _render_projection_chart(inc, proj_inc, ticker)

    # ── Statement Tables ─────────────────────────────────────────────────
    st.markdown("---")

    # Combine historical + projected for display
    with st.expander("Projected Income Statement", expanded=True):
        combined = _combine_historical_projected(inc, proj_inc,
                                                  ["revenue", "cost_of_revenue", "gross_profit",
                                                   "operating_income", "net_income", "ebitda"])
        st.dataframe(combined, use_container_width=True)

    with st.expander("Projected Balance Sheet"):
        st.dataframe(proj_bal, use_container_width=True)

    with st.expander("Projected Cash Flow"):
        st.dataframe(proj_cf, use_container_width=True)


def _render_projection_chart(historical_inc, projected_inc, ticker):
    """Combined bar+line chart: historical + projected revenue and net income."""
    fig = go.Figure()

    # Historical
    if historical_inc is not None and "revenue" in historical_inc.columns:
        hist_rev = historical_inc["revenue"].dropna()
        fig.add_trace(go.Bar(x=hist_rev.index.astype(str), y=hist_rev.values,
                             name="Historical Revenue", marker_color=BLUE, opacity=0.7))
        if "net_income" in historical_inc.columns:
            hist_ni = historical_inc["net_income"].dropna()
            fig.add_trace(go.Scatter(x=hist_ni.index.astype(str), y=hist_ni.values,
                                      name="Historical Net Income", line=dict(color=GREEN, width=2),
                                      mode="lines+markers"))

    # Projected
    fig.add_trace(go.Bar(x=projected_inc.index, y=projected_inc["revenue"],
                         name="Projected Revenue", marker_color=BLUE, opacity=0.4,
                         marker_pattern_shape="/"))
    fig.add_trace(go.Scatter(x=projected_inc.index, y=projected_inc["net_income"],
                              name="Projected Net Income", line=dict(color=GREEN, width=2, dash="dash"),
                              mode="lines+markers"))

    # Projection boundary
    if historical_inc is not None and not historical_inc.empty:
        boundary_x = str(historical_inc.index[0])  # most recent historical
        fig.add_vline(x=boundary_x, line_dash="dot", line_color=TEXT_SECONDARY,
                      annotation_text="Projection Start")

    fig.update_layout(title=f"{ticker} — Historical & Projected Financials",
                      height=450, barmode="overlay", **plotly_theme())
    st.plotly_chart(fig, use_container_width=True)


def _combine_historical_projected(hist_df, proj_df, columns):
    """Combine historical and projected data into one display table."""
    result_rows = {}

    # Historical (limited to available columns)
    if hist_df is not None and not hist_df.empty:
        # Deduplicate index and columns to prevent .loc returning Series instead of scalar
        h_df = hist_df.loc[~hist_df.index.duplicated(keep='first')]
        h_df = h_df.loc[:, ~h_df.columns.duplicated()]
        
        for col in columns:
            if col in h_df.columns:
                for idx in h_df.index:
                    period_label = str(idx)[:10] if hasattr(idx, 'strftime') else str(idx)
                    if col not in result_rows:
                        result_rows[col] = {}
                    
                    val = h_df.loc[idx, col]
                    result_rows[col][f"Hist: {period_label}"] = float(val) if pd.notna(val) else None

    # Projected
    for col in columns:
        proj_col = col
        if proj_col in proj_df.columns:
            for idx in proj_df.index:
                if col not in result_rows:
                    result_rows[col] = {}
                result_rows[col][f"Proj: {idx}"] = proj_df.loc[idx, proj_col]

    if not result_rows:
        return pd.DataFrame()

    df = pd.DataFrame(result_rows).T
    df.index = [c.replace("_", " ").title() for c in df.index]
    return df
