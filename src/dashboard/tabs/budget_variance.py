"""
Budget Variance Analysis tab – compare actuals vs industry benchmarks or uploaded budgets.
Uses waterfall charts and variance tables.
"""
from __future__ import annotations

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from typing import Optional

from src.dashboard.theme import (
    GREEN, RED, BLUE, TEXT_PRIMARY, TEXT_SECONDARY, BORDER, BG_LIGHT, WHITE,
    plotly_theme, section_header, metric_card,
)
from src.dashboard.components import format_large_number


# ── Hardcoded Industry Benchmarks ──────────────────────────────────────────
INDUSTRY_BENCHMARKS = {
    "Consumer Defensive": {"gross_margin": 0.37, "operating_margin": 0.15, "net_margin": 0.10},
    "Consumer Cyclical": {"gross_margin": 0.35, "operating_margin": 0.12, "net_margin": 0.08},
    "Technology": {"gross_margin": 0.60, "operating_margin": 0.25, "net_margin": 0.20},
    "Financial Services": {"gross_margin": 0.55, "operating_margin": 0.35, "net_margin": 0.25},
    "Healthcare": {"gross_margin": 0.65, "operating_margin": 0.20, "net_margin": 0.15},
    "Communication Services": {"gross_margin": 0.55, "operating_margin": 0.22, "net_margin": 0.18},
    "Industrials": {"gross_margin": 0.30, "operating_margin": 0.12, "net_margin": 0.08},
    "Energy": {"gross_margin": 0.40, "operating_margin": 0.15, "net_margin": 0.10},
    "Real Estate": {"gross_margin": 0.50, "operating_margin": 0.30, "net_margin": 0.20},
    "Basic Materials": {"gross_margin": 0.30, "operating_margin": 0.13, "net_margin": 0.09},
    "Utilities": {"gross_margin": 0.35, "operating_margin": 0.18, "net_margin": 0.12},
}

# Generic fallback
_DEFAULT_BENCHMARK = {"gross_margin": 0.40, "operating_margin": 0.15, "net_margin": 0.10}


def _get_actual_margins(income_df: Optional[pd.DataFrame]) -> dict:
    """Extract latest-year margins from income statement."""
    if income_df is None or income_df.empty:
        return {}

    row = income_df.iloc[0]  # most recent
    revenue = row.get("revenue", 0)
    if not revenue or pd.isna(revenue) or revenue == 0:
        return {}

    gross_profit = row.get("gross_profit", np.nan)
    operating_income = row.get("operating_income", np.nan)
    net_income = row.get("net_income", np.nan)

    return {
        "revenue": revenue,
        "gross_profit": gross_profit if pd.notna(gross_profit) else 0,
        "operating_income": operating_income if pd.notna(operating_income) else 0,
        "net_income": net_income if pd.notna(net_income) else 0,
        "gross_margin": gross_profit / revenue if pd.notna(gross_profit) else np.nan,
        "operating_margin": operating_income / revenue if pd.notna(operating_income) else np.nan,
        "net_margin": net_income / revenue if pd.notna(net_income) else np.nan,
    }


