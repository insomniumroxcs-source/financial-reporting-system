"""
Segment Analysis tab – YoY segment revenue growth with stacked bars & waterfall chart.
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
from src.data_processing.segment_parser import (
    extract_segments_yfinance,
    parse_segment_csv,
    get_demo_segments,
    calculate_segment_yoy,
    calculate_segment_contribution,
)


def render(ticker: str, info: dict, prices, fundamentals, ratios, peers, period, **kw):
    """Render the Segment Analysis tab."""
    section_header("Segment Analysis", "Revenue breakdown by business segment with YoY growth")

    # ── Data Source Selector ───────────────────────────────────────────────
    source = st.radio(
        "Data Source",
        ["Auto-detect", "Upload CSV", "Demo Data"],
        horizontal=True,
        help="yfinance has limited segment data. Upload a CSV or use demo data for full analysis.",
    )

    segment_df: Optional[pd.DataFrame] = None

    if source == "Auto-detect":
        with st.spinner("Checking yfinance for segment data..."):
            segment_df = extract_segments_yfinance(ticker)
        if segment_df is None or segment_df.empty:
            st.info(
                "No segment data available via yfinance for this ticker. "
                "Falling back to **Demo Data**."
            )
            segment_df = get_demo_segments(ticker)

    elif source == "Upload CSV":
        uploaded = st.file_uploader(
            "Upload segment data (CSV/Excel)",
            type=["csv", "xlsx", "xls"],
            help="Expected columns: segment, year, revenue. Optional: profit.",
        )
        if uploaded is not None:
            segment_df = parse_segment_csv(uploaded)
            if segment_df is None:
                st.error("Could not parse segment data. Check column names (segment, year, revenue).")
                return
        else:
            st.info("Upload a file to begin analysis.")
            return

    else:  # Demo Data
        segment_df = get_demo_segments(ticker)

    if segment_df is None or segment_df.empty:
        st.warning("No segment data available.")
        return

    # ── Compute YoY & Contribution ─────────────────────────────────────────
    yoy_df = calculate_segment_yoy(segment_df)
    contrib_df = calculate_segment_contribution(segment_df)

    # ── KPI Row ────────────────────────────────────────────────────────────
    segments = segment_df["segment"].unique()
    latest_year = int(segment_df["year"].max())
    latest_total = segment_df[segment_df["year"] == latest_year]["revenue"].sum()
    prev_year_data = segment_df[segment_df["year"] == latest_year - 1]
    prev_total = prev_year_data["revenue"].sum() if not prev_year_data.empty else 0

    total_growth = ((latest_total / prev_total) - 1) * 100 if prev_total > 0 else 0

    cols = st.columns(4)
    with cols[0]:
        st.markdown(metric_card("Total Segments", str(len(segments))), unsafe_allow_html=True)
    with cols[1]:
        st.markdown(
            metric_card("Latest Revenue", f"${latest_total / 1e6:,.0f}M" if latest_total >= 1e6 else f"${latest_total:,.0f}"),
            unsafe_allow_html=True,
        )
    with cols[2]:
        st.markdown(
            metric_card("Total YoY Growth", f"{total_growth:+.1f}%", delta=f"{total_growth:+.1f}%"),
            unsafe_allow_html=True,
        )
    with cols[3]:
        top_seg = (
            segment_df[segment_df["year"] == latest_year]
            .sort_values("revenue", ascending=False)
            .iloc[0]["segment"]
        )
        st.markdown(metric_card("Top Segment", top_seg), unsafe_allow_html=True)

    st.markdown("---")

    # ── Stacked Bar Chart: Revenue by Segment ──────────────────────────────
    section_header("Revenue by Segment", "Stacked view across fiscal years")

    pivot = segment_df.pivot_table(index="year", columns="segment", values="revenue", aggfunc="sum").fillna(0)
    fig_stacked = go.Figure()
    colors = [BLUE, GREEN, RED, "#ff9800", "#9c27b0", "#00bcd4", "#e91e63", "#795548"]
    for i, seg in enumerate(pivot.columns):
        fig_stacked.add_trace(go.Bar(
            name=seg,
            x=[str(y) for y in pivot.index],
            y=pivot[seg],
            marker_color=colors[i % len(colors)],
        ))
    fig_stacked.update_layout(
        barmode="stack",
        height=450,
        **plotly_theme(),
        yaxis_title="Revenue ($M)",
        xaxis_title="Fiscal Year",
        legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5),
    )
    st.plotly_chart(fig_stacked, use_container_width=True)

    # ── YoY Growth Rates Table ─────────────────────────────────────────────
    section_header("YoY Growth Rates", "Per-segment annual growth with conditional coloring")

    if not yoy_df.empty and "yoy_growth" in yoy_df.columns:
        growth_pivot = yoy_df.pivot_table(
            index="segment", columns="year", values="yoy_growth", aggfunc="first"
        )

        def _color_growth(val):
            if pd.isna(val):
                return ""
            color = GREEN if val >= 0 else RED
            return f"color: {color}; font-weight: 600"

        display_growth = growth_pivot.copy()
        for col in display_growth.columns:
            display_growth[col] = display_growth[col].apply(
                lambda v: f"{v * 100:+.1f}%" if pd.notna(v) else "—"
            )

        st.dataframe(
            display_growth.style.applymap(
                lambda v: f"color: {GREEN}; font-weight:600" if v.startswith("+") else
                          (f"color: {RED}; font-weight:600" if v.startswith("-") else ""),
            ),
            use_container_width=True,
        )
    else:
        st.info("Insufficient data for YoY growth calculations.")

    # ── Waterfall Chart: Contribution to Revenue Change ────────────────────
    section_header("Revenue Change Waterfall", "Segment contribution to total revenue change")

    years = sorted(segment_df["year"].unique())
    if len(years) >= 2:
        last_yr = years[-1]
        prev_yr = years[-2]

        last_data = segment_df[segment_df["year"] == last_yr].set_index("segment")["revenue"]
        prev_data = segment_df[segment_df["year"] == prev_yr].set_index("segment")["revenue"]
        all_segs = sorted(set(last_data.index) | set(prev_data.index))

        changes = []
        for seg in all_segs:
            curr = last_data.get(seg, 0)
            prev = prev_data.get(seg, 0)
            changes.append({"segment": seg, "change": curr - prev})
        changes_df = pd.DataFrame(changes).sort_values("change", ascending=False)

        fig_waterfall = go.Figure(go.Waterfall(
            name="Revenue Change",
            orientation="v",
            x=changes_df["segment"].tolist() + ["Total"],
            y=changes_df["change"].tolist() + [0],
            measure=["relative"] * len(changes_df) + ["total"],
            connector=dict(line=dict(color=BORDER, width=1)),
            increasing=dict(marker=dict(color=GREEN)),
            decreasing=dict(marker=dict(color=RED)),
            totals=dict(marker=dict(color=BLUE)),
        ))
        fig_waterfall.update_layout(
            height=420,
            **plotly_theme(),
            yaxis_title=f"Revenue Change (FY{prev_yr}→FY{last_yr})",
            showlegend=False,
        )
        st.plotly_chart(fig_waterfall, use_container_width=True)
    else:
        st.info("Need at least 2 years of data for the waterfall chart.")

    # ── Segment Contribution Pie ───────────────────────────────────────────
    section_header("Segment Mix", f"Revenue contribution in FY{latest_year}")

    latest_contrib = contrib_df[contrib_df["year"] == latest_year].copy()
    if not latest_contrib.empty:
        fig_pie = go.Figure(go.Pie(
            labels=latest_contrib["segment"],
            values=latest_contrib["revenue"],
            hole=0.45,
            marker=dict(colors=colors[:len(latest_contrib)]),
            textinfo="label+percent",
            textfont=dict(color=TEXT_PRIMARY),
        ))
        fig_pie.update_layout(
            height=400,
            paper_bgcolor=WHITE,
            plot_bgcolor=WHITE,
            showlegend=True,
            legend=dict(orientation="h", yanchor="top", y=-0.05, xanchor="center", x=0.5),
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    # ── Disclaimer ─────────────────────────────────────────────────────────
    st.caption(
        "⚠️ Segment data availability depends on company filings and data sources. "
        "yfinance has limited segment coverage; use CSV upload for precise analysis."
    )
