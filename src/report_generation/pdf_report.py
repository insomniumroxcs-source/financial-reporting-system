"""
PDF Report Generator – CFI Standards Edition
Uses FinancialPDF(FPDF) subclass with custom header/footer, CFI visual identity,
and structured multi-page financial report.
"""
import os
from datetime import datetime
from typing import Dict, Optional

import pandas as pd
import numpy as np

from src.utils.logger import setup_logger

logger = setup_logger("pdf_report")

# ── CFI Color Constants (RGB) ─────────────────────────────────────────────
CFI_NAVY_RGB = (0, 12, 63)         # #000C3F
CFI_DARK_NAVY_RGB = (19, 46, 87)   # #132E57
CFI_BLUE_ACCENT_RGB = (68, 114, 196)  # #4472C4
CFI_SECTION_BLUE_RGB = (50, 113, 210)  # #3271D2
CFI_INPUT_BLUE_RGB = (0, 0, 255)   # #0000FF
CFI_LIGHT_GRAY_RGB = (246, 246, 246)  # #F6F6F6
CFI_LIGHT_BLUE_RGB = (231, 242, 255)  # #E7F2FF
CFI_GREEN_RGB = (0, 176, 80)
CFI_RED_RGB = (255, 0, 0)


def _sanitize(text) -> str:
    if not isinstance(text, str):
        text = str(text)
    replacements = {
        '\u2014': '-', '\u2013': '-', '\u2018': "'", '\u2019': "'",
        '\u201c': '"', '\u201d': '"', '\u2026': '...', '\u2022': '*',
        '\u2713': '[OK]', '\u2717': '[X]', '\u00ae': '(R)',
        '\u2122': '(TM)', '\u00a9': '(C)', '\u00b0': 'deg',
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text.encode('latin-1', errors='replace').decode('latin-1')


def _fmt_dollar(value) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "N/A"
    try:
        v = float(value)
        if abs(v) >= 1e9:
            return f"${v/1e9:,.1f}B"
        elif abs(v) >= 1e6:
            return f"${v/1e6:,.1f}M"
        else:
            return f"${v:,.0f}"
    except (ValueError, TypeError):
        return str(value)


def _fmt_pct(value) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "N/A"
    try:
        return f"{float(value)*100:.1f}%"
    except (ValueError, TypeError):
        return str(value)


def _fmt_ratio(value) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "N/A"
    try:
        return f"{float(value):.2f}"
    except (ValueError, TypeError):
        return str(value)


# ── FinancialPDF Subclass ─────────────────────────────────────────────────
class FinancialPDF:
    """Wrapper around FPDF with CFI-standard header/footer and helpers."""

    def __init__(self, ticker: str, company_name: str):
        from fpdf import FPDF
        self.pdf = FPDF()
        self.pdf.set_auto_page_break(auto=True, margin=20)
        self.ticker = ticker
        self.company_name = company_name
        self._page_count = 0
        self._sections = []

    def _header(self):
        """Custom CFI header: company left, report title right, navy line."""
        self.pdf.set_font("Helvetica", "B", 9)
        self.pdf.set_text_color(*CFI_NAVY_RGB)
        self.pdf.cell(95, 6, _sanitize(f"{self.company_name} ({self.ticker})"), align="L")
        self.pdf.set_font("Helvetica", "", 9)
        self.pdf.set_text_color(100, 100, 100)
        self.pdf.cell(95, 6, "Financial Report", align="R")
        self.pdf.ln(7)
        self.pdf.set_draw_color(*CFI_NAVY_RGB)
        self.pdf.set_line_width(0.5)
        self.pdf.line(10, self.pdf.get_y(), 200, self.pdf.get_y())
        self.pdf.ln(5)

    def _footer(self):
        """Custom CFI footer: date left, page right, navy separator."""
        self.pdf.set_y(-18)
        self.pdf.set_draw_color(*CFI_NAVY_RGB)
        self.pdf.set_line_width(0.3)
        self.pdf.line(10, self.pdf.get_y(), 200, self.pdf.get_y())
        self.pdf.ln(2)
        self.pdf.set_font("Helvetica", "", 7)
        self.pdf.set_text_color(100, 100, 100)
        self.pdf.cell(95, 5, datetime.now().strftime("%B %d, %Y"), align="L")
        self.pdf.cell(95, 5, f"Page {self.pdf.page_no()}", align="R")

    def add_page(self):
        self.pdf.add_page()
        self._page_count += 1
        if self._page_count > 1:
            self._header()

    def section_header(self, title: str):
        """Dark navy bar with white text for section headers."""
        self.pdf.set_fill_color(*CFI_DARK_NAVY_RGB)
        self.pdf.set_text_color(255, 255, 255)
        self.pdf.set_font("Helvetica", "B", 13)
        self.pdf.cell(0, 10, f"  {_sanitize(title)}", ln=True, fill=True)
        self.pdf.set_text_color(0, 0, 0)
        self.pdf.ln(3)

    def subtitle(self, text: str = "All figures in USD thousands unless stated"):
        self.pdf.set_font("Helvetica", "I", 8)
        self.pdf.set_text_color(150, 150, 150)
        self.pdf.cell(0, 5, _sanitize(text), ln=True)
        self.pdf.set_text_color(0, 0, 0)
        self.pdf.ln(2)

    def output(self, filepath: str):
        self.pdf.output(filepath)


def _add_cover_page(fpdf: FinancialPDF, info: dict, ticker: str):
    """CFI-style cover with navy rect and blue title."""
    fpdf.add_page()

    # Navy banner
    fpdf.pdf.set_fill_color(*CFI_NAVY_RGB)
    fpdf.pdf.rect(0, 0, 210, 75, "F")

    fpdf.pdf.set_text_color(255, 255, 255)
    fpdf.pdf.set_font("Helvetica", "B", 28)
    fpdf.pdf.set_y(18)
    fpdf.pdf.cell(0, 15, "Financial Report", ln=True, align="C")

    fpdf.pdf.set_font("Helvetica", "", 18)
    fpdf.pdf.cell(0, 12, _sanitize(fpdf.company_name), ln=True, align="C")

    fpdf.pdf.set_font("Helvetica", "", 12)
    fpdf.pdf.cell(0, 8, f"Ticker: {ticker.upper()}", ln=True, align="C")

    fpdf.pdf.set_text_color(0, 0, 0)
    fpdf.pdf.set_y(85)

    # Company overview
    fpdf.pdf.set_font("Helvetica", "B", 14)
    fpdf.pdf.set_text_color(*CFI_DARK_NAVY_RGB)
    fpdf.pdf.cell(0, 10, "Company Overview", ln=True)
    fpdf.pdf.set_text_color(0, 0, 0)
    fpdf.pdf.set_font("Helvetica", "", 11)
    fpdf.pdf.ln(2)

    lines = [
        f"Sector: {info.get('sector', 'N/A')}",
        f"Industry: {info.get('industry', 'N/A')}",
        f"Market Cap: {_fmt_dollar(info.get('marketCap'))}",
        f"P/E (Trailing): {_fmt_ratio(info.get('trailingPE'))}",
        f"P/E (Forward): {_fmt_ratio(info.get('forwardPE'))}",
        f"Dividend Yield: {_fmt_pct(info.get('dividendYield'))}",
        f"52W High: {_fmt_dollar(info.get('fiftyTwoWeekHigh'))}",
        f"52W Low: {_fmt_dollar(info.get('fiftyTwoWeekLow'))}",
        f"Beta: {_fmt_ratio(info.get('beta'))}",
    ]
    for line in lines:
        fpdf.pdf.cell(0, 7, _sanitize(f"  {line}"), ln=True)

    fpdf.pdf.ln(5)

    # Key Takeaways box
    fpdf.pdf.set_fill_color(*CFI_LIGHT_BLUE_RGB)
    fpdf.pdf.set_draw_color(*CFI_SECTION_BLUE_RGB)
    fpdf.pdf.rect(15, fpdf.pdf.get_y(), 180, 30, "D")
    fpdf.pdf.set_xy(20, fpdf.pdf.get_y() + 3)
    fpdf.pdf.set_font("Helvetica", "B", 10)
    fpdf.pdf.set_text_color(*CFI_SECTION_BLUE_RGB)
    fpdf.pdf.cell(0, 6, "Key Takeaways", ln=True)
    fpdf.pdf.set_x(20)
    fpdf.pdf.set_font("Helvetica", "", 9)
    fpdf.pdf.set_text_color(0, 0, 0)
    sector = info.get("sector", "N/A")
    fpdf.pdf.multi_cell(170, 5, _sanitize(
        f"This report provides a comprehensive financial analysis of {fpdf.company_name} ({ticker}), "
        f"operating in the {sector} sector. Analysis includes financial statements, "
        f"key ratios, and trend analysis based on the latest available data."
    ))

    fpdf.pdf.ln(10)
    fpdf.pdf.set_font("Helvetica", "I", 9)
    fpdf.pdf.set_text_color(128, 128, 128)
    fpdf.pdf.cell(0, 6, f"Report generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", ln=True)
    fpdf.pdf.set_text_color(0, 0, 0)


def _add_toc_page(fpdf: FinancialPDF, sections: list):
    """CFI-style Table of Contents."""
    fpdf.add_page()
    fpdf.section_header("Table of Contents")

    fpdf.pdf.set_font("Helvetica", "", 11)
    for i, (title, page) in enumerate(sections, 1):
        fpdf.pdf.set_text_color(*CFI_NAVY_RGB)
        fpdf.pdf.cell(10, 8, f"{i}.", align="R")
        fpdf.pdf.set_text_color(*CFI_SECTION_BLUE_RGB)
        fpdf.pdf.set_font("Helvetica", "", 11)
        fpdf.pdf.cell(140, 8, _sanitize(f"  {title}"))
        fpdf.pdf.set_text_color(100, 100, 100)
        fpdf.pdf.cell(40, 8, str(page), align="R")
        fpdf.pdf.ln()
    fpdf.pdf.set_text_color(0, 0, 0)


def _add_executive_summary(fpdf: FinancialPDF, info: dict, ratios_df):
    """1-page executive summary with key metrics."""
    fpdf.add_page()
    fpdf.section_header("Executive Summary")
    fpdf.subtitle()

    fpdf.pdf.set_font("Helvetica", "", 10)
    company = fpdf.company_name
    sector = info.get("sector", "N/A")
    fpdf.pdf.multi_cell(0, 6, _sanitize(
        f"{company} is a {sector} company. This section provides a high-level overview "
        f"of the company's financial health based on the most recent available data."
    ))
    fpdf.pdf.ln(5)

    # 2x2 metric grid
    metrics = [
        ("Market Cap", _fmt_dollar(info.get("marketCap"))),
        ("P/E Ratio", _fmt_ratio(info.get("trailingPE"))),
        ("Dividend Yield", _fmt_pct(info.get("dividendYield"))),
        ("Beta", _fmt_ratio(info.get("beta"))),
    ]

    fpdf.pdf.set_font("Helvetica", "B", 10)
    for i, (label, value) in enumerate(metrics):
        x = 15 + (i % 2) * 92
        y = fpdf.pdf.get_y() if i < 2 else fpdf.pdf.get_y()
        if i == 2:
            fpdf.pdf.ln(20)

        fpdf.pdf.set_xy(x, fpdf.pdf.get_y())
        fpdf.pdf.set_fill_color(*CFI_LIGHT_GRAY_RGB)
        fpdf.pdf.cell(85, 16, "", fill=True)
        fpdf.pdf.set_xy(x + 3, fpdf.pdf.get_y())
        fpdf.pdf.set_text_color(*CFI_SECTION_BLUE_RGB)
        fpdf.pdf.set_font("Helvetica", "", 8)
        fpdf.pdf.cell(40, 5, label)
        fpdf.pdf.set_xy(x + 3, fpdf.pdf.get_y() + 5)
        fpdf.pdf.set_text_color(0, 0, 0)
        fpdf.pdf.set_font("Helvetica", "B", 14)
        fpdf.pdf.cell(40, 8, _sanitize(value))


def _add_statement_page(fpdf: FinancialPDF, title: str, df):
    """Add a financial statement table page."""
    fpdf.add_page()
    fpdf.section_header(title)
    fpdf.subtitle()

    if df is None or (isinstance(df, pd.DataFrame) and df.empty):
        fpdf.pdf.set_font("Helvetica", "I", 11)
        fpdf.pdf.cell(0, 8, "  No data available", ln=True)
        return

    display_df = df.copy()
    if "ticker" in display_df.columns:
        display_df = display_df.drop(columns=["ticker"])
    if len(display_df.columns) > 6:
        display_df = display_df.iloc[:, :6]

    n_cols = len(display_df.columns) + 1
    col_width = min(170 / n_cols, 30)
    label_width = 170 - col_width * len(display_df.columns)

    # Header row
    fpdf.pdf.set_font("Helvetica", "B", 8)
    fpdf.pdf.set_fill_color(*CFI_DARK_NAVY_RGB)
    fpdf.pdf.set_text_color(255, 255, 255)
    fpdf.pdf.cell(label_width, 7, "Metric", border=1, fill=True)
    for col in display_df.columns:
        label = col.strftime("%Y-%m") if hasattr(col, "strftime") else str(col)[:12]
        fpdf.pdf.cell(col_width, 7, label, border=1, align="C", fill=True)
    fpdf.pdf.ln()

    # Data rows
    fpdf.pdf.set_text_color(0, 0, 0)
    fpdf.pdf.set_font("Helvetica", "", 7)
    for i, (idx, row_data) in enumerate(display_df.iterrows()):
        if i % 2 == 1:
            fpdf.pdf.set_fill_color(*CFI_LIGHT_GRAY_RGB)
        else:
            fpdf.pdf.set_fill_color(255, 255, 255)

        label = idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx)[:25]
        fpdf.pdf.cell(label_width, 6, _sanitize(f" {label}"), border=1, fill=True)

        for val in row_data:
            formatted = _fmt_dollar(val) if pd.notna(val) else "-"
            # Color negatives red
            if pd.notna(val):
                try:
                    if float(val) < 0:
                        fpdf.pdf.set_text_color(*CFI_RED_RGB)
                except (ValueError, TypeError):
                    pass
            fpdf.pdf.cell(col_width, 6, _sanitize(formatted), border=1, align="R", fill=True)
            fpdf.pdf.set_text_color(0, 0, 0)
        fpdf.pdf.ln()


