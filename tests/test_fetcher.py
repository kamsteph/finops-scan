"""
Unit tests for CostExplorerFetcher using a fake boto3 client.
No AWS credentials or network needed.
"""
from decimal import Decimal

from finops_scan.fetcher import CostExplorerFetcher


class FakeClient:
    """Returns canned responses in order and records every call."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get_cost_and_usage(self, **kwargs):
        self.calls.append(kwargs)
        return self.responses.pop(0)


def day(date, service, amount):
    return {
        "TimePeriod": {"Start": date},
        "Groups": [{"Keys": [service],
                    "Metrics": {"BlendedCost": {"Amount": amount}}}],
    }


def total(amount):
    return {"Total": {"BlendedCost": {"Amount": amount}}}


class TestFetchLast30Days:

    def test_follows_next_page_token(self):
        client = FakeClient([
            {"ResultsByTime": [day("2026-09-01", "EC2", "10.00")],
             "NextPageToken": "abc"},
            {"ResultsByTime": [day("2026-09-02", "S3", "5.00")]},
        ])
        records = CostExplorerFetcher(client=client).fetch_last_30_days()
        assert [r.service for r in records] == ["EC2", "S3"]
        assert "NextPageToken" not in client.calls[0]
        assert client.calls[1]["NextPageToken"] == "abc"

    def test_skips_negligible_amounts(self):
        client = FakeClient([
            {"ResultsByTime": [day("2026-09-01", "EC2", "0.0001")]},
        ])
        assert CostExplorerFetcher(client=client).fetch_last_30_days() == []


class TestFetchTagCoverage:

    def test_uses_absent_match_option(self):
        client = FakeClient([
            {"ResultsByTime": [total("30.00")]},
            {"ResultsByTime": [total("100.00")]},
        ])
        CostExplorerFetcher(client=client).fetch_tag_coverage()
        tags = client.calls[0]["Filter"]["Tags"]
        assert tags["MatchOptions"] == ["ABSENT"]

    def test_sums_buckets_across_month_boundary(self):
        # A 30-day window can span two calendar months -> two buckets.
        client = FakeClient([
            {"ResultsByTime": [total("10.00"), total("20.00")]},   # untagged
            {"ResultsByTime": [total("40.00"), total("60.00")]},   # total
        ])
        cov = CostExplorerFetcher(client=client).fetch_tag_coverage()
        assert cov["untagged_spend"] == Decimal("30.00")
        assert cov["untagged_pct"] == 30.0
        assert cov["tagged_pct"] == 70.0

    def test_zero_spend_reports_fully_untagged(self):
        client = FakeClient([
            {"ResultsByTime": []},
            {"ResultsByTime": []},
        ])
        cov = CostExplorerFetcher(client=client).fetch_tag_coverage()
        assert cov == {"tagged_pct": 0.0, "untagged_pct": 100.0,
                       "untagged_spend": Decimal("0")}