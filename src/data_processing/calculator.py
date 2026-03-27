"""
Financial ratio calculator.
All ratios computed from raw components (not pre-calculated third-party values).

Ratio categories:
  - Profitability: gross margin, operating margin, net margin, ROE, ROA
  - DuPont decomposition: net margin × asset turnover × equity multiplier
  - Liquidity: current ratio, quick ratio
  - Leverage: debt-to-equity, interest coverage
  - Growth: YoY revenue growth, EPS growth
  - Valuation helpers: FCF, EBITDA margin
"""
import pandas as pd
import numpy as np
from typing import Dict, Optional

from src.utils.logger import setup_logger

logger = setup_logger("calculator")


def _safe_divide(numerator, denominator):
    """Division that returns NaN instead of raising on zero/NaN."""
    try:
        if denominator is None or denominator == 0 or pd.isna(denominator):
            return np.nan
        if numerator is None or pd.isna(numerator):
            return np.nan
        return numerator / denominator
    except (TypeError, ZeroDivisionError):
        return np.nan


# ── Profitability Ratios ──────────────────────────────────────────────────
def calc_gross_margin(gross_profit, revenue):
    return _safe_divide(gross_profit, revenue)

def calc_operating_margin(operating_income, revenue):
    return _safe_divide(operating_income, revenue)

def calc_net_margin(net_income, revenue):
    return _safe_divide(net_income, revenue)

def calc_roe(net_income, total_equity):
    return _safe_divide(net_income, total_equity)

def calc_roa(net_income, total_assets):
    return _safe_divide(net_income, total_assets)

def calc_ebitda_margin(ebitda, revenue):
    return _safe_divide(ebitda, revenue)


# ── DuPont Decomposition ─────────────────────────────────────────────────
def calc_dupont(net_income, revenue, total_assets, total_equity):
    """
    DuPont 3-factor: ROE = Net Margin × Asset Turnover × Equity Multiplier.
    Returns dict with each component and the composite ROE.
    """
    net_margin = _safe_divide(net_income, revenue)
    asset_turnover = _safe_divide(revenue, total_assets)
    equity_multiplier = _safe_divide(total_assets, total_equity)
    roe = net_margin * asset_turnover * equity_multiplier if not any(
        pd.isna(x) for x in [net_margin, asset_turnover, equity_multiplier]
    ) else np.nan

    return {
        "net_margin": net_margin,
        "asset_turnover": asset_turnover,
        "equity_multiplier": equity_multiplier,
        "dupont_roe": roe,
    }


# ── Liquidity Ratios ─────────────────────────────────────────────────────
def calc_current_ratio(current_assets, current_liabilities):
    return _safe_divide(current_assets, current_liabilities)

def calc_quick_ratio(current_assets, inventory, current_liabilities):
    """Quick ratio = (Current Assets - Inventory) / Current Liabilities."""
    if current_assets is None or pd.isna(current_assets):
        return np.nan
    inv = inventory if inventory is not None and not pd.isna(inventory) else 0
    return _safe_divide(current_assets - inv, current_liabilities)


# ── Leverage Ratios ───────────────────────────────────────────────────────
def calc_debt_to_equity(total_liabilities, total_equity):
    return _safe_divide(total_liabilities, total_equity)

def calc_interest_coverage(operating_income, interest_expense):
    return _safe_divide(operating_income, interest_expense)


# ── Growth Metrics ────────────────────────────────────────────────────────
def calc_yoy_growth(current_value, prior_value):
    """Year-over-year growth rate."""
    return _safe_divide(current_value - prior_value, abs(prior_value)) if prior_value else np.nan


# ── Free Cash Flow ────────────────────────────────────────────────────────
def calc_fcf(operating_cash_flow, capital_expenditure):
    """FCF = Operating Cash Flow - CapEx (CapEx usually stored as positive)."""
    if operating_cash_flow is None or pd.isna(operating_cash_flow):
        return np.nan
    capex = capital_expenditure if capital_expenditure is not None and not pd.isna(capital_expenditure) else 0
    return operating_cash_flow - abs(capex)


