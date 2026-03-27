"""
Tab: Financial Statement Deep Analysis
5-year ratio analysis, common-size analysis, industry-specific metrics, trend charts.
"""
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

from src.dashboard.theme import plotly_theme, section_header, styled_dataframe, GREEN, RED, BLUE, TEXT_PRIMARY, TEXT_SECONDARY, format_large_numbers


def render(ticker, info, prices, fundamentals, ratios, peers, period):
    section_header("Financial Statement Analysis", "Deep-dive into income statement, balance sheet, and cash flow with trend analysis")

    inc = fundamentals.get("income_statement") if fundamentals else None
    bal = fundamentals.get("balance_sheet") if fundamentals else None
    cf = fundamentals.get("cash_flow") if fundamentals else None

    if inc is None or inc.empty:
        st.info("No financial statement data available for analysis.")
        return

    # ── Sub-tabs ─────────────────────────────────────────────────────────
    sub1, sub2, sub3 = st.tabs(["Income Statement", "Balance Sheet", "Cash Flow"])

    with sub1:
        _render_income_analysis(inc, ticker)
    with sub2:
        _render_balance_analysis(bal, ticker)
    with sub3:
        _render_cashflow_analysis(cf, ticker)

    st.markdown("---")

    # ── Ratio Trends ─────────────────────────────────────────────────────
    if ratios is not None and not ratios.empty:
        st.subheader("Key Ratio Trends")
        _render_ratio_trends(ratios)

    # ── Auto Insights ────────────────────────────────────────────────────
    _render_auto_insights(inc, bal, cf, ratios, info)


def _render_income_analysis(df, ticker):
    """Income statement trend + common-size analysis."""
    if df is None or df.empty:
        st.info("No income statement data available.")
        return

    # Trend chart
    fig = go.Figure()
    cols_to_plot = [("revenue", "Revenue", BLUE), ("gross_profit", "Gross Profit", GREEN),
                    ("operating_income", "Operating Income", "#624bff"), ("net_income", "Net Income", RED)]

    for col, name, color in cols_to_plot:
        if col in df.columns:
            vals = df[col].dropna()
            if not vals.empty:
                # Use clean lines for all income statement items to avoid blocky grey areas
                fig.add_trace(go.Scatter(
                    x=vals.index.astype(str), 
                    y=vals.values, 
                    name=name,
                    mode="lines+markers",
                    line=dict(color=color, width=2)
                ))

    fig.update_layout(
        title=f"{ticker} — Income Statement Trends", 
        height=400,
        hovermode="x unified",
        **plotly_theme()
    )
    st.plotly_chart(fig, use_container_width=True)

    # Common-size analysis
    with st.expander("Common-Size Analysis (% of Revenue)", expanded=False):
        if "revenue" in df.columns:
            revenue = df["revenue"].replace(0, np.nan)
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            common_size = df[numeric_cols].div(revenue, axis=0) * 100
            common_size = common_size.round(1)
            st.dataframe(common_size, use_container_width=True)

    # Raw data
    with st.expander("Raw Income Statement Data"):
        st.dataframe(format_large_numbers(df), use_container_width=True)


def _render_balance_analysis(df, ticker):
    """Balance sheet trend + common-size analysis."""
    if df is None or df.empty:
        st.info("No balance sheet data available.")
        return

    fig = go.Figure()
    cols_to_plot = [("total_assets", "Total Assets", BLUE), ("total_equity", "Total Equity", GREEN),
                    ("total_liabilities", "Total Liabilities", RED)]

    for col, name, color in cols_to_plot:
        if col in df.columns:
            vals = df[col].dropna()
            if not vals.empty:
                fig.add_trace(go.Bar(x=vals.index.astype(str), y=vals.values, name=name,
                                     marker_color=color, opacity=0.9))

    fig.update_layout(
        title=f"{ticker} — Balance Sheet Trends", 
        height=400,
        barmode="group", 
        bargap=0.25,
        bargroupgap=0.1,
        **plotly_theme()
    )
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("Common-Size Analysis (% of Total Assets)", expanded=False):
        if "total_assets" in df.columns:
            ta = df["total_assets"].replace(0, np.nan)
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            common_size = df[numeric_cols].div(ta, axis=0) * 100
            st.dataframe(common_size.round(1), use_container_width=True)

    with st.expander("Raw Balance Sheet Data"):
        st.dataframe(format_large_numbers(df), use_container_width=True)