def _add_ratios_page(fpdf: FinancialPDF, ratios_df):
    """Add ratios summary page."""
    fpdf.add_page()
    fpdf.section_header("Key Financial Ratios")

    pct_cols = {"gross_margin", "operating_margin", "net_margin", "ebitda_margin",
                "roe", "roa", "dupont_roe"}
    ratio_display = [
        "gross_margin", "operating_margin", "net_margin",
        "roe", "roa", "current_ratio", "debt_to_equity",
    ]
    available = [c for c in ratio_display if c in ratios_df.columns]
    if not available:
        fpdf.pdf.set_font("Helvetica", "I", 11)
        fpdf.pdf.cell(0, 8, "  No ratio data", ln=True)
        return

    display_df = ratios_df[available]
    n_cols = len(display_df.columns) + 1
    col_width = min(170 / n_cols, 28)
    label_width = 170 - col_width * len(display_df.columns)

    fpdf.pdf.set_font("Helvetica", "B", 8)
    fpdf.pdf.set_fill_color(*CFI_DARK_NAVY_RGB)
    fpdf.pdf.set_text_color(255, 255, 255)
    fpdf.pdf.cell(label_width, 7, "Period", border=1, fill=True)
    for col in display_df.columns:
        fpdf.pdf.cell(col_width, 7, col.replace("_", " ").title()[:15], border=1, align="C", fill=True)
    fpdf.pdf.ln()

    fpdf.pdf.set_text_color(0, 0, 0)
    fpdf.pdf.set_font("Helvetica", "", 7)
    for i, (idx, row_data) in enumerate(display_df.iterrows()):
        if i % 2 == 1:
            fpdf.pdf.set_fill_color(*CFI_LIGHT_GRAY_RGB)
        else:
            fpdf.pdf.set_fill_color(255, 255, 255)

        fpdf.pdf.cell(label_width, 6, f" {str(idx)[:15]}", border=1, fill=True)
        for col, val in row_data.items():
            formatted = _fmt_pct(val) if col in pct_cols else _fmt_ratio(val)
            fpdf.pdf.cell(col_width, 6, formatted, border=1, align="R", fill=True)
        fpdf.pdf.ln()


