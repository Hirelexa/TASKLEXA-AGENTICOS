# Vultr Deployment Architecture

Status: Phase 0 proposal. No paid infrastructure should be provisioned without explicit approval.

## Target Runtime

Tasklexa should deploy to Vultr Kubernetes Engine after the local Docker Compose MVP works.

Verified docs:

- Vultr supports Kubernetes through self-managed clusters or managed Vultr Kubernetes Engine.
- VKE cluster configuration can be downloaded for `kubectl` access from the Vultr console or retrieved through CLI/API workflows.

Sources:

- https://docs.vultr.com/support/products/vke/can-i-run-kubernetes-on-vultr
- https://docs.vultr.com/products/compute/kubernetes/management/connection
- https://docs.vultr.com/reference/vultr-cli/kubernetes/config

## Proposed Kubernetes Workloads

- `web` deployment and service
- `api` deployment and service
- `orchestrator` deployment
- `agent-worker` deployment
- `redis` deployment or managed equivalent
- PostgreSQL deployment only for non-production or demo environments unless managed database strategy is approved
- Neo4j deployment only for non-production or demo environments unless managed graph database strategy is approved

## External Providers

The cluster will communicate outbound to:

- Band
- OpenRouter
- Similarweb

No external provider SDK object should leak into core orchestration types.

## Ingress and Networking

Phase 15 should define:

- Ingress controller or Vultr LoadBalancer service
- TLS certificate strategy
- DNS records
- Allowed CORS origins
- Private service networking for databases where available
- Egress policies for provider APIs where feasible

## Secrets

Store provider credentials in Kubernetes Secrets or an approved external secret manager:

- `OPENROUTER_API_KEY`
- `BAND_AGENT_KEY`
- `BAND_USER_KEY`
- `SIMILARWEB_API_KEY`
- `POSTGRES_PASSWORD`
- `NEO4J_PASSWORD`
- `REDIS_PASSWORD`

Never bake secrets into images, manifests, ConfigMaps, or frontend bundles.

## Observability

Kubernetes deployment should expose:

- Container logs with structured JSON.
- Readiness and liveness probes.
- `mission_id`, `task_id`, and `agent_execution_id` correlation fields in backend and worker logs.
- Provider call metrics with latency, success/failure, and error category.

## Rollout Sequence

1. Verify local Docker Compose MVP.
2. Build container images locally.
3. Push images to approved registry.
4. Apply namespace, ConfigMaps, and Secrets.
5. Deploy databases according to approved strategy.
6. Deploy API and workers.
7. Deploy web.
8. Configure ingress/TLS/DNS.
9. Run smoke tests.
10. Run live integration tests only with approved credentials.

## Blockers Before Deployment

- Vultr account and API token.
- Cluster region and node-pool sizing.
- Registry selection.
- Database deployment strategy.
- TLS and DNS ownership.
- Explicit authorization to create billable infrastructure.
