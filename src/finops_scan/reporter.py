"""
Reporter: formats and prints the waste report to the terminal.
Uses Rich for colored, structured output.
Separated from analyzer: formatting concerns are independent
of business logic. Easy to add JSON or CSV output later.
"""
from decimal import Decimal
from typing import List

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

from finops_scan.analyzer import ServiceSummary, WasteOpportunity

console = Console()


class WasteReporter:
    """
    Prints the finops-scan waste report to the terminal.
    All output goes through Rich for consistent formatting.
    """

    TREND_ICONS = {
        "increasing": "[red]↑[/red]",
        "decreasing": "[green]↓[/green]",
        "stable":     "[yellow]→[/yellow]",
    }

    def print_header(self, account_id: str) -> None:
        """Prints the fynC branded header."""
        console.print()
        console.print(Panel(
            Text.from_markup(
                "[bold #E8460A]finops-scan[/bold #E8460A]  "
                "[dim]by fynC[/dim]\n"
                "[dim]Cloud waste scanner: "
                "Read-only (No data stored)[/dim]"
            ),
            border_style="#E8460A",
            padding=(0, 2),
        ))
        console.print(
            f"[dim]Account:[/dim] [bold]{account_id}[/bold]  "
            f"[dim]Period:[/dim] [bold]Last 30 days[/bold]"
        )
        console.print()

    def print_summary(
            self,
            total_spend:       Decimal,
            estimated_savings: Decimal,
            tag_coverage:      dict,
    ) -> None:
        """Prints the 3-number KPI summary at the top."""
        table = Table(box=box.SIMPLE, show_header=False, padding=(0, 3))
        table.add_column(style="dim")
        table.add_column(style="bold")

        table.add_row(
            "Total 30-day spend",
            f"[bold white]${total_spend:,.2f}[/bold white]",
        )
        table.add_row(
            "Estimated savings available",
            f"[bold green]${estimated_savings:,.2f}[/bold green]",
        )
        table.add_row(
            "Tag coverage",
            f"[bold {'green' if tag_coverage['tagged_pct'] >= 80 else 'red'}]"
            f"{tag_coverage['tagged_pct']}%[/]",
        )

        console.print(Panel(table, title="[bold]Summary[/bold]",
                            border_style="dim"))

    def print_top_services(
            self,
            summaries: List[ServiceSummary],
            top_n: int = 8,
    ) -> None:
        """Prints the top N services by spend."""
        table = Table(
            title="Top Services by Spend",
            box=box.SIMPLE_HEAD,
            show_lines=False,
            title_style="bold",
        )
        table.add_column("#",        style="dim",   width=3)
        table.add_column("Service",  style="white", min_width=35)
        table.add_column("30-day",   style="bold",  justify="right")
        table.add_column("Daily avg",               justify="right")
        table.add_column("Trend",                   justify="center")

        for i, s in enumerate(summaries[:top_n], 1):
            # Shorten long AWS service names
            name = s.service.replace(
                "Amazon Elastic Compute Cloud Compute", "EC2 Compute"
            ).replace(
                "Amazon Relational Database Service", "RDS"
            ).replace(
                "Amazon Simple Storage Service", "S3"
            )
            table.add_row(
                str(i),
                name,
                f"${s.total_30d:,.2f}",
                f"${s.daily_average:,.2f}",
                self.TREND_ICONS.get(s.trend, "→"),
            )

        console.print(table)

    def print_waste_opportunities(
            self,
            opportunities: List[WasteOpportunity],
    ) -> None:
        """Prints ranked waste opportunities with actions."""
        console.print()
        console.print("[bold]Waste Opportunities[/bold]")
        console.print("[dim]Ranked by estimated impact[/dim]")
        console.print()

        if not opportunities:
            console.print(
                "[green]✓ No significant waste detected.[/green] "
                "Your account looks well optimized."
            )
            return

        for opp in opportunities:
            console.print(
                f"[bold #E8460A]#{opp.rank}[/bold #E8460A]  "
                f"[bold]{opp.service}[/bold]"
            )
            console.print(
                f"   [dim]Finding:[/dim]  {opp.finding}"
            )
            console.print(
                f"   [dim]Action:[/dim]   [green]{opp.action}[/green]"
            )
            console.print()

    def print_cta(self) -> None:
        """Prints the call to action at the end."""
        console.print(Panel(
            Text.from_markup(
                "[bold]Want this monitored automatically?[/bold]\n\n"
                "fynC tracks your cloud and AI spend continuously,\n"
                "alerts you when costs spike, and attributes every\n"
                "dollar to a team without any manual work.\n\n"
                "[bold #E8460A] → fync-1.onrender.com[/bold #E8460A]   "
                "[dim](or reply to the Show HN post)[/dim]"
            ),
            border_style="#E8460A",
            title="[bold #E8460A]fynC[/bold #E8460A]",
            padding=(1, 3),
        ))
        console.print()