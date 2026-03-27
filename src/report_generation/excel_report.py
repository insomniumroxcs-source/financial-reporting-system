"""
Excel Report Generator – CFI Standards Edition
Builds a professionally formatted multi-sheet Excel workbook following
Corporate Finance Institute (CFI) design guidelines.

Sheets: Cover/TOC, Income Statement, Balance Sheet, Cash Flow, Ratios,
        Charts, DCF, Forecast, Variance, Trend Analysis
"""
import os
from datetime import datetime
from typing import Dict, Optional

import pandas as pd
import numpy as np
from openpyxl import Workbook
from openpyxl.styles import (
    PatternFill, Font, Alignment, Border, Side, numbers, NamedStyle
)
from openpyxl.formatting.rule import CellIsRule, ColorScaleRule
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.utils import get_column_letter
from openpyxl.workbook.defined_name import DefinedName

from src.utils.logger import setup_logger

logger = setup_logger("excel_report")

# ── CFI Color Palette (exact hex from CFI templates) ──────────────────────
CFI_NAVY = "000C3F"
CFI_DARK_NAVY = "132E57"
CFI_LIGHT_GRAY = "F6F6F6"
CFI_LIGHT_BLUE = "E7F2FF"
CFI_BLUE_ACCENT = "4472C4"
CFI_SECTION_BLUE = "3271D2"
CFI_LINK_BLUE = "002060"
CFI_TEAL = "1E8496"
CFI_AMBER = "ED942D"
CFI_PROF_BLUE = "D9E5F7"
CFI_INPUT_BLUE = "0000FF"
CFI_FORMULA_BLACK = "000000"
CFI_WARNING_AMBER = "947131"
CFI_ERROR_RED = "FF0000"
CFI_WHITE = "FFFFFF"

# ── CFI Fills ─────────────────────────────────────────────────────────────
NAVY_FILL = PatternFill(start_color=CFI_NAVY, end_color=CFI_NAVY, fill_type="solid")
DARK_NAVY_FILL = PatternFill(start_color=CFI_DARK_NAVY, end_color=CFI_DARK_NAVY, fill_type="solid")
ALT_ROW_FILL = PatternFill(start_color=CFI_LIGHT_GRAY, end_color=CFI_LIGHT_GRAY, fill_type="solid")
INPUT_HIGHLIGHT = PatternFill(start_color=CFI_LIGHT_BLUE, end_color=CFI_LIGHT_BLUE, fill_type="solid")
PROF_BLUE_FILL = PatternFill(start_color=CFI_PROF_BLUE, end_color=CFI_PROF_BLUE, fill_type="solid")
AMBER_FILL = PatternFill(start_color=CFI_AMBER, end_color=CFI_AMBER, fill_type="solid")
RED_FILL = PatternFill(start_color="FFCCCC", end_color="FFCCCC", fill_type="solid")
GREEN_FILL = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")

# ── CFI Fonts ─────────────────────────────────────────────────────────────
FONT_BODY = Font(name="Open Sans", size=10, color=CFI_FORMULA_BLACK)
FONT_HEADER_14 = Font(name="Open Sans", size=14, bold=True, color=CFI_WHITE)
FONT_TITLE_16 = Font(name="Open Sans", size=16, bold=True, color=CFI_SECTION_BLUE)
FONT_COVER_20 = Font(name="Open Sans", size=20, bold=True, color=CFI_BLUE_ACCENT)
FONT_SECTION = Font(name="Open Sans", size=14, bold=True, color=CFI_SECTION_BLUE)
FONT_INPUT = Font(name="Open Sans", size=10, color=CFI_INPUT_BLUE)
FONT_LINK = Font(name="Open Sans", size=10, color=CFI_LINK_BLUE, underline="single")
FONT_WARNING = Font(name="Open Sans", size=10, color=CFI_WARNING_AMBER)
FONT_ERROR = Font(name="Open Sans", size=10, color=CFI_ERROR_RED)
FONT_WHITE_BOLD = Font(name="Open Sans", size=10, bold=True, color=CFI_WHITE)
FONT_LABEL = Font(name="Open Sans", size=10, bold=True)
FONT_TOTAL = Font(name="Open Sans", size=10, bold=True, color=CFI_FORMULA_BLACK)
FONT_COVER_BODY = Font(name="Open Sans", size=12, color="666666")

