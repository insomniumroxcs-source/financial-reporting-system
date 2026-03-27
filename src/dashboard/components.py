"""
Shared UI components for the Streamlit financial dashboard.
Provides sidebar setup, KPI display, download helpers, and formatters.
"""

from __future__ import annotations

import base64
from datetime import date
from typing import Optional

import streamlit as st
import streamlit.components.v1 as components

from src.dashboard.theme import (
    BLUE,
    DARK_NAVY,
    GREEN,
    RED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    WHITE,
    metric_card,
    section_header,
)


# ---------------------------------------------------------------------------
# js_download_button  – blob-based download via injected JS
# ---------------------------------------------------------------------------
def js_download_button(data: bytes, filename: str, mime: str, label: str) -> None:
    """Render a download button that triggers a JS Blob download."""
    b64 = base64.b64encode(data).decode()
    btn_id = f"dl_{hash(filename) % 100000}"
    html_code = f"""
    <button id="{btn_id}" style="
        display:block;width:100%;padding:0.65rem 1rem;
        background:{BLUE};color:#fff;
        border-radius:8px;border:none;
        font-weight:600;font-size:14px;cursor:pointer;
        font-family:Inter,sans-serif;text-align:center;
        transition:opacity 0.15s ease;
    " onmouseover="this.style.opacity='0.85'" onmouseout="this.style.opacity='1'">
        {label}
    </button>
    <script>
    document.getElementById("{btn_id}").addEventListener("click", function() {{
        var b64 = "{b64}";
        var byteChars = atob(b64);
        var byteArray = new Uint8Array(byteChars.length);
        for (var i = 0; i < byteChars.length; i++) {{
            byteArray[i] = byteChars.charCodeAt(i);
        }}
        var blob = new Blob([byteArray], {{type: "{mime}"}});
        var url = URL.createObjectURL(blob);
        var a = document.createElement("a");
        a.href = url;
        a.download = "{filename}";
        document.body.appendChild(a);
        a.click();
        setTimeout(function() {{
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }}, 100);
    }});
    </script>
    """
    components.html(html_code, height=50)


# ---------------------------------------------------------------------------
# format_large_number
# ---------------------------------------------------------------------------
def format_large_number(value: float | int | None, prefix: str = "$") -> str:
    """Format a number with T/B/M/K suffixes for readability."""
    if value is None:
        return "N/A"
    try:
        value = float(value)
    except (ValueError, TypeError):
        return "N/A"

    abs_val = abs(value)
    sign = "-" if value < 0 else ""

    if abs_val >= 1e12:
        return f"{sign}{prefix}{abs_val / 1e12:.2f}T"
    if abs_val >= 1e9:
        return f"{sign}{prefix}{abs_val / 1e9:.2f}B"
    if abs_val >= 1e6:
        return f"{sign}{prefix}{abs_val / 1e6:.2f}M"
    if abs_val >= 1e3:
        return f"{sign}{prefix}{abs_val / 1e3:.1f}K"
    return f"{sign}{prefix}{abs_val:,.0f}"


# ---------------------------------------------------------------------------
# ticker_sidebar
# ---------------------------------------------------------------------------
_PERIOD_MAP: dict[str, str] = {
    "1M": "1mo",
    "3M": "3mo",
    "6M": "6mo",
    "1Y": "1y",
    "2Y": "2y",
    "5Y": "5y",
    "Max": "max",
}

_DEFAULT_PEERS: list[str] = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "META",
    "NVDA", "TSLA", "JPM", "V", "JNJ",
    "WMT", "PG", "UNH", "HD", "BAC",
]


def ticker_sidebar() -> tuple[str, str, list[str]]:
    """Set up the sidebar controls and return (ticker, yf_period, peers)."""
    st.sidebar.markdown(
        f'<div style="font-size:22px;font-weight:700;color:{WHITE};'
        f'padding:8px 0 16px 0;letter-spacing:-0.02em;">'
        f'&#128200; Financial Dashboard</div>',
        unsafe_allow_html=True,
    )

    ticker = st.sidebar.text_input("Ticker Symbol", value="AAPL").upper().strip()

    period_label = st.sidebar.selectbox(
        "Price Period",
        options=list(_PERIOD_MAP.keys()),
        index=3,  # default 1Y
    )
    yf_period: str = _PERIOD_MAP[period_label]

    peers = st.sidebar.multiselect(
        "Peer Comparison",
        options=[t for t in _DEFAULT_PEERS if t != ticker],
        default=[],
    )

    # Market section
    st.sidebar.markdown("---")
    st.sidebar.markdown(
        f'<div style="font-size:11px;text-transform:uppercase;'
        f'letter-spacing:0.06em;color:rgba(255,255,255,0.5);'
        f'margin-bottom:4px;">Market</div>'
        f'<div style="font-size:14px;color:{WHITE};">'
        f'{date.today().strftime("%B %d, %Y")}</div>',
        unsafe_allow_html=True,
    )

    return ticker, yf_period, peers