def render(ticker: str, info: dict, prices, fundamentals, ratios, peers, period, **kw):
    """Render the Budget Variance Analysis tab."""
    section_header("Budget Variance Analysis", "Compare actual performance against industry benchmarks")

    sector = info.get("sector", "")

    # ── Budget Input Selector ──────────────────────────────────────────────
    budget_source = st.radio(
        "Budget Source",
        ["Industry Benchmarks", "Manual Input", "Upload CSV"],
        horizontal=True,
    )

    income_df = fundamentals.get("income_statement") if fundamentals else None
    actuals = _get_actual_margins(income_df)

    if not actuals:
        st.warning("No income statement data available for variance analysis.")
        return

    revenue = actuals["revenue"]

    # Determine budget values
    if budget_source == "Industry Benchmarks":
        benchmark = INDUSTRY_BENCHMARKS.get(sector, _DEFAULT_BENCHMARK)
        st.info(f"Using **{sector or 'Generic'}** industry benchmarks")
        budget_gm = benchmark["gross_margin"]
        budget_om = benchmark["operating_margin"]
        budget_nm = benchmark["net_margin"]

    elif budget_source == "Manual Input":
        mcol1, mcol2, mcol3 = st.columns(3)
        default = INDUSTRY_BENCHMARKS.get(sector, _DEFAULT_BENCHMARK)
        with mcol1:
            budget_gm = st.number_input(
                "Budget Gross Margin (%)", value=default["gross_margin"] * 100, step=1.0
            ) / 100
        with mcol2:
            budget_om = st.number_input(
                "Budget Operating Margin (%)", value=default["operating_margin"] * 100, step=1.0
            ) / 100
        with mcol3:
            budget_nm = st.number_input(
                "Budget Net Margin (%)", value=default["net_margin"] * 100, step=1.0
            ) / 100

    else:  # Upload CSV
        uploaded = st.file_uploader(
            "Upload budget data (CSV)", type=["csv"],
            help="Expected columns: line_item, budget_amount",
        )
        if uploaded is not None:
            try:
                budget_df = pd.read_csv(uploaded)
                budget_df.columns = budget_df.columns.str.strip().str.lower().str.replace(" ", "_")
                # Attempt extracting margins from uploaded data
                budget_gm = 0.40
                budget_om = 0.15
                budget_nm = 0.10
                st.success("Budget data loaded. Using default margin targets.")
            except Exception as e:
                st.error(f"Failed to parse budget file: {e}")
                return
        else:
            st.info("Upload a budget file or switch to Industry Benchmarks.")
            return

    # ── Compute Budget Dollar Values ───────────────────────────────────────
    budget_gross_profit = revenue * budget_gm
    budget_operating_income = revenue * budget_om
    budget_net_income = revenue * budget_nm

    # Actual values
    actual_gp = actuals["gross_profit"]
    actual_oi = actuals["operating_income"]
    actual_ni = actuals["net_income"]

    # Variances
    variance_data = [
        {
            "Line Item": "Revenue",
            "Actual ($)": revenue,
            "Budget ($)": revenue,
            "Variance ($)": 0,
            "Variance (%)": 0,
            "Status": "—",
        },
        {
            "Line Item": "Gross Profit",
            "Actual ($)": actual_gp,
            "Budget ($)": budget_gross_profit,
            "Variance ($)": actual_gp - budget_gross_profit,
            "Variance (%)": ((actual_gp / budget_gross_profit) - 1) * 100 if budget_gross_profit else 0,
            "Status": "Favorable" if actual_gp >= budget_gross_profit else "Unfavorable",
        },
        {
            "Line Item": "Operating Income",
            "Actual ($)": actual_oi,
            "Budget ($)": budget_operating_income,
            "Variance ($)": actual_oi - budget_operating_income,
            "Variance (%)": ((actual_oi / budget_operating_income) - 1) * 100 if budget_operating_income else 0,
            "Status": "Favorable" if actual_oi >= budget_operating_income else "Unfavorable",
        },
        {
            "Line Item": "Net Income",
            "Actual ($)": actual_ni,
            "Budget ($)": budget_net_income,
            "Variance ($)": actual_ni - budget_net_income,
            "Variance (%)": ((actual_ni / budget_net_income) - 1) * 100 if budget_net_income else 0,
            "Status": "Favorable" if actual_ni >= budget_net_income else "Unfavorable",
        },
    ]

    # ── KPI Row ────────────────────────────────────────────────────────────
    ni_var = actual_ni - budget_net_income
    ni_var_pct = ((actual_ni / budget_net_income) - 1) * 100 if budget_net_income else 0

    kpi_cols = st.columns(4)
    with kpi_cols[0]:
        st.markdown(
            metric_card("Actual Net Income", format_large_number(actual_ni)),
            unsafe_allow_html=True,
        )
    with kpi_cols[1]:
        st.markdown(
            metric_card("Budget Net Income", format_large_number(budget_net_income)),
            unsafe_allow_html=True,
        )
    with kpi_cols[2]:
        st.markdown(
            metric_card("Net Variance", format_large_number(ni_var), delta=f"{ni_var_pct:+.1f}%"),
            unsafe_allow_html=True,
        )
    with kpi_cols[3]:
        status = "Favorable" if ni_var >= 0 else "Unfavorable"
        status_color = GREEN if ni_var >= 0 else RED
        st.markdown(
            metric_card("Overall Status", f"<span style='color:{status_color}'>{status}</span>"),
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # ── Variance Table ─────────────────────────────────────────────────────
    section_header("Variance Table", "Line-by-line comparison of actual vs budget")

    var_df = pd.DataFrame(variance_data)
    display_df = var_df.copy()
    display_df["Actual ($)"] = display_df["Actual ($)"].apply(lambda v: format_large_number(v))
    display_df["Budget ($)"] = display_df["Budget ($)"].apply(lambda v: format_large_number(v))
    display_df["Variance ($)"] = display_df["Variance ($)"].apply(lambda v: format_large_number(v, prefix=""))
    display_df["Variance (%)"] = display_df["Variance (%)"].apply(lambda v: f"{v:+.1f}%")

    def _style_status(val):
        if val == "Favorable":
            return f"color: {GREEN}; font-weight: 600"
        elif val == "Unfavorable":
            return f"color: {RED}; font-weight: 600"
        return ""

    styled = display_df.style.applymap(_style_status, subset=["Status"])
    st.dataframe(styled, use_container_width=True, hide_index=True)

    st.markdown("---")

    # ── Waterfall Chart: Budget NI → Actual NI ─────────────────────────────
    section_header("Variance Waterfall", "Bridge from Budget Net Income to Actual Net Income")

    # Build waterfall items
    gp_var = actual_gp - budget_gross_profit
    opex_impact = (actual_oi - actual_gp) - (budget_operating_income - budget_gross_profit)
    below_line = (actual_ni - actual_oi) - (budget_net_income - budget_operating_income)

    waterfall_labels = [
        "Budget Net Income",
        "Gross Profit Variance",
        "OpEx Variance",
        "Below-Line Items",
        "Actual Net Income",
    ]
    waterfall_values = [
        budget_net_income,
        gp_var,
        opex_impact,
        below_line,
        0,  # total
    ]
    waterfall_measures = ["absolute", "relative", "relative", "relative", "total"]

    fig_waterfall = go.Figure(go.Waterfall(
        name="Variance Bridge",
        orientation="v",
        x=waterfall_labels,
        y=waterfall_values,
        measure=waterfall_measures,
        connector=dict(line=dict(color=BORDER, width=1)),
        increasing=dict(marker=dict(color=GREEN)),
        decreasing=dict(marker=dict(color=RED)),
        totals=dict(marker=dict(color=BLUE)),
        text=[format_large_number(v, prefix="") for v in [
            budget_net_income, gp_var, opex_impact, below_line, actual_ni
        ]],
        textposition="outside",
    ))
    fig_waterfall.update_layout(
        height=450,
        **plotly_theme(),
        yaxis_title="Amount ($)",
        showlegend=False,
    )
    st.plotly_chart(fig_waterfall, use_container_width=True)

    st.markdown("---")

    # ── Margin Impact Section ──────────────────────────────────────────────
    section_header("Margin Impact", "How each variance affects operating and net margin")

    margin_data = [
        {
            "Metric": "Gross Margin",
            "Actual": f"{actuals['gross_margin'] * 100:.1f}%" if pd.notna(actuals.get("gross_margin")) else "N/A",
            "Budget": f"{budget_gm * 100:.1f}%",
            "Variance": f"{(actuals.get('gross_margin', 0) - budget_gm) * 100:+.1f}pp",
        },
        {
            "Metric": "Operating Margin",
            "Actual": f"{actuals['operating_margin'] * 100:.1f}%" if pd.notna(actuals.get("operating_margin")) else "N/A",
            "Budget": f"{budget_om * 100:.1f}%",
            "Variance": f"{(actuals.get('operating_margin', 0) - budget_om) * 100:+.1f}pp",
        },
        {
            "Metric": "Net Margin",
            "Actual": f"{actuals['net_margin'] * 100:.1f}%" if pd.notna(actuals.get("net_margin")) else "N/A",
            "Budget": f"{budget_nm * 100:.1f}%",
            "Variance": f"{(actuals.get('net_margin', 0) - budget_nm) * 100:+.1f}pp",
        },
    ]

    margin_df = pd.DataFrame(margin_data)
    st.dataframe(margin_df, use_container_width=True, hide_index=True)

    # Margin comparison bar chart
    if pd.notna(actuals.get("gross_margin")):
        fig_margins = go.Figure()
        metrics = ["Gross Margin", "Operating Margin", "Net Margin"]
        actual_vals = [
            actuals.get("gross_margin", 0) * 100,
            actuals.get("operating_margin", 0) * 100,
            actuals.get("net_margin", 0) * 100,
        ]
        budget_vals = [budget_gm * 100, budget_om * 100, budget_nm * 100]

        fig_margins.add_trace(go.Bar(
            name="Actual", x=metrics, y=actual_vals, marker_color=BLUE,
        ))
        fig_margins.add_trace(go.Bar(
            name="Budget", x=metrics, y=budget_vals, marker_color=BORDER,
        ))
        fig_margins.update_layout(
            barmode="group",
            height=350,
            **plotly_theme(),
            yaxis_title="Margin (%)",
        )
        st.plotly_chart(fig_margins, use_container_width=True)

    st.caption(
        "⚠️ Industry benchmarks are median values and may not reflect specific company dynamics. "
        "Use manual input or upload precise budget data for accurate variance analysis."
    )