# ── Comprehensive Ratio Calculator ───────────────────────────────────────
def compute_all_ratios(
    income_df: Optional[pd.DataFrame],
    balance_df: Optional[pd.DataFrame],
    cashflow_df: Optional[pd.DataFrame],
    ticker: str = "",
) -> pd.DataFrame:
    """
    Compute all financial ratios from cleaned statement DataFrames.
    Each row represents one fiscal period.

    Returns:
        DataFrame with ratio columns indexed by period.
    """
    logger.info(f"[{ticker}] Computing financial ratios")
    rows = []

    # Determine which DataFrame to iterate over
    base_df = income_df if income_df is not None and not income_df.empty else None
    if base_df is None:
        logger.warning(f"[{ticker}] No income statement data for ratio calculation")
        return pd.DataFrame()

    for idx, inc_row in base_df.iterrows():
        row = {"period": idx, "ticker": ticker}

        # Pull values from income statement
        revenue = inc_row.get("revenue", np.nan)
        gross_profit = inc_row.get("gross_profit", np.nan)
        operating_income = inc_row.get("operating_income", np.nan)
        net_income = inc_row.get("net_income", np.nan)
        interest_expense = inc_row.get("interest_expense", np.nan)
        ebitda = inc_row.get("ebitda", np.nan)

        # Pull from balance sheet (match by index if possible)
        total_assets = total_equity = total_liabilities = np.nan
        current_assets = current_liabilities = np.nan
        if balance_df is not None and not balance_df.empty:
            if idx in balance_df.index:
                bs_row = balance_df.loc[idx]
            elif len(balance_df) > 0:
                bs_row = balance_df.iloc[-1]  # Use latest available
            else:
                bs_row = pd.Series(dtype=float)
            total_assets = bs_row.get("total_assets", np.nan)
            total_equity = bs_row.get("total_equity", np.nan)
            total_liabilities = bs_row.get("total_liabilities", np.nan)
            current_assets = bs_row.get("total_current_assets", np.nan)
            current_liabilities = bs_row.get("total_current_liabilities", np.nan)

        # Pull from cash flow
        operating_cf = capex = np.nan
        if cashflow_df is not None and not cashflow_df.empty:
            if idx in cashflow_df.index:
                cf_row = cashflow_df.loc[idx]
            elif len(cashflow_df) > 0:
                cf_row = cashflow_df.iloc[-1]
            else:
                cf_row = pd.Series(dtype=float)
            operating_cf = cf_row.get("operating_cash_flow", np.nan)
            capex = cf_row.get("capital_expenditure", np.nan)

        # Compute ratios
        row["gross_margin"] = calc_gross_margin(gross_profit, revenue)
        row["operating_margin"] = calc_operating_margin(operating_income, revenue)
        row["net_margin"] = calc_net_margin(net_income, revenue)
        row["ebitda_margin"] = calc_ebitda_margin(ebitda, revenue)
        row["roe"] = calc_roe(net_income, total_equity)
        row["roa"] = calc_roa(net_income, total_assets)
        row["current_ratio"] = calc_current_ratio(current_assets, current_liabilities)
        row["debt_to_equity"] = calc_debt_to_equity(total_liabilities, total_equity)
        row["interest_coverage"] = calc_interest_coverage(operating_income, interest_expense)
        row["fcf"] = calc_fcf(operating_cf, capex)

        # DuPont
        dupont = calc_dupont(net_income, revenue, total_assets, total_equity)
        row.update({f"dupont_{k}" if not k.startswith("dupont") else k: v
                     for k, v in dupont.items()})

        # Raw values for reference
        row["revenue"] = revenue
        row["net_income"] = net_income
        row["total_assets"] = total_assets
        row["total_equity"] = total_equity

        rows.append(row)

    ratios_df = pd.DataFrame(rows)
    if "period" in ratios_df.columns:
        ratios_df = ratios_df.set_index("period")

    logger.info(f"[{ticker}] Computed {len(ratios_df)} periods of ratios")
    return ratios_df