def _add_appendix(fpdf: FinancialPDF):
    """Appendix with methodology notes and disclaimers."""
    fpdf.add_page()
    fpdf.section_header("Appendix")

    fpdf.pdf.set_font("Helvetica", "B", 10)
    fpdf.pdf.cell(0, 8, "Data Sources", ln=True)
    fpdf.pdf.set_font("Helvetica", "", 9)
    fpdf.pdf.multi_cell(0, 5, _sanitize(
        "- Price data: Yahoo Finance (yfinance)\n"
        "- Financial statements: SEC EDGAR / yfinance\n"
        "- Ratios: Computed from raw financial statement data\n"
    ))
    fpdf.pdf.ln(3)

    fpdf.pdf.set_font("Helvetica", "B", 10)
    fpdf.pdf.cell(0, 8, "Ratio Definitions", ln=True)
    fpdf.pdf.set_font("Helvetica", "", 9)
    fpdf.pdf.multi_cell(0, 5, _sanitize(
        "- Gross Margin = Gross Profit / Revenue\n"
        "- Operating Margin = Operating Income / Revenue\n"
        "- Net Margin = Net Income / Revenue\n"
        "- ROE = Net Income / Total Equity\n"
        "- ROA = Net Income / Total Assets\n"
        "- Current Ratio = Current Assets / Current Liabilities\n"
        "- Debt/Equity = Total Liabilities / Total Equity\n"
    ))
    fpdf.pdf.ln(3)

    fpdf.pdf.set_font("Helvetica", "B", 10)
    fpdf.pdf.cell(0, 8, "Disclaimer", ln=True)
    fpdf.pdf.set_font("Helvetica", "I", 8)
    fpdf.pdf.set_text_color(100, 100, 100)
    fpdf.pdf.multi_cell(0, 5, _sanitize(
        "This report is generated automatically and is for informational purposes only. "
        "It does not constitute investment advice. Data accuracy depends on third-party "
        "sources. Always verify critical figures before making investment decisions."
    ))
    fpdf.pdf.set_text_color(0, 0, 0)


