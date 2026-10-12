# AWS Forensic Audit: Historical BeerPassport Infrastructure

- **Date:** October 11, 2026
- **Account:** Frank_Pizz210 (149290600858)
- **Method:** Read-only console audit as IAM user `agent-read-only`. Task definitions, target groups, IAM roles, log groups, Route53, and ACM were inspected. Secret and env var VALUES were never opened or recorded; only names.
- **Timing anchor:** Last service activity February 24, 2026 (about 8 months ago), consistent with shutdown within the last year.

## Reconstructed architecture (as it ran)

DNS `beer-passport.com` → classic ELB `beer-passport-ld` (now deleted; a stale A-record alias remains) → target group `beer-passport-tg-1` (HTTP:80, health-check override port 3000, now 0 targets) → ECS Fargate service `beer-passport-app-service` in cluster `beer-passport-cluster` (now 0 tasks) → task definition `beer-passport-task-def1:55` with two containers:

- `express-app`: image `frankpizz10/beer-passport-image:latest` (Docker Hub), port 3000, env var names `PORT`, `SECRET_NAME`, `ENVIRONMENT` (secret `prod/beerpassport/backend`).
- `mysql-db`: image `mysql:latest` (Docker Hub), port 3306, MySQL data stored on EFS volume `fs-09de5e0a09bc3ddff` mounted at `/var/lib/mysql`, env var names `MYSQL_DATABASE`, `MYSQL_ROOT_PASSWORD` (plaintext env vars, a security issue).

Task: Fargate/awsvpc, 0.25 vCPU, 1024 MiB. Logs to CloudWatch group `/ecs/beer-passport-task-def1` (77 MB retained, retention "Never expire", last events Feb 24, 2026). A second task definition (`beer-passport-task-def2`, Sep 2024, express-app only, no MySQL) appears to have been a brief test of running the API without the sidecar database.

## Key implications

1. **The database was never RDS.** MySQL ran as a sidecar container in the same ECS task, with data on EFS. The audit finding "database lifecycle coupled to API compute" is confirmed in this specific form: scaling or replacing the task risked the database, and deleting the service orphaned the data volume question.
2. **The MySQL data may still exist on EFS.** Whether file system `fs-09de5e0a09bc3ddff` survives is being verified separately. If it does, the catalog and user data could be recoverable. If it was deleted with no backup, treat the data as lost and reseed from the repo CSVs.
3. **TLS is broken.** The ACM certificate for `beer-passport.com` is EXPIRED and not in use. The DNS A-record still points at the deleted load balancer, so the domain is dead.
4. **Frontend is on Netlify and still live:** `admin.beer-passport.com` and `web.beer-passport.com` are CNAMEs to Netlify sites.
5. **IAM was overly broad:** `ecsTaskExecutionRole` served as both task execution role and task role, with `secretsmanager:GetSecretValue` on ALL secrets in the account.
6. **Logs survive:** 77 MB of historical app/DB logs with no expiration. Useful for diagnosing the old runtime if needed.

## What was checked and not found

- ECR: no private repositories; images came from Docker Hub.
- AWS Config: never enabled; no configuration history for deleted resources.
- CloudTrail: no trails; no API activity history.
- Cost Explorer: access denied for the auditor user; historical per-service spend still unverified.

## Still open

- Exact earliest log timestamp in `/ecs/beer-passport-task-def1` (console pagination refused).
- Target-group health-check path (not visible in console).
- Cause of the small residual RDS charge (~$0.18/mo with zero instances).
- The plan's historical ~$50/month figure predates the 12-month Cost Explorer window and remains unverified.

## EFS verdict (verified October 11, 2026): the MySQL data is recoverable

File system `fs-09de5e0a09bc3ddff` (name `mysql-efs2`, us-east-1) still exists, state Available, with 244.54 MiB of data (the MySQL datadir the ECS container mounted at `/var/lib/mysql`). All data has aged into the Archive tier (untouched 90+ days, consistent with the Feb 2026 shutdown). Two mount targets are Available in the original VPC. Automatic backups are enabled: 35 daily recovery points in `aws/efs/automatic-backup-vault`, 35-day retention, covering Oct 2 through Oct 11, 2026. Recovery routes: launch a task/instance in the VPC with EFS access via the existing mount targets, or restore any recovery point into a new file system. Nothing was mounted or read during the audit.
