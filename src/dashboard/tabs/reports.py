"""Reports tab — Generate and download Excel and PDF reports."""

import tempfile
from datetime import datetime

import streamlit as st

from src.dashboard.theme import plotly_theme, section_header, styled_dataframe
from src.dashboard.components import js_download_button
from src.data_processing.calculator import compute_all_ratios
from src.report_generation.excel_report import generate_excel_report
from src.report_generation.pdf_report import generate_pdf_report


def render(ticker, info, prices, fundamentals, ratios, peers, period):
    """Render the Reports tab with Excel and PDF generation and download."""
    st.subheader("Generate & Download Reports")
    st.markdown(
        f"Generate professional-grade financial reports for **{ticker}** "
        "using the data loaded in this session."
    )
    st.markdown("---")

    # Compute ratios for reports
    inc_r = fundamentals.get("income_statement") if fundamentals else None
    bal_r = fundamentals.get("balance_sheet") if fundamentals else None
    cf_r = fundamentals.get("cash_flow") if fundamentals else None
    report_ratios = compute_all_ratios(inc_r, bal_r, cf_r, ticker)

    # Clear cached reports when ticker changes
    if st.session_state.get("_report_ticker") != ticker:
        st.session_state["_report_ticker"] = ticker
        st.session_state.pop("excel_bytes", None)
        st.session_state.pop("excel_filename", None)
        st.session_state.pop("pdf_bytes", None)
        st.session_state.pop("pdf_filename", None)

    col_excel, col_pdf = st.columns(2)

    # -- Excel Report --------------------------------------------------------
    with col_excel:
        st.markdown("### Excel Report")
        st.markdown(
            "IB-style workbook with navy headers, conditional formatting, "
            "embedded charts, and multi-sheet layout (Cover, Income Statement, "
            "Balance Sheet, Cash Flow, Ratios, Charts)."
        )
        if st.button(
            "Generate Excel Report",
            key="gen_excel",
            use_container_width=True,
        ):
            with st.spinner("Building Excel workbook..."):
                try:
                    with tempfile.TemporaryDirectory() as tmp_dir:
                        excel_path = generate_excel_report(
                            ticker, info, fundamentals, report_ratios, tmp_dir
                        )
                        with open(excel_path, "rb") as f:
                            st.session_state["excel_bytes"] = f.read()
                    st.session_state["excel_filename"] = (
                        f"{ticker}_Financial_Report_"
                        f"{datetime.now().strftime('%Y%m%d')}.xlsx"
                    )
                except Exception as e:
                    st.error(f"Excel generation failed: {e}")

        if "excel_bytes" in st.session_state:
            st.success("Excel report ready!")
            js_download_button(
                st.session_state["excel_bytes"],
                st.session_state["excel_filename"],
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "Download Excel (.xlsx)",
            )

    # -- PDF Report ----------------------------------------------------------
    with col_pdf:
        st.markdown("### PDF Report")
        st.markdown(
            "Professional PDF with cover page, company overview, "
            "3-statement financial tables (Income Statement, Balance Sheet, "
            "Cash Flow), and key financial ratios summary."
        )
        if st.button(
            "Generate PDF Report",
            key="gen_pdf",
            use_container_width=True,
        ):
            with st.spinner("Building PDF report..."):
                try:
                    with tempfile.TemporaryDirectory() as tmp_dir:
                        pdf_path = generate_pdf_report(
                            ticker, info, fundamentals, report_ratios, tmp_dir
                        )
                        with open(pdf_path, "rb") as f:
                            st.session_state["pdf_bytes"] = f.read()
                    st.session_state["pdf_filename"] = (
                        f"{ticker}_Financial_Report_"
                        f"{datetime.now().strftime('%Y%m%d')}.pdf"
                    )
                except Exception as e:
                    st.error(f"PDF generation failed: {e}")

        if "pdf_bytes" in st.session_state:
            st.success("PDF report ready!")
            js_download_button(
                st.session_state["pdf_bytes"],
                st.session_state["pdf_filename"],
                "application/pdf",
                "Download PDF (.pdf)",
            )

    st.markdown("---")
    st.caption(
        "Reports generated on-demand using live session data. "
        "No files are stored on the server."
    )
