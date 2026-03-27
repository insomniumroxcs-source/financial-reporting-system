"""
Data cleaning and standardization.
- XBRL → human-readable column name mapping
- Forward-fill missing quarters within fiscal year
- Schema enforcement (explicit dtypes)
- Save to Parquet
"""
import os
import pandas as pd
from typing import Dict, Optional

from src.utils.logger import setup_logger
from src.utils.helpers import load_config, get_field_mapping

logger = setup_logger("cleaner")


def standardize_columns(df: pd.DataFrame, config: dict = None) -> pd.DataFrame:
    """
    Rename columns from XBRL / source names to standardised internal names
    using the mapping in config.yaml.
    """
    if df is None or df.empty:
        return df

    mapping = get_field_mapping(config)
    rename_map = {}

    for standard_name, source_names in mapping.items():
        for source_name in source_names:
            if source_name in df.columns:
                rename_map[source_name] = standard_name
                break  # Use first match

    if rename_map:
        df = df.rename(columns=rename_map)
        logger.debug(f"Renamed {len(rename_map)} columns: {list(rename_map.keys())}")

    return df


def enforce_schema(df: pd.DataFrame) -> pd.DataFrame:
    """
    Enforce numeric dtypes on known financial columns.
    Non-convertible values become NaN.
    """
    if df is None or df.empty:
        return df

    numeric_fields = [
        "revenue", "cost_of_revenue", "gross_profit", "operating_income",
        "net_income", "total_assets", "total_liabilities", "total_equity",
        "operating_cash_flow", "capital_expenditure", "total_current_assets",
        "total_current_liabilities", "long_term_debt", "interest_expense",
        "ebitda", "depreciation", "earnings_per_share",
    ]

    for col in numeric_fields:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def forward_fill_within_year(df: pd.DataFrame, year_col: str = "fiscal_year") -> pd.DataFrame:
    """
    Forward-fill missing values, but only within the same fiscal year
    to avoid carrying stale data across years.
    """
    if df is None or df.empty or year_col not in df.columns:
        return df

    filled = df.groupby(year_col, group_keys=False).apply(
        lambda g: g.ffill()
    )
    return filled


def clean_financial_data(
    raw_data: Dict[str, Optional[pd.DataFrame]],
    ticker: str,
    config: dict = None,
) -> Dict[str, Optional[pd.DataFrame]]:
    """
    Full cleaning pipeline for financial statement DataFrames.

    Steps:
        1. Standardise column names
        2. Enforce numeric schema
        3. Add ticker column

    Returns:
        Dict with cleaned DataFrames for each statement.
    """
    if config is None:
        config = load_config()

    cleaned = {}
    for stmt_name, df in raw_data.items():
        if df is None or (isinstance(df, pd.DataFrame) and df.empty):
            cleaned[stmt_name] = df
            continue

        if not isinstance(df, pd.DataFrame):
            logger.warning(f"[{ticker}] {stmt_name} is not a DataFrame, skipping")
            cleaned[stmt_name] = None
            continue

        df = df.copy()
        df = standardize_columns(df, config)
        df = enforce_schema(df)
        df["ticker"] = ticker
        cleaned[stmt_name] = df
        logger.info(f"[{ticker}] Cleaned {stmt_name}: {df.shape}")

    return cleaned


def save_to_parquet(
    df: pd.DataFrame,
    filename: str,
    output_dir: str = "data/processed",
) -> str:
    """Save DataFrame to Parquet, preserving dtypes."""
    if df is None or df.empty:
        logger.warning(f"Empty DataFrame, skipping save for {filename}")
        return ""
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, f"{filename}.parquet")
    df.to_parquet(path, index=True)
    logger.info(f"Saved {path} ({len(df)} rows)")
    return path