# ── Dashboard Charts Page ────────────────────────────────────────────────
def _add_dashboard_charts(fpdf: FinancialPDF, financials, ratios_df):
    """Visual summary page with key metric indicators."""
    fpdf.add_page()
    fpdf.section_header("Dashboard Charts")
    fpdf.subtitle("Visual summary of key financial metrics")

    income_df = financials.get("income_statement") if financials else None
    if income_df is not None and not income_df.empty and "revenue" in income_df.columns:
        fpdf.pdf.set_font("Helvetica", "B", 11)
        fpdf.pdf.set_text_color(*CFI_SECTION_BLUE_RGB)
        fpdf.pdf.cell(0, 8, "Revenue Trend", ln=True)
        fpdf.pdf.set_text_color(0, 0, 0)
        fpdf.pdf.set_font("Helvetica", "", 9)
        for idx, row in income_df.iterrows():
            label = idx.strftime("%Y-%m") if hasattr(idx, "strftime") else str(idx)[:10]
            val = _fmt_dollar(row.get("revenue"))
            fpdf.pdf.cell(50, 6, _sanitize(label))
            fpdf.pdf.cell(60, 6, _sanitize(val), align="R")
            fpdf.pdf.ln()
        fpdf.pdf.ln(5)

    if ratios_df is not None and not ratios_df.empty:
        margin_cols = [c for c in ["gross_margin", "operating_margin", "net_margin"] if c in ratios_df.columns]
        if margin_cols:
            fpdf.pdf.set_font("Helvetica", "B", 11)
            fpdf.pdf.set_text_color(*CFI_SECTION_BLUE_RGB)
            fpdf.pdf.cell(0, 8, "Margin Trends", ln=True)
            fpdf.pdf.set_text_color(0, 0, 0)
            fpdf.pdf.set_font("Helvetica", "", 9)
            for idx, row in ratios_df.iterrows():
                label = str(idx)[:10]
                margins = " | ".join(f"{c.replace('_',' ').title()}: {_fmt_pct(row.get(c))}" for c in margin_cols)
                fpdf.pdf.cell(0, 6, _sanitize(f"{label}: {margins}"), ln=True)