def _render_cashflow_analysis(df, ticker):
    """Cash flow trend analysis."""
    if df is None or df.empty:
        st.info("No cash flow data available.")
        return

    fig = go.Figure()
    cols_to_plot = [("operating_cash_flow", "Operating CF", GREEN),
                    ("capital_expenditure", "CapEx", RED)]

    for col, name, color in cols_to_plot:
        if col in df.columns:
            vals = df[col].dropna()
            if not vals.empty:
                fig.add_trace(go.Bar(x=vals.index.astype(str), y=vals.values, name=name,
                                     marker_color=color, opacity=0.7))

    # Add FCF line if both exist
    if "operating_cash_flow" in df.columns and "capital_expenditure" in df.columns:
        ocf = df["operating_cash_flow"].fillna(0)
        capex = df["capital_expenditure"].fillna(0).abs()
        fcf = ocf - capex
        fig.add_trace(go.Scatter(x=fcf.index.astype(str), y=fcf.values, name="Free Cash Flow",
                                  line=dict(color=BLUE, width=3), mode="lines+markers"))

    fig.update_layout(
        title=f"{ticker} — Cash Flow Trends", 
        height=400,
        barmode="group", 
        bargap=0.25,
        bargroupgap=0.1,
        **plotly_theme()
    )
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("Raw Cash Flow Data"):
        st.dataframe(format_large_numbers(df), use_container_width=True)


def _render_ratio_trends(ratios_df):
    """2x3 grid of mini ratio trend charts."""
    ratio_configs = [
        ("gross_margin", "Gross Margin", True),
        ("operating_margin", "Operating Margin", True),
        ("roe", "Return on Equity", True),
        ("roa", "Return on Assets", True),
        ("debt_to_equity", "Debt to Equity", False),
        ("current_ratio", "Current Ratio", False),
    ]

    cols = st.columns(3)
    for i, (col_name, title, is_pct) in enumerate(ratio_configs):
        with cols[i % 3]:
            if col_name in ratios_df.columns:
                vals = ratios_df[col_name].dropna()
                if not vals.empty:
                    fig = go.Figure()
                    y_vals = vals.values * 100 if is_pct else vals.values
                    fig.add_trace(go.Scatter(x=vals.index.astype(str), y=y_vals,
                                             mode="lines+markers", line=dict(color=BLUE, width=2),
                                             fill="tozeroy", fillcolor="rgba(0,136,234,0.1)"))
                    # Average line
                    avg = float(np.nanmean(y_vals))
                    fig.add_hline(y=avg, line_dash="dash", line_color=TEXT_SECONDARY,
                                  annotation_text=f"Avg: {avg:.1f}{'%' if is_pct else ''}")
                    fig.update_layout(title=title, height=220, showlegend=False,
                                      **plotly_theme())
                    if is_pct:
                        fig.update_yaxes(ticksuffix="%")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.caption(f"{title}: No data")
            else:
                st.caption(f"{title}: Not available")

        if i == 2:
            cols = st.columns(3)


def _render_auto_insights(inc, bal, cf, ratios, info):
    """Generate automatic text insights from the data."""
    insights = []

    if inc is not None and "revenue" in inc.columns:
        rev = inc["revenue"].dropna()
        if len(rev) >= 2:
            first, last = float(rev.iloc[-1]), float(rev.iloc[0])
            n = len(rev) - 1
            if first > 0 and last > 0 and n > 0:
                cagr = (last / first) ** (1/n) - 1
                direction = "grew" if cagr > 0 else "declined"
                insights.append(f"Revenue {direction} at a **{abs(cagr)*100:.1f}% CAGR** over {n} years")

    if ratios is not None and not ratios.empty:
        if "net_margin" in ratios.columns:
            nm = ratios["net_margin"].dropna()
            if len(nm) >= 2:
                first_nm, last_nm = float(nm.iloc[-1]) * 100, float(nm.iloc[0]) * 100
                change = "improved" if last_nm > first_nm else "declined"
                insights.append(f"Net margin {change} from **{first_nm:.1f}%** to **{last_nm:.1f}%**")

        if "roe" in ratios.columns:
            roe = ratios["roe"].dropna()
            if not roe.empty:
                avg_roe = float(roe.mean()) * 100
                insights.append(f"Average Return on Equity: **{avg_roe:.1f}%**")

    sector = info.get("sector", "")
    if sector:
        insights.append(f"Sector: **{sector}** — {info.get('industry', 'N/A')}")

    if insights:
        st.subheader("Key Insights")
        for insight in insights:
            st.markdown(f"- {insight}")
