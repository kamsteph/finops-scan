# finops-scan

**Scan your AWS account for cloud waste in 60 seconds.**

Free, open source, read-only. No data stored. No resources modified.

```bash
pip install finops-scan
finops-scan --demo        # see a sample report, no AWS account needed
finops-scan               # scan your own account (see credentials below)
```

---

## What it does

finops-scan connects to your AWS Cost Explorer API (read-only) and produces a ranked waste report in your terminal:

- **Top services by spend** — with 30-day trend (increasing/decreasing/stable)
- **Waste opportunities** — ranked by estimated impact, with specific actions
- **Tag coverage score** — what % of your spend has team attribution
- **Estimated savings** — conservative 20% estimate of actionable waste

It works at the service level (for example "EC2 spend is up 40%"). It does not list individual idle resources by ID.

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

### Option 1: AWS profile (safest, no keys typed)

```bash
aws configure --profile finops

# macOS / Linux
AWS_PROFILE=finops finops-scan

# Windows PowerShell
$env:AWS_PROFILE="finops"
finops-scan
```

### Option 2: environment variables

```bash
# macOS / Linux (bash, zsh)
export AWS_ACCESS_KEY_ID=YOUR_ACCESS_KEY
export AWS_SECRET_ACCESS_KEY=YOUR_SECRET_KEY
finops-scan
```

```powershell
# Windows PowerShell
$env:AWS_ACCESS_KEY_ID="YOUR_ACCESS_KEY"
$env:AWS_SECRET_ACCESS_KEY="YOUR_SECRET_KEY"
finops-scan
```

### Option 3: flags

```bash
finops-scan \
  --access-key YOUR_ACCESS_KEY \
  --secret-key YOUR_SECRET_KEY \
  --region us-east-1 \
  --account-id my-company
```

Flags can end up in your shell history, so prefer options 1 or 2.

### Try it without an AWS account

```bash
finops-scan --demo
```

Runs the full report on built-in sample data. Nothing is sent to AWS.

## Cost of a scan

AWS bills Cost Explorer API requests (about $0.01 per request at the time of writing; check the current AWS pricing). A scan makes only a few requests, so it should cost a few cents at most.

## Good to know

- **Tag coverage** looks for a `team` tag. The tag key must be activated as a cost allocation tag in the AWS Billing console, which can take up to 24 hours. Until then, all spend counts as untagged.
- **New accounts:** Cost Explorer must be enabled once in the Billing console, and data can take up to 24 hours to appear. An account with no spend reports "No cost data found".

## Troubleshooting

| Error | Meaning | Fix |
|---|---|---|
| `UnrecognizedClientException` ("security token is invalid") | AWS does not recognize the credentials | Re-copy the access key and secret key; check the key is active in IAM |
| `AccessDeniedException` ("not authorized to perform ce:GetCostAndUsage") | Credentials are valid but the permission is missing | Attach the policy shown above to the IAM user |
| "No AWS credentials found" | Nothing to authenticate with | Set `AWS_PROFILE`, set the environment variables, or pass the flags |
| "No cost data found" | No spend above $0.001 in the last 30 days | Normal for new or free-tier accounts; try `--demo` |

## What it does NOT do

- Does not store any data
- Does not modify any AWS resources
- Does not require CUR or S3 setup
- Does not need root AWS credentials
- Does not send data anywhere except your terminal

## Built by fynC

finops-scan is the free CLI companion to
[fynC](https://fync-1.onrender.com) — a FinOps platform for cloud
and AI spend visibility.

fynC monitors your spend continuously, alerts you on anomalies,
attributes costs to teams automatically, and tracks AI/LLM spend
at the model level alongside cloud infrastructure costs.

[Join the early access list →](https://fync-1.onrender.com)

## License

MIT