# ── DCF Page ─────────────────────────────────────────────────────────────
def _add_dcf_page(fpdf: FinancialPDF, info: dict):
    """DCF valuation summary page."""
    fpdf.add_page()
    fpdf.section_header("DCF Valuation Summary")
    fpdf.subtitle("Discounted Cash Flow analysis overview")

    fpdf.pdf.set_font("Helvetica", "", 10)
    beta = info.get("beta", "N/A")
    market_cap = _fmt_dollar(info.get("marketCap"))
    total_debt = _fmt_dollar(info.get("totalDebt", 0))
    total_cash = _fmt_dollar(info.get("totalCash", 0))

    rows = [
        ("Beta", _fmt_ratio(beta)),
        ("Market Capitalization", market_cap),
        ("Total Debt", total_debt),
        ("Total Cash", total_cash),
        ("Risk-Free Rate (default)", "4.25%"),
        ("Market Premium (default)", "5.50%"),
        ("Terminal Growth (default)", "2.50%"),
    ]

    fpdf.pdf.set_fill_color(*CFI_DARK_NAVY_RGB)
    fpdf.pdf.set_text_color(255, 255, 255)
    fpdf.pdf.set_font("Helvetica", "B", 9)
    fpdf.pdf.cell(90, 7, "  Parameter", border=1, fill=True)
    fpdf.pdf.cell(80, 7, "Value", border=1, align="C", fill=True)
    fpdf.pdf.ln()

    fpdf.pdf.set_text_color(0, 0, 0)
    fpdf.pdf.set_font("Helvetica", "", 9)
    for i, (label, val) in enumerate(rows):
        if i % 2 == 1:
            fpdf.pdf.set_fill_color(*CFI_LIGHT_GRAY_RGB)
        else:
            fpdf.pdf.set_fill_color(255, 255, 255)
        fpdf.pdf.cell(90, 6, _sanitize(f"  {label}"), border=1, fill=True)
        fpdf.pdf.cell(80, 6, _sanitize(val), border=1, align="R", fill=True)
        fpdf.pdf.ln()

    fpdf.pdf.ln(5)
    fpdf.pdf.set_font("Helvetica", "I", 8)
    fpdf.pdf.set_text_color(100, 100, 100)
    fpdf.pdf.cell(0, 5, "Note: Full DCF with sensitivity analysis is available in the interactive dashboard.", ln=True)
    fpdf.pdf.set_text_color(0, 0, 0)


