"""
Unit tests for CostAnalyzer.
No AWS credentials needed — pure computation tests.
"""
import pytest
from decimal import Decimal
from finops_scan.fetcher import DailySpend
from finops_scan.analyzer import CostAnalyzer, WasteOpportunity


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


def make_growing(service: str, early: str = "5.00", late: str = "15.00") -> list:
    """7 early days and 7 late days, so the trend reads 'increasing'."""
    rows = []
    for i in range(7):
        rows.append(DailySpend(date=f"2026-05-{str(i+1).zfill(2)}",
                               service=service, amount=Decimal(early)))
    for i in range(7):
        rows.append(DailySpend(date=f"2026-05-{str(i+22).zfill(2)}",
                               service=service, amount=Decimal(late)))
    return rows


class TestRankingAndCap:

    def test_cap_of_10_with_real_findings(self, analyzer):
        records = []
        # 5 services that trigger rule 1 (increasing + in IDLE_SIGNALS)
        for name in CostAnalyzer.IDLE_SIGNALS:
            records += make_growing(name)
        # 8 services that trigger rule 2 (Data Transfer, > $100 each)
        for i in range(8):
            records += make_records(f"Data Transfer {i}", 30, "10.00")
        summaries = analyzer.summarize_by_service(records)
        coverage  = {"tagged_pct": 10.0, "untagged_pct": 90.0,
                     "untagged_spend": Decimal("1000.00")}
        opps = analyzer.identify_waste(summaries, coverage)
        # 5 + 8 + 1 (tagging) = 14 candidates, capped to 10
        assert len(opps) == 10

    def test_ranked_by_cost_descending(self, analyzer):
        records = (
                make_growing("Amazon Elastic Compute Cloud - Compute") +
                make_records("Data Transfer", 30, "100.00")      # $3,000
        )
        summaries = analyzer.summarize_by_service(records)
        coverage  = {"tagged_pct": 100.0, "untagged_pct": 0.0,
                     "untagged_spend": Decimal("0")}
        opps = analyzer.identify_waste(summaries, coverage)
        assert [o.rank for o in opps] == list(range(1, len(opps) + 1))
        costs = [o.monthly_cost for o in opps]
        assert costs == sorted(costs, reverse=True)
        assert opps[0].service == "Data Transfer"


class TestTrendEdgeCases:

    def test_new_service_without_first_week_is_stable(self, analyzer):
        # Spend only appears in the last week of the window.
        early_other = make_records("S3", 7, "1.00")
        late_only = [
            DailySpend(date=f"2026-05-{str(i+22).zfill(2)}",
                       service="NewService", amount=Decimal("9.00"))
            for i in range(7)
        ]
        summaries = analyzer.summarize_by_service(early_other + late_only)
        new = [s for s in summaries if s.service == "NewService"][0]
        assert new.trend == "stable"