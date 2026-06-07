"""
Unit tests for CostAnalyzer.
No AWS credentials needed — pure computation tests.
"""
import pytest
from decimal import Decimal
from src.finops_scan.fetcher import DailySpend
from src.finops_scan.analyzer import CostAnalyzer


def make_records(service: str, days: int, amount: str) -> list:
    """Factory — creates DailySpend records for a service."""
    return [
        DailySpend(
            date=f"2026-05-{str(i+1).zfill(2)}",
            service=service,
            amount=Decimal(amount),
        )
        for i in range(days)
    ]


@pytest.fixture
def analyzer():
    return CostAnalyzer()


class TestSummarizeByService:

    def test_aggregates_by_service(self, analyzer):
        records = make_records("Amazon EC2", 30, "10.00")
        summaries = analyzer.summarize_by_service(records)
        assert len(summaries) == 1
        assert summaries[0].service == "Amazon EC2"
        assert summaries[0].total_30d == Decimal("300.00")

    def test_sorted_by_total_descending(self, analyzer):
        records = (
                make_records("EC2", 30, "10.00") +
                make_records("S3",  30, "1.00")
        )
        summaries = analyzer.summarize_by_service(records)
        assert summaries[0].service == "EC2"
        assert summaries[1].service == "S3"

    def test_trend_increasing(self, analyzer):
        early = [
            DailySpend(date=f"2026-05-{str(i+1).zfill(2)}",
                       service="EC2", amount=Decimal("5.00"))
            for i in range(7)
        ]
        late = [
            DailySpend(date=f"2026-05-{str(i+22).zfill(2)}",
                       service="EC2", amount=Decimal("15.00"))
            for i in range(7)
        ]
        summaries = analyzer.summarize_by_service(early + late)
        assert summaries[0].trend == "increasing"

    def test_empty_records_returns_empty(self, analyzer):
        assert analyzer.summarize_by_service([]) == []


class TestIdentifyWaste:

    def test_low_tag_coverage_flagged(self, analyzer):
        records   = make_records("EC2", 30, "100.00")
        summaries = analyzer.summarize_by_service(records)
        coverage  = {"tagged_pct": 20.0, "untagged_pct": 80.0,
                     "untagged_spend": Decimal("2400.00")}
        opps = analyzer.identify_waste(summaries, coverage)
        services = [o.service for o in opps]
        assert "All services" in services

    def test_maximum_10_opportunities(self, analyzer):
        records = []
        for i in range(20):
            records += make_records(f"Service{i}", 30, "100.00")
        summaries = analyzer.summarize_by_service(records)
        coverage  = {"tagged_pct": 10.0, "untagged_pct": 90.0,
                     "untagged_spend": Decimal("1000.00")}
        opps = analyzer.identify_waste(summaries, coverage)
        assert len(opps) <= 10


class TestTotalSpend:

    def test_sums_all_records(self, analyzer):
        records = make_records("EC2", 3, "100.00")
        assert analyzer.total_spend(records) == Decimal("300.00")

    def test_empty_returns_zero(self, analyzer):
        assert analyzer.total_spend([]) == Decimal("0")


class TestEstimatedSavings:

    def test_twenty_percent_of_waste(self, analyzer):
        from src.finops_scan.analyzer import WasteOpportunity
        opps = [
            WasteOpportunity(
                rank=1,
                service="EC2",
                finding="test",
                action="test",
                monthly_cost=Decimal("1000.00"),
            )
        ]
        savings = analyzer.estimated_savings(opps)
        assert savings == Decimal("200.00")