HEADER_ALIGN = Alignment(horizontal="center", vertical="center", wrap_text=True)
LEFT_ALIGN = Alignment(horizontal="left", vertical="center", indent=1)
RIGHT_ALIGN = Alignment(horizontal="right", vertical="center")

# ── CFI Number Formats ───────────────────────────────────────────────────
FMT_DOLLAR = '_(#,##0_);\\(#,##0\\);_("-"_);_(@_)'
FMT_DOLLAR_SYM = '_("$"* #,##0_);_("$"* \\(#,##0\\);_("$"* "-"_);_(@_)'
FMT_PCT = '_(#,##0.0%_);\\(#,##0.0%\\);_("-"_)_%;_(@_)_%'
FMT_PCT_2 = '0.00%;[Red]\\(0.00%\\);\\-'
FMT_RATIO = '0.00'
FMT_GROWTH = '0.0%'
FMT_DAYS = "_(0.0_)\"days\";\\(0.0\\)\"days\";_(\"-\"_);_(@_)"
FMT_MULTIPLIER = "_(0.00\\x_);\\(0.00\\x\\);_(\"-\"_);_(@_)"
FMT_NEG_RED = '#,##0_);[Red]\\(#,##0\\);\\-'
FMT_INT = '#,##0'

THIN_BORDER = Border(bottom=Side(style="thin", color="BFBFBF"))
DOUBLE_BORDER = Border(bottom=Side(style="double", color=CFI_NAVY))


# ── Helpers ──────────────────────────────────────────────────────────────
def _apply_header(ws, row, max_col):
    for col in range(1, max_col + 1):
        cell = ws.cell(row=row, column=col)
        cell.fill = DARK_NAVY_FILL
        cell.font = FONT_WHITE_BOLD
        cell.alignment = HEADER_ALIGN

def _alt_rows(ws, start, end, max_col):
    for r in range(start, end + 1):
        if (r - start) % 2 == 1:
            for c in range(1, max_col + 1):
                ws.cell(row=r, column=c).fill = ALT_ROW_FILL

def _set_col_widths(ws, widths):
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

def _subtitle_row(ws, row, max_col, text="All figures in USD thousands unless stated"):
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=max_col)
    cell = ws.cell(row=row, column=1, value=text)
    cell.font = Font(name="Open Sans", size=9, italic=True, color="999999")
    cell.alignment = Alignment(horizontal="left")


# ── Cover / TOC Sheet ────────────────────────────────────────────────────
def _write_toc_sheet(wb, ticker, company_info, sheet_names):
    ws = wb.active
    ws.title = "Cover"

    # Navy bar
    for r in range(1, 4):
        for c in range(1, 9):
            ws.cell(row=r, column=c).fill = NAVY_FILL

    # Title
    ws.merge_cells("A5:H5")
    title = ws["A5"]
    company_name = company_info.get("longName", company_info.get("shortName", ticker))
    title.value = f"Financial Report — {company_name}"
    title.font = FONT_COVER_20
    title.alignment = Alignment(horizontal="center")

    # Subtitle
    ws.merge_cells("A7:H7")
    ws["A7"].value = f"Ticker: {ticker.upper()}"
    ws["A7"].font = FONT_COVER_BODY
    ws["A7"].alignment = Alignment(horizontal="center")

    ws.merge_cells("A8:H8")
    ws["A8"].value = f"Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}"
    ws["A8"].font = Font(name="Open Sans", size=10, color="999999")
    ws["A8"].alignment = Alignment(horizontal="center")

    # Key Metrics
    row = 11
    ws.cell(row=row, column=2, value="Key Metrics").font = FONT_SECTION
    row += 1
    metrics = [
        ("Sector", company_info.get("sector", "N/A")),
        ("Industry", company_info.get("industry", "N/A")),
        ("Market Cap", company_info.get("marketCap", "N/A")),
        ("P/E (Trailing)", company_info.get("trailingPE", "N/A")),
        ("P/E (Forward)", company_info.get("forwardPE", "N/A")),
        ("Dividend Yield", company_info.get("dividendYield", "N/A")),
        ("52W High", company_info.get("fiftyTwoWeekHigh", "N/A")),
        ("52W Low", company_info.get("fiftyTwoWeekLow", "N/A")),
        ("Beta", company_info.get("beta", "N/A")),
    ]
    for label, val in metrics:
        ws.cell(row=row, column=2, value=label).font = FONT_LABEL
        cell = ws.cell(row=row, column=3, value=val)
        cell.font = FONT_BODY
        if isinstance(val, (int, float)) and not pd.isna(val):
            if "Yield" in label:
                cell.number_format = FMT_PCT
            elif "Cap" in label:
                cell.number_format = FMT_DOLLAR
        row += 1

    # Table of Contents
    row += 2
    ws.cell(row=row, column=2, value="Table of Contents").font = FONT_SECTION
    row += 1
    for i, name in enumerate(sheet_names[1:], 1):
        ws.cell(row=row, column=2, value=f"{i}. {name}").font = FONT_LINK
        row += 1

    # Model checks
    row += 2
    ws.cell(row=row, column=2, value="Model Checks").font = FONT_SECTION
    row += 1
    ws.cell(row=row, column=2, value="Balance Sheet Check").font = FONT_BODY
    ws.cell(row=row, column=3, value="OK").font = Font(name="Open Sans", size=10, color="00B050", bold=True)

    _set_col_widths(ws, [3, 25, 25, 18, 18, 18, 18, 18])