# ── Industry-Specific Ratios ─────────────────────────────────────────────
def compute_industry_ratios(
    income_df: Optional[pd.DataFrame],
    balance_df: Optional[pd.DataFrame],
    cashflow_df: Optional[pd.DataFrame],
    ticker: str = "",
    sector: str = "",
) -> pd.DataFrame:
    """
    Compute sector-specific financial ratios beyond the standard set.

    Sector logic:
      - Financial Services (Banking): NIM proxy, loan-to-deposit, provisioning
      - Consumer Defensive/Cyclical (FMCG): Inventory turnover, DSO, WC turnover
      - Technology: R&D % of revenue
      - Generic: Asset turnover, working capital ratio
    """
    logger.info(f"[{ticker}] Computing industry-specific ratios (sector={sector})")
    rows = []

    if income_df is None or income_df.empty:
        return pd.DataFrame()

    for idx, inc_row in income_df.iterrows():
        row = {"period": idx, "ticker": ticker}
        revenue = inc_row.get("revenue", np.nan)

        # Balance sheet values
        total_assets = total_equity = np.nan
        current_assets = current_liabilities = np.nan
        inventory = accounts_receivable = accounts_payable = np.nan
        if balance_df is not None and not balance_df.empty:
            bs_row = balance_df.loc[idx] if idx in balance_df.index else balance_df.iloc[-1]
            total_assets = bs_row.get("total_assets", np.nan)
            total_equity = bs_row.get("total_equity", np.nan)
            current_assets = bs_row.get("total_current_assets", np.nan)
            current_liabilities = bs_row.get("total_current_liabilities", np.nan)
            inventory = bs_row.get("inventory", np.nan)
            accounts_receivable = bs_row.get("accounts_receivable", bs_row.get("net_receivables", np.nan))
            accounts_payable = bs_row.get("accounts_payable", np.nan)

        # Generic ratios (all sectors) ─────────────────────────────────────
        row["asset_turnover"] = _safe_divide(revenue, total_assets)
        working_capital = (current_assets - current_liabilities) if (
            pd.notna(current_assets) and pd.notna(current_liabilities)
        ) else np.nan
        row["working_capital"] = working_capital
        row["working_capital_ratio"] = _safe_divide(working_capital, revenue)

        # ── Banking / Financial Services ──────────────────────────────────
        if "financial" in sector.lower() or "bank" in sector.lower():
            interest_income = inc_row.get("interest_income", np.nan)
            interest_expense = inc_row.get("interest_expense", np.nan)
            # NIM proxy = (Interest Income - Interest Expense) / Total Assets
            if pd.notna(interest_income) and pd.notna(interest_expense):
                row["nim_proxy"] = _safe_divide(interest_income - interest_expense, total_assets)
            else:
                row["nim_proxy"] = np.nan

            # Loan-to-deposit proxy (use total assets / total liabilities)
            total_liabilities = (total_assets - total_equity) if (
                pd.notna(total_assets) and pd.notna(total_equity)
            ) else np.nan
            row["loan_to_deposit_proxy"] = _safe_divide(total_assets * 0.65, total_liabilities * 0.80)

            # Provisioning ratio proxy
            provision = inc_row.get("provision_for_loan_losses", np.nan)
            row["provisioning_ratio"] = _safe_divide(provision, revenue) if pd.notna(provision) else np.nan

        # ── Consumer / FMCG ───────────────────────────────────────────────
        elif "consumer" in sector.lower():
            cogs = inc_row.get("cost_of_revenue", inc_row.get("cogs", np.nan))
            # Inventory turnover = COGS / Inventory
            row["inventory_turnover"] = _safe_divide(cogs, inventory)
            # DSO = AR / Revenue * 365
            row["dso"] = _safe_divide(accounts_receivable, revenue) * 365 if (
                pd.notna(accounts_receivable) and pd.notna(revenue) and revenue != 0
            ) else np.nan
            # Working capital turnover = Revenue / Working Capital
            row["working_capital_turnover"] = _safe_divide(revenue, working_capital)

        # ── Technology ────────────────────────────────────────────────────
        elif "tech" in sector.lower():
            r_and_d = inc_row.get("research_development", inc_row.get("research_and_development", np.nan))
            row["r_and_d_pct_revenue"] = _safe_divide(r_and_d, revenue)

        rows.append(row)

    result = pd.DataFrame(rows)
    if "period" in result.columns:
        result = result.set_index("period")

    logger.info(f"[{ticker}] Computed {len(result)} periods of industry ratios")
    return result
