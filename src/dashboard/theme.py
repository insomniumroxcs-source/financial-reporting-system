import streamlit as st
import pandas as pd
import os
from typing import Optional

# ---------------------------------------------------------------------------
# Color palette (Curator Finance Design System)
# ---------------------------------------------------------------------------
DARK_NAVY = "#0c0e11"
BG_LIGHT = "#0c0e11"
GREEN = "#02c953"
RED = "#ff7350"
BLUE = "#c3c7cc"
PURPLE_PREMIUM = "#624bff"
TEXT_PRIMARY = "#e0e6f1"
TEXT_SECONDARY = "#a5abb6"
TEXT_TERTIARY = "#707680"
BORDER = "rgba(66, 72, 81, 0.2)"
WHITE = "#161a1f"  # Used as card background equivalent to surface-container
CARD_SHADOW = "0 1px 2px rgba(0,0,0,0.4)"
CARD_SHADOW_RAISED = "0 3px 12px rgba(0,0,0,0.6)"

_FONT_STACK = "'Inter', sans-serif"

# ---------------------------------------------------------------------------
# inject_theme_css  – call once at the top of the app
# ---------------------------------------------------------------------------
def inject_theme_css() -> None:
    """Inject Curator Finance CSS from style.css"""
    css_file = os.path.join(os.path.dirname(__file__), "assets", "style.css")
    try:
        with open(css_file, "r") as f:
            css_content = f.read()
            st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Failed to load CSS: {e}")

# ---------------------------------------------------------------------------
# plotly_theme  – pass to fig.update_layout(**plotly_theme())
# ---------------------------------------------------------------------------
def plotly_theme() -> dict:
    """Return a Plotly layout dict matching the Curator Finance design system."""
    return dict(
        paper_bgcolor=DARK_NAVY,
        plot_bgcolor=DARK_NAVY,
        font=dict(
            family=_FONT_STACK,
            color=TEXT_PRIMARY,
        ),
        xaxis=dict(
            gridcolor="rgba(66, 72, 81, 0.1)",
            linecolor="rgba(66, 72, 81, 0.2)",
            zeroline=False,
        ),
        yaxis=dict(
            gridcolor="rgba(66, 72, 81, 0.1)",
            linecolor="rgba(66, 72, 81, 0.2)",
            zeroline=False,
        ),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.15,
            xanchor="center",
            x=0.5,
            font=dict(color=TEXT_SECONDARY)
        ),
        margin=dict(l=40, r=20, t=40, b=40),
        colorway=[
            GREEN, BLUE, RED, "#624bff",
            "#ff9800", "#00bcd4", "#e91e63", "#9c27b0",
        ],
        hoverlabel=dict(
            bgcolor="#20262e",
            bordercolor="rgba(66, 72, 81, 0.2)",
            font_color=TEXT_PRIMARY,
        ),
    )

# ---------------------------------------------------------------------------
# metric_card  – returns an HTML snippet for a styled KPI card
# ---------------------------------------------------------------------------
def metric_card(
    label: str,
    value: str,
    delta: Optional[str] = None,
    prefix: str = "",
    suffix: str = "",
    delta_color: bool = True,
) -> str:
    """Return an HTML string for a styled metric card using Curator classes."""
    display_value = f"{prefix}{value}{suffix}"
    
    delta_html = ""
    if delta is not None:
        if delta_color:
            try:
                # Find the first sign to determine color
                color = GREEN if "+" in str(delta) else (RED if "-" in str(delta) else TEXT_SECONDARY)
            except Exception:
                color = TEXT_SECONDARY
        else:
            color = TEXT_SECONDARY
            
        delta_html = (
            f'<div style="font-size:13px;color:{color};margin-top:10px; font-weight:600; font-family:Inter,sans-serif; letter-spacing:-0.01em;">'
            f'— {delta}</div>'
        )

    return (
        f'<div style="background-color:#161a1f; border-radius:12px; padding:20px; box-shadow:0 4px 6px rgba(0,0,0,0.2); height:100%;">'
        f'<div style="font-size:11px; font-weight:800; color:{TEXT_SECONDARY}; text-transform:uppercase; letter-spacing:0.07em; font-family:Inter,sans-serif; margin-bottom:12px;">{label}</div>'
        f'<div style="font-size:32px; font-weight:800; color:{TEXT_PRIMARY}; font-family:Inter,sans-serif; letter-spacing:-0.03em; line-height:1.1;">'
        f'{display_value}</div>'
        f'{delta_html}'
        f'</div>'
    )

# ---------------------------------------------------------------------------
# section_header  – renders a titled section divider
# ---------------------------------------------------------------------------
def section_header(title: str, subtitle: Optional[str] = None) -> None:
    subtitle_html = ""
    if subtitle:
        subtitle_html = (
            f'<div style="font-size:0.875rem;color:{TEXT_SECONDARY};'
            f'margin-top:0.25rem;">{subtitle}</div>'
        )

    st.markdown(
        f'<div style="border-bottom:1px solid {BORDER};'
        f'padding-bottom:1rem;margin-bottom:1.5rem;margin-top:2rem;">'
        f'<div style="font-size:1.5rem;font-weight:800;font-family:\'Manrope\',sans-serif;'
        f'color:{TEXT_PRIMARY};">{title}</div>'
        f'{subtitle_html}'
        f'</div>',
        unsafe_allow_html=True,
    )

def format_large_numbers(df: pd.DataFrame) -> pd.DataFrame:
    """Convert large numeric columns locally to M/B strings for display."""
    res = df.copy()
    for col in res.columns:
        if pd.api.types.is_numeric_dtype(res[col]):
            # If large numbers are found, format the whole column
            if res[col].abs().max() >= 1_000_000:
                def _fmt(x):
                    if pd.isna(x): return x
                    if abs(x) >= 1_000_000_000:
                        return f"{x/1_000_000_000:.2f}B"
                    elif abs(x) >= 1_000_000:
                        return f"{x/1_000_000:.2f}M"
                    return f"{x:,.0f}"
                res[col] = res[col].apply(_fmt)
    return res

def styled_dataframe(
    df: pd.DataFrame,
    pct_cols: Optional[list[str]] = None,
    dollar_cols: Optional[list[str]] = None,
    ratio_cols: Optional[list[str]] = None,
) -> None:
    pct_cols = pct_cols or []
    dollar_cols = dollar_cols or []
    ratio_cols = ratio_cols or []

    col_config: dict = {}
    for c in pct_cols:
        if c in df.columns:
            col_config[c] = st.column_config.NumberColumn(format="%.1f%%")
    for c in dollar_cols:
        if c in df.columns:
            col_config[c] = st.column_config.NumberColumn(format="$%.0f")
    for c in ratio_cols:
        if c in df.columns:
            col_config[c] = st.column_config.NumberColumn(format="%.2f")

    st.dataframe(
        df,
        column_config=col_config,
        use_container_width=True,
        hide_index=True,
    )
