"""Settings for the margin summary report. Edit here, not in src/margins.py."""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
LEDGER_PATH = ROOT / "data" / "ledger.csv"
OUTPUT_DIR = ROOT / "outputs"
SUMMARY_CSV = OUTPUT_DIR / "monthly_margin_summary.csv"
SUMMARY_MD = OUTPUT_DIR / "margin_summary.md"

# Which margin is the headline in the report: "gross" or "after_rd".
HEADLINE_MARGIN = "gross"

# Reporting window (12 months, invoice-date / accrual basis).
PERIOD_START = "2025-11"
PERIOD_END = "2026-10"
MONTHS = [str(p) for p in pd.period_range(PERIOD_START, PERIOD_END, freq="M")]

# Ledger vocabulary.
REVENUE_TYPE = "revenue_invoice"
MODEL_BILL_TYPE = "model_bill"
REVENUE_ACCOUNT = "revenue"
COGS_ACCOUNT = "cost_of_revenue"
RD_ACCOUNT = "research_and_development"

# Cost rule: only these workloads are the cost of serving customers.
COGS_WORKLOADS = ("contract_review", "legal_research", "document_drafting")
# Internal work, kept out of COGS and reported separately as R&D model spend.
RD_WORKLOAD = "model_evaluation_and_finetuning"

# Cross-check only (never used to classify): memo words that mean eval/training work.
EVAL_MEMO_PATTERN = r"eval batch|benchmark|fine-tun"

# Figure quoted in the kickoff notes. Its source and definition are NOT in the ledger
# and are unconfirmed; the report states the gap rather than explaining it.
KICKOFF_NOTES_MARGIN_PCT = 38.0