# ── Forecast Page ────────────────────────────────────────────────────────
def _add_forecast_page(fpdf: FinancialPDF, info: dict):
    """3-statement forecast summary page."""
    fpdf.add_page()
    fpdf.section_header("Financial Forecast Summary")
    fpdf.subtitle("3-statement model projection overview")

    fpdf.pdf.set_font("Helvetica", "", 10)
    fpdf.pdf.multi_cell(0, 6, _sanitize(
        f"The financial model projects {fpdf.company_name}'s income statement, balance sheet, "
        f"and cash flow statement over a 5-year horizon. Key assumptions are derived from "
        f"historical averages with user-adjustable growth rates."
    ))
    fpdf.pdf.ln(5)

    # Assumptions summary
    fpdf.pdf.set_font("Helvetica", "B", 10)
    fpdf.pdf.set_text_color(*CFI_SECTION_BLUE_RGB)
    fpdf.pdf.cell(0, 8, "Default Assumptions", ln=True)
    fpdf.pdf.set_text_color(0, 0, 0)
    fpdf.pdf.set_font("Helvetica", "", 9)

    defaults = [
        ("Revenue Growth", "Based on historical CAGR"),
        ("COGS %", "Historical average"),
        ("OpEx % of Revenue", "Historical average"),
        ("Tax Rate", "21% (US corporate)"),
        ("CapEx % of Revenue", "5% default"),
        ("Projection Horizon", "5 years"),
    ]
    for label, val in defaults:
        fpdf.pdf.cell(80, 6, _sanitize(f"  {label}"))
        fpdf.pdf.cell(90, 6, _sanitize(val))
        fpdf.pdf.ln()

    fpdf.pdf.ln(5)
    fpdf.pdf.set_font("Helvetica", "I", 8)
    fpdf.pdf.set_text_color(100, 100, 100)
    fpdf.pdf.cell(0, 5, "Note: Full projected statements are available in the interactive dashboard.", ln=True)
    fpdf.pdf.set_text_color(0, 0, 0)


