# VITBOT Backend — Docker Quickstart

This document explains how to build and run the VITBOT backend using Docker and Docker Compose. It assumes you are in the repository root and have Docker and Docker Compose installed.

## Quick steps (development)

1. Copy example env file and customize secrets (do not commit real secrets):

   cp backend/.env.example backend/.env

2. Build images and start services:

   docker compose build
   docker compose up -d

3. Verify the backend is running:

   # health endpoint
   curl http://localhost:8000/health

   # API docs
   open http://localhost:8000/docs

## Environment configuration

- The Compose file loads runtime env vars for the backend from `backend/.env` (via `env_file`).
- For local dev you can use the provided `backend/.env.example` as a starting point. Replace `SECRET_KEY`, database credentials and `GROQ_API_KEY` as needed.
- For production, prefer not to store secrets in plaintext files. Use Docker secrets, a secret manager, or injection through your orchestrator.

## Database migrations / creation

The repository contains a full DDL file at `backend/migrations/006_vitbot_full_setup.sql` that creates all tables, triggers and seeds an admin and test user.

To apply the migration to the Postgres service started by docker-compose, run:

```bash
chmod +x scripts/apply_sql_to_db.sh
./scripts/apply_sql_to_db.sh backend/migrations/006_vitbot_full_setup.sql
```

This script executes the SQL using `psql` inside the `db` service container. The SQL is idempotent (uses IF NOT EXISTS / ON CONFLICT guards) so re-running it is safe.

Verify the tables and seeded users:

```bash
docker compose exec db psql -U postgres -d VITBOT -c "\dt"
docker compose exec db psql -U postgres -d VITBOT -c "SELECT email, role FROM users;"
```

## Run without docker-compose (docker run)

Build the backend image:

```bash
docker build -t vitbot-backend -f backend/Dockerfile .
```

Run it while supplying envs at runtime (recommended):

```bash
docker run --rm -p 8000:8000 \
  -e SECRET_KEY=change-me \
  -e ALGORITHM=HS256 \
  -e ADMIN_ACCESS_TOKEN_EXPIRE_MINUTES=30 \
  -e USER_ACCESS_TOKEN_EXPIRE_MINUTES=1440 \
  -e DB_HOST=host.docker.internal -e DB_PORT=5432 -e DB_NAME=VITBOT -e DB_USER=postgres -e DB_PASSWORD=postgres \
  -e GROQ_API_KEY=your_key_if_needed \
  vitbot-backend
```

Note: use `host.docker.internal` on Docker Desktop to reach the host's Postgres from the container.

## Troubleshooting

- `docker compose up` failing: check `docker compose logs` to find errors (permission, build failures, port conflicts).
- Backend failing to connect to DB: ensure the `DB_*` env values point to the running Postgres. If using compose, `DB_HOST=db` is correct.
- If migrations fail, inspect the SQL output from the helper script. Use `docker compose exec db psql -U postgres -d VITBOT` to get an interactive shell.

## Security recommendations

- Do NOT commit `backend/.env` with real secrets. Add it to `.gitignore`.
- Use Docker secrets or a secrets manager for production credentials.

## Next steps (optional)

- Add a CI step to run the SQL migrations automatically against a test DB.
- Replace raw SQL with a migration tool (Alembic, Flyway) for incremental, versioned migrations.

If you'd like, I can add a `backend/README.md` entry to the top-level README or create a small script to generate a secure SECRET_KEY automatically.