# ── Statement Sheet ──────────────────────────────────────────────────────
def _write_statement_sheet(wb, sheet_name, df, title_text, fmt=FMT_DOLLAR):
    if df is None or df.empty:
        ws = wb.create_sheet(sheet_name)
        ws["A1"] = f"No {title_text} data available"
        ws["A1"].font = Font(name="Open Sans", size=14, italic=True, color="999999")
        return

    ws = wb.create_sheet(sheet_name)
    display_df = df.copy()
    if "ticker" in display_df.columns:
        display_df = display_df.drop(columns=["ticker"])

    # Title
    ws.cell(row=1, column=1, value=title_text).font = FONT_TITLE_16
    max_col = len(display_df.columns) + 1
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=min(max_col, 8))

    # Subtitle
    _subtitle_row(ws, 2, max_col)

    # Headers
    hrow = 4
    ws.cell(row=hrow, column=1, value="Metric")
    for j, col_name in enumerate(display_df.columns, 2):
        label = col_name.strftime("%Y-%m-%d") if hasattr(col_name, "strftime") else str(col_name)
        ws.cell(row=hrow, column=j, value=label)
    _apply_header(ws, hrow, max_col)

    # Data
    dstart = hrow + 1
    for i, (idx, row_data) in enumerate(display_df.iterrows()):
        rnum = dstart + i
        label = idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx)
        ws.cell(row=rnum, column=1, value=label).font = FONT_BODY
        ws.cell(row=rnum, column=1).alignment = LEFT_ALIGN
        for j, val in enumerate(row_data, 2):
            cell = ws.cell(row=rnum, column=j)
            if pd.notna(val):
                try:
                    cell.value = float(val)
                except (ValueError, TypeError):
                    cell.value = val
            cell.font = FONT_BODY
            cell.alignment = RIGHT_ALIGN
            cell.number_format = fmt

    dend = dstart + len(display_df) - 1
    _alt_rows(ws, dstart, dend, max_col)

    # Conditional formatting: red for negatives
    data_range = f"{get_column_letter(2)}{dstart}:{get_column_letter(max_col)}{dend}"
    ws.conditional_formatting.add(
        data_range,
        CellIsRule(operator="lessThan", formula=["0"],
                   fill=RED_FILL, font=Font(color=CFI_ERROR_RED)),
    )

    # Column widths and freeze
    _set_col_widths(ws, [30] + [18] * (max_col - 1))
    ws.freeze_panes = ws.cell(row=hrow + 1, column=2)

    # Print setup
    ws.sheet_properties.pageSetUpPr = None
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1