# ── Variance Page ────────────────────────────────────────────────────────
def _add_variance_page(fpdf: FinancialPDF, info: dict, financials):
    """Budget variance analysis summary page."""
    fpdf.add_page()
    fpdf.section_header("Budget Variance Analysis")
    fpdf.subtitle("Actual vs industry benchmark comparison")

    sector = info.get("sector", "N/A")
    fpdf.pdf.set_font("Helvetica", "", 10)
    fpdf.pdf.multi_cell(0, 6, _sanitize(
        f"This section compares {fpdf.company_name}'s actual financial performance "
        f"against industry benchmarks for the {sector} sector."
    ))
    fpdf.pdf.ln(5)

    # Industry benchmarks
    benchmarks = {
        "Technology": {"Gross Margin": "60%", "Operating Margin": "25%", "Net Margin": "20%"},
        "Financial Services": {"Gross Margin": "55%", "Operating Margin": "35%", "Net Margin": "25%"},
        "Healthcare": {"Gross Margin": "65%", "Operating Margin": "20%", "Net Margin": "15%"},
        "Consumer Defensive": {"Gross Margin": "37%", "Operating Margin": "15%", "Net Margin": "10%"},
    }
    bm = benchmarks.get(sector, {"Gross Margin": "40%", "Operating Margin": "15%", "Net Margin": "10%"})

    fpdf.pdf.set_font("Helvetica", "B", 10)
    fpdf.pdf.set_text_color(*CFI_SECTION_BLUE_RGB)
    fpdf.pdf.cell(0, 8, f"Industry Benchmarks ({sector})", ln=True)
    fpdf.pdf.set_text_color(0, 0, 0)

    fpdf.pdf.set_fill_color(*CFI_DARK_NAVY_RGB)
    fpdf.pdf.set_text_color(255, 255, 255)
    fpdf.pdf.set_font("Helvetica", "B", 9)
    fpdf.pdf.cell(90, 7, "  Metric", border=1, fill=True)
    fpdf.pdf.cell(80, 7, "Benchmark", border=1, align="C", fill=True)
    fpdf.pdf.ln()

    fpdf.pdf.set_text_color(0, 0, 0)
    fpdf.pdf.set_font("Helvetica", "", 9)
    for i, (metric, val) in enumerate(bm.items()):
        if i % 2 == 1:
            fpdf.pdf.set_fill_color(*CFI_LIGHT_GRAY_RGB)
        else:
            fpdf.pdf.set_fill_color(255, 255, 255)
        fpdf.pdf.cell(90, 6, _sanitize(f"  {metric}"), border=1, fill=True)
        fpdf.pdf.cell(80, 6, val, border=1, align="R", fill=True)
        fpdf.pdf.ln()

    fpdf.pdf.ln(5)
    fpdf.pdf.set_font("Helvetica", "I", 8)
    fpdf.pdf.set_text_color(100, 100, 100)
    fpdf.pdf.cell(0, 5, "Note: Detailed variance waterfall and margin impact available in the interactive dashboard.", ln=True)
    fpdf.pdf.set_text_color(0, 0, 0)


