"""
DCF Valuation tab – WACC, FCF projection, sensitivity heatmap, and scenario analysis.
"""
from __future__ import annotations

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from typing import Optional

from src.dashboard.theme import (
    GREEN, RED, BLUE, TEXT_PRIMARY, TEXT_SECONDARY, BORDER, BG_LIGHT, WHITE,
    PURPLE_PREMIUM, plotly_theme, section_header, metric_card,
)
from src.dashboard.components import format_large_number
from src.data_processing.dcf_engine import run_full_dcf


def render(ticker: str, info: dict, prices, fundamentals, ratios, peers, period, **kw):
    """Render the DCF Valuation tab."""
    section_header("DCF Valuation", "Discounted Cash Flow model with sensitivity & scenario analysis")

    # ── Input Panel ────────────────────────────────────────────────────────
    with st.expander("⚙️ DCF Assumptions", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            risk_free = st.number_input("Risk-Free Rate (%)", value=4.25, step=0.25, format="%.2f") / 100
            beta_val = info.get("beta", 1.0) or 1.0
            st.metric("Beta (from market data)", f"{beta_val:.2f}")
            market_premium = st.number_input("Market Premium (%)", value=5.50, step=0.25, format="%.2f") / 100

        with col2:
            cost_of_debt = st.number_input("Cost of Debt (%)", value=5.00, step=0.25, format="%.2f") / 100
            tax_rate = st.number_input("Tax Rate (%)", value=21.0, step=1.0, format="%.1f") / 100
            terminal_growth = st.number_input("Terminal Growth (%)", value=2.50, step=0.25, format="%.2f") / 100

        with col3:
            st.markdown(f"**D/E Ratio** (from data)")
            total_debt = info.get("totalDebt", 0) or 0
            total_cash = info.get("totalCash", 0) or 0
            market_cap = info.get("marketCap", 0) or 0
            if market_cap > 0:
                de_ratio = total_debt / market_cap
                st.metric("Debt/Equity", f"{de_ratio:.2f}")
            else:
                st.metric("Debt/Equity", "N/A")
                de_ratio = 0.3

            g1 = st.number_input("FCF Growth Yr 1 (%)", value=8.0, step=0.5) / 100
            g2 = st.number_input("FCF Growth Yr 2 (%)", value=7.0, step=0.5) / 100

        g3 = st.number_input("FCF Growth Yr 3 (%)", value=6.0, step=0.5, key="g3") / 100
        g4 = st.number_input("FCF Growth Yr 4 (%)", value=5.0, step=0.5, key="g4") / 100
        g5 = st.number_input("FCF Growth Yr 5 (%)", value=4.0, step=0.5, key="g5") / 100

    # ── Run DCF Engine ─────────────────────────────────────────────────────
    assumptions = {
        "risk_free_rate": risk_free,
        "market_premium": market_premium,
        "cost_of_debt": cost_of_debt,
        "tax_rate": tax_rate,
        "terminal_growth": terminal_growth,
        "fcf_growth_rates": [g1, g2, g3, g4, g5],
    }

    cashflow_df = fundamentals.get("cash_flow") if fundamentals else None
    ratios_df = ratios if ratios is not None and not ratios.empty else None

    try:
        dcf = run_full_dcf(info, ratios_df, cashflow_df, assumptions)
    except Exception as e:
        st.error(f"DCF calculation failed: {e}")
        return

    result = dcf["dcf_result"]
    current_price = dcf.get("current_price", 0) or 0
    fair_value = result.get("fair_value_per_share", 0)
    upside = result.get("upside_pct", 0)

    # ── WACC Breakdown ─────────────────────────────────────────────────────
    section_header("WACC Breakdown", "Weighted Average Cost of Capital calculation")

    wacc_cols = st.columns(4)
    with wacc_cols[0]:
        st.markdown(metric_card("WACC", f"{dcf['wacc'] * 100:.2f}%"), unsafe_allow_html=True)
    with wacc_cols[1]:
        st.markdown(metric_card("Cost of Equity", f"{dcf['cost_of_equity'] * 100:.2f}%"), unsafe_allow_html=True)
    with wacc_cols[2]:
        st.markdown(metric_card("Equity Weight", f"{dcf['equity_weight'] * 100:.1f}%"), unsafe_allow_html=True)
    with wacc_cols[3]:
        st.markdown(metric_card("Debt Weight", f"{dcf['debt_weight'] * 100:.1f}%"), unsafe_allow_html=True)

    # WACC formula
    st.markdown(
        f"<div style='background:{BG_LIGHT};border:1px solid {BORDER};border-radius:4px;"
        f"padding:12px 16px;font-size:13px;color:{TEXT_SECONDARY};margin:8px 0 16px 0;'>"
        f"WACC = E/(E+D) × Ke + D/(E+D) × Kd × (1−t) = "
        f"{dcf['equity_weight']:.1%} × {dcf['cost_of_equity']:.2%} + "
        f"{dcf['debt_weight']:.1%} × {dcf['cost_of_debt']:.2%} × (1−{dcf['tax_rate']:.0%})"
        f" = <b>{dcf['wacc']:.2%}</b></div>",
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # ── FCF Projection Table ───────────────────────────────────────────────
    section_header("FCF Projection", "5-year projected free cash flow")

    fcf_data = {
        "Year": [f"Year {i+1}" for i in range(5)],
        "Growth Rate": [f"{r*100:.1f}%" for r in dcf["growth_rates"][:5]],
        "Projected FCF": [format_large_number(f) for f in dcf["projected_fcf"]],
    }
    st.dataframe(pd.DataFrame(fcf_data), use_container_width=True, hide_index=True)

    # FCF bar chart
    fig_fcf = go.Figure()
    fig_fcf.add_trace(go.Bar(
        x=[f"Year {i+1}" for i in range(5)],
        y=dcf["projected_fcf"],
        marker_color=BLUE,
        text=[format_large_number(f) for f in dcf["projected_fcf"]],
        textposition="outside",
    ))
    fig_fcf.update_layout(height=350, **plotly_theme(), yaxis_title="Free Cash Flow ($)")
    st.plotly_chart(fig_fcf, use_container_width=True)

    st.markdown("---")

    # ── DCF Result Card ────────────────────────────────────────────────────
    section_header("Valuation Result", "Enterprise Value → Equity Value → Fair Value per Share")

    res_cols = st.columns(4)
    with res_cols[0]:
        st.markdown(metric_card("Enterprise Value", format_large_number(result["enterprise_value"])), unsafe_allow_html=True)
    with res_cols[1]:
        net_debt_val = dcf.get("net_debt", 0)
        st.markdown(metric_card("Net Debt", format_large_number(net_debt_val)), unsafe_allow_html=True)
    with res_cols[2]:
        st.markdown(metric_card("Equity Value", format_large_number(result["equity_value"])), unsafe_allow_html=True)
    with res_cols[3]:
        delta_str = f"{upside * 100:+.1f}%" if upside and not np.isnan(upside) else None
        st.markdown(
            metric_card(
                "Fair Value / Share",
                f"${fair_value:,.2f}" if fair_value and not np.isnan(fair_value) else "N/A",
                delta=delta_str,
            ),
            unsafe_allow_html=True,
        )

    # Current vs Fair Value comparison
    if current_price > 0 and fair_value and not np.isnan(fair_value):
        verdict_color = GREEN if fair_value > current_price else RED
        verdict_text = "UNDERVALUED" if fair_value > current_price else "OVERVALUED"
        st.markdown(
            f"<div style='text-align:center;padding:12px;background:{BG_LIGHT};"
            f"border:1px solid {BORDER};border-radius:4px;margin:12px 0;'>"
            f"Current Price: <b>${current_price:,.2f}</b> &nbsp;|&nbsp; "
            f"Fair Value: <b>${fair_value:,.2f}</b> &nbsp;|&nbsp; "
            f"<span style='color:{verdict_color};font-weight:700;'>{verdict_text} "
            f"({upside * 100:+.1f}%)</span></div>",
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # ── Sensitivity Heatmap ────────────────────────────────────────────────
    section_header("Sensitivity Analysis", "Fair value across WACC and Terminal Growth scenarios")

    sens_df = dcf["sensitivity"]
    if sens_df is not None and not sens_df.empty:
        # Convert to numeric for heatmap
        numeric_sens = sens_df.apply(pd.to_numeric, errors="coerce")

        fig_heat = go.Figure(data=go.Heatmap(
            z=numeric_sens.values,
            x=numeric_sens.columns.tolist(),
            y=numeric_sens.index.tolist(),
            colorscale=[
                [0.0, RED],
                [0.5, WHITE],
                [1.0, GREEN],
            ],
            text=numeric_sens.applymap(lambda v: f"${v:,.0f}" if pd.notna(v) else "").values,
            texttemplate="%{text}",
            textfont=dict(size=10),
            hovertemplate="WACC: %{y}<br>Terminal Growth: %{x}<br>Fair Value: %{text}<extra></extra>",
        ))
        fig_heat.update_layout(
            height=450,
            paper_bgcolor=WHITE,
            plot_bgcolor=WHITE,
            xaxis_title="Terminal Growth Rate",
            yaxis_title="WACC",
            font=dict(color=TEXT_PRIMARY),
        )
        # Highlight current price row/col
        st.plotly_chart(fig_heat, use_container_width=True)
    else:
        st.info("Sensitivity analysis unavailable.")

    st.markdown("---")

    # ── Scenario Cards ─────────────────────────────────────────────────────
    section_header("Scenario Analysis", "Bull / Base / Bear cases")

    scenarios = dcf.get("scenarios", {})
    if scenarios:
        scenario_cols = st.columns(3)
        for i, (key, label, color) in enumerate([
            ("bull", "🐂 Bull Case", GREEN),
            ("base", "📊 Base Case", BLUE),
            ("bear", "🐻 Bear Case", RED),
        ]):
            sc = scenarios.get(key, {})
            fv = sc.get("fair_value_per_share", 0)
            ups = sc.get("upside_pct", 0)
            with scenario_cols[i]:
                st.markdown(
                    f"<div style='background:{WHITE};border:2px solid {color};border-radius:8px;"
                    f"padding:20px;text-align:center;'>"
                    f"<div style='font-size:18px;font-weight:700;color:{color};margin-bottom:8px;'>"
                    f"{label}</div>"
                    f"<div style='font-size:28px;font-weight:700;color:{TEXT_PRIMARY};'>"
                    f"${fv:,.2f}</div>"
                    f"<div style='font-size:14px;color:{color};margin-top:4px;'>"
                    f"{ups * 100:+.1f}% upside</div>"
                    f"<div style='font-size:11px;color:{TEXT_SECONDARY};margin-top:8px;'>"
                    f"WACC: {sc.get('wacc', 0):.1%} | TG: {sc.get('terminal_growth', 0):.1%}</div>"
                    f"<div style='font-size:11px;color:{TEXT_SECONDARY};margin-top:2px;'>"
                    f"{sc.get('description', '')}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
    else:
        st.info("Scenario analysis unavailable.")

    st.caption(
        "⚠️ DCF models are sensitive to assumptions. The fair value estimate should be "
        "used as one of several inputs in investment analysis, not as a standalone recommendation."
    )
