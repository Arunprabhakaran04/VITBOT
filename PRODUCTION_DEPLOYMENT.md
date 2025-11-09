# VITBOT Production Deployment Guide

This guide shows how to deploy VITBOT in production without baking secrets into the Docker image.

## Prerequisites

1. Clean Docker image built without secrets:
   ```bash
   docker compose build
   ```

2. No `.env` file in the `backend/` directory (secrets passed at runtime)

## Production Deployment Options

### Option 1: Docker Run with Environment Variables

Replace the placeholder values with your actual credentials:

```bash
docker run --rm -p 8000:8000 \
  -e SECRET_KEY="your-secure-secret-key-here" \
  -e ALGORITHM="HS256" \
  -e ADMIN_ACCESS_TOKEN_EXPIRE_MINUTES=30 \
  -e USER_ACCESS_TOKEN_EXPIRE_MINUTES=1440 \
  -e DB_HOST="host.docker.internal" \
  -e DB_PORT=5432 \
  -e DB_NAME="VITBOT" \
  -e DB_USER="postgres" \
  -e DB_PASSWORD="your-db-password" \
  -e GROQ_API_KEY="your-groq-api-key" \
  -e HOST="0.0.0.0" \
  -e PORT=8000 \
  -e WORKERS=1 \
  vitbot-backend
```

### Option 2: Using Environment File (More Secure)

1. Create a secure environment file outside your codebase:
   ```bash
   # Create file: /secure/path/production.env
   SECRET_KEY=your-secure-secret-key-here
   ALGORITHM=HS256
   ADMIN_ACCESS_TOKEN_EXPIRE_MINUTES=30
   USER_ACCESS_TOKEN_EXPIRE_MINUTES=1440
   DB_HOST=host.docker.internal
   DB_PORT=5432
   DB_NAME=VITBOT
   DB_USER=postgres
   DB_PASSWORD=your-db-password
   GROQ_API_KEY=your-groq-api-key
   HOST=0.0.0.0
   PORT=8000
   WORKERS=1
   ```

2. Run with env file:
   ```bash
   docker run --rm -p 8000:8000 --env-file /secure/path/production.env vitbot-backend
   ```

### Option 3: Interactive Setup Script

Use this PowerShell script to prompt for credentials:

```powershell
# production-deploy.ps1
Write-Host "=== VITBOT Production Deployment ===" -ForegroundColor Green

# Prompt for secrets
$SECRET_KEY = Read-Host "Enter SECRET_KEY (generate a secure 64-char string)"
$DB_PASSWORD = Read-Host "Enter Database Password" -MaskInput
$GROQ_API_KEY = Read-Host "Enter GROQ API Key" -MaskInput

# Run container with provided secrets
docker run --rm -p 8000:8000 `
  -e SECRET_KEY="$SECRET_KEY" `
  -e ALGORITHM="HS256" `
  -e ADMIN_ACCESS_TOKEN_EXPIRE_MINUTES=30 `
  -e USER_ACCESS_TOKEN_EXPIRE_MINUTES=1440 `
  -e DB_HOST="host.docker.internal" `
  -e DB_PORT=5432 `
  -e DB_NAME="VITBOT" `
  -e DB_USER="postgres" `
  -e DB_PASSWORD="$DB_PASSWORD" `
  -e GROQ_API_KEY="$GROQ_API_KEY" `
  -e HOST="0.0.0.0" `
  -e PORT=8000 `
  -e WORKERS=1 `
  vitbot-backend

Write-Host "VITBOT Backend started at http://localhost:8000" -ForegroundColor Green
```

## Required Values to Replace

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | 64-character random string for JWT | `4b43fa41bb51ca5453d2ca718110b9780c591384a5368c660d8491069d13632e` |
| `DB_PASSWORD` | Your PostgreSQL password | `your-secure-db-password` |
| `GROQ_API_KEY` | Your GROQ API key | `gsk_...` |

## Security Best Practices

1. **Never commit secrets**: Keep production credentials out of version control
2. **Use strong SECRET_KEY**: Generate with `openssl rand -hex 32`
3. **Secure database**: Use strong passwords for database access
4. **Environment isolation**: Keep production env files in secure locations
5. **Rotate secrets**: Regularly update API keys and passwords

## Database Setup

If you need a separate database container:

```bash
# Start database first
docker run -d --name vitbot-prod-db \
  -e POSTGRES_DB=VITBOT \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=your-db-password \
  -p 5432:5432 \
  postgres:16-alpine

# Then start backend (update DB_HOST to localhost if running separate containers)
```

## Health Check

After deployment, verify the service:

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "VITBOT Backend",
  "version": "2.0.0",
  "database": "connected"
}
```

## Troubleshooting

1. **Connection errors**: Check if database is running and accessible
2. **Authentication errors**: Verify GROQ_API_KEY is valid
3. **Port conflicts**: Ensure port 8000 is available

## Cloud Deployment

For cloud platforms (AWS, GCP, Azure):

- Use their secret management services (AWS Secrets Manager, Azure Key Vault, etc.)
- Set environment variables through their container services
- Use managed databases when possible

---

This approach ensures no secrets are baked into your Docker image, making it safe to distribute.