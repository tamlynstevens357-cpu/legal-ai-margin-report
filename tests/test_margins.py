import pandas as pd
import pytest

import config
from src import margins

EXPECTED_REVENUE = 1_363_640.65
EXPECTED_COGS = 1_008_366.57
EXPECTED_RD = 128_890.39


@pytest.fixture(scope="module")
def ledger():
    df = margins.load_ledger()
    margins.validate_ledger(df)
    return df


@pytest.fixture(scope="module")
def summary(ledger):
    return margins.monthly_summary(ledger)


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    d = tmp_path_factory.mktemp("out")
    csv, md = d / "s.csv", d / "s.md"
    margins.build(csv_path=csv, md_path=md)
    return pd.read_csv(csv, index_col="month"), md.read_text(encoding="utf-8")


# --- totals reconcile to the ledger -------------------------------------
def test_totals_reconcile(ledger, summary):
    t = summary.loc["TOTAL"]
    assert t["revenue_total"] == pytest.approx(EXPECTED_REVENUE, abs=0.005)
    assert t["cogs"] == pytest.approx(EXPECTED_COGS, abs=0.005)
    assert t["rd_model_spend"] == pytest.approx(EXPECTED_RD, abs=0.005)
    # and straight from the raw ledger, independent of classify()
    rev = ledger[ledger.entry_type == "revenue_invoice"].amount_usd.sum()
    cogs = ledger[ledger.booked_account == "cost_of_revenue"].amount_usd.sum()
    rd = ledger[ledger.booked_account == "research_and_development"].amount_usd.sum()
    assert (rev, cogs, rd) == pytest.approx((EXPECTED_REVENUE, EXPECTED_COGS, EXPECTED_RD), abs=0.005)


def test_monthly_rows_sum_to_total(summary):
    months = summary.drop(index="TOTAL")
    for col in margins.DOLLAR_COLUMNS:
        assert months[col].sum() == pytest.approx(summary.loc["TOTAL", col], abs=0.005)


def test_recurring_plus_one_time_equals_revenue(summary):
    diff = (summary["revenue_recurring"] + summary["revenue_one_time"] - summary["revenue_total"]).abs()
    assert diff.max() < 0.005


# --- every month exactly once -------------------------------------------
def test_every_month_exactly_once(built):
    csv, _ = built
    assert list(csv.index) == config.MONTHS + ["TOTAL"]
    assert csv.index.is_unique and len(config.MONTHS) == 12


# --- total margin uses summed dollars -----------------------------------
def test_total_margin_is_from_summed_dollars(summary):
    t, months = summary.loc["TOTAL"], summary.drop(index="TOTAL")
    assert t["gross_margin_pct"] == pytest.approx((t.revenue_total - t.cogs) / t.revenue_total * 100)
    assert t["gross_margin_pct"] != pytest.approx(months["gross_margin_pct"].mean(), abs=1)


# --- the three margins match across CSV and markdown ---------------------
def _md_table_rows(md: str):
    rows = {}
    for line in md.splitlines():
        cells = [c.strip().strip("*") for c in line.strip().strip("|").split("|")]
        if line.startswith("|") and len(cells) == 10 and (cells[0][:2] == "20" or cells[0] == "TOTAL"):
            rows[cells[0]] = cells
    return rows


def test_margins_match_between_csv_and_markdown(built):
    csv, md = built
    rows = _md_table_rows(md)
    assert set(rows) == set(csv.index)
    for month, cells in rows.items():
        for col, idx in (("gross_margin_pct", 6), ("margin_after_rd_pct", 8),
                         ("margin_recurring_only_pct", 9)):
            md_val = float(cells[idx].rstrip("%"))
            assert md_val == pytest.approx(csv.loc[month, col], abs=0.06), (month, col)


def test_headline_follows_config(ledger, summary):
    gross = margins.render_report(ledger, summary, headline="gross")
    after = margins.render_report(ledger, summary, headline="after_rd")
    assert gross.split("Headline margin: ")[1].startswith("**Gross margin")
    assert after.split("Headline margin: ")[1].startswith("**Margin after R&D")
    with pytest.raises(ValueError):
        margins.render_report(ledger, summary, headline="nonsense")


# --- cost rule ------------------------------------------------------------
def test_redline_benchmark_bills_are_rd_not_cogs(ledger, summary):
    hit = ledger[ledger.memo.str.contains("redline accuracy benchmark", case=False)]
    assert len(hit) == 31
    assert (hit.booked_account == "research_and_development").all()
    assert (hit.workload == config.RD_WORKLOAD).all()
    assert hit.amount_usd.sum() == pytest.approx(51_063.58, abs=0.005)


def test_cogs_only_contains_serving_workloads(ledger):
    d = margins.classify(ledger)
    assert set(d[d.bucket == "cogs"].workload) == set(config.COGS_WORKLOADS)
    assert set(d[d.bucket == "rd"].workload) == {config.RD_WORKLOAD}


def test_revenue_recurring_flag_matches_memos(ledger):
    rev = ledger[ledger.entry_type == "revenue_invoice"]
    assert (rev.is_recurring == ~rev.memo.str.startswith("One-time")).all()


# --- validation fails loudly ----------------------------------------------
def test_fails_when_workload_and_account_disagree(ledger):
    bad = ledger.copy()
    i = bad[bad.workload == "contract_review"].index[0]
    bad.loc[i, "booked_account"] = "research_and_development"
    with pytest.raises(margins.LedgerValidationError, match="not booked to 'cost_of_revenue'"):
        margins.validate_ledger(bad)


def test_fails_when_cogs_bill_has_eval_memo(ledger):
    bad = ledger.copy()
    i = bad[bad.booked_account == "cost_of_revenue"].index[0]
    bad.loc[i, "memo"] = "OpenAI eval batch, redline accuracy benchmark"
    with pytest.raises(margins.LedgerValidationError, match="eval/fine-tuning memo"):
        margins.validate_ledger(bad)


def test_fails_on_unknown_workload_and_missing_month(ledger):
    bad = ledger.copy()
    i = bad[bad.entry_type == "model_bill"].index[0]
    bad.loc[i, "workload"] = "something_new"
    with pytest.raises(margins.LedgerValidationError, match="unknown or blank workload"):
        margins.validate_ledger(bad)
    with pytest.raises(margins.LedgerValidationError, match="reporting window"):
        margins.validate_ledger(ledger[ledger.month != "2026-03"])


# --- flags and reconciliation are written, not silently fixed -------------
def test_report_flags_and_38_reconciliation(built):
    _, md = built
    assert "## Why this report does not show 38%" in md
    assert "unconfirmed" in md
    assert "2026-08" in md and "2026-09" in md
    assert "customer_segment" in md and "18 of 18" in md
