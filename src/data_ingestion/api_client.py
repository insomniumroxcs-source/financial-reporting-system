"""
Data Ingestion API Client
Wrappers for yfinance (prices) and edgartools (SEC financials).
Uses requests-cache with 24h SQLite TTL and retry with exponential backoff.
"""
import os
import pandas as pd
import requests_cache
from datetime import datetime, timedelta

from src.utils.logger import setup_logger
from src.utils.helpers import load_config, retry

logger = setup_logger("data_ingestion")

# ── Cache setup ────────────────────────────────────────────────────────────
_CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", ".cache")
os.makedirs(_CACHE_DIR, exist_ok=True)
requests_cache.install_cache(
    os.path.join(_CACHE_DIR, "http_cache"),
    backend="sqlite",
    expire_after=timedelta(hours=24),
)


# ── Price Data (yfinance) ──────────────────────────────────────────────────
@retry(max_retries=3, backoff_factor=1.0)
def fetch_price_data(
    ticker: str,
    period: str = None,
    start: str = None,
    end: str = None,
    lookback_years: int = 2,
) -> pd.DataFrame:
    """
    Fetch OHLCV price data via yfinance.

    Args:
        ticker: Stock ticker symbol (e.g. 'AAPL').
        period: yfinance period string (e.g. '1y', '5y'). Takes precedence.
        start/end: Date strings 'YYYY-MM-DD'. Used if period is None.
        lookback_years: Fallback lookback window if no dates given.

    Returns:
        DataFrame with columns: Open, High, Low, Close, Volume and DatetimeIndex.
    """
    import yfinance as yf

    logger.info(f"Fetching price data for {ticker}")
    stock = yf.Ticker(ticker)

    if period:
        df = stock.history(period=period)
    elif start and end:
        df = stock.history(start=start, end=end)
    else:
        end_dt = datetime.today()
        start_dt = end_dt - timedelta(days=lookback_years * 365)
        df = stock.history(start=start_dt.strftime("%Y-%m-%d"),
                           end=end_dt.strftime("%Y-%m-%d"))

    if df.empty:
        logger.warning(f"No price data returned for {ticker}")
        return pd.DataFrame()

    # Keep only standard OHLCV columns
    keep_cols = ["Open", "High", "Low", "Close", "Volume"]
    df = df[[c for c in keep_cols if c in df.columns]]
    logger.info(f"  ✓ {len(df)} price rows for {ticker}")
    return df


# ── Company Info (yfinance) ────────────────────────────────────────────────
@retry(max_retries=2, backoff_factor=0.5)
def fetch_company_info(ticker: str) -> dict:
    """
    Fetch company info dict from yfinance (.info).
    Contains P/E, market cap, dividend yield, sector, etc.
    """
    import yfinance as yf

    logger.info(f"Fetching company info for {ticker}")
    stock = yf.Ticker(ticker)
    info = stock.info
    if not info or info.get("regularMarketPrice") is None:
        logger.warning(f"Limited info returned for {ticker}")
    return info


