# LocalStack (local AWS)

The **`localstack/`** directory is **not committed**: create it locally and put **`localstack/.env`** there (copy from **`localstack.env.example`** in the repo root). The setup script lives in **`scripts/localstack_setup_resources.sh`** (tracked) and is what **`docker compose`** runs for **init-aws**.

The full dev stack (LocalStack + cafe + image + static `web/`) starts from the repo root:

```bash
docker compose up -d
```

## Prerequisites

- Docker (Compose v2)
- Repo-root **`.env`** (gitignored) with **`LOCALSTACK_AUTH_TOKEN`** for **`docker compose`** (Compose only auto-loads the project root `.env`, not `localstack/.env`).
- **`localstack/.env`**: `mkdir -p localstack && cp localstack.env.example localstack/.env` — used for **`source`** when running AWS CLI on your machine (`AWS_*`, bucket names). You can add other host-only vars here; keep the LocalStack auth token in **root `.env`** so the `localstack` container receives it.

## Health check

```bash
curl -s http://localhost:4566/_localstack/health | head -1
```

Logs: `docker compose logs -f localstack`

## Point your host shell at LocalStack

| Variable | Value |
|----------|--------|
| `AWS_ENDPOINT_URL` | `http://localhost:4566` |
| `AWS_ACCESS_KEY_ID` | `test` |
| `AWS_SECRET_ACCESS_KEY` | `test` |
| `AWS_DEFAULT_REGION` | `us-east-1` |

```bash
set -a && source localstack/.env && set +a
```

## Seed S3 / DynamoDB manually (optional)

After LocalStack is up:

```bash
bash scripts/localstack_setup_resources.sh
```

(`docker compose` already runs this inside **init-aws**.)

## Terraform against LocalStack

Point the AWS provider at the emulator (separate workspace recommended):

```hcl
provider "aws" {
  region                      = "us-east-1"
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true

  endpoints {
    apigateway = "http://localhost:4566"
    dynamodb   = "http://localhost:4566"
    lambda     = "http://localhost:4566"
    s3         = "http://localhost:4566"
  }
}
```

## Stop

```bash
docker compose down
```

Persistence: see [LocalStack configuration](https://docs.localstack.cloud/references/configuration/) (`PERSISTENCE=0` in compose by default).