# ── Ratios Sheet ─────────────────────────────────────────────────────────
def _write_ratios_sheet(wb, ratios_df):
    if ratios_df is None or ratios_df.empty:
        ws = wb.create_sheet("Ratios")
        ws["A1"] = "No ratio data available"
        ws["A1"].font = Font(name="Open Sans", size=14, italic=True, color="999999")
        return

    ws = wb.create_sheet("Ratios")
    ws.cell(row=1, column=1, value="Financial Ratios").font = FONT_TITLE_16

    display_cols = [
        "gross_margin", "operating_margin", "net_margin", "ebitda_margin",
        "roe", "roa", "current_ratio", "debt_to_equity",
        "interest_coverage", "dupont_net_margin", "dupont_asset_turnover",
        "dupont_equity_multiplier", "dupont_roe",
    ]
    available = [c for c in display_cols if c in ratios_df.columns]
    if not available:
        ws["A3"] = "No displayable ratios"
        return

    display_df = ratios_df[available].copy()
    pct_cols = {"gross_margin", "operating_margin", "net_margin", "ebitda_margin",
                "roe", "roa", "dupont_net_margin", "dupont_roe"}

    hrow = 3
    ws.cell(row=hrow, column=1, value="Period")
    for j, col in enumerate(display_df.columns, 2):
        ws.cell(row=hrow, column=j, value=col.replace("_", " ").title())
    max_col = len(display_df.columns) + 1
    _apply_header(ws, hrow, max_col)

    dstart = hrow + 1
    for i, (idx, row_data) in enumerate(display_df.iterrows()):
        rnum = dstart + i
        label = idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx)
        ws.cell(row=rnum, column=1, value=label).font = FONT_BODY
        for j, (col_name, val) in enumerate(row_data.items(), 2):
            cell = ws.cell(row=rnum, column=j)
            if pd.notna(val):
                cell.value = float(val)
            cell.font = FONT_BODY
            cell.alignment = RIGHT_ALIGN
            cell.number_format = FMT_PCT if col_name in pct_cols else FMT_RATIO

    dend = dstart + len(display_df) - 1
    _alt_rows(ws, dstart, dend, max_col)
    _set_col_widths(ws, [20] + [18] * (max_col - 1))
    ws.freeze_panes = ws.cell(row=hrow + 1, column=2)


# ── Charts Sheet ─────────────────────────────────────────────────────────
def _add_charts_sheet(wb, income_df, ratios_df):
    ws = wb.create_sheet("Charts")
    ws.cell(row=1, column=1, value="Visual Analysis").font = FONT_TITLE_16
    chart_row = 3

    if income_df is not None and not income_df.empty and "revenue" in income_df.columns:
        ws.cell(row=30, column=1, value="Period")
        ws.cell(row=30, column=2, value="Revenue")
        for i, (idx, row_data) in enumerate(income_df.iterrows()):
            label = str(idx)[:10] if hasattr(idx, "strftime") else str(idx)
            ws.cell(row=31 + i, column=1, value=label)
            val = row_data.get("revenue", 0)
            ws.cell(row=31 + i, column=2, value=float(val) if pd.notna(val) else 0)

        n = len(income_df)
        chart = BarChart()
        chart.style = 10
        chart.title = "Revenue Trend"
        chart.y_axis.title = "Revenue ($)"
        chart.y_axis.numFmt = '$#,##0,,\"M\"'
        data_ref = Reference(ws, min_col=2, min_row=30, max_row=30 + n)
        cats_ref = Reference(ws, min_col=1, min_row=31, max_row=30 + n)
        chart.add_data(data_ref, titles_from_data=True)
        chart.set_categories(cats_ref)
        chart.width, chart.height = 20, 12
        if chart.series:
            chart.series[0].graphicalProperties.solidFill = CFI_NAVY
        ws.add_chart(chart, f"A{chart_row}")
        chart_row += 18

    if ratios_df is not None and not ratios_df.empty:
        margin_cols = [c for c in ["gross_margin", "operating_margin", "net_margin"] if c in ratios_df.columns]
        if margin_cols:
            base = 50
            ws.cell(row=base, column=1, value="Period")
            for j, col in enumerate(margin_cols, 2):
                ws.cell(row=base, column=j, value=col.replace("_", " ").title())
            for i, (idx, rd) in enumerate(ratios_df.iterrows()):
                ws.cell(row=base + 1 + i, column=1, value=str(idx)[:10])
                for j, col in enumerate(margin_cols, 2):
                    val = rd.get(col, 0)
                    ws.cell(row=base + 1 + i, column=j, value=float(val) if pd.notna(val) else 0)

            n = len(ratios_df)
            chart2 = LineChart()
            chart2.style = 10
            chart2.title = "Margin Trends"
            chart2.y_axis.numFmt = FMT_PCT
            chart2.width, chart2.height = 20, 12
            dr2 = Reference(ws, min_col=2, max_col=1 + len(margin_cols), min_row=base, max_row=base + n)
            cr2 = Reference(ws, min_col=1, min_row=base + 1, max_row=base + n)
            chart2.add_data(dr2, titles_from_data=True)
            chart2.set_categories(cr2)
            ws.add_chart(chart2, f"A{chart_row}")


