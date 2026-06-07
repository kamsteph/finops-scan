# finops-scan

**Scan your AWS account for cloud waste in 60 seconds.**

Free, open source, read-only. No data stored. No resources modified.

```bash
pip install finops-scan
finops-scan --access-key AKIA... --secret-key ...
```

---

## What it does

finops-scan connects to your AWS Cost Explorer API (read-only) and produces a ranked waste report in your terminal:

- **Top services by spend** — with 30-day trend (increasing/decreasing/stable)
- **Waste opportunities** — ranked by estimated impact, with specific actions
- **Tag coverage score** — what % of your spend has team attribution
- **Estimated savings** — conservative 20% estimate of actionable waste

## Example output
╭─────────────────────────────────────────────╮
│  finops-scan  by fynC                        │
│  Cloud waste scanner · Read-only             │
╰─────────────────────────────────────────────╯
Account: my-aws-account   Period: Last 30 days
Total 30-day spend        $18,420.55
Estimated savings          $3,684.11
Tag coverage                    42%
Top Services by Spend
Service          30-day      Daily avg   Trend
1  EC2 Compute    $9,240.00      $308.00      ↑
2  RDS            $4,100.00      $136.67      →
3  S3             $1,820.00       $60.67      ↓
Waste Opportunities
#1  EC2 Compute
Finding:  EC2 Compute spend increased 10%+ over the last 7 days.
30-day total: $9,240.00
Action:   Review EC2 utilization. Rightsizing or stopping idle
instances could reduce this cost by 20-40%.
#2  All services
Finding:  58% of spend ($10,683.92) has no team tag.
You cannot allocate what you cannot attribute.
Action:   Apply team tags to all resources.
╭─────────────────────────────────────────────╮
│  Want this monitored automatically?          │
│                                              │
│  fynC tracks your cloud and AI spend         │
│  continuously, alerts you when costs spike,  │
│  and attributes every dollar to a team.      │
│                                              │
│  → fync.io/early-access                      │
╰─────────────────────────────────────────────╯

## Required IAM permission

finops-scan only needs one permission:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ce:GetCostAndUsage"
      ],
      "Resource": "*"
    }
  ]
}
```

Create a read-only IAM user with this policy and pass the credentials to finops-scan.

## Installation

```bash
pip install finops-scan
```

## Usage

```bash
# Using flags
finops-scan \
  --access-key YOUR_ACCESS_KEY \
  --secret-key YOUR_SECRET_KEY \
  --region us-east-1 \
  --account-id my-company

# Using environment variables (recommended)
export AWS_ACCESS_KEY_ID=YOUR_ACCESS_KEY
export AWS_SECRET_ACCESS_KEY=YOUR_SECRET_KEY
finops-scan
```

## What it does NOT do

- Does not store any data
- Does not modify any AWS resources
- Does not require CUR or S3 setup
- Does not need root AWS credentials
- Does not send data anywhere except your terminal

## Built by fynC

finops-scan is the free CLI companion to
[fynC](https://fync.io) — a FinOps platform for cloud
and AI spend visibility.

fynC monitors your spend continuously, alerts you on anomalies,
attributes costs to teams automatically, and tracks AI/LLM spend
at the model level alongside cloud infrastructure costs.

[Join the early access list →](https://fync.io/early-access)

## License

MIT