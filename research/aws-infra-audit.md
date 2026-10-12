# AWS Infrastructure Audit

- **Date:** October 11, 2026
- **Account:** Frank_Pizz210 (149290600858)
- **Method:** Read-only audit via the AWS console as IAM user `agent-read-only` (`ReadOnlyAccess` plus billing read permissions). Nothing was created, modified, or deleted. Cost Explorer was not accessible to the auditor user (access denied), so historical per-service spend could not be retrieved; all billing figures below come from the Budgets table.
- **Status:** Starting point for the D1 hosting decision and the audit checklist, not a substitute for ongoing monitoring.

## Headline findings

1. **The BeerPassport backend is fully shut down.** No EC2 instances, no RDS databases, no RDS snapshots, no Lambda functions anywhere. The ECS cluster `beer-passport-cluster` (us-east-1) exists but runs 0 services, 0 tasks, 0 container instances. The historical ~$50/month spend is gone with it.
2. **Current spend is about $2/month.** Month-to-date $1.72, forecasted $2.12, against the existing $50/month budget ("My Monthly Cost Budget", healthy).
3. **The production MySQL database appears to be gone.** No RDS instances or snapshots exist in us-east-1 or us-east-2. Console search surfaced names `beerpassport-db-snapshot` and `beerpassport-rds-snapshot-final`, but they appear in no snapshot list and could not be verified (likely stale search-index entries). If the catalog data only lived in that database, it may be unrecoverable from AWS. Mitigation: the server repo contains CSV seed data (`data/beers.csv` 4.1 MB, plus breweries/categories/styles), so the catalog can be reseeded. The Secrets Manager secret `prod/beerpassport/backend` (us-east-1, created Oct 2023) reportedly holds the old MySQL credentials; it was not opened.
4. **Security gaps worth fixing:** no CloudTrail trail exists (no API audit logging at all); IAM user `frank-pizz-cli` has two active access keys aged 995 and 1425 days that have never been used; no MFA on either IAM user (root does have MFA); all three S3 buckets are publicly readable with Block Public Access off.
5. **Orphaned/stale resources:** CloudFront distribution E28SQQ8C7G4XBJ is still Enabled but points at a nonexistent bucket (`capstonevideoclips`); security group `lb-sg` allows 0.0.0.0/0 on ports 80/443 with no load balancer in place; the idle ECS cluster and two task definitions remain; an `EFS-SG` security group exists, implying an EFS file system that was not verified (EFS was outside the checked scope).

## Billing (verified via Cost Explorer and Billing invoices, October 11, 2026)

**Last 12 months** (Oct 2025 – Sep 2026, Cost Explorer): **$19.32 total, $1.61/month average.** Monthly: Oct 2025–Jan 2026 $0.00 each (service still running; likely credit-covered), Feb 2026 $4.28 (shutdown month), Mar–Sep 2026 ~$2.14–2.19 each. Top services: Route 53 $12.14, Secrets Manager $3.20, ECS $1.91 (Feb 2026 only), RDS $1.41 (residual ~$0.18/mo, cause unverified), EFS $0.25. Month-to-date Oct 2026: $1.72; forecasted $2.12.

**Historical invoices** (Billing → Bills, back to Nov 2022; Cost Explorer only retains 12 months):

| Month | Total | Top drivers |
|---|---|---|
| Nov 2022 | $1.00 | Route 53 $1.00 |
| Oct 2023 | $8.74 | EFS $4.86, EC2 $2.61, Route 53 $1.01, ECS $0.26 |
| Nov 2023 | $4.59 | EFS $1.63, Route 53 $1.53, ECS $1.23 |
| Dec 2023 | $18.75 | ELB $16.74, Route 53 $1.50 |
| Jan 2024 | $28.46 | ELB $16.74, ECS $6.48, WAF $2.89, Route 53 $1.50 |
| Feb 2024 – Jan 2025 | ~$37–39/mo | Region-spend proxy; bill detail UI would not render for these months |

**Correction to the plan's "~$50/month" figure:** the $50 was the "My Monthly Cost Budget" threshold, not actual spend. No invoiced or proxied month reached $50; the observed peak is ~$39–40. The ramp's cost drivers were the classic ELB (~$16.74/mo, nearly half the bill), ECS Fargate, and WAF. Feb 2024 shows a billing correction (invoice issued and reversed).

**Takeaway for D1:** the single most expensive component of the old stack was the classic load balancer. At this scale the relaunch does not need a dedicated LB. Current baseline ~$2/mo is dominated by Route 53 hosted zones ($1.50/mo).

## Resource inventory

