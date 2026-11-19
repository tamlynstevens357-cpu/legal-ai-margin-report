# Prompt note

Repo built from this prompt (cost rule in section 2, monthly deliverables in section 3).

**Task:** build the 12-month margin summary report from `data/ledger.csv`.

**Input:** revenue_invoice = money in; model_bill = money out; invoice-date (accrual) basis.

**Cost rule:** COGS = model bills for `contract_review`, `legal_research`, `document_drafting`
(production inference, booked to `cost_of_revenue`). Leave out `model_evaluation_and_finetuning`
(booked to `research_and_development`), including bills whose memo says "redline accuracy
benchmark". Classify by `booked_account` and `workload` only, never memo keywords; fail loudly on
disagreement or an eval/fine-tuning memo in COGS. Ignore `is_recurring` on model bills. Do not use
`customer_segment` for breakdowns. Headline = gross margin excluding R&D, also report margin after R&D,
switchable via `HEADLINE_MARGIN` in `config.py`.

**Per month:** revenue_total, revenue_recurring, revenue_one_time, cogs, gross_profit,
gross_margin_pct, rd_model_spend, margin_after_rd_pct, margin_recurring_only_pct, plus a TOTAL row
computed from summed dollars. Save to `outputs/monthly_margin_summary.csv` and
`outputs/margin_summary.md`. Logic in `src/margins.py`, settings in `config.py`, tests in `tests/`.

**Flag, do not fix:** Aug/Sep 2026 negative margins (unconfirmed churn vs missing invoices); segment
label inconsistency.

## Added after the first build
- Kickoff notes quote 38%. Report adds a section stating the ledger does not reproduce it and
  that its source is unconfirmed; the cost rule was not changed to close the gap.
- Correction: the prompt said Aug and Sep both have the fewest invoices and billed accounts. The data
  shows that is true of August only; the report states the computed ranks.
