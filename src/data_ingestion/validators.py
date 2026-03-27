"""
Data quality validators.
Checks schema, dtypes, required fields, and flags suspicious values.
"""
import pandas as pd
from typing import Dict, List, Optional
from src.utils.logger import setup_logger

logger = setup_logger("validators")

# ── Expected schema per statement type ─────────────────────────────────────
PRICE_SCHEMA = {
    "Open": "float64",
    "High": "float64",
    "Low": "float64",
    "Close": "float64",
    "Volume": "float64",
}

FINANCIAL_REQUIRED_FIELDS = [
    "revenue",
    "net_income",
    "total_assets",
    "total_equity",
]


def validate_price_data(df: pd.DataFrame, ticker: str = "") -> Dict[str, any]:
    """
    Validate price DataFrame: check columns, dtypes, no-null close prices,
    monotonic dates.

    Returns:
        dict with 'valid' (bool), 'warnings' (list[str]), 'errors' (list[str]).
    """
    result = {"valid": True, "warnings": [], "errors": []}
    prefix = f"[{ticker}] " if ticker else ""

    if df is None or df.empty:
        result["valid"] = False
        result["errors"].append(f"{prefix}Price data is empty or None")
        return result

    # Check required columns
    for col in ["Open", "High", "Low", "Close", "Volume"]:
        if col not in df.columns:
            result["errors"].append(f"{prefix}Missing column: {col}")
            result["valid"] = False

    # Check for null close prices
    if "Close" in df.columns:
        null_count = df["Close"].isna().sum()
        if null_count > 0:
            result["warnings"].append(
                f"{prefix}{null_count} null Close prices found"
            )

    # Check date index is monotonic
    if not df.index.is_monotonic_increasing:
        result["warnings"].append(f"{prefix}Date index is not monotonic")

    # Check for suspiciously zero prices
    if "Close" in df.columns:
        zero_count = (df["Close"] == 0).sum()
        if zero_count > 0:
            result["warnings"].append(
                f"{prefix}{zero_count} zero Close prices found"
            )

    for item in result["errors"]:
        logger.error(item)
    for item in result["warnings"]:
        logger.warning(item)

    return result


def validate_financial_data(
    data: Dict[str, Optional[pd.DataFrame]], ticker: str = ""
) -> Dict[str, any]:
    """
    Validate financial statement DataFrames.

    Args:
        data: Dict with keys 'income_statement', 'balance_sheet', 'cash_flow'.

    Returns:
        dict with 'valid', 'warnings', 'errors'.
    """
    result = {"valid": True, "warnings": [], "errors": []}
    prefix = f"[{ticker}] " if ticker else ""

    for stmt_name in ["income_statement", "balance_sheet", "cash_flow"]:
        df = data.get(stmt_name)
        if df is None or (isinstance(df, pd.DataFrame) and df.empty):
            result["warnings"].append(f"{prefix}{stmt_name} is empty or None")
            continue

        if not isinstance(df, pd.DataFrame):
            result["errors"].append(
                f"{prefix}{stmt_name} is not a DataFrame (got {type(df).__name__})"
            )
            result["valid"] = False
            continue

        # Flag suspicious values
        if stmt_name == "income_statement":
            _check_suspicious(df, "revenue", prefix, result, expect_positive=True)
        elif stmt_name == "balance_sheet":
            _check_suspicious(df, "total_assets", prefix, result, expect_positive=True)

    for item in result["errors"]:
        logger.error(item)
    for item in result["warnings"]:
        logger.warning(item)

    return result


def _check_suspicious(
    df: pd.DataFrame,
    field: str,
    prefix: str,
    result: dict,
    expect_positive: bool = True,
):
    """Flag fields that are zero or have unexpected sign."""
    if field not in df.columns:
        return
    col = pd.to_numeric(df[field], errors="coerce")
    if col.isna().all():
        result["warnings"].append(f"{prefix}{field} is all NaN")
    elif expect_positive and (col <= 0).any():
        result["warnings"].append(
            f"{prefix}{field} has non-positive values — verify data quality"
        )