### Compute and database
- EC2 instances: 0 (us-east-1 and us-east-2).
- RDS: 0 instances, 0 clusters, 0 snapshots (all snapshot types) in both regions.
- ECS: 1 cluster `beer-passport-cluster` (us-east-1), 0 services / 0 tasks / 0 container instances. Two ACTIVE task definitions: `beer-passport-task-def1`, `beer-passport-task-def2`. Nothing in us-east-2.
- EKS: 0 clusters. Lambda: 0 functions. Load balancers: none.

### Storage and CDN
- S3 (us-east-1), 3 buckets, all Block Public Access OFF with public-read bucket policies:
  - `beerpassportadmin` (created Jan 2024): BeerPassport admin site. Also grants CloudFront OAI E2RFY0B8O4L8VB.
  - `frank-pizz-chess-bucket` (created Nov 2022): 10 objects, static site.
  - `frank-pizz-portfolio-website` (created Dec 2023): 12 objects, includes `BeerPassportAndroid_1_0_1.apk` (64.8 MB, Apr 2024).
- CloudFront, 4 distributions, all Enabled:
  - E2PPA2RPT75J9Q (`d2l6nne29zsyai.cloudfront.net`): origin `beerpassportadmin` website endpoint. The admin site distribution.
  - E28SQQ8C7G4XBJ (`d349i6nqyoufg1.cloudfront.net`): origin `capstonevideoclips.s3.us-east-1.amazonaws.com`, a bucket that does not exist in this account. Stale/orphaned.
  - ELYXVUTEASII9 (`frankpizzella.com`): origin `frank-pizz-portfolio-website`. Portfolio site.
  - E5CC3VH5KDRFP (`chess.frankpizzella.com`): origin `frank-pizz-chess-bucket`. Chess site.

### Secrets
- Secrets Manager (us-east-1): 1 secret, `prod/beerpassport/backend`, described as containing Firebase and MySQL credentials. Last retrieved Feb 2026. Not opened during the audit.

## Security posture

- IAM users: `agent-read-only` (created Oct 11, 2026 for this audit; console access on; no MFA) and `frank-pizz-cli` (created Nov 2022; console access off; no MFA; 2 active access keys, aged 995 and 1425 days, never used).
- Root: MFA enabled.
- S3: all 3 buckets publicly readable (consistent with static-site hosting; confirm this is intended for each).
- Security groups with 0.0.0.0/0 ingress: only `lb-sg` (us-east-1), ports 80/443 open to the world, with no load balancer attached. Others are tightly scoped (RDS/MySQL 3306 from single /32 IPs, ECS 3000 from lb-sg, EFS NFS from ecs-sg only).
- CloudTrail: no trails in us-east-1 or us-east-2. There is currently no API activity logging.

## BeerPassport mapping

| Known component | State |
|---|---|
| Express API (Docker, port 3000) | Not running. No EC2, ECS idle. |
| MySQL database | Not running. No RDS instances or snapshots. |
| S3 `beerpassportadmin` | Exists, publicly readable. |
| CloudFront E2PPA2RPT75J9Q | Enabled, serves the admin bucket. |
| Secrets Manager `prod/beerpassport/backend` | Exists, not opened. |
| Firebase project `beerpassport-b31d8` | Not AWS; out of scope. |

## Limitations

- Cost Explorer denied access, so historical spend by service is unverified; the $50/month figure remains a plan-stated historical baseline, not a measured one.
- RDS snapshot names from console search could not be verified as real or deleted.
- Possible EFS file system (implied by `EFS-SG`) was not inventoried.
- Only us-east-1 and us-east-2 were inventoried for regional resources; other regions were not checked.

## Recommendations

1. **Verify the billing policy** on `agent-read-only` (or check Cost Explorer as root) to retrieve the 12-month per-service history; useful context for the D1 hosting decision.
2. **Delete the two unused `frank-pizz-cli` access keys** (995 and 1425 days old, never used). They are a standing credential risk with zero utility.
3. **Enable CloudTrail** with logging to S3. It is cheap and there is currently no audit trail of API activity.
4. **Decide the fate of the auditor user**: keep `agent-read-only` for future audits or delete it now that this pass is done.
5. **Clean up orphans** (after confirming nothing references them): the stale CloudFront distribution E28SQQ8C7G4XBJ, the idle ECS cluster and task definitions, the world-open `lb-sg` rules, and verify whether the implied EFS file system still exists.
6. **Confirm the S3 public-read posture is intended** for all three buckets.
7. **Treat the old production database as lost** unless a backup surfaces elsewhere; plan the relaunch around reseeding from the repo CSVs plus a fresh managed database (feeds D2).