# ── Trend Analysis Page ─────────────────────────────────────────────────
def _add_trend_analysis_page(fpdf: FinancialPDF, ratios_df):
    """Multi-year trend analysis of key ratios."""
    fpdf.add_page()
    fpdf.section_header("Trend Analysis")
    fpdf.subtitle("Multi-year trend of key financial ratios")

    if ratios_df is None or (isinstance(ratios_df, pd.DataFrame) and ratios_df.empty):
        fpdf.pdf.set_font("Helvetica", "I", 11)
        fpdf.pdf.cell(0, 8, "  No ratio data available for trend analysis", ln=True)
        return

    sections = {
        "Profitability": ["gross_margin", "operating_margin", "net_margin", "roe", "roa"],
        "Leverage": ["debt_to_equity", "interest_coverage"],
        "Liquidity": ["current_ratio"],
    }

    for section_name, cols in sections.items():
        available = [c for c in cols if c in ratios_df.columns]
        if not available:
            continue

        fpdf.pdf.set_font("Helvetica", "B", 11)
        fpdf.pdf.set_text_color(*CFI_SECTION_BLUE_RGB)
        fpdf.pdf.cell(0, 8, section_name, ln=True)
        fpdf.pdf.set_text_color(0, 0, 0)

        pct_cols = {"gross_margin", "operating_margin", "net_margin", "roe", "roa"}

        # Table
        n_periods = min(len(ratios_df), 5)
        col_width = 25
        label_width = 170 - col_width * n_periods

        fpdf.pdf.set_fill_color(*CFI_DARK_NAVY_RGB)
        fpdf.pdf.set_text_color(255, 255, 255)
        fpdf.pdf.set_font("Helvetica", "B", 8)
        fpdf.pdf.cell(label_width, 7, "  Metric", border=1, fill=True)
        for j, idx in enumerate(ratios_df.index[:n_periods]):
            label = idx.strftime("%Y") if hasattr(idx, "strftime") else str(idx)[:8]
            fpdf.pdf.cell(col_width, 7, label, border=1, align="C", fill=True)
        fpdf.pdf.ln()

        fpdf.pdf.set_text_color(0, 0, 0)
        fpdf.pdf.set_font("Helvetica", "", 8)
        for i, col_name in enumerate(available):
            if i % 2 == 1:
                fpdf.pdf.set_fill_color(*CFI_LIGHT_GRAY_RGB)
            else:
                fpdf.pdf.set_fill_color(255, 255, 255)
            fpdf.pdf.cell(label_width, 6, _sanitize(f"  {col_name.replace('_', ' ').title()}"), border=1, fill=True)
            for j, val in enumerate(ratios_df[col_name].iloc[:n_periods]):
                formatted = _fmt_pct(val) if col_name in pct_cols else _fmt_ratio(val)
                fpdf.pdf.cell(col_width, 6, formatted, border=1, align="R", fill=True)
            fpdf.pdf.ln()
        fpdf.pdf.ln(3)


# ── Main Generator ───────────────────────────────────────────────────────
def generate_pdf_report(
    ticker: str,
    company_info: dict,
    financials: Dict[str, Optional[pd.DataFrame]],
    ratios_df: Optional[pd.DataFrame],
    output_dir: str = "output/pdf",
) -> str:
    logger.info(f"[{ticker}] Generating CFI-standard PDF report")

    company_name = company_info.get("longName", company_info.get("shortName", ticker))
    fpdf = FinancialPDF(ticker, company_name)

    # Build sections
    sections = [
        ("Company Overview", 1),
        ("Table of Contents", 2),
        ("Executive Summary", 3),
        ("Dashboard Charts", 4),
        ("Income Statement", 5),
        ("Balance Sheet", 6),
        ("Cash Flow Statement", 7),
        ("Key Financial Ratios", 8),
        ("DCF Valuation Summary", 9),
        ("Financial Forecast Summary", 10),
        ("Budget Variance Analysis", 11),
        ("Trend Analysis", 12),
        ("Appendix", 13),
    ]

    _add_cover_page(fpdf, company_info, ticker)
    _add_toc_page(fpdf, sections)
    _add_executive_summary(fpdf, company_info, ratios_df)
    _add_dashboard_charts(fpdf, financials, ratios_df)

    # Financial statements
    for title, df in [
        ("Income Statement", financials.get("income_statement")),
        ("Balance Sheet", financials.get("balance_sheet")),
        ("Cash Flow Statement", financials.get("cash_flow")),
    ]:
        _add_statement_page(fpdf, title, df)

    if ratios_df is not None and not ratios_df.empty:
        _add_ratios_page(fpdf, ratios_df)

    _add_dcf_page(fpdf, company_info)
    _add_forecast_page(fpdf, company_info)
    _add_variance_page(fpdf, company_info, financials)
    _add_trend_analysis_page(fpdf, ratios_df)
    _add_appendix(fpdf)

    # Add footer to all pages
    for page_num in range(1, fpdf.pdf.page_no() + 1):
        fpdf.pdf.page = page_num
        fpdf._footer()

    # Save
    os.makedirs(output_dir, exist_ok=True)
    filename = f"{ticker.upper()}_Financial_Report_{datetime.now().strftime('%Y%m%d')}.pdf"
    filepath = os.path.join(output_dir, filename)
    fpdf.output(filepath)
    logger.info(f"[{ticker}] CFI PDF report saved: {filepath}")
    return filepath

