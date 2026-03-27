"""Comparison tab — Normalized peer performance and returns table."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from src.dashboard.theme import plotly_theme, section_header, styled_dataframe
from src.data_ingestion.api_client import fetch_price_data

def render(ticker, info, prices, fundamentals, ratios, peers, period):
    """Render the Comparison tab with normalized performance chart and returns table."""
    if not peers:
        st.info("Select peer tickers in the sidebar to compare performance.")
        return

    all_tickers = [ticker] + [p for p in peers if p != ticker]

    fig = go.Figure()
    returns_data = []

    for t in all_tickers:
        try:
            if t == ticker:
                p = prices
            else:
                p = fetch_price_data(t, period=period)
                
            if p is not None and not p.empty:
                normalized = (p.Close / p.Close.iloc[0]) * 100
                fig.add_trace(
                    go.Scatter(x=p.index, y=normalized, name=t)
                )
                # Calculate period return
                period_return = ((p.Close.iloc[-1] / p.Close.iloc[0]) - 1) * 100
                returns_data.append({"Ticker": t, "Period Return (%)": period_return})
        except Exception:
            pass

    if not returns_data:
        st.info("Could not load price data for the selected tickers.")
        return

    # Apply Tickertape theme
    theme = plotly_theme()
    fig.update_layout(
        title="Normalized Performance (Base=100)",
        height=500,
        **theme,
    )

    st.plotly_chart(fig, use_container_width=True)

    # Returns table
    st.subheader("Period Returns")
    returns_df = pd.DataFrame(returns_data)
    returns_df["Period Return (%)"] = returns_df["Period Return (%)"].round(2)

    def _color_returns(val):
        if isinstance(val, (int, float)):
            color = "#19af55" if val >= 0 else "#d82f44"
            return f"color: {color}; font-weight: 600"
        return ""

    styled = returns_df.style.applymap(
        _color_returns, subset=["Period Return (%)"]
    ).format({"Period Return (%)": "{:+.2f}%"})

    st.dataframe(styled, use_container_width=True)
