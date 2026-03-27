"""
Three-statement financial model projection engine.
Projects Income Statement, Balance Sheet, and Cash Flow from historical data + assumptions.

Pure computation module -- ZERO Streamlit imports. Uses only pandas / numpy.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from src.utils.logger import setup_logger

logger = setup_logger("forecaster")


# ---------------------------------------------------------------------------
# Historical averages
# ---------------------------------------------------------------------------

def compute_historical_averages(
    income_df: Optional[pd.DataFrame],
    balance_df: Optional[pd.DataFrame],
    cashflow_df: Optional[pd.DataFrame],
) -> Dict[str, float]:
    """Extract historical averages from financial statements to seed default assumptions."""
    averages: Dict[str, float] = {}

    if income_df is not None and not income_df.empty:
        income_df = income_df.loc[:, ~income_df.columns.duplicated()]
    if balance_df is not None and not balance_df.empty:
        balance_df = balance_df.loc[:, ~balance_df.columns.duplicated()]
    if cashflow_df is not None and not cashflow_df.empty:
        cashflow_df = cashflow_df.loc[:, ~cashflow_df.columns.duplicated()]

    if income_df is not None and not income_df.empty:
        rev = income_df.get("revenue")

        # Revenue CAGR ---------------------------------------------------
        if rev is not None and len(rev) > 1:
            valid = rev.dropna()
            if len(valid) >= 2:
                # yfinance stores most-recent period first; iloc[-1] is oldest
                first, last = float(valid.iloc[-1]), float(valid.iloc[0])
                n = len(valid) - 1
                if first > 0 and last > 0 and n > 0:
                    averages["revenue_cagr"] = (last / first) ** (1 / n) - 1

        # Gross margin / COGS % ------------------------------------------
        gp = income_df.get("gross_profit")
        if gp is not None and rev is not None:
            margins = (gp / rev).replace([np.inf, -np.inf], np.nan).dropna()
            if not margins.empty:
                averages["cogs_pct"] = float(1 - margins.mean())

        # OpEx as % of revenue -------------------------------------------
        oi = income_df.get("operating_income")
        if oi is not None and gp is not None and rev is not None:
            opex = gp - oi
            opex_pct = (opex / rev).replace([np.inf, -np.inf], np.nan).dropna()
            if not opex_pct.empty:
                averages["opex_pct_revenue"] = opex_pct.mean()

        # Effective tax rate ---------------------------------------------
        ni = income_df.get("net_income")
        if ni is not None and oi is not None:
            effective_tax = (1 - ni / oi).replace([np.inf, -np.inf], np.nan).dropna()
            if not effective_tax.empty:
                averages["tax_rate"] = float(np.clip(effective_tax.mean(), 0.0, 0.50))

    # CapEx as % of revenue from cash-flow statement ----------------------
    if cashflow_df is not None and not cashflow_df.empty:
        capex = cashflow_df.get("capital_expenditure") or cashflow_df.get("capex")
        rev_for_capex = income_df.get("revenue") if income_df is not None else None
        if capex is not None and rev_for_capex is not None:
            # capex is typically negative in statements
            capex_abs = capex.abs()
            pct = (capex_abs / rev_for_capex).replace([np.inf, -np.inf], np.nan).dropna()
            if not pct.empty:
                averages["capex_pct_revenue"] = pct.mean()

    # Working-capital days from balance sheet & income stmt ----------------
    if balance_df is not None and not balance_df.empty and income_df is not None:
        rev = income_df.get("revenue")
        cogs_series = income_df.get("cost_of_revenue") or income_df.get("cogs")

        ar = balance_df.get("accounts_receivable") or balance_df.get("net_receivables")
        inv = balance_df.get("inventory")
        ap = balance_df.get("accounts_payable")

        if ar is not None and rev is not None:
            days = (ar / rev * 365).replace([np.inf, -np.inf], np.nan).dropna()
            if not days.empty:
                averages["ar_days"] = float(max(0, days.mean()))

        if inv is not None and cogs_series is not None:
            days = (inv / cogs_series * 365).replace([np.inf, -np.inf], np.nan).dropna()
            if not days.empty:
                averages["inventory_days"] = float(max(0, days.mean()))

        if ap is not None and cogs_series is not None:
            days = (ap / cogs_series * 365).replace([np.inf, -np.inf], np.nan).dropna()
            if not days.empty:
                averages["ap_days"] = float(max(0, days.mean()))

    # Fill in sensible defaults for anything still missing ----------------
    averages.setdefault("revenue_cagr", 0.05)
    averages.setdefault("cogs_pct", 0.60)
    averages.setdefault("opex_pct_revenue", 0.25)
    averages.setdefault("tax_rate", 0.21)
    averages.setdefault("capex_pct_revenue", 0.05)
    averages.setdefault("depreciation_pct_assets", 0.03)
    averages.setdefault("ar_days", 30)
    averages.setdefault("inventory_days", 45)
    averages.setdefault("ap_days", 30)
    averages.setdefault("dividend_payout", 0.30)
    averages.setdefault("interest_rate", 0.05)

    return averages


# ---------------------------------------------------------------------------
# Income-statement projection
# ---------------------------------------------------------------------------

def project_income_statement(
    historical_df: Optional[pd.DataFrame],
    assumptions: Dict[str, float],
    n_years: int = 5,
) -> pd.DataFrame:
    """
    Project income statement for *n_years*.

    Required keys in *assumptions*:
        revenue_growth_rates  – list[float] of annual growth rates (len >= n_years)
        cogs_pct              – COGS as fraction of revenue
        opex_pct_revenue      – OpEx as fraction of revenue
        tax_rate              – effective tax rate
        interest_rate         – interest expense as fraction of total debt
        depreciation_pct_assets – depreciation as fraction of total assets
        last_revenue          – (optional) starting revenue; inferred from historical_df if missing
        last_total_assets     – (optional) starting total assets for depreciation calc
        last_total_debt       – (optional) starting long-term debt for interest calc
    """
    # Resolve starting revenue
    last_revenue = assumptions.get("last_revenue")
    if last_revenue is None and historical_df is not None and not historical_df.empty:
        rev_col = historical_df.get("revenue")
        if rev_col is not None and not rev_col.dropna().empty:
            last_revenue = float(rev_col.dropna().iloc[0])  # most-recent first
    if last_revenue is None or last_revenue == 0:
        last_revenue = 1_000_000  # fallback

    growth_rates = assumptions.get("revenue_growth_rates", [assumptions.get("revenue_cagr", 0.05)] * n_years)
    cogs_pct = assumptions.get("cogs_pct", 0.60)
    opex_pct = assumptions.get("opex_pct_revenue", 0.25)
    tax_rate = assumptions.get("tax_rate", 0.21)
    interest_rate = assumptions.get("interest_rate", 0.05)
    dep_pct = assumptions.get("depreciation_pct_assets", 0.03)

    last_total_assets = assumptions.get("last_total_assets", last_revenue * 1.5)
    last_total_debt = assumptions.get("last_total_debt", last_revenue * 0.3)

    rows = []
    revenue = last_revenue
    total_assets = last_total_assets

    for i in range(n_years):
        g = growth_rates[i] if i < len(growth_rates) else growth_rates[-1]
        revenue = revenue * (1 + g)

        cogs = revenue * cogs_pct
        gross_profit = revenue - cogs
        opex = revenue * opex_pct

        # Depreciation grows roughly in line with assets
        depreciation = total_assets * dep_pct

        operating_income = gross_profit - opex
        ebitda = operating_income + depreciation

        interest_expense = last_total_debt * interest_rate
        pre_tax_income = operating_income - interest_expense
        tax = max(0, pre_tax_income * tax_rate)
        net_income = pre_tax_income - tax

        rows.append({
            "revenue": round(revenue, 2),
            "cogs": round(cogs, 2),
            "gross_profit": round(gross_profit, 2),
            "opex": round(opex, 2),
            "depreciation": round(depreciation, 2),
            "operating_income": round(operating_income, 2),
            "ebitda": round(ebitda, 2),
            "interest_expense": round(interest_expense, 2),
            "pre_tax_income": round(pre_tax_income, 2),
            "tax": round(tax, 2),
            "net_income": round(net_income, 2),
        })

        # Update running asset estimate for depreciation in next year
        capex_pct = assumptions.get("capex_pct_revenue", 0.05)
        total_assets = total_assets + revenue * capex_pct - depreciation

    df = pd.DataFrame(rows, index=[f"Year {i+1}" for i in range(n_years)])
    logger.info("Projected income statement for %d years", n_years)
    return df


# ---------------------------------------------------------------------------
# Balance-sheet projection
# ---------------------------------------------------------------------------

def project_balance_sheet(
    historical_df: Optional[pd.DataFrame],
    projected_income: pd.DataFrame,
    assumptions: Dict[str, float],
    n_years: int = 5,
) -> pd.DataFrame:
    """
    Project balance sheet for *n_years* using projected income and assumptions.

    Working-capital items derive from days outstanding.
    PP&E rolls forward with CapEx - Depreciation.
    Cash is the balancing plug.
    """
    ar_days = assumptions.get("ar_days", 30)
    inv_days = assumptions.get("inventory_days", 45)
    ap_days = assumptions.get("ap_days", 30)
    capex_pct = assumptions.get("capex_pct_revenue", 0.05)
    dep_pct = assumptions.get("depreciation_pct_assets", 0.03)
    dividend_payout = assumptions.get("dividend_payout", 0.30)

    # Starting balance-sheet values
    def _hist_val(col):
        if historical_df is not None and not historical_df.empty:
            s = historical_df.get(col)
            if s is not None and not s.dropna().empty:
                return float(s.dropna().iloc[0])
        return None

    ppe_net = _hist_val("ppe_net") or _hist_val("net_ppe") or assumptions.get("last_total_assets", 1_000_000) * 0.4
    retained_earnings = _hist_val("retained_earnings") or 0
    long_term_debt = assumptions.get("last_total_debt", projected_income["revenue"].iloc[0] * 0.3)
    cash = _hist_val("cash") or _hist_val("cash_and_equivalents") or 0

    rows = []
    for i in range(n_years):
        inc = projected_income.iloc[i]
        revenue = inc["revenue"]
        cogs = inc["cogs"]
        net_income = inc["net_income"]
        depreciation = inc["depreciation"]

        # Working capital
        accounts_receivable = revenue * ar_days / 365
        inventory = cogs * inv_days / 365
        accounts_payable = cogs * ap_days / 365

        # CapEx & PP&E
        capex = revenue * capex_pct
        ppe_net = ppe_net + capex - depreciation

        # Retained earnings
        dividends = max(0, net_income * dividend_payout) if net_income > 0 else 0
        retained_earnings = retained_earnings + net_income - dividends

        total_current_assets_ex_cash = accounts_receivable + inventory
        total_current_liabilities = accounts_payable
        total_equity = retained_earnings  # simplified; no share issuance
        total_liabilities = total_current_liabilities + long_term_debt

        # Cash is the plug: Total Assets = Total Liabilities + Equity
        # Total Assets = Cash + Current Assets (ex cash) + PP&E
        # => Cash = (Total Liabilities + Equity) - Current Assets (ex cash) - PP&E
        cash_plug = total_liabilities + total_equity - total_current_assets_ex_cash - ppe_net

        total_current_assets = cash_plug + total_current_assets_ex_cash
        total_assets = total_current_assets + ppe_net

        rows.append({
            "cash": round(cash_plug, 2),
            "accounts_receivable": round(accounts_receivable, 2),
            "inventory": round(inventory, 2),
            "total_current_assets": round(total_current_assets, 2),
            "ppe_net": round(ppe_net, 2),
            "total_assets": round(total_assets, 2),
            "accounts_payable": round(accounts_payable, 2),
            "total_current_liabilities": round(total_current_liabilities, 2),
            "long_term_debt": round(long_term_debt, 2),
            "total_liabilities": round(total_liabilities, 2),
            "retained_earnings": round(retained_earnings, 2),
            "total_equity": round(total_equity, 2),
            "capex": round(capex, 2),
            "dividends": round(dividends, 2),
        })

    df = pd.DataFrame(rows, index=[f"Year {i+1}" for i in range(n_years)])
    logger.info("Projected balance sheet for %d years", n_years)
    return df


# ---------------------------------------------------------------------------
# Cash-flow statement projection
# ---------------------------------------------------------------------------

def project_cash_flow(
    projected_income: pd.DataFrame,
    projected_bs: pd.DataFrame,
    historical_bs: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """
    Derive cash flow statement from projected income statement and balance-sheet
    changes (indirect method).
    """
    rows = []
    n_years = len(projected_income)

    for i in range(n_years):
        inc = projected_income.iloc[i]
        bs = projected_bs.iloc[i]
        net_income = inc["net_income"]
        depreciation = inc["depreciation"]

        # Prior-period balance sheet values
        if i == 0:
            if historical_bs is not None and not historical_bs.empty:
                prev_ar = float(historical_bs.get("accounts_receivable", pd.Series([0])).dropna().iloc[0])
                prev_inv = float(historical_bs.get("inventory", pd.Series([0])).dropna().iloc[0])
                prev_ap = float(historical_bs.get("accounts_payable", pd.Series([0])).dropna().iloc[0])
            else:
                # Assume first projected period's values as starting point (zero change)
                prev_ar = bs["accounts_receivable"]
                prev_inv = bs["inventory"]
                prev_ap = bs["accounts_payable"]
        else:
            prev_bs = projected_bs.iloc[i - 1]
            prev_ar = prev_bs["accounts_receivable"]
            prev_inv = prev_bs["inventory"]
            prev_ap = prev_bs["accounts_payable"]

        # Changes in working capital (increase in assets = cash outflow)
        delta_ar = -(bs["accounts_receivable"] - prev_ar)
        delta_inv = -(bs["inventory"] - prev_inv)
        delta_ap = bs["accounts_payable"] - prev_ap  # increase in payable = cash inflow
        change_in_wc = delta_ar + delta_inv + delta_ap

        cfo = net_income + depreciation + change_in_wc

        # Investing
        capex = -bs["capex"]  # cash outflow
        cfi = capex

        # Financing
        dividends = -bs["dividends"]
        # Debt assumed constant here; could be extended
        change_in_debt = 0
        cff = change_in_debt + dividends

        net_change = cfo + cfi + cff

        rows.append({
            "net_income": round(net_income, 2),
            "depreciation": round(depreciation, 2),
            "change_in_working_capital": round(change_in_wc, 2),
            "cfo": round(cfo, 2),
            "capex": round(-capex, 2),  # show as positive number
            "cfi": round(cfi, 2),
            "dividends_paid": round(-dividends, 2),  # show as positive
            "change_in_debt": round(change_in_debt, 2),
            "cff": round(cff, 2),
            "net_change_in_cash": round(net_change, 2),
            "free_cash_flow": round(cfo + cfi, 2),
        })

    df = pd.DataFrame(rows, index=[f"Year {i+1}" for i in range(n_years)])
    logger.info("Projected cash flow statement for %d years", n_years)
    return df


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def build_three_statement_model(
    historical_financials: Dict[str, Optional[pd.DataFrame]],
    assumptions: Optional[Dict[str, float]] = None,
    n_years: int = 5,
) -> Dict:
    """
    Build a complete 3-statement model.

    Parameters
    ----------
    historical_financials : dict
        Keys: "income", "balance", "cashflow" -> DataFrames (may be None).
    assumptions : dict, optional
        Override any assumption. Missing keys filled from historical averages.
    n_years : int
        Projection horizon.

    Returns
    -------
    dict with keys:
        projected_income, projected_balance, projected_cashflow,
        assumptions_used, historical_averages
    """
    income_df = historical_financials.get("income")
    balance_df = historical_financials.get("balance")
    cashflow_df = historical_financials.get("cashflow")

    # Step 1 -- compute historical averages as default assumptions
    hist_avg = compute_historical_averages(income_df, balance_df, cashflow_df)

    # Step 2 -- merge user overrides on top of defaults
    merged = {**hist_avg}
    if assumptions:
        merged.update(assumptions)

    # Ensure growth rates list exists
    if "revenue_growth_rates" not in merged:
        base_g = merged.get("revenue_cagr", 0.05)
        merged["revenue_growth_rates"] = [base_g] * n_years

    # Seed starting values from historicals when available
    if "last_revenue" not in merged and income_df is not None and not income_df.empty:
        rev = income_df.get("revenue")
        if rev is not None and not rev.dropna().empty:
            merged["last_revenue"] = float(rev.dropna().iloc[0])

    if "last_total_assets" not in merged and balance_df is not None and not balance_df.empty:
        ta = balance_df.get("total_assets")
        if ta is not None and not ta.dropna().empty:
            merged["last_total_assets"] = float(ta.dropna().iloc[0])

    if "last_total_debt" not in merged and balance_df is not None and not balance_df.empty:
        debt = balance_df.get("long_term_debt") or balance_df.get("total_debt")
        if debt is not None and not debt.dropna().empty:
            merged["last_total_debt"] = float(debt.dropna().iloc[0])

    # Step 3 -- project each statement
    proj_income = project_income_statement(income_df, merged, n_years)
    proj_balance = project_balance_sheet(balance_df, proj_income, merged, n_years)
    proj_cashflow = project_cash_flow(proj_income, proj_balance, balance_df)

    logger.info("Three-statement model built successfully (%d-year horizon)", n_years)

    return {
        "projected_income": proj_income,
        "projected_balance": proj_balance,
        "projected_cashflow": proj_cashflow,
        "assumptions_used": merged,
        "historical_averages": hist_avg,
    }
