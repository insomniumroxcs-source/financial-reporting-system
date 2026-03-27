"""Technical tab — Moving averages and RSI analysis."""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.dashboard.theme import plotly_theme, section_header, styled_dataframe


def render(ticker, info, prices, fundamentals, ratios, peers, period):
    """Render the Technical tab with moving averages and RSI subplot."""
    if prices is None or prices.empty:
        st.info("No price data available for technical analysis.")
        return

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.65, 0.35],
        vertical_spacing=0.05,
        subplot_titles=("Moving Averages", "RSI (14)"),
    )

    # Close price line
    fig.add_trace(
        go.Scatter(
            x=prices.index,
            y=prices.Close,
            name="Close",
            line=dict(color="#0088ea", width=1.5),
        ),
        row=1,
        col=1,
    )

    # Moving averages
    ma_config = [
        (20, "#ff9800", "solid"),
        (50, "#624bff", "solid"),
        (200, "#d82f44", "dash"),
    ]
    for ma, color, dash in ma_config:
        if len(prices) >= ma:
            fig.add_trace(
                go.Scatter(
                    x=prices.index,
                    y=prices.Close.rolling(ma).mean(),
                    name=f"{ma}d MA",
                    line=dict(color=color, dash=dash),
                ),
                row=1,
                col=1,
            )

    # RSI calculation (14-period)
    delta = prices.Close.diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))

    # RSI line
    fig.add_trace(
        go.Scatter(
            x=prices.index,
            y=rsi,
            name="RSI",
            line=dict(color="#0088ea", width=1.5),
        ),
        row=2,
        col=1,
    )

    # Overbought / oversold reference lines
    fig.add_hline(
        y=70,
        line_dash="dash",
        line_color="#d82f44",
        annotation_text="Overbought (70)",
        annotation_position="right",
        row=2,
        col=1,
    )
    fig.add_hline(
        y=30,
        line_dash="dash",
        line_color="#19af55",
        annotation_text="Oversold (30)",
        annotation_position="right",
        row=2,
        col=1,
    )

    # Apply Tickertape theme
    theme = plotly_theme()
    fig.update_layout(
        height=500,
        **theme,
    )
    fig.update_yaxes(range=[0, 100], row=2, col=1)

    st.plotly_chart(fig, use_container_width=True)
