# CafeHop

Serverless cafe photos: static gallery on GitHub Pages (`web/`), S3 uploads, optional **DynamoDB** cafe list, and small **Lambda** APIs (auth JWT, image presign/thumbnails, legacy code under `legacy/lambda/`).

## Layout

```
cafeHop/
├── web/                 # Static site: index.html, map.html, add.html, api-config*.js
├── legacy/lambda/       # Legacy monolith Lambdas + utils (presign, elo, sharecard, …)
├── assets/templates/    # SVG templates (e.g. receipt cards for sharecard flow)
├── data/
│   ├── gtfs_subway/     # Raw GTFS excerpts (optional / offline use)
│   └── cafes.sample.json # Example cafe list shape (real data lives in S3 / DynamoDB)
├── terraform/           # AWS: auth + optional image + optional cafe Lambdas, DynamoDB cafes
├── localstack.env.example # Template → copy to gitignored localstack/.env (see docs/localstack.md)
├── scripts/             # docker_push_lambda_*.sh, localstack_setup_resources.sh, dev_local.sh, …
├── services/
│   ├── auth/            # uploadAuth container (JWT)
│   ├── image/           # presigned-url + process (FastAPI + Mangum)
│   └── cafe/            # FastAPI cafe API (Docker / deploy separately if used)
├── pyproject.toml       # uv + [dependency-groups]
└── docker-compose.yml   # Local cafe + image + LocalStack; static HTTP root is ./web
```

**GitHub Pages:** Built-in “deploy from branch” only supports **`/`** or **`/docs`**, not **`/web`**. Options: (1) add a small Action that uploads **`web/`** as the site root (e.g. to `gh-pages`), (2) set Pages to **`/docs`** and move static assets into `docs/` (keep Terraform docs elsewhere or rename), or (3) keep a separate publishing step that copies `web/*` to the branch root you use for Pages.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (see `.python-version`)
- AWS CLI + Terraform for cloud deploys
- Docker for Lambda images and `docker compose`

## AWS deploy (Terraform + ECR)

1. `cd terraform && terraform init && terraform apply` (set `TF_VAR_jwt_secret`; see `docs/terraform-import-auth.md` if importing).

2. **Auth image:** `./scripts/docker_push_lambda_auth.sh <tag>` then `terraform apply -var="auth_lambda_image_tag=<tag>"`.

3. **Image API (optional):** `TF_VAR_enable_image_terraform=true`, then follow `docs/terraform-import-image.md`.

4. Put outputs into **`web/api-config.js`** (`authUrl`, `imageUrl`, …).

## Local dev

```bash
docker compose up --build
```

Open **http://127.0.0.1:3000/add.html** (static root is `web/`). APIs: cafe `8000`, image `8002`, LocalStack `4566`. For compose, point **`web/api-config.js`** at those URLs and the LocalStack bucket (see `docker-compose.yml` comments), or keep a gitignored local copy. LocalStack: **`docs/localstack.md`** (create **`localstack/.env`** from **`localstack.env.example`**; that folder is gitignored).

## Python env (repo root)

```bash
uv sync
uv run python -m pytest
```

Run `uv lock` after dependency changes.

## Legacy zip layers

The **`function-legacy`** dependency group is for a **manual** `pip install --target package/python` zip layer. **Cafe API** on AWS: `scripts/docker_push_lambda_cafe.sh` + `module.cafe` (see `docs/terraform-import-cafe.md`).

## Docs

- `docs/terraform-import-auth.md`, `docs/terraform-import-image.md`, `docs/terraform-import-cafe.md`
- `docs/localstack.md` — LocalStack + `localstack/.env` (from `localstack.env.example`)
