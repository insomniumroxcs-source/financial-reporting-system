"""
Tab: Deal Insights & Corporate Actions
M&A news, corporate actions, ownership analysis from yfinance.
"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime

from src.dashboard.theme import plotly_theme, section_header, BLUE, GREEN, RED, TEXT_PRIMARY, TEXT_SECONDARY, BG_LIGHT


# M&A related keywords
DEAL_KEYWORDS = [
    "acquire", "acquisition", "merger", "merge", "deal", "buyout", "takeover",
    "stake", "partnership", "joint venture", "divestiture", "spin-off", "spinoff",
    "ipo", "offering", "investment", "divest", "sell", "purchase", "bid",
]


@st.cache_data(ttl=3600, show_spinner="Loading news...")
def _fetch_news(ticker):
    import yfinance as yf
    try:
        stock = yf.Ticker(ticker)
        return stock.news or []
    except Exception:
        return []


@st.cache_data(ttl=3600, show_spinner="Loading corporate actions...")
def _fetch_actions(ticker):
    import yfinance as yf
    try:
        stock = yf.Ticker(ticker)
        result = {}
        try:
            result["splits"] = stock.splits
        except Exception:
            result["splits"] = pd.Series(dtype=float)
        try:
            result["dividends"] = stock.dividends
        except Exception:
            result["dividends"] = pd.Series(dtype=float)
        try:
            result["major_holders"] = stock.major_holders
        except Exception:
            result["major_holders"] = None
        try:
            result["institutional_holders"] = stock.institutional_holders
        except Exception:
            result["institutional_holders"] = None
        return result
    except Exception:
        return {}


def render(ticker, info, prices, fundamentals, ratios, peers, period):
    section_header("Deal Insights & Corporate Actions",
                   "M&A activity, corporate actions, and ownership breakdown")

    tab_actions, tab_ownership = st.tabs(["Corporate Actions", "Ownership"])

    # ── Corporate Actions ────────────────────────────────────────────────
    with tab_actions:
        actions = _fetch_actions(ticker)
        _render_corporate_actions(actions, ticker)

    # ── Ownership ────────────────────────────────────────────────────────
    with tab_ownership:
        actions = _fetch_actions(ticker)
        _render_ownership(actions, ticker)

    st.caption("Data sourced from Yahoo Finance. M&A deal data is limited to news feed — "
               "no structured deal database is available without premium data providers.")



def _render_corporate_actions(actions, ticker):
    if not actions:
        st.info("No corporate action data available.")
        return

    # Dividends
    dividends = actions.get("dividends")
    if dividends is not None and not dividends.empty:
        st.subheader("Dividend History")
        # Last 20 dividends
        recent_div = dividends.tail(40)
        fig = go.Figure()
        fig.add_trace(go.Bar(x=recent_div.index, y=recent_div.values,
                             marker_color=GREEN, name="Dividend"))
        fig.update_layout(title=f"{ticker} — Dividend History", height=350,
                          yaxis_title="Dividend per Share ($)", **plotly_theme())
        st.plotly_chart(fig, use_container_width=True)

        with st.expander("Dividend Data Table"):
            div_df = pd.DataFrame({"Date": recent_div.index, "Dividend": recent_div.values})
            st.dataframe(div_df, use_container_width=True)
    else:
        st.info("No dividend history available.")

    # Splits
    splits = actions.get("splits")
    if splits is not None and not splits.empty:
        st.subheader("Stock Splits")
        split_df = pd.DataFrame({"Date": splits.index, "Ratio": splits.values})
        st.dataframe(split_df, use_container_width=True)
    else:
        st.info("No stock split history available.")


def _render_ownership(actions, ticker):
    """Display ownership breakdown."""
    if not actions:
        st.info("No ownership data available.")
        return

    col1, col2 = st.columns(2)

    # Major holders
    with col1:
        major = actions.get("major_holders")
        if major is not None and not major.empty:
            st.subheader("Major Holders")
            st.dataframe(major, use_container_width=True)
        else:
            st.info("No major holder data available.")

    # Institutional holders
    with col2:
        inst = actions.get("institutional_holders")
        if inst is not None and not inst.empty:
            st.subheader("Top Institutional Holders")
            top10 = inst.head(10)
            st.dataframe(top10, use_container_width=True)
        else:
            st.info("No institutional holder data available.")

    # Pie chart for ownership if major holders available
    major = actions.get("major_holders")
    if major is not None and not major.empty:
        try:
            # Try to extract % values
            values = []
            labels = []
            for _, row in major.iterrows():
                val_str = str(row.iloc[0]).replace("%", "").strip()
                try:
                    val = float(val_str)
                    values.append(val)
                    labels.append(str(row.iloc[1]).strip())
                except ValueError:
                    pass

            if values:
                fig = go.Figure(data=[go.Pie(labels=labels, values=values,
                                             hole=0.4, marker_colors=[BLUE, GREEN, RED, "#624bff"])])
                fig.update_layout(title="Ownership Breakdown", height=350, **plotly_theme())
                st.plotly_chart(fig, use_container_width=True)
        except Exception:
            pass
