# Local Docker

Phase 1 uses the root `docker-compose.yml` so the project can start with:

```bash
docker compose up
```

Services:

- `web` on http://localhost:3000
- `api` on http://localhost:8000
- `postgres` on localhost:5432
- `neo4j` browser on http://localhost:7474 and Bolt on localhost:7687
- `redis` on localhost:6379

Docker is not currently available on this machine, so Compose startup is scaffolded but not verified.