# ── Financial Statements (edgartools / SEC EDGAR) ─────────────────────────
@retry(max_retries=3, backoff_factor=2.0)
def fetch_financials_edgar(ticker: str) -> dict:
    """
    Fetch income statement, balance sheet, and cash flow from SEC EDGAR
    using the edgartools library.

    Returns:
        Dict with keys 'income_statement', 'balance_sheet', 'cash_flow',
        each containing a pandas DataFrame (or None on failure).
    """
    try:
        from edgar import Company, set_identity
    except ImportError:
        logger.error(
            "edgartools not installed. Install with: pip install edgartools"
        )
        return {"income_statement": None, "balance_sheet": None, "cash_flow": None}

    config = load_config()
    identity = config.get("sec", {}).get("identity", "user@example.com")
    set_identity(identity)

    logger.info(f"Fetching SEC financials for {ticker}")
    result = {
        "income_statement": None,
        "balance_sheet": None,
        "cash_flow": None,
    }

    def _to_df(obj):
        """Convert edgartools financial object to DataFrame."""
        if obj is None:
            return None
        if isinstance(obj, pd.DataFrame):
            return obj
        for method in ['to_dataframe', 'to_pandas', 'as_dataframe']:
            if hasattr(obj, method):
                try:
                    return getattr(obj, method)()
                except Exception:
                    continue
        # Try accessing .data or .df attributes
        for attr in ['data', 'df', 'dataframe']:
            if hasattr(obj, attr):
                val = getattr(obj, attr)
                if isinstance(val, pd.DataFrame):
                    return val
        # Last resort: if it has dict-like behavior
        try:
            return pd.DataFrame(dict(obj))
        except Exception:
            pass
        return None

    try:
        company = Company(ticker)
        financials = company.get_financials()

        if financials is None:
            logger.warning(f"No financials object for {ticker}")
            return result

        stmt_map = [
            ("income_statement", "income_statement"),
            ("balance_sheet", "balance_sheet"),
            ("cash_flow", "cash_flow_statement"),
        ]
        for key, attr in stmt_map:
            try:
                obj = getattr(financials, attr, None)
                df = _to_df(obj)
                if df is not None and not df.empty:
                    result[key] = df
                    logger.info(f"  + {key} for {ticker} ({df.shape})")
                else:
                    logger.warning(f"  - {key} empty for {ticker}")
            except Exception as e:
                logger.warning(f"  - {key} failed for {ticker}: {e}")

    except Exception as e:
        logger.error(f"Failed to fetch EDGAR data for {ticker}: {e}")

    return result


# ── yfinance Financial Statements (fallback) ──────────────────────────────
@retry(max_retries=2, backoff_factor=1.0)
def fetch_financials_yfinance(ticker: str) -> dict:
    """
    Fallback: fetch financial statements from yfinance.
    Less reliable than EDGAR but does not require edgartools.

    Returns:
        Dict with keys 'income_statement', 'balance_sheet', 'cash_flow'.
    """
    import yfinance as yf

    logger.info(f"Fetching yfinance financials for {ticker} (fallback)")
    stock = yf.Ticker(ticker)

    result = {}
    try:
        inc = stock.financials
        result["income_statement"] = inc.T if inc is not None and not inc.empty else None
    except Exception:
        result["income_statement"] = None

    try:
        bs = stock.balance_sheet
        result["balance_sheet"] = bs.T if bs is not None and not bs.empty else None
    except Exception:
        result["balance_sheet"] = None

    try:
        cf = stock.cashflow
        result["cash_flow"] = cf.T if cf is not None and not cf.empty else None
    except Exception:
        result["cash_flow"] = None

    return result


# ── Company News (yfinance) ────────────────────────────────────────────────
@retry(max_retries=2, backoff_factor=0.5)
def fetch_company_news(ticker: str, max_items: int = 20) -> list:
    """
    Fetch recent news for a ticker via yfinance .news attribute.
    Returns list of news dicts with title, link, publisher, providerPublishTime.
    """
    import yfinance as yf

    logger.info(f"Fetching news for {ticker}")
    stock = yf.Ticker(ticker)
    try:
        news = stock.news or []
        return news[:max_items]
    except Exception as e:
        logger.warning(f"Failed to fetch news for {ticker}: {e}")
        return []


# ── Corporate Actions (yfinance) ───────────────────────────────────────────
@retry(max_retries=2, backoff_factor=0.5)
def fetch_company_actions(ticker: str) -> dict:
    """
    Fetch corporate actions: splits, dividends, major holders, institutional holders.
    Returns dict with keys 'actions', 'dividends', 'splits',
    'major_holders', 'institutional_holders'.
    """
    import yfinance as yf

    logger.info(f"Fetching corporate actions for {ticker}")
    stock = yf.Ticker(ticker)
    result = {
        "actions": None,
        "dividends": None,
        "splits": None,
        "major_holders": None,
        "institutional_holders": None,
    }

    try:
        result["actions"] = stock.actions if hasattr(stock, "actions") else None
        result["dividends"] = stock.dividends if hasattr(stock, "dividends") else None
        result["splits"] = stock.splits if hasattr(stock, "splits") else None
        result["major_holders"] = stock.major_holders if hasattr(stock, "major_holders") else None
        result["institutional_holders"] = stock.institutional_holders if hasattr(stock, "institutional_holders") else None
    except Exception as e:
        logger.warning(f"Failed to fetch actions for {ticker}: {e}")

    return result

