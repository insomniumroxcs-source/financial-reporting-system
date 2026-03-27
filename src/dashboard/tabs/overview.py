"""Overview tab — Simulated Curator Finance Dashboard layout."""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

from src.dashboard.theme import plotly_theme, metric_card, styled_dataframe

def render(ticker, info, prices, fundamentals, ratios, peers, period):
    st.markdown("<br>", unsafe_allow_html=True)
    
    # --- Live Ticker Marquee ---
    marquee_html = f"""
    <div class="glass-ticker" style="border-radius: 9999px; padding: 0.5rem 1.5rem; display: flex; align-items: center; overflow: hidden; margin-bottom: 2rem;">
        <div style="flex-shrink: 0; display: flex; align-items: center; gap: 0.5rem; margin-right: 1.5rem; border-right: 1px solid rgba(66, 72, 81, 0.3); padding-right: 1.5rem;">
            <span style="display: flex; height: 8px; width: 8px; border-radius: 9999px; background-color: var(--color-secondary);"></span>
            <span style="font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: var(--color-secondary);">LIVE MARKET</span>
        </div>
        <div style="display: flex; gap: 3rem; white-space: nowrap; overflow: hidden; animation: var(--animate-marquee);">
            <p style="font-size: 14px; font-weight: 500; color: var(--color-on-surface-variant); margin: 0;">
                <span style="color: var(--color-on-surface); font-weight: 700;">{ticker} Volatility:</span> Tracking 52-week normal range.
            </p>
            <p style="font-size: 14px; font-weight: 500; color: var(--color-on-surface-variant); margin: 0;">
                <span style="color: var(--color-on-surface); font-weight: 700;">FED Rate Decision:</span> Holding steady at 5.25% - 5.50% range.
            </p>
        </div>
    </div>
    """
    st.markdown(marquee_html, unsafe_allow_html=True)

    # --- Hero Section (Mirroring Portfolio from Option 1) ---
    col1, col2 = st.columns([1.8, 1])
    
    with col1:
        current_price = info.get('currentPrice', 0.0)
        daily_change = info.get('regularMarketChangePercent', 0.0)
        daily_change_str = f"{daily_change:.2f}%" if pd.notnull(daily_change) else "0.00%"
        color = "var(--color-secondary)" if daily_change >= 0 else "var(--color-tertiary)"
        
        hero_html = f"""
        <div class="curator-hero" style="min-height: 280px; display: flex; flex-direction: column; justify-content: space-between;">
            <div>
                <span class="curator-hero-label">CURRENT ASSET VALUATION</span>
                <h1 class="curator-hero-value">${current_price:,.2f}</h1>
                <div style="display: flex; align-items: center; gap: 1rem; margin-top: 1rem;">
                    <div style="background-color: rgba(2, 201, 83, 0.1); padding: 0.25rem 0.75rem; border-radius: 9999px;">
                        <span style="color: {color}; font-weight: 700; font-size: 14px;">{daily_change_str} Today</span>
                    </div>
                </div>
            </div>
            <div style="display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 2rem; margin-top: 2rem; border-top: 1px solid rgba(66, 72, 81, 0.1); padding-top: 1rem;">
                <div>
                    <p style="font-size: 10px; font-weight: 700; color: var(--color-on-surface-variant); text-transform: uppercase;">Volume</p>
                    <p style="font-size: 1.125rem; font-weight: 700; font-family: 'Manrope', sans-serif;">{info.get('volume', 0):,}</p>
                </div>
                <div>
                    <p style="font-size: 10px; font-weight: 700; color: var(--color-on-surface-variant); text-transform: uppercase;">Avg Vol (10d)</p>
                    <p style="font-size: 1.125rem; font-weight: 700; font-family: 'Manrope', sans-serif;">{info.get('averageVolume10days', 0):,}</p>
                </div>
                <div>
                    <p style="font-size: 10px; font-weight: 700; color: var(--color-on-surface-variant); text-transform: uppercase;">P/E Ratio</p>
                    <p style="font-size: 1.125rem; font-weight: 700; font-family: 'Manrope', sans-serif;">{info.get('trailingPE', 0):.2f}</p>
                </div>
            </div>
        </div>
        """
        st.markdown(hero_html, unsafe_allow_html=True)

    with col2:
        mmi_html = """
        <div style="background-color: var(--color-surface-container); border-radius: 1rem; padding: 1.5rem; text-align: center; height: 100%;">
            <h3 style="font-size: 12px; font-weight: 700; color: var(--color-on-surface-variant); text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 2rem;">Market Mood Index</h3>
            <p style="font-size: 3rem; font-weight: 900; font-family: 'Manrope', sans-serif; color: var(--color-secondary); line-height: 1;">68</p>
            <p style="font-size: 14px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: var(--color-on-surface); margin-top: 0.5rem;">Greed</p>
            <p style="font-size: 12px; color: var(--color-on-surface-variant); margin-top: 1rem;">Sentiment is bullish. Investors are showing increased risk appetite.</p>
        </div>
        """
        st.markdown(mmi_html, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- Candlestick Chart with Option 2 styling ---
    if prices is not None and not prices.empty:
        fig = make_subplots(rows=1, cols=1)
        fig.add_trace(
            go.Candlestick(
                x=prices.index,
                open=prices.Open, high=prices.High, low=prices.Low, close=prices.Close,
                increasing_line_color="#02c953",
                decreasing_line_color="#ff7350",
            )
        )
        theme = plotly_theme()
        fig.update_layout(
            title=f"<b>{ticker} Asset Performance</b>",
            title_font=dict(size=20, family="'Manrope', sans-serif"),
            xaxis_rangeslider_visible=False,
            height=450,
            showlegend=False,
            **theme,
        )
        st.plotly_chart(fig, use_container_width=True)
