"""Build the 12-month margin summary from the legal-AI startup ledger.

Cost rule (see config.py and README.md):
  * COGS = model bills for contract_review, legal_research, document_drafting.
  * model_evaluation_and_finetuning bills are R&D, not COGS.
  * Classification uses `workload` and `booked_account` only. Memo text is a
    cross-check and is never used to decide where a bill goes.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

import config

REQUIRED_COLUMNS = [
    "entry_id", "entry_date", "month", "entry_type", "counterparty",
    "customer_segment", "model_provider", "workload", "booked_account",
    "tokens_processed", "amount_usd", "is_recurring", "memo",
]
OUTPUT_COLUMNS = [
    "revenue_total", "revenue_recurring", "revenue_one_time", "cogs",
    "gross_profit", "gross_margin_pct", "rd_model_spend",
    "margin_after_rd_pct", "margin_recurring_only_pct",
]
DOLLAR_COLUMNS = ["revenue_total", "revenue_recurring", "revenue_one_time", "cogs",
                  "gross_profit", "rd_model_spend"]
PCT_COLUMNS = ["gross_margin_pct", "margin_after_rd_pct", "margin_recurring_only_pct"]


class LedgerValidationError(ValueError):
    """Raised when the ledger breaks a rule the report depends on."""


# --------------------------------------------------------------------------
# Load and validate
# --------------------------------------------------------------------------
def load_ledger(path: Path | str | None = None) -> pd.DataFrame:
    df = pd.read_csv(path or config.LEDGER_PATH)
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise LedgerValidationError(f"Ledger is missing columns: {missing}")
    df["is_recurring"] = df["is_recurring"].map(lambda v: str(v).strip().lower() == "true")
    return df


def validate_ledger(df: pd.DataFrame) -> None:
    """Fail loudly (collecting every problem) if the ledger breaks the cost rule."""
    errors: list[str] = []

    if df["entry_id"].duplicated().any():
        errors.append(f"{int(df['entry_id'].duplicated().sum())} duplicate entry_id values")
    amounts = pd.to_numeric(df["amount_usd"], errors="coerce")
    if amounts.isna().any() or (amounts <= 0).any():
        errors.append("amount_usd has missing, zero or negative values")

    unknown_types = set(df["entry_type"]) - {config.REVENUE_TYPE, config.MODEL_BILL_TYPE}
    if unknown_types:
        errors.append(f"Unknown entry_type values: {sorted(unknown_types)}")

    ledger_months = set(df["month"])
    if ledger_months != set(config.MONTHS):
        errors.append(
            "Ledger months do not match the reporting window: "
            f"extra={sorted(ledger_months - set(config.MONTHS))}, "
            f"missing={sorted(set(config.MONTHS) - ledger_months)}"
        )

    rev = df[df["entry_type"] == config.REVENUE_TYPE]
    bad_rev = rev[rev["booked_account"] != config.REVENUE_ACCOUNT]
    if len(bad_rev):
        errors.append(f"{len(bad_rev)} revenue invoices not booked to '{config.REVENUE_ACCOUNT}': "
                      f"{bad_rev['entry_id'].tolist()[:10]}")

    bills = df[df["entry_type"] == config.MODEL_BILL_TYPE]
    known = set(config.COGS_WORKLOADS) | {config.RD_WORKLOAD}
    unknown_wl = bills[~bills["workload"].isin(known)]
    if len(unknown_wl):
        errors.append(f"{len(unknown_wl)} model bills with an unknown or blank workload: "
                      f"{unknown_wl['entry_id'].tolist()[:10]}")

    # booked_account and workload must agree.
    serving = bills[bills["workload"].isin(config.COGS_WORKLOADS)]
    bad_serving = serving[serving["booked_account"] != config.COGS_ACCOUNT]
    if len(bad_serving):
        errors.append(f"{len(bad_serving)} serving-workload bills not booked to "
                      f"'{config.COGS_ACCOUNT}': {bad_serving['entry_id'].tolist()[:10]}")
    internal = bills[bills["workload"] == config.RD_WORKLOAD]
    bad_internal = internal[internal["booked_account"] != config.RD_ACCOUNT]
    if len(bad_internal):
        errors.append(f"{len(bad_internal)} eval/fine-tuning bills not booked to "
                      f"'{config.RD_ACCOUNT}': {bad_internal['entry_id'].tolist()[:10]}")

    # Memo cross-check: a COGS-booked bill must not read like eval/training work.
    cogs_booked = bills[bills["booked_account"] == config.COGS_ACCOUNT]
    suspicious = cogs_booked[cogs_booked["memo"].str.contains(
        config.EVAL_MEMO_PATTERN, flags=re.IGNORECASE, regex=True)]
    if len(suspicious):
        errors.append(f"{len(suspicious)} COGS-booked bills have an eval/fine-tuning memo: "
                      f"{suspicious['entry_id'].tolist()[:10]}")

    if errors:
        raise LedgerValidationError("Ledger validation failed:\n  - " + "\n  - ".join(errors))


# --------------------------------------------------------------------------
# Classify and summarise
# --------------------------------------------------------------------------
def classify(df: pd.DataFrame) -> pd.DataFrame:
    """Add a `bucket` column (revenue / cogs / rd) from entry_type and workload only."""
    out = df.copy()
    bucket = pd.Series(pd.NA, index=out.index, dtype="object")
    bills = out["entry_type"] == config.MODEL_BILL_TYPE
    bucket[out["entry_type"] == config.REVENUE_TYPE] = "revenue"
    bucket[bills & out["workload"].isin(config.COGS_WORKLOADS)] = "cogs"
    bucket[bills & (out["workload"] == config.RD_WORKLOAD)] = "rd"
    out["bucket"] = bucket
    return out


def _pct(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    return (numerator / denominator.where(denominator != 0)) * 100


def monthly_summary(df: pd.DataFrame) -> pd.DataFrame:
    """One row per month plus TOTAL. Sums are done in integer cents; the TOTAL
    margins are computed from summed dollars, never by averaging monthly %."""
    d = classify(df)
    if d["bucket"].isna().any():
        raise LedgerValidationError("Some rows could not be classified; run validate_ledger first.")
    d["cents"] = (pd.to_numeric(d["amount_usd"]) * 100).round().astype("int64")

    def by_month(mask: pd.Series) -> pd.Series:
        return (d[mask].groupby("month")["cents"].sum()
                .reindex(config.MONTHS, fill_value=0).astype("int64"))

    is_rev = d["bucket"] == "revenue"
    cents = pd.DataFrame({
        "revenue_total": by_month(is_rev),
        "revenue_recurring": by_month(is_rev & d["is_recurring"]),
        "revenue_one_time": by_month(is_rev & ~d["is_recurring"]),
        "cogs": by_month(d["bucket"] == "cogs"),
        "rd_model_spend": by_month(d["bucket"] == "rd"),
    })
    cents.index.name = "month"
    cents.loc["TOTAL"] = cents.sum()

    gross_profit = cents["revenue_total"] - cents["cogs"]
    out = pd.DataFrame(index=cents.index)
    out["revenue_total"] = cents["revenue_total"] / 100
    out["revenue_recurring"] = cents["revenue_recurring"] / 100
    out["revenue_one_time"] = cents["revenue_one_time"] / 100
    out["cogs"] = cents["cogs"] / 100
    out["gross_profit"] = gross_profit / 100
    out["gross_margin_pct"] = _pct(gross_profit, cents["revenue_total"])
    out["rd_model_spend"] = cents["rd_model_spend"] / 100
    out["margin_after_rd_pct"] = _pct(gross_profit - cents["rd_model_spend"], cents["revenue_total"])
    out["margin_recurring_only_pct"] = _pct(cents["revenue_recurring"] - cents["cogs"],
                                            cents["revenue_recurring"])
    return out[OUTPUT_COLUMNS]


def monthly_activity(df: pd.DataFrame) -> pd.DataFrame:
    """Invoice count and distinct billed accounts per month (for the negative-margin flag)."""
    rev = df[df["entry_type"] == config.REVENUE_TYPE]
    act = (rev.groupby("month")
              .agg(invoices=("entry_id", "size"), billed_accounts=("counterparty", "nunique"))
              .reindex(config.MONTHS, fill_value=0))
    act["invoice_rank"] = act["invoices"].rank(method="min").astype(int)      # 1 = fewest
    act["accounts_rank"] = act["billed_accounts"].rank(method="min").astype(int)
    return act


def segment_check(df: pd.DataFrame) -> dict:
    rev = df[df["entry_type"] == config.REVENUE_TYPE]
    per_account = rev.groupby("counterparty")["customer_segment"].nunique()
    return {
        "accounts": int(len(per_account)),
        "accounts_in_multiple_segments": int((per_account > 1).sum()),
        "max_segments_per_account": int(per_account.max()),
    }


def reconciliation(summary: pd.DataFrame, target_pct: float | None = None) -> dict:
    """Compare this report's margins with the kickoff-notes figure, using ledger data only."""
    target = config.KICKOFF_NOTES_MARGIN_PCT if target_pct is None else target_pct
    total = summary.loc["TOTAL"]
    months = summary.drop(index="TOTAL")
    positive = months[months["gross_margin_pct"] > 0]
    pos_rev, pos_cogs = positive["revenue_total"].sum(), positive["cogs"].sum()
    revenue = total["revenue_total"]
    required_cogs = revenue * (1 - target / 100)
    return {
        "target_pct": target,
        "bases": [
            ("Gross margin, summed dollars (headline)", total["gross_margin_pct"]),
            ("Margin after R&D model spend", total["margin_after_rd_pct"]),
            ("Recurring revenue only", total["margin_recurring_only_pct"]),
            ("Simple average of the 12 monthly gross margins", months["gross_margin_pct"].mean()),
            (f"Gross margin excluding the {len(months) - len(positive)} negative-margin months",
             (pos_rev - pos_cogs) / pos_rev * 100 if pos_rev else float("nan")),
        ],
        "required_cogs": required_cogs,
        "cogs_gap": total["cogs"] - required_cogs,
    }


# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------
def write_csv(summary: pd.DataFrame, path: Path | str) -> None:
    out = summary.copy()
    out[DOLLAR_COLUMNS] = out[DOLLAR_COLUMNS].round(2)
    out[PCT_COLUMNS] = out[PCT_COLUMNS].round(2)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(path, index=True, index_label="month")


def _money(x: float) -> str:
    return f"-${abs(x):,.2f}" if x < 0 else f"${x:,.2f}"


def _pct_str(x: float) -> str:
    return "n/a" if pd.isna(x) else f"{x:.1f}%"


def render_report(df: pd.DataFrame, summary: pd.DataFrame, headline: str | None = None) -> str:
    headline = headline or config.HEADLINE_MARGIN
    if headline not in ("gross", "after_rd"):
        raise ValueError(f"HEADLINE_MARGIN must be 'gross' or 'after_rd', got {headline!r}")

    total = summary.loc["TOTAL"]
    months = summary.drop(index="TOTAL")
    activity = monthly_activity(df)
    seg = segment_check(df)
    rec = reconciliation(summary)

    gross_line = (f"**Gross margin (excluding R&D): {_pct_str(total['gross_margin_pct'])}**"
                  f" - revenue {_money(total['revenue_total'])}, cost of revenue {_money(total['cogs'])},"
                  f" gross profit {_money(total['gross_profit'])}.")
    after_line = (f"**Margin after R&D model spend: {_pct_str(total['margin_after_rd_pct'])}**"
                  f" - after also subtracting {_money(total['rd_model_spend'])} of model evaluation"
                  f" and fine-tuning spend.")
    if headline == "gross":
        top = [f"Headline margin: {gross_line}", "", f"Also reported: {after_line}"]
    else:
        top = [f"Headline margin: {after_line}", "", f"Also reported: {gross_line}"]

    lines = [
        "# Margin summary: Nov 2025 to Oct 2026",
        "",
        "Basis: invoice date (accrual). Money in = customer invoices; money out = AI provider bills.",
        "",
        "## Headline",
        "",
        *top,
        "",
        f"Recurring-revenue-only margin (one-time fees removed): {_pct_str(total['margin_recurring_only_pct'])}.",
        "",
        "## Monthly table",
        "",
        "| Month | Revenue | Recurring | One-time | COGS | Gross profit | Gross margin | "
        "R&D model spend | Margin after R&D | Recurring-only margin |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for label, r in summary.iterrows():
        name = f"**{label}**" if label == "TOTAL" else label
        lines.append(
            f"| {name} | {_money(r['revenue_total'])} | {_money(r['revenue_recurring'])} | "
            f"{_money(r['revenue_one_time'])} | {_money(r['cogs'])} | {_money(r['gross_profit'])} | "
            f"{_pct_str(r['gross_margin_pct'])} | {_money(r['rd_model_spend'])} | "
            f"{_pct_str(r['margin_after_rd_pct'])} | {_pct_str(r['margin_recurring_only_pct'])} |"
        )
    lines += [
        "",
        "TOTAL margins are computed from summed dollars, not by averaging the monthly percentages.",
        "",
        "## Why this report does not show 38%",
        "",
        f"The kickoff notes quote a margin of {rec['target_pct']:.0f}%. This ledger does not reproduce it, "
        f"and the notes' source and definition are not in the ledger, so the reason for the gap is "
        f"**unconfirmed**. What the ledger shows:",
        "",
        "| Basis | Margin |",
        "|---|---:|",
        *[f"| {name} | {_pct_str(v)} |" for name, v in rec["bases"]],
        "",
        f"None of these equals {rec['target_pct']:.0f}%. For {rec['target_pct']:.0f}% to hold on this "
        f"revenue ({_money(total['revenue_total'])}), cost of revenue would have to be about "
        f"{_money(rec['required_cogs'])}, which is {_money(rec['cogs_gap'])} less than the "
        f"{_money(total['cogs'])} of serving-workload bills in the ledger. The cost rule below has not "
        f"been adjusted to close this gap. Ask the author of the kickoff notes how {rec['target_pct']:.0f}% "
        f"was defined (period, revenue basis, which costs) before the partners compare the two numbers.",
        "",
        "## Data notes",
        "",
        "**Cost rule**",
        "",
        f"- Cost of revenue counts only model bills for {', '.join(f'`{w}`' for w in config.COGS_WORKLOADS)}. "
        f"These are production inference, booked to `{config.COGS_ACCOUNT}`.",
        f"- Bills with workload `{config.RD_WORKLOAD}` are left out of COGS and shown as R&D model spend. "
        "They pay for benchmarking and training models (eval batches, classifier fine-tuning, "
        "drafting-style model fine-tuning), not for serving a customer.",
        "- This includes bills whose memo says \"redline accuracy benchmark\". Customers pay for redlines, "
        "but these bills pay for testing the accuracy of our redline output, not for producing a "
        "customer's redline.",
        "- Classification uses `booked_account` and `workload` only, not memo keywords (\"redline\" also "
        "appears in revenue memos). Memo words are a cross-check; the run fails if the two disagree.",
        "- The `is_recurring` flag on model bills is ignored because it is inconsistent with the memos. "
        "It is used only to split revenue into recurring and one-time.",
        "- `customer_segment` is not used for any breakdown (see flag 2).",
        "",
        "## Flags (reported, not corrected)",
        "",
    ]

    negative = months[months["gross_margin_pct"] < 0]
    lines += ["**1. Negative gross margin months: unconfirmed whether churn or missing invoices**", ""]
    if len(negative):
        for m, r in negative.iterrows():
            a = activity.loc[m]
            lines.append(
                f"- {m}: gross margin {_pct_str(r['gross_margin_pct'])}; revenue {_money(r['revenue_total'])} "
                f"against COGS {_money(r['cogs'])}; {int(a['invoices'])} invoices from "
                f"{int(a['billed_accounts'])} billed accounts (invoice count ranks {int(a['invoice_rank'])} "
                f"of 12 and billed accounts ranks {int(a['accounts_rank'])} of 12, where 1 = fewest)."
            )
        lines += [
            "",
            "Revenue fell in these months while COGS stayed roughly flat. The ledger cannot show whether "
            "that is real customer churn or invoices missing from the extract. Confirm with the ledger "
            "owner before using these months in a narrative. No adjustment has been made.",
        ]
    else:
        lines.append("- No month has a negative gross margin.")
    lines += ["", "| Month | Invoices | Billed accounts |", "|---|---:|---:|"]
    for m, a in activity.iterrows():
        lines.append(f"| {m} | {int(a['invoices'])} | {int(a['billed_accounts'])} |")
    lines += [
        "",
        "**2. Customer segment labels are inconsistent**",
        "",
        f"- {seg['accounts_in_multiple_segments']} of {seg['accounts']} client accounts appear under more than "
        f"one `customer_segment` (up to {seg['max_segments_per_account']} different segments per account). "
        "The label is not a stable property of the account, so no margin is broken out by segment or "
        "customer. A proper account-to-segment mapping is needed first.",
        "",
    ]
    return "\n".join(lines)


def build(ledger_path=None, csv_path=None, md_path=None, headline=None) -> pd.DataFrame:
    df = load_ledger(ledger_path)
    validate_ledger(df)
    summary = monthly_summary(df)
    csv_path = Path(csv_path or config.SUMMARY_CSV)
    md_path = Path(md_path or config.SUMMARY_MD)
    write_csv(summary, csv_path)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_report(df, summary, headline), encoding="utf-8")
    return summary


def main() -> int:
    try:
        summary = build()
    except LedgerValidationError as exc:
        print(exc, file=sys.stderr)
        return 1
    t = summary.loc["TOTAL"]
    print(f"Wrote {config.SUMMARY_CSV.relative_to(config.ROOT)} and {config.SUMMARY_MD.relative_to(config.ROOT)}")
    print(f"Revenue ${t['revenue_total']:,.2f} | COGS ${t['cogs']:,.2f} | R&D ${t['rd_model_spend']:,.2f}")
    print(f"Gross margin {t['gross_margin_pct']:.1f}% | after R&D {t['margin_after_rd_pct']:.1f}% "
          f"| recurring-only {t['margin_recurring_only_pct']:.1f}% | headline = {config.HEADLINE_MARGIN}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
