"""
Segment data extraction and parsing.
Attempts to get business segment data from yfinance, with CSV upload / demo fallback.
"""
import pandas as pd
import numpy as np
from typing import Optional

from src.utils.logger import setup_logger

logger = setup_logger("segment_parser")


def extract_segments_yfinance(ticker: str) -> Optional[pd.DataFrame]:
    """
    Try to extract segment revenue data from yfinance.
    Returns DataFrame with columns [segment, year, revenue] or None.
    """
    try:
        import yfinance as yf
        stock = yf.Ticker(ticker)
        # yfinance doesn't have a direct segment API for most companies
        # Try to get from quarterly/annual financials metadata
        logger.info(f"[{ticker}] Attempting segment data extraction")
        return None  # yfinance doesn't expose segment data
    except Exception as e:
        logger.warning(f"[{ticker}] Segment extraction failed: {e}")
        return None


def parse_segment_csv(uploaded_file) -> Optional[pd.DataFrame]:
    """
    Parse a user-uploaded CSV/Excel containing segment data.

    Expected columns (case-insensitive, flexible naming):
        segment / business / division — segment name
        year / period / fiscal_year — time period
        revenue / sales / amount — revenue figure
        profit / operating_income (optional)
    """
    try:
        if uploaded_file.name.endswith((".xlsx", ".xls")):
            df = pd.read_excel(uploaded_file)
        else:
            df = pd.read_csv(uploaded_file)

        # Normalize column names
        df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

        col_map = {}
        for col in df.columns:
            if col in ("segment", "business", "division", "segment_name", "business_unit"):
                col_map["segment"] = col
            elif col in ("year", "period", "fiscal_year", "fy"):
                col_map["year"] = col
            elif col in ("revenue", "sales", "amount", "total_revenue", "net_revenue"):
                col_map["revenue"] = col
            elif col in ("profit", "operating_income", "op_income", "segment_profit"):
                col_map["profit"] = col

        if "segment" not in col_map or "revenue" not in col_map:
            logger.warning("CSV missing required columns (segment, revenue)")
            return None

        result = pd.DataFrame()
        result["segment"] = df[col_map["segment"]]
        result["revenue"] = pd.to_numeric(df[col_map["revenue"]], errors="coerce")

        if "year" in col_map:
            result["year"] = df[col_map["year"]]
        else:
            result["year"] = 2024  # default

        if "profit" in col_map:
            result["profit"] = pd.to_numeric(df[col_map["profit"]], errors="coerce")

        return result.dropna(subset=["segment", "revenue"])
    except Exception as e:
        logger.error(f"Failed to parse segment CSV: {e}")
        return None


def get_demo_segments(ticker: str = "AAPL") -> pd.DataFrame:
    """Return realistic demo segment data for popular companies."""
    demos = {
        "AAPL": {
            "segments": ["iPhone", "Services", "Mac", "iPad", "Wearables & Accessories"],
            "2021": [191973, 68425, 35190, 31862, 38367],
            "2022": [205489, 78129, 40177, 29292, 41241],
            "2023": [200583, 85200, 29357, 28300, 39845],
            "2024": [201183, 96169, 29984, 26694, 37005],
        },
        "MSFT": {
            "segments": ["Intelligent Cloud", "Productivity & Business Processes", "More Personal Computing"],
            "2021": [60080, 53915, 54093],
            "2022": [74965, 63364, 59941],
            "2023": [87907, 69274, 54734],
            "2024": [105360, 77478, 58928],
        },
        "GOOGL": {
            "segments": ["Google Search & Other", "YouTube Ads", "Google Cloud", "Other Bets"],
            "2021": [148951, 28845, 19206, 753],
            "2022": [162450, 29243, 26280, 1068],
            "2023": [175033, 31510, 33088, 1527],
            "2024": [198117, 36049, 43232, 1615],
        },
        "AMZN": {
            "segments": ["North America", "International", "AWS"],
            "2021": [279833, 127787, 62202],
            "2022": [315880, 118007, 80096],
            "2023": [352828, 131200, 90757],
            "2024": [387700, 142400, 107600],
        },
        "META": {
            "segments": ["Family of Apps", "Reality Labs"],
            "2021": [115655, 2274],
            "2022": [114450, 2159],
            "2023": [131948, 1896],
            "2024": [156225, 2200],
        },
    }

    d = demos.get(ticker.upper())
    if d is None:
        # Generic fallback
        d = {
            "segments": ["Segment A", "Segment B", "Segment C", "Segment D"],
            "2021": [25000, 18000, 12000, 8000],
            "2022": [27500, 19500, 13200, 8800],
            "2023": [29000, 21000, 14500, 9600],
            "2024": [31500, 22800, 15800, 10500],
        }

    rows = []
    for seg_idx, seg in enumerate(d["segments"]):
        for year_str in ["2021", "2022", "2023", "2024"]:
            if year_str in d:
                rows.append({
                    "segment": seg,
                    "year": int(year_str),
                    "revenue": d[year_str][seg_idx],
                })
    return pd.DataFrame(rows)


def calculate_segment_yoy(segment_df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate YoY growth rate per segment.

    Returns DataFrame with columns [segment, year, revenue, yoy_growth].
    """
    if segment_df is None or segment_df.empty:
        return pd.DataFrame()

    df = segment_df.sort_values(["segment", "year"]).copy()
    df["yoy_growth"] = df.groupby("segment")["revenue"].pct_change()
    return df


def calculate_segment_contribution(segment_df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate each segment's percentage contribution to total revenue per year.

    Returns DataFrame with columns [segment, year, revenue, contribution_pct].
    """
    if segment_df is None or segment_df.empty:
        return pd.DataFrame()

    df = segment_df.copy()
    totals = df.groupby("year")["revenue"].sum().rename("total_revenue")
    df = df.merge(totals, on="year")
    df["contribution_pct"] = df["revenue"] / df["total_revenue"]
    df = df.drop(columns=["total_revenue"])
    return df
