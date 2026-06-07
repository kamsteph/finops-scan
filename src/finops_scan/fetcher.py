"""
AWS Cost Explorer fetcher.
Pulls cost and usage data using the Cost Explorer API.
Works on any AWS account — no CUR or S3 setup required.
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


@dataclass
class ResourceWaste:
    service:      str
    resource_id:  str
    monthly_cost: Decimal
    reason:       str
    savings:      Decimal


class CostExplorerFetcher:
    """
    Fetches cost data from AWS Cost Explorer API.

    Required IAM permissions:
      ce:GetCostAndUsage
      ce:GetCostAndUsageWithResources (optional — for resource-level)

    These are read-only permissions. fynC and finops-scan
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
        Fetches tag coverage — what fraction of spend has team tags.
        Returns dict with tagged_pct, untagged_pct, untagged_spend.
        """
        end   = date.today()
        start = end - timedelta(days=30)

        tagged = self._client.get_cost_and_usage(
            TimePeriod={"Start": start.isoformat(), "End": end.isoformat()},
            Granularity="MONTHLY",
            Metrics=["BlendedCost"],
            Filter={
                "Tags": {
                    "Key":    "team",
                    "Values": ["*"],
                    "MatchOptions": ["EXISTS"],
                }
            },
        )

        total = self._client.get_cost_and_usage(
            TimePeriod={"Start": start.isoformat(), "End": end.isoformat()},
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

        tagged_spend = extract(tagged)
        total_spend  = extract(total)

        if total_spend == Decimal("0"):
            return {"tagged_pct": 0.0, "untagged_pct": 100.0,
                    "untagged_spend": Decimal("0")}

        tagged_pct   = float(tagged_spend / total_spend * 100)
        untagged_pct = 100.0 - tagged_pct

        return {
            "tagged_pct":     round(tagged_pct, 1),
            "untagged_pct":   round(untagged_pct, 1),
            "untagged_spend": total_spend - tagged_spend,
        }