"""
AWS Cost Explorer fetcher.
Pulls cost and usage data using the Cost Explorer API.
Works on any AWS account — no CUR or S3 setup required.
Just needs credentials with the ce:GetCostAndUsage permission.
"""
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import List

import boto3


@dataclass
class DailySpend:
    date:     str
    service:  str
    amount:   Decimal
    currency: str = "USD"


class CostExplorerFetcher:
    """
    Fetches cost data from AWS Cost Explorer API.

    Required IAM permission:
      ce:GetCostAndUsage

    This is a read-only permission. fynC and finops-scan
    never write to or modify any AWS resources.
    """

    def __init__(
            self,
            aws_access_key: str = None,
            aws_secret_key: str = None,
            region:         str = "us-east-1",
            client=None,
    ) -> None:
        # `client` lets tests inject a fake. When keys are None, boto3 falls
        # back to its default credential chain (env vars, AWS_PROFILE, ...).
        self._client = client or boto3.client(
            "ce",
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=region,
        )

    def fetch_last_30_days(self) -> List[DailySpend]:
        """
        Fetches daily spend by service for the last 30 days.
        Returns a flat list of DailySpend records.
        Follows NextPageToken so large accounts are not truncated.
        """
        end   = date.today()
        start = end - timedelta(days=30)

        records: List[DailySpend] = []
        token = None

        while True:
            kwargs = dict(
                TimePeriod={
                    "Start": start.isoformat(),
                    "End":   end.isoformat(),
                },
                Granularity="DAILY",
                Metrics=["BlendedCost"],
                GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
            )
            if token:
                kwargs["NextPageToken"] = token

            response = self._client.get_cost_and_usage(**kwargs)

            for result in response.get("ResultsByTime", []):
                period = result["TimePeriod"]["Start"]
                for group in result.get("Groups", []):
                    service = group["Keys"][0]
                    amount  = Decimal(
                        group["Metrics"]["BlendedCost"]["Amount"]
                    )
                    if amount > Decimal("0.001"):  # skip negligible costs
                        records.append(DailySpend(
                            date=period,
                            service=service,
                            amount=amount,
                        ))

            token = response.get("NextPageToken")
            if not token:
                break

        return records

    @staticmethod
    def _sum_total(response: dict) -> Decimal:
        """
        Sums BlendedCost across ALL result buckets of a response.
        MONTHLY granularity returns one bucket per calendar month touched
        by the period, so a 30-day window can span two buckets.
        """
        return sum(
            (Decimal(r["Total"]["BlendedCost"]["Amount"])
             for r in response.get("ResultsByTime", [])),
            Decimal("0"),
        )

    def fetch_tag_coverage(self) -> dict:
        """
        Fetches tag coverage — what fraction of spend has a team tag.
        Cost Explorer has no "tag exists" filter, so we query the spend
        where the tag is ABSENT and derive tagged = total - untagged.
        The tag key must be activated as a cost allocation tag in the
        Billing console; until then all spend counts as untagged.
        Returns dict with tagged_pct, untagged_pct, untagged_spend.
        """
        end   = date.today()
        start = end - timedelta(days=30)
        period = {"Start": start.isoformat(), "End": end.isoformat()}

        untagged = self._client.get_cost_and_usage(
            TimePeriod=period,
            Granularity="MONTHLY",
            Metrics=["BlendedCost"],
            Filter={
                "Tags": {
                    "Key":          "team",
                    "MatchOptions": ["ABSENT"],
                }
            },
        )

        total = self._client.get_cost_and_usage(
            TimePeriod=period,
            Granularity="MONTHLY",
            Metrics=["BlendedCost"],
        )

        untagged_spend = self._sum_total(untagged)
        total_spend    = self._sum_total(total)

        if total_spend == Decimal("0"):
            return {"tagged_pct": 0.0, "untagged_pct": 100.0,
                    "untagged_spend": Decimal("0")}

        untagged_spend = min(untagged_spend, total_spend)  # guard rounding
        untagged_pct   = float(untagged_spend / total_spend * 100)
        tagged_pct     = 100.0 - untagged_pct

        return {
            "tagged_pct":     round(tagged_pct, 1),
            "untagged_pct":   round(untagged_pct, 1),
            "untagged_spend": untagged_spend,
        }