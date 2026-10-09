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
from botocore.exceptions import ClientError, NoCredentialsError
from finops_scan.demo import demo_records, demo_tag_coverage


console = Console()

@click.command()
@click.option(
    "--access-key",
    envvar="AWS_ACCESS_KEY_ID",
    help="AWS Access Key ID (or set AWS_ACCESS_KEY_ID env var)",
)
@click.option(
    "--secret-key",
    envvar="AWS_SECRET_ACCESS_KEY",
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
@click.option(
    "--demo",
    is_flag=True,
    help="Run on built-in sample data. No AWS account or credentials needed."
)

def main(
        access_key: str,
        secret_key:  str,
        region:      str,
        account_id:  str,
        demo: bool,
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
    if demo:
        if account_id == "my-account":
            account_id = "demo-account"
    elif not (access_key and secret_key):
        raise click.UsageError(
            "Missing AWS credentials. Pass --access-key and --secret-key, "
            "set AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY, "
            "or try --demo to see a sample report."
        )

    reporter = WasteReporter()
    reporter.print_header(account_id)

    # Step 1: Fetch (or load demo data)
    if demo:
        console.print(
            "[bold yellow]DEMO MODE: sample data, not your AWS account.[/bold yellow]"
        )
        records      = demo_records()
        tag_coverage = demo_tag_coverage(records)
    else:
        console.print("[dim]Fetching cost data from AWS Cost Explorer...[/dim]")
        try:
            fetcher = CostExplorerFetcher(
                aws_access_key=access_key,
                aws_secret_key=secret_key,
                region=region,
            )
            records      = fetcher.fetch_last_30_days()
            tag_coverage = fetcher.fetch_tag_coverage()

        except NoCredentialsError:
            console.print(
                "[red]✗ No AWS credentials found.[/red] "
                "Set AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY, "
                "or pass --access-key and --secret-key."
            )
            sys.exit(1)
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code in ("UnrecognizedClientException", "InvalidClientTokenId",
                        "SignatureDoesNotMatch"):
                console.print(
                    "[red]✗ Invalid AWS credentials.[/red] "
                    "Re-check the access key and secret key."
                )
            elif code in ("AccessDeniedException", "AccessDenied"):
                console.print(
                    "[red]✗ Permission denied.[/red] "
                    "Attach a policy allowing ce:GetCostAndUsage to this user."
                )
            else:
                console.print(f"[red]✗ AWS error ({code}):[/red] {e}")
                console.print(
                    "[dim]Unexpected error. Please open an issue on GitHub.[/dim]"
                )
            sys.exit(1)
        except Exception as e:
            console.print(f"[red]✗ Unexpected error:[/red] {e}")
            console.print("[dim]Please open an issue on GitHub.[/dim]")
            sys.exit(1)

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