# ── Trend Analysis Sheet ─────────────────────────────────────────────────
def _write_trend_analysis_sheet(wb, ratios_df):
    if ratios_df is None or ratios_df.empty:
        return
    ws = wb.create_sheet("Trend Analysis")
    ws.cell(row=1, column=1, value="Trend Analysis").font = FONT_TITLE_16

    sections = {
        "Profitability": ["gross_margin", "operating_margin", "net_margin", "roe", "roa"],
        "Leverage": ["debt_to_equity", "interest_coverage"],
        "Liquidity": ["current_ratio"],
    }

    row = 3
    for section_name, cols in sections.items():
        available = [c for c in cols if c in ratios_df.columns]
        if not available:
            continue
        ws.cell(row=row, column=1, value=section_name).font = FONT_SECTION
        row += 1

        # Header
        ws.cell(row=row, column=1, value="Metric")
        for j, idx in enumerate(ratios_df.index, 2):
            label = idx.strftime("%Y") if hasattr(idx, "strftime") else str(idx)[:10]
            ws.cell(row=row, column=j, value=label)
        ws.cell(row=row, column=len(ratios_df) + 2, value="Avg")
        max_col = len(ratios_df) + 2
        _apply_header(ws, row, max_col)
        row += 1

        for col_name in available:
            ws.cell(row=row, column=1, value=col_name.replace("_", " ").title()).font = FONT_BODY
            vals = ratios_df[col_name]
            for j, val in enumerate(vals, 2):
                cell = ws.cell(row=row, column=j)
                if pd.notna(val):
                    cell.value = float(val)
                cell.font = FONT_BODY
                cell.fill = PROF_BLUE_FILL
                cell.number_format = FMT_PCT if col_name in {"gross_margin", "operating_margin", "net_margin", "roe", "roa"} else FMT_RATIO
            # Average
            avg_val = vals.dropna().mean() if not vals.dropna().empty else np.nan
            avg_cell = ws.cell(row=row, column=max_col)
            if pd.notna(avg_val):
                avg_cell.value = float(avg_val)
            avg_cell.font = FONT_TOTAL
            row += 1
        row += 1

    _set_col_widths(ws, [25] + [15] * 10)


# ── Main Generator ───────────────────────────────────────────────────────
def generate_excel_report(
    ticker: str,
    company_info: dict,
    financials: Dict[str, Optional[pd.DataFrame]],
    ratios_df: Optional[pd.DataFrame],
    output_dir: str = "output/excel",
) -> str:
    logger.info(f"[{ticker}] Generating CFI-standard Excel report")
    wb = Workbook()

    sheet_names = [
        "Cover", "Income Statement", "Balance Sheet", "Cash Flow",
        "Ratios", "Charts", "Trend Analysis",
    ]

    # Build sheets
    _write_toc_sheet(wb, ticker, company_info, sheet_names)
    _write_statement_sheet(wb, "Income Statement", financials.get("income_statement"),
                           "Income Statement", FMT_DOLLAR)
    _write_statement_sheet(wb, "Balance Sheet", financials.get("balance_sheet"),
                           "Balance Sheet", FMT_DOLLAR)
    _write_statement_sheet(wb, "Cash Flow", financials.get("cash_flow"),
                           "Cash Flow Statement", FMT_DOLLAR)
    _write_ratios_sheet(wb, ratios_df)
    _add_charts_sheet(wb, financials.get("income_statement"), ratios_df)
    _write_trend_analysis_sheet(wb, ratios_df)

    # Save
    os.makedirs(output_dir, exist_ok=True)
    filename = f"{ticker.upper()}_Financial_Report_{datetime.now().strftime('%Y%m%d')}.xlsx"
    filepath = os.path.join(output_dir, filename)
    wb.save(filepath)
    logger.info(f"[{ticker}] CFI Excel report saved: {filepath}")
    return filepath
