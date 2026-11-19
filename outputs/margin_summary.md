# Margin summary: Nov 2025 to Oct 2026

Basis: invoice date (accrual). Money in = customer invoices; money out = AI provider bills.

## Headline

Headline margin: **Gross margin (excluding R&D): 26.1%** - revenue $1,363,640.65, cost of revenue $1,008,366.57, gross profit $355,274.08.

Also reported: **Margin after R&D model spend: 16.6%** - after also subtracting $128,890.39 of model evaluation and fine-tuning spend.

Recurring-revenue-only margin (one-time fees removed): 23.5%.

## Monthly table

| Month | Revenue | Recurring | One-time | COGS | Gross profit | Gross margin | R&D model spend | Margin after R&D | Recurring-only margin |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2025-11 | $131,564.35 | $121,136.11 | $10,428.24 | $78,113.31 | $53,451.04 | 40.6% | $5,187.72 | 36.7% | 35.5% |
| 2025-12 | $127,965.43 | $117,764.71 | $10,200.72 | $68,941.47 | $59,023.96 | 46.1% | $19,686.62 | 30.7% | 41.5% |
| 2026-01 | $126,388.70 | $117,076.52 | $9,312.18 | $103,549.02 | $22,839.68 | 18.1% | $12,315.88 | 8.3% | 11.6% |
| 2026-02 | $84,153.90 | $82,661.57 | $1,492.33 | $69,243.74 | $14,910.16 | 17.7% | $8,993.38 | 7.0% | 16.2% |
| 2026-03 | $150,470.22 | $150,470.22 | $0.00 | $78,841.88 | $71,628.34 | 47.6% | $10,134.75 | 40.9% | 47.6% |
| 2026-04 | $142,465.73 | $140,828.13 | $1,637.60 | $95,503.64 | $46,962.09 | 33.0% | $13,889.05 | 23.2% | 32.2% |
| 2026-05 | $105,960.94 | $103,206.37 | $2,754.57 | $85,769.44 | $20,191.50 | 19.1% | $11,322.58 | 8.4% | 16.9% |
| 2026-06 | $95,175.50 | $95,175.50 | $0.00 | $54,457.10 | $40,718.40 | 42.8% | $1,907.31 | 40.8% | 42.8% |
| 2026-07 | $108,827.26 | $101,446.43 | $7,380.83 | $96,110.46 | $12,716.80 | 11.7% | $4,702.35 | 7.4% | 5.3% |
| 2026-08 | $67,217.84 | $67,217.84 | $0.00 | $90,415.25 | -$23,197.41 | -34.5% | $18,950.03 | -62.7% | -34.5% |
| 2026-09 | $83,010.17 | $80,286.07 | $2,724.10 | $103,609.78 | -$20,599.61 | -24.8% | $12,846.19 | -40.3% | -29.1% |
| 2026-10 | $140,440.61 | $140,440.61 | $0.00 | $83,811.48 | $56,629.13 | 40.3% | $8,954.53 | 33.9% | 40.3% |
| **TOTAL** | $1,363,640.65 | $1,317,710.08 | $45,930.57 | $1,008,366.57 | $355,274.08 | 26.1% | $128,890.39 | 16.6% | 23.5% |

TOTAL margins are computed from summed dollars, not by averaging the monthly percentages.

## Why this report does not show 38%

The kickoff notes quote a margin of 38%. This ledger does not reproduce it, and the notes' source and definition are not in the ledger, so the reason for the gap is **unconfirmed**. What the ledger shows:

| Basis | Margin |
|---|---:|
| Gross margin, summed dollars (headline) | 26.1% |
| Margin after R&D model spend | 16.6% |
| Recurring revenue only | 23.5% |
| Simple average of the 12 monthly gross margins | 21.5% |
| Gross margin excluding the 2 negative-margin months | 32.9% |

None of these equals 38%. For 38% to hold on this revenue ($1,363,640.65), cost of revenue would have to be about $845,457.20, which is $162,909.37 less than the $1,008,366.57 of serving-workload bills in the ledger. The cost rule below has not been adjusted to close this gap. Ask the author of the kickoff notes how 38% was defined (period, revenue basis, which costs) before the partners compare the two numbers.

## Data notes

**Cost rule**

- Cost of revenue counts only model bills for `contract_review`, `legal_research`, `document_drafting`. These are production inference, booked to `cost_of_revenue`.
- Bills with workload `model_evaluation_and_finetuning` are left out of COGS and shown as R&D model spend. They pay for benchmarking and training models (eval batches, classifier fine-tuning, drafting-style model fine-tuning), not for serving a customer.
- This includes bills whose memo says "redline accuracy benchmark". Customers pay for redlines, but these bills pay for testing the accuracy of our redline output, not for producing a customer's redline.
- Classification uses `booked_account` and `workload` only, not memo keywords ("redline" also appears in revenue memos). Memo words are a cross-check; the run fails if the two disagree.
- The `is_recurring` flag on model bills is ignored because it is inconsistent with the memos. It is used only to split revenue into recurring and one-time.
- `customer_segment` is not used for any breakdown (see flag 2).

## Flags (reported, not corrected)

**1. Negative gross margin months: unconfirmed whether churn or missing invoices**

- 2026-08: gross margin -34.5%; revenue $67,217.84 against COGS $90,415.25; 19 invoices from 12 billed accounts (invoice count ranks 1 of 12 and billed accounts ranks 1 of 12, where 1 = fewest).
- 2026-09: gross margin -24.8%; revenue $83,010.17 against COGS $103,609.78; 28 invoices from 15 billed accounts (invoice count ranks 5 of 12 and billed accounts ranks 7 of 12, where 1 = fewest).

Revenue fell in these months while COGS stayed roughly flat. The ledger cannot show whether that is real customer churn or invoices missing from the extract. Confirm with the ledger owner before using these months in a narrative. No adjustment has been made.

| Month | Invoices | Billed accounts |
|---|---:|---:|
| 2025-11 | 31 | 14 |
| 2025-12 | 32 | 13 |
| 2026-01 | 30 | 17 |
| 2026-02 | 23 | 13 |
| 2026-03 | 31 | 15 |
| 2026-04 | 38 | 17 |
| 2026-05 | 30 | 14 |
| 2026-06 | 24 | 16 |
| 2026-07 | 26 | 13 |
| 2026-08 | 19 | 12 |
| 2026-09 | 28 | 15 |
| 2026-10 | 32 | 16 |

**2. Customer segment labels are inconsistent**

- 18 of 18 client accounts appear under more than one `customer_segment` (up to 3 different segments per account). The label is not a stable property of the account, so no margin is broken out by segment or customer. A proper account-to-segment mapping is needed first.
