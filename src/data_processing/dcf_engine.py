"""
DCF (Discounted Cash Flow) valuation engine.
Computes WACC, projects FCF, calculates terminal value, and runs sensitivity analysis.
Pure computation — zero Streamlit imports.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple

from src.utils.logger import setup_logger

logger = setup_logger("dcf_engine")


# ── WACC ─────────────────────────────────────────────────────────────────
def calculate_wacc(risk_free_rate: float, beta: float, market_premium: float,
                   cost_of_debt: float, tax_rate: float,
                   equity_weight: float, debt_weight: float) -> Tuple[float, float]:
    """
    Weighted Average Cost of Capital.

    Returns:
        (wacc, cost_of_equity)
    """
    cost_of_equity = risk_free_rate + beta * market_premium
    wacc = (equity_weight * cost_of_equity +
            debt_weight * cost_of_debt * (1 - tax_rate))
    return wacc, cost_of_equity


# ── FCF Projection ──────────────────────────────────────────────────────
def project_fcf(last_fcf: float, growth_rates: list, n_years: int = 5) -> list:
    """Project Free Cash Flow for *n_years* using supplied growth rates."""
    if last_fcf is None or np.isnan(last_fcf) or last_fcf == 0:
        last_fcf = 1_000_000  # fallback
    fcf_list = []
    current = last_fcf
    for i in range(n_years):
        rate = growth_rates[i] if i < len(growth_rates) else growth_rates[-1]
        current = current * (1 + rate)
        fcf_list.append(current)
    return fcf_list


# ── Terminal Value ───────────────────────────────────────────────────────
def calculate_terminal_value(final_fcf: float, wacc: float,
                             terminal_growth: float) -> float:
    """Gordon Growth Model: TV = FCF × (1+g) / (WACC − g)."""
    if wacc <= terminal_growth:
        return np.nan
    return final_fcf * (1 + terminal_growth) / (wacc - terminal_growth)


# ── Discounting ──────────────────────────────────────────────────────────
def discount_cash_flows(cash_flows: list, wacc: float,
                        terminal_value: float = None) -> float:
    """Discount a series of cash flows (and optional terminal value) to PV."""
    pv = 0.0
    for i, cf in enumerate(cash_flows):
        pv += cf / (1 + wacc) ** (i + 1)
    if terminal_value is not None:
        n = len(cash_flows)
        pv += terminal_value / (1 + wacc) ** n
    return pv


# ── Full DCF Calculation ────────────────────────────────────────────────
def calculate_dcf(projected_fcf: list, terminal_value: float, wacc: float,
                  net_debt: float, shares_outstanding: float,
                  current_price: float = None) -> dict:
    """
    Full DCF → fair value per share.

    Returns dict with enterprise_value, equity_value, fair_value_per_share,
    pv_fcf, pv_terminal, upside_pct.
    """
    pv_fcf = discount_cash_flows(projected_fcf, wacc)
    n = len(projected_fcf)
    pv_tv = terminal_value / (1 + wacc) ** n if terminal_value and not np.isnan(terminal_value) else 0

    enterprise_value = pv_fcf + pv_tv
    equity_value = enterprise_value - net_debt
    fair_value = equity_value / shares_outstanding if shares_outstanding and shares_outstanding > 0 else np.nan

    result = {
        "enterprise_value": enterprise_value,
        "equity_value": equity_value,
        "fair_value_per_share": fair_value,
        "pv_fcf": pv_fcf,
        "pv_terminal": pv_tv,
        "pv_fcf_pct": pv_fcf / enterprise_value * 100 if enterprise_value else 0,
        "pv_terminal_pct": pv_tv / enterprise_value * 100 if enterprise_value else 0,
    }
    if current_price and current_price > 0:
        result["upside_pct"] = (fair_value / current_price - 1) if not np.isnan(fair_value) else np.nan
        result["current_price"] = current_price
    return result


# ── Sensitivity Table ────────────────────────────────────────────────────
def sensitivity_table(base_fcf_list: list, terminal_fcf: float,
                      net_debt: float, shares_outstanding: float,
                      wacc_range: list, terminal_growth_range: list) -> pd.DataFrame:
    """
    Build a WACC × Terminal Growth sensitivity matrix of fair values.

    Returns DataFrame — index = WACC labels, columns = TG labels.
    """
    data = {}
    for tg in terminal_growth_range:
        col = {}
        for w in wacc_range:
            if w <= tg:
                col[f"{w:.1%}"] = np.nan
            else:
                tv = terminal_fcf * (1 + tg) / (w - tg)
                ev = discount_cash_flows(base_fcf_list, w, tv)
                eq = ev - net_debt
                fv = eq / shares_outstanding if shares_outstanding > 0 else np.nan
                col[f"{w:.1%}"] = round(fv, 2)
        data[f"{tg:.1%}"] = col

    df = pd.DataFrame(data)
    df.index.name = "WACC \\ Terminal Growth"
    return df


# ── Scenario Analysis ────────────────────────────────────────────────────
def scenario_analysis(base_result: dict, base_wacc: float,
                      base_tg: float, base_fcf_list: list,
                      terminal_fcf: float, net_debt: float,
                      shares_outstanding: float,
                      current_price: float = None) -> dict:
    """
    Run Bull / Base / Bear scenarios.

    Returns dict with keys 'bull', 'base', 'bear', each containing a DCF result dict.
    """
    scenarios = {}

    # Bull: +2% growth, −1% WACC, +0.5% TG
    bull_wacc = max(0.01, base_wacc - 0.01)
    bull_tg = base_tg + 0.005
    bull_fcf = [cf * 1.05 for cf in base_fcf_list]  # 5% higher FCFs
    bull_term_fcf = terminal_fcf * 1.05
    bull_tv = calculate_terminal_value(bull_term_fcf, bull_wacc, bull_tg)
    scenarios["bull"] = calculate_dcf(bull_fcf, bull_tv, bull_wacc, net_debt,
                                      shares_outstanding, current_price)
    scenarios["bull"]["label"] = "Bull Case"
    scenarios["bull"]["wacc"] = bull_wacc
    scenarios["bull"]["terminal_growth"] = bull_tg
    scenarios["bull"]["description"] = "Higher growth, lower discount rate"

    # Base
    scenarios["base"] = {**base_result}
    scenarios["base"]["label"] = "Base Case"
    scenarios["base"]["wacc"] = base_wacc
    scenarios["base"]["terminal_growth"] = base_tg
    scenarios["base"]["description"] = "Current assumptions"

    # Bear: −2% growth, +1% WACC, −0.5% TG
    bear_wacc = base_wacc + 0.01
    bear_tg = max(0.005, base_tg - 0.005)
    bear_fcf = [cf * 0.95 for cf in base_fcf_list]
    bear_term_fcf = terminal_fcf * 0.95
    bear_tv = calculate_terminal_value(bear_term_fcf, bear_wacc, bear_tg)
    scenarios["bear"] = calculate_dcf(bear_fcf, bear_tv, bear_wacc, net_debt,
                                      shares_outstanding, current_price)
    scenarios["bear"]["label"] = "Bear Case"
    scenarios["bear"]["wacc"] = bear_wacc
    scenarios["bear"]["terminal_growth"] = bear_tg
    scenarios["bear"]["description"] = "Lower growth, higher discount rate"

    return scenarios


# ── High-Level Convenience ────────────────────────────────────────────────
def run_full_dcf(info: dict, ratios_df, cashflow_df,
                 assumptions: dict = None) -> dict:
    """
    Run a complete DCF from raw company data.

    Args:
        info: yfinance .info dict
        ratios_df: DataFrame with 'fcf' column
        cashflow_df: cash flow statement DataFrame
        assumptions: optional overrides

    Returns dict with all DCF outputs including sensitivity & scenarios.
    """
    assumptions = assumptions or {}

    # Extract key values
    beta = info.get("beta", 1.0) or 1.0
    shares = info.get("sharesOutstanding", 0) or info.get("impliedSharesOutstanding", 0) or 1
    current_price = info.get("currentPrice") or info.get("regularMarketPrice") or 0
    market_cap = info.get("marketCap", 0) or 0
    total_debt = info.get("totalDebt", 0) or 0
    total_cash = info.get("totalCash", 0) or 0
    net_debt = total_debt - total_cash

    # Capital structure weights
    equity_value_market = market_cap if market_cap > 0 else shares * current_price
    total_capital = equity_value_market + total_debt
    equity_weight = equity_value_market / total_capital if total_capital > 0 else 0.8
    debt_weight = 1 - equity_weight

    # Assumptions with defaults
    risk_free = assumptions.get("risk_free_rate", 0.0425)
    market_premium = assumptions.get("market_premium", 0.055)
    cost_of_debt = assumptions.get("cost_of_debt", 0.05)
    tax_rate = assumptions.get("tax_rate", 0.21)
    terminal_growth = assumptions.get("terminal_growth", 0.025)

    # WACC
    wacc, cost_of_equity = calculate_wacc(
        risk_free, beta, market_premium, cost_of_debt, tax_rate,
        equity_weight, debt_weight
    )

    # Historical FCF
    last_fcf = 0
    if ratios_df is not None and "fcf" in ratios_df.columns:
        fcf_vals = ratios_df["fcf"].dropna()
        if not fcf_vals.empty:
            last_fcf = float(fcf_vals.iloc[0])
    if last_fcf == 0 and cashflow_df is not None:
        ocf = cashflow_df.get("operating_cash_flow")
        capex = cashflow_df.get("capital_expenditure")
        if ocf is not None and capex is not None:
            fcf_calc = ocf - capex.abs()
            valid = fcf_calc.dropna()
            if not valid.empty:
                last_fcf = float(valid.iloc[0])
    if last_fcf == 0:
        last_fcf = market_cap * 0.04 if market_cap > 0 else 1_000_000

    # FCF growth
    growth_rates = assumptions.get("fcf_growth_rates", [0.08, 0.07, 0.06, 0.05, 0.04])

    # Project
    projected_fcf = project_fcf(last_fcf, growth_rates, 5)
    terminal_value = calculate_terminal_value(projected_fcf[-1], wacc, terminal_growth)
    dcf_result = calculate_dcf(projected_fcf, terminal_value, wacc, net_debt,
                               shares, current_price)

    # Sensitivity
    wacc_range = [wacc + d for d in [-0.02, -0.015, -0.01, -0.005, 0, 0.005, 0.01, 0.015, 0.02]]
    tg_range = [terminal_growth + d for d in [-0.01, -0.0075, -0.005, -0.0025, 0, 0.0025, 0.005, 0.0075, 0.01]]
    sens_df = sensitivity_table(projected_fcf, projected_fcf[-1], net_debt, shares,
                                wacc_range, tg_range)

    # Scenarios
    scenarios = scenario_analysis(dcf_result, wacc, terminal_growth,
                                  projected_fcf, projected_fcf[-1],
                                  net_debt, shares, current_price)

    return {
        "wacc": wacc,
        "cost_of_equity": cost_of_equity,
        "beta": beta,
        "risk_free_rate": risk_free,
        "market_premium": market_premium,
        "cost_of_debt": cost_of_debt,
        "tax_rate": tax_rate,
        "equity_weight": equity_weight,
        "debt_weight": debt_weight,
        "terminal_growth": terminal_growth,
        "last_fcf": last_fcf,
        "projected_fcf": projected_fcf,
        "growth_rates": growth_rates,
        "terminal_value": terminal_value,
        "dcf_result": dcf_result,
        "sensitivity": sens_df,
        "scenarios": scenarios,
        "net_debt": net_debt,
        "shares_outstanding": shares,
        "current_price": current_price,
    }
