# Curator Finance — Intelligent Financial Dashboard

Curator Finance is a dual-purpose financial analysis platform designed for professional-grade equity research and automated reporting. It combines a robust **Python-based Automation Pipeline** with a high-fidelity **Streamlit Interactive Dashboard** featuring a premium "Curator" dark-mode aesthetic.

![Dashboard Preview](assets/demo.webp)

## 🚀 Key Features

### 1. Automated Financial Reporting (`main.py`)
- **Multi-Source Data Ingestion**: Seamlessly fetches market data using YFinance and EDGAR.
- **Precision Cleaning**: Validates and standardizes inconsistent financial statement schemas into a unified Parquet-based data lake.
- **Ratio Analysis Engine**: Automatically computes over 25+ key financial metrics (Profitability, Liquidity, Solvency, Efficiency).
- **Batch Report Generation**: Generates professionally formatted **Excel** and **PDF** financial summaries in seconds.

### 2. Interactive "Curator" Dashboard (`app.py`)
- **Real-time Visualization**: High-visibility line and bar charts powered by Plotly.
- **Modern UI/UX**: Custom-injected CSS providing a glassmorphic dark-navy theme.
- **Deep Fundamentals**: Integrated multi-year Income Statements, Balance Sheets, and Cash Flow views with "Millions/Billions" auto-formatting.
- **Peer Comparison**: Dynamic peer analysis and technical trend monitoring.
- **DCF & Variance**: Built-in Discounted Cash Flow valuation engine and budget variance trackers.

## 🛠️ Tech Stack
- **Dashboard**: Streamlit, Plotly, Custom Vanilla CSS.
- **Data Engine**: Pandas, NumPy, Parquet (Fast I/O).
- **APIs**: YFinance, SEC-EDGAR.
- **Reporting**: ReportLab (PDF), OpenPyXL (Excel).

## 📥 Installation & Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-username/curator-finance.git
   cd curator-finance
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Environment Setup**:
   - Create a `.env` file based on `.env.example` if API keys are required for advanced data providers.

## 🏃 Usage

### Start the Dashboard
```bash
streamlit run src/dashboard/app.py
```

### Run the Automation Pipeline
```bash
python main.py --tickers AAPL MSFT GOOGL --output-dir ./output
```

## 📂 Project Structure
- `src/`: Core Python logic (Processing, Ingestion, Reports).
- `src/dashboard/`: Streamlit app modules, CSS assets, and tab definitions.
- `data/`: Parquet data lake for raw and processed financials.
- `output/`: Generated Excel and PDF reports.
- `assets/`: UI assets and styling documents.

---
*Created for High-Performance Financial Analysis.*
