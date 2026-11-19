# Legal-AI startup: 12-month margin summary

Margins for Nov 2025 to Oct 2026, built from one ledger of customer invoices (money in)
and AI provider bills (money out). Basis is invoice date (accrual); the ledger has no payment dates.

## Run

```bash
pip install -r requirements.txt
python -m src.margins      # writes the two files in outputs/
python -m pytest           # 14 tests
```

Outputs:
- `outputs/monthly_margin_summary.csv`: one row per month plus a TOTAL row.
- `outputs/margin_summary.md`: headline margin, margin after R&D, monthly table,
  reconciliation to the 38% in the kickoff notes, data notes and flags.

## Cost rule

| Workload | Treatment |
|---|---|
| `contract_review`, `legal_research`, `document_drafting` | **Cost of revenue.** Production inference that serves customers, booked to `cost_of_revenue`. |
| `model_evaluation_and_finetuning` | **Not COGS.** Booked to `research_and_development`. Eval batches and fine-tuning runs pay for benchmarking and training models, not for serving a customer. |

- This includes the 31 bills whose memo says "redline accuracy benchmark" ($51,063.58).
  Customers pay for redlines, but these bills pay for testing the accuracy of our redline
  output, not for producing a customer's redline.
- Classification uses `workload` and `booked_account` only. Memo keywords are never used to
  classify (the word "redline" also appears in revenue memos). Memo words are a cross-check:
  the run **fails** if `workload` and `booked_account` disagree, if a COGS-booked bill has an
  eval or fine-tuning memo, if a workload is unknown, or if a month is missing.
- `is_recurring` on model bills is ignored (inconsistent with memos). It is used only to split
  revenue into recurring and one-time.
- `customer_segment` is not used: all 18 client accounts appear under more than one segment.

## Headline setting

`config.py`: `HEADLINE_MARGIN = "gross"` (default) or `"after_rd"`.

- `gross`: revenue less serving-workload bills, 26.1% over 12 months.
- `after_rd`: also subtracts the $128,890.39 of eval and fine-tuning spend, 16.6%.

Both are always reported; the setting only decides which one leads. TOTAL margins are
computed from summed dollars, never by averaging monthly percentages.

## Known open items (also in the report)

1. Aug 2026 (-34.5%) and Sep 2026 (-24.8%) gross margins are negative. Unconfirmed whether this
   is real churn or missing invoices. August has the fewest invoices (19) and billed accounts (12)
   of any month; September does not (28 invoices, 15 accounts).
2. The kickoff notes quote 38%. The ledger does not reproduce it on any basis tested, and the
   source of that figure is unconfirmed. The report states the gap rather than explaining it.
3. Segment labels need an account-to-segment mapping before any segment-level margin is possible.

## Layout

```
config.py                 settings: headline, period, cost-rule workloads
src/margins.py            load, validate, classify, summarise, write
tests/test_margins.py     reconciliation, month coverage, CSV/markdown agreement, validation
data/ledger.csv           input ledger (1,200 rows)
outputs/                  generated report files
docs/PROMPT.md            the prompt this repo was built from
```
