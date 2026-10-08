"""
AWS Cost Explorer fetcher.
Pulls cost and usage data using the Cost Explorer API.
Works on any AWS account and no CUR or S3 setup required.
Just needs Access Key + Secret Key with ce:GetCostAndUsage permission.
"""
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import List, Optional

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

    Required IAM permissions:
      ce:GetCostAndUsage

    These are read-only permissions. finops-scan
    never write to or modify any AWS resources.
    """

    def __init__(
            self,
            aws_access_key: str,
            aws_secret_key: str,
            region:         str = "us-east-1",
    ) -> None:
        self._client = boto3.client(
            "ce",
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=region,
        )

    def fetch_last_30_days(self) -> List[DailySpend]:
        """
        Fetches daily spend by service for the last 30 days.
        Returns a flat list of DailySpend records.
        """
        end   = date.today()
        start = end - timedelta(days=30)

        response = self._client.get_cost_and_usage(
            TimePeriod={
                "Start": start.isoformat(),
                "End":   end.isoformat(),
            },
            Granularity="DAILY",
            Metrics=["BlendedCost"],
            GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
        )

        records: List[DailySpend] = []

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

        return records

    def fetch_tag_coverage(self) -> dict:
        """
        Fetches tag coverage: what fraction of spend has team tags.
        Cost Explorer has no "tag exists" filter, so we query the spend
        where the tag is ABSENT and derive tagged = total - untagged.
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

        def extract(resp) -> Decimal:
            results = resp.get("ResultsByTime", [])
            if not results:
                return Decimal("0")
            return Decimal(
                results[0]["Total"]["BlendedCost"]["Amount"]
            )

        untagged_spend = extract(untagged)
        total_spend    = extract(total)

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