"""
Analyzer — derives waste insights from Cost Explorer data.
No AWS API calls here — pure computation on DailySpend records.
Separated from fetcher so it can be unit tested without AWS credentials.
"""
from dataclasses import dataclass
from decimal import Decimal
from typing import List, Dict
from src.finops_scan.fetcher import DailySpend


@dataclass
class ServiceSummary:
    service:       str
    total_30d:     Decimal
    daily_average: Decimal
    trend:         str    # "increasing" | "decreasing" | "stable"


@dataclass
class WasteOpportunity:
    rank:         int
    service:      str
    finding:      str
    monthly_cost: Decimal
    action:       str


class CostAnalyzer:
    """
    Derives ranked waste opportunities from DailySpend records.

    All methods are pure functions — same input always produces
    same output. No side effects, no API calls.
    Easy to unit test without AWS credentials.
    """

    # Services that typically indicate waste when spend is high
    # relative to their utility
    IDLE_SIGNALS = {
        "Amazon Elastic Compute Cloud - Compute": "EC2 instances",
        "Amazon Relational Database Service":     "RDS instances",
        "Amazon ElastiCache":                     "ElastiCache clusters",
        "Amazon Redshift":                        "Redshift clusters",
        "AWS Lambda":                              "Lambda functions",
    }

    AI_SERVICES = {
        "Amazon Bedrock",
        "Amazon SageMaker",
    }

    def summarize_by_service(
            self,
            records: List[DailySpend],
    ) -> List[ServiceSummary]:
        """
        Aggregates DailySpend records into per-service summaries.
        Sorted by total_30d descending — highest spend first.
        """
        totals:  Dict[str, Decimal] = {}
        counts:  Dict[str, int]     = {}
        first7:  Dict[str, Decimal] = {}
        last7:   Dict[str, Decimal] = {}

        sorted_records = sorted(records, key=lambda r: r.date)
        all_dates = sorted(set(r.date for r in sorted_records))
        first_7_dates = set(all_dates[:7])
        last_7_dates  = set(all_dates[-7:])

        for r in records:
            totals[r.service]  = totals.get(r.service, Decimal("0")) + r.amount
            counts[r.service]  = counts.get(r.service, 0) + 1
            if r.date in first_7_dates:
                first7[r.service] = first7.get(r.service,
                                               Decimal("0")) + r.amount
            if r.date in last_7_dates:
                last7[r.service]  = last7.get(r.service,
                                              Decimal("0")) + r.amount

        summaries = []
        for service, total in totals.items():
            count = counts[service]
            daily_avg = total / count if count > 0 else Decimal("0")
            f = first7.get(service, Decimal("0"))
            l = last7.get(service, Decimal("0"))
            if l > f * Decimal("1.10"):
                trend = "increasing"
            elif l < f * Decimal("0.90"):
                trend = "decreasing"
            else:
                trend = "stable"

            summaries.append(ServiceSummary(
                service=service,
                total_30d=total,
                daily_average=daily_avg,
                trend=trend,
            ))

        return sorted(summaries, key=lambda s: s.total_30d, reverse=True)

    def identify_waste(
            self,
            summaries: List[ServiceSummary],
            tag_coverage: dict,
    ) -> List[WasteOpportunity]:
        """
        Produces ranked waste opportunities from service summaries.
        Each opportunity has a specific finding and action.
        """
        opportunities: List[WasteOpportunity] = []
        rank = 1

        # Opportunity 1: increasing spend on compute services
        for s in summaries:
            if s.trend == "increasing" and s.service in self.IDLE_SIGNALS:
                name = self.IDLE_SIGNALS[s.service]
                opportunities.append(WasteOpportunity(
                    rank=rank,
                    service=s.service,
                    finding=(
                        f"{name} spend increased 10%+ over the last 7 days. "
                        f"30-day total: ${s.total_30d:,.2f}"
                    ),
                    monthly_cost=s.total_30d,
                    action=(
                        f"Review {name} utilization. "
                        f"Rightsizing or stopping idle instances "
                        f"could reduce this cost by 20-40%."
                    ),
                ))
                rank += 1

        # Opportunity 2: high spend on data transfer
        for s in summaries:
            if "Data Transfer" in s.service and s.total_30d > Decimal("100"):
                opportunities.append(WasteOpportunity(
                    rank=rank,
                    service=s.service,
                    finding=(
                        f"Data transfer cost ${s.total_30d:,.2f} in 30 days. "
                        f"Often caused by cross-AZ traffic or "
                        f"unoptimized S3 access patterns."
                    ),
                    monthly_cost=s.total_30d,
                    action=(
                        "Move resources to the same AZ. "
                        "Use S3 VPC endpoints to eliminate "
                        "data transfer charges."
                    ),
                ))
                rank += 1

        # Opportunity 3: low tag coverage
        if tag_coverage.get("untagged_pct", 100) > 20:
            untagged = tag_coverage.get("untagged_spend", Decimal("0"))
            opportunities.append(WasteOpportunity(
                rank=rank,
                service="All services",
                finding=(
                    f"{tag_coverage['untagged_pct']}% of spend "
                    f"(${untagged:,.2f}) has no team tag. "
                    f"You cannot allocate what you cannot attribute."
                ),
                monthly_cost=untagged,
                action=(
                    "Apply team tags to all resources. "
                    "fynC can automate tag suggestions "
                    "based on resource naming patterns."
                ),
            ))
            rank += 1

        # Opportunity 4: AI services with no visibility
        ai_spend = sum(
            s.total_30d for s in summaries
            if any(ai in s.service for ai in self.AI_SERVICES)
        )
        if ai_spend > Decimal("0"):
            opportunities.append(WasteOpportunity(
                rank=rank,
                service="AI Services",
                finding=(
                    f"${ai_spend:,.2f} spent on AI services in 30 days "
                    f"with no model-level breakdown. "
                    f"You cannot optimize what you cannot see."
                ),
                monthly_cost=ai_spend,
                action=(
                    "Track AI spend at the model level with fynC. "
                    "See which team is driving cost and "
                    "which model gives the best cost/quality ratio."
                ),
            ))
            rank += 1

        return opportunities[:10]  # top 10 only

    def total_spend(self, records: List[DailySpend]) -> Decimal:
        """Total spend across all services for the period."""
        return sum((r.amount for r in records), Decimal("0"))

    def estimated_savings(
            self,
            opportunities: List[WasteOpportunity],
    ) -> Decimal:
        """
        Conservative savings estimate: 20% of waste opportunity costs.
        Real savings depend on which actions are taken.
        """
        total = sum(
            (o.monthly_cost for o in opportunities
             if o.service != "All services"),
            Decimal("0"),
        )
        return total * Decimal("0.20")