"""
Pipeline Orchestrator — main.py
Fetches, cleans, computes ratios, generates Excel + PDF reports.
Usage: python main.py [--tickers AAPL MSFT] [--output-dir ./output]
"""
import argparse
import os
import sys

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.utils.logger import setup_logger
from src.utils.helpers import load_config, ensure_directories
from src.data_ingestion.api_client import (
    fetch_price_data, fetch_company_info,
    fetch_financials_edgar, fetch_financials_yfinance,
)
from src.data_ingestion.validators import validate_price_data, validate_financial_data
from src.data_processing.cleaner import clean_financial_data, save_to_parquet
from src.data_processing.calculator import compute_all_ratios
from src.report_generation.excel_report import generate_excel_report
from src.report_generation.pdf_report import generate_pdf_report

logger = setup_logger("pipeline")


def run_pipeline(tickers: list, output_dir: str = None):
    """Run the full data → report pipeline for a list of tickers."""
    config = load_config()
    ensure_directories(config)

    if output_dir is None:
        output_dir = "output"
    excel_dir = os.path.join(output_dir, "excel")
    pdf_dir = os.path.join(output_dir, "pdf")
    processed_dir = config.get("output", {}).get("processed_data_dir", "data/processed")

    logger.info(f"{'='*60}")
    logger.info(f"Financial Reporting Pipeline")
    logger.info(f"Tickers: {', '.join(tickers)}")
    logger.info(f"{'='*60}")

    results = []

    for ticker in tickers:
        logger.info(f"\n{'─'*40}")
        logger.info(f"Processing: {ticker}")
        logger.info(f"{'─'*40}")

        # 1. Fetch company info
        try:
            info = fetch_company_info(ticker)
        except Exception as e:
            logger.error(f"[{ticker}] Failed to fetch company info: {e}")
            info = {}

        # 2. Fetch price data
        try:
            prices = fetch_price_data(ticker)
            price_validation = validate_price_data(prices, ticker)
            if prices is not None and not prices.empty:
                save_to_parquet(prices, f"{ticker}_prices", processed_dir)
        except Exception as e:
            logger.error(f"[{ticker}] Failed to fetch prices: {e}")
            prices = None

        # 3. Fetch financial statements (EDGAR first, yfinance fallback)
        financials = None
        try:
            financials = fetch_financials_edgar(ticker)
            if all(v is None for v in financials.values()):
                logger.info(f"[{ticker}] EDGAR returned no data, trying yfinance fallback")
                financials = fetch_financials_yfinance(ticker)
        except Exception as e:
            logger.warning(f"[{ticker}] EDGAR failed ({e}), trying yfinance fallback")
            try:
                financials = fetch_financials_yfinance(ticker)
            except Exception as e2:
                logger.error(f"[{ticker}] yfinance fallback also failed: {e2}")
                financials = {"income_statement": None, "balance_sheet": None, "cash_flow": None}

        # 4. Validate
        fin_validation = validate_financial_data(financials, ticker)

        # 5. Clean
        cleaned = clean_financial_data(financials, ticker, config)

        # Save cleaned data
        for stmt_name, df in cleaned.items():
            if df is not None and not df.empty:
                save_to_parquet(df, f"{ticker}_{stmt_name}", processed_dir)

        # 6. Compute ratios
        ratios = compute_all_ratios(
            cleaned.get("income_statement"),
            cleaned.get("balance_sheet"),
            cleaned.get("cash_flow"),
            ticker,
        )
        if not ratios.empty:
            save_to_parquet(ratios, f"{ticker}_ratios", processed_dir)

        # 7. Generate Excel report
        try:
            excel_path = generate_excel_report(ticker, info, cleaned, ratios, excel_dir)
            logger.info(f"[{ticker}] ✓ Excel: {excel_path}")
        except Exception as e:
            logger.error(f"[{ticker}] Excel generation failed: {e}")
            excel_path = None

        # 8. Generate PDF report
        try:
            pdf_path = generate_pdf_report(ticker, info, cleaned, ratios, pdf_dir)
            logger.info(f"[{ticker}] ✓ PDF: {pdf_path}")
        except Exception as e:
            logger.error(f"[{ticker}] PDF generation failed: {e}")
            pdf_path = None

        results.append({
            "ticker": ticker,
            "excel": excel_path,
            "pdf": pdf_path,
            "ratios_computed": not ratios.empty,
        })

    # Summary
    logger.info(f"\n{'='*60}")
    logger.info("Pipeline Complete — Summary")
    logger.info(f"{'='*60}")
    for r in results:
        status = "✓" if r["excel"] or r["pdf"] else "✗"
        logger.info(f"  {status} {r['ticker']}: Excel={'Yes' if r['excel'] else 'No'}, "
                     f"PDF={'Yes' if r['pdf'] else 'No'}, Ratios={'Yes' if r['ratios_computed'] else 'No'}")

    return results


def main():
    parser = argparse.ArgumentParser(description="Financial Reporting Pipeline")
    parser.add_argument("--tickers", nargs="+", default=None, help="Ticker symbols")
    parser.add_argument("--output-dir", default=None, help="Output directory")
    args = parser.parse_args()

    config = load_config()
    tickers = args.tickers or config.get("tickers", ["AAPL"])
    run_pipeline(tickers, args.output_dir)


if __name__ == "__main__":
    main()
