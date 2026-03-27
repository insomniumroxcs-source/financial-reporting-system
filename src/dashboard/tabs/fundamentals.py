"""Fundamentals tab — Financial statements and key ratios."""

import streamlit as st
import plotly.graph_objects as go

from src.dashboard.theme import plotly_theme, section_header, styled_dataframe
from src.data_processing.calculator import compute_all_ratios


def render(ticker, info, prices, fundamentals, ratios, peers, period):
    """Render the Fundamentals tab with financial statements and ratios."""
    inc = fundamentals.get("income_statement") if fundamentals else None
    bal = fundamentals.get("balance_sheet") if fundamentals else None
    cf = fundamentals.get("cash_flow") if fundamentals else None

    for name, df in [
        ("Income Statement", inc),
        ("Balance Sheet", bal),
        ("Cash Flow", cf),
    ]:
        with st.expander(name, expanded=(name == "Income Statement")):
            if df is not None and not df.empty:
                from src.dashboard.theme import format_large_numbers
                st.dataframe(format_large_numbers(df), use_container_width=True)
            else:
                st.info(f"No {name} data available.")

    # Key ratios table
    if ratios is not None and not ratios.empty:
        st.subheader("Key Ratios")

        pct_cols = [
            "gross_margin",
            "operating_margin",
            "net_margin",
            "ebitda_margin",
            "roe",
            "roa",
        ]
        ratio_cols = [
            "current_ratio",
            "debt_to_equity",
            "interest_coverage",
        ]

        styled_dataframe(ratios, pct_cols=pct_cols, ratio_cols=ratio_cols)
    else:
        st.info("No ratio data available.")
