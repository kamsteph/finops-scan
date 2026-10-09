"""
Demo data for `finops-scan --demo`.

Builds sample spend records so the analyzer and reporter can run without
an AWS account or credentials. Nothing here calls AWS.
The fake services are chosen so every rule in CostAnalyzer has something to find.
"""
from datetime import date, timedelta
from decimal import Decimal
from typing import List

from finops_scan.fetcher import DailySpend

DAYS = 30

def _wiggle(i: int) -> float:
    """Small deterministic ups and downs so the data does not look synthetic."""
    return ((i * 37) % 11 - 5) * 0.15

def _money(value: float) -> Decimal:
    return Decimal(str(round(max(value, 0.0), 2)))

# (AWS service name, daily amount as a function of day index i; 0 = oldest day)
_CURVES = [
    # Rising steadily: first week ~$45/day, last week ~$84/day -> "increasing",
    # and it is in IDLE_SIGNALS, so it produces a waste finding.
    ("Amazon Elastic Compute Cloud - Compute", lambda i: 40 + 1.7 * i + _wiggle(i)),
    # Falling steadily -> "decreasing".
    ("Amazon Relational Database Service", lambda i: 60 - 0.8 * i + _wiggle(i)),
    # Flat -> "stable".
    ("Amazon Simple Storage Service", lambda i: 12 + _wiggle(i) * 0.5),
    # Flat, and "Data Transfer" in the name with > $100 total -> data transfer finding.
    ("AWS Data Transfer", lambda i: 9 + _wiggle(i) * 0.5),
    # Rises then falls: first and last week are similar, so the analyzer
    # (which only compares those two weeks) calls it "stable". Also an AI
    # service, so it produces the AI-spend finding.
    ("Amazon Bedrock", lambda i: 4 + 1.2 * min(i, DAYS - 1 - i) + _wiggle(i) * 0.3),
    # Small flat line so the table has a long tail.
    ("Amazon CloudWatch", lambda i: 3 + _wiggle(i) * 0.2),
]

def demo_records() -> List[DailySpend]:
    """30 days x 6 services of sample DailySpend records (same window as the real fetcher)."""
    end = date.today()
    records: List[DailySpend] = []
    for i in range(DAYS):
        day = (end - timedelta(days=DAYS - i)).isoformat()
        for service, curve in _CURVES:
            records.append(DailySpend(date=day, service=service, amount=_money(curve(i))))

    return records

def demo_tag_coverage(records: List[DailySpend], tagged_pct: float = 58.0) -> dict:
    """Same dict shape as CostExplorerFetcher.fetch_tag_coverage()."""
    total = sum((r.amount for r in records), Decimal("0"))
    untagged_pct = round(100.0 - tagged_pct, 1)
    untagged_spend = (total * Decimal(str(untagged_pct))) / Decimal("100").quantize(Decimal("0.01"))

    return {
        "tagged_pct": round(tagged_pct, 1),
        "untagged_pct": untagged_pct,
        "untagged_spend": untagged_spend,
    }