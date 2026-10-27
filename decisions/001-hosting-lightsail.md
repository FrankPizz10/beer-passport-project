# 001: Hosting is a single Lightsail instance

- **Date:** 2026-10-27
- **Status:** accepted
- **Closes:** decision D1 (hosting)

## Context

The original backend (ECS, load balancer, self-managed MySQL) died when AWS credits ran out; the load balancer alone cost about $17/month. The relaunch constraints are roughly $0-15/month infrastructure, one operator, and a catalog-scale workload. The plan source is "BeerPassport Relaunch: Cost-First AWS Plan" and the approved "BeerPassport Relaunch: Deployment Proposal" (Google Drive, Jarvis/BeerPassport).

## Options considered

- **Lightsail single instance** ($5 tier: 1 GB RAM, 2 vCPU, 40 GB SSD, static IP included) running Docker with Postgres and the Express API; snapshots about $1/month; S3 + CloudFront for images; one Route 53 zone. Total about $8/month.
- **Serverless AWS** (Lambda + Aurora Serverless / RDS): higher cost at this scale, slower to deploy and iterate, more moving parts for one operator.
- **Plain EC2:** the same single-box shape as Lightsail with worse billing predictability and more setup.
- **Managed container platforms (ECS/Fargate, etc.):** recreates the cost structure that killed the original deployment.

## Decision

Lightsail, one instance, Docker Compose with Postgres and the API as separate containers, the database on a persistent volume independent of the API container (TD-5's intent, at single-box scale). The database port is never exposed to the internet; the API is the only public surface, behind HTTPS.

## Rationale

Cheapest option that is boring and predictable. Containers keep the lift to a bigger platform possible later without committing to it now. Frank can be talked out of Lightsail; nobody produced a cheaper credible alternative, so it stands.

## Consequences and affected repositories

- Single point of failure, accepted; snapshots plus a written restore procedure (P0.3, P0.5) are the mitigation. First upgrade is the $10 Lightsail tier.
- Administration is SSH with a dedicated `jarvis` user, key-only auth, and Frank's approval for state-changing commands.
- Affects `beer-passport-server` deployment artifacts (Docker) and this hub's operations docs.
