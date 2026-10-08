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

- **Top services by spend**: with 30-day trend (increasing/decreasing/stable)
- **Waste opportunities**: ranked by estimated impact, with specific actions
- **Tag coverage score**: what % of your spend has team attribution
- **Estimated savings**: conservative 20% estimate of actionable waste

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
[fynC](https://fync-1.onrender.com): a FinOps platform for cloud
and AI spend visibility.

fynC monitors your spend continuously, alerts you on anomalies,
attributes costs to teams automatically, and tracks AI/LLM spend
at the model level alongside cloud infrastructure costs.

[Join the early access list →](https://fync-1.onrender.com)

## License

MIT