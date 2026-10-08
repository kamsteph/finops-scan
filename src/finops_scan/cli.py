"""
CLI entry point for finops-scan.
Uses Click for argument parsing and command structure.
Orchestrates: fetcher → analyzer → reporter.
"""
import sys

import click
from rich.console import Console

from finops_scan.analyzer import CostAnalyzer
from finops_scan.fetcher import CostExplorerFetcher
from finops_scan.reporter import WasteReporter

console = Console()

@click.command()
@click.option(
    "--access-key",
    envvar="AWS_ACCESS_KEY_ID",
    required=True,
    help="AWS Access Key ID (or set AWS_ACCESS_KEY_ID env var)",
)
@click.option(
    "--secret-key",
    envvar="AWS_SECRET_ACCESS_KEY",
    required=True,
    help="AWS Secret Access Key (or set AWS_SECRET_ACCESS_KEY env var)",
)
@click.option(
    "--region",
    default="us-east-1",
    show_default=True,
    help="AWS region",
)
@click.option(
    "--account-id",
    default="my-account",
    help="AWS account ID or alias (display only)",
)
def main(
        access_key: str,
        secret_key:  str,
        region:      str,
        account_id:  str,
) -> None:
    """
    finops-scan: scan your AWS account for cloud waste in 60 seconds.

    Reads cost data via AWS Cost Explorer API (read-only).
    No data is stored. No resources are modified.

    Required IAM permission: ce:GetCostAndUsage

    Example:

        finops-scan --access-key AKIA... --secret-key ... --region us-east-1

    Or use environment variables:

        export AWS_ACCESS_KEY_ID=AKIA...

        export AWS_SECRET_ACCESS_KEY=...

        finops-scan
    """
    reporter = WasteReporter()
    reporter.print_header(account_id)

    # Step 1: Fetch
    console.print("[dim]Fetching cost data from AWS Cost Explorer...[/dim]")
    try:
        fetcher = CostExplorerFetcher(
            aws_access_key=access_key,
            aws_secret_key=secret_key,
            region=region,
        )
        records      = fetcher.fetch_last_30_days()
        tag_coverage = fetcher.fetch_tag_coverage()


    except Exception as e:
        console.print(f"[red]✗ Failed to connect to AWS:[/red] {e}")
        console.print(
            "[dim]Check your credentials and ensure "
            "ce:GetCostAndUsage permission is attached.[/dim]"
        )
        sys.exit(1)

    if not records:
        console.print(
            "[yellow]No cost data found for the last 30 days.[/yellow]"
        )
        sys.exit(0)

    console.print(
        f"[dim]✓ Fetched {len(records)} cost records.[/dim]"
    )

    # Step 2: Analyze
    console.print("[dim]Analyzing waste patterns...[/dim]")
    analyzer     = CostAnalyzer()
    summaries    = analyzer.summarize_by_service(records)
    opportunities = analyzer.identify_waste(summaries, tag_coverage)
    total        = analyzer.total_spend(records)
    savings      = analyzer.estimated_savings(opportunities)
    console.print("[dim]✓ Analysis complete.[/dim]\n")

    # Step 3: Report
    reporter.print_summary(total, savings, tag_coverage)
    reporter.print_top_services(summaries)
    reporter.print_waste_opportunities(opportunities)
    reporter.print_cta()


if __name__ == "__main__":
    main()