# ---------------------------------------------------------------------------
# kpi_row  – render 4 key metrics in columns
# ---------------------------------------------------------------------------
def kpi_row(info: dict) -> None:
    """Display four KPI metric cards from a yfinance *info* dict."""
    current_price = info.get("currentPrice") or info.get("regularMarketPrice")
    previous_close = info.get("previousClose") or info.get("regularMarketPreviousClose")
    market_cap = info.get("marketCap")
    pe_ratio = info.get("trailingPE")
    week52_low = info.get("fiftyTwoWeekLow")
    week52_high = info.get("fiftyTwoWeekHigh")

    # Compute price delta
    price_delta: Optional[str] = None
    if current_price is not None and previous_close is not None:
        diff = current_price - previous_close
        pct = (diff / previous_close) * 100 if previous_close else 0
        sign = "+" if diff >= 0 else ""
        price_delta = f"{sign}{diff:,.2f} ({sign}{pct:.2f}%)"

    cols = st.columns(4)

    with cols[0]:
        st.markdown(
            metric_card(
                "Price",
                f"{current_price:,.2f}" if current_price else "N/A",
                delta=price_delta,
                prefix="$",
            ),
            unsafe_allow_html=True,
        )
    with cols[1]:
        st.markdown(
            metric_card("Market Cap", format_large_number(market_cap)),
            unsafe_allow_html=True,
        )
    with cols[2]:
        pe_display = f"{pe_ratio:.2f}" if pe_ratio else "N/A"
        st.markdown(
            metric_card("P/E Ratio", pe_display),
            unsafe_allow_html=True,
        )
    with cols[3]:
        if week52_low is not None and week52_high is not None:
            range_str = f"${week52_low:,.2f} - ${week52_high:,.2f}"
        else:
            range_str = "N/A"
        st.markdown(
            metric_card("52W Range", range_str),
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# render_company_header
# ---------------------------------------------------------------------------
def render_company_header(ticker: str, info: dict) -> None:
    """Render a styled header with company name, sector, and industry."""
    name = info.get("longName") or info.get("shortName") or ticker
    sector = info.get("sector", "")
    industry = info.get("industry", "")

    badge_parts: list[str] = []
    if sector:
        badge_parts.append(
            f'<div style="background:#ffffff;padding:4px 14px;'
            f'border-radius:16px;font-size:12px;color:#161a1f;'
            f'font-weight:700;font-family:Inter,sans-serif;">{sector}</div>'
        )
    if industry:
        badge_parts.append(
            f'<div style="background:#ffffff;padding:4px 14px;'
            f'border-radius:16px;font-size:12px;color:#161a1f;'
            f'font-weight:700;font-family:Inter,sans-serif;">{industry}</div>'
        )

    badges = " ".join(badge_parts)

    st.markdown(
        f'<div style="margin-bottom:28px;">'
        f'<div style="font-size:26px;font-weight:800;color:{TEXT_PRIMARY}; font-family:Inter,sans-serif; letter-spacing:-0.02em;'
        f'margin-bottom:12px;">{name}'
        f'<span style="font-size:14px;color:{TEXT_SECONDARY};'
        f'font-weight:600;margin-left:8px;font-family:Inter,sans-serif;">{ticker}</span></div>'
        f'<div style="display:flex;gap:12px;align-items:center;">{badges}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# loading_wrapper – execute a function inside a spinner
# ---------------------------------------------------------------------------
def loading_wrapper(func, *args, message: str = "Loading...", **kwargs):
    """Execute *func* inside a `st.spinner` and return its result."""
    with st.spinner(message):
        return func(*args, **kwargs)

