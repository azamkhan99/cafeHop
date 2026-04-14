# Auth service (uploadAuth)

JWT-based auth Lambda: POST with `{"password": "..."}`; returns `{"token": "..."}` if password matches.

**Deploy:** Terraform provisions an **ECR repository** and a **container-image** Lambda (`package_type = Image`). Dependencies come from the root **`pyproject.toml`** dependency group **`lambda-auth`** (PyJWT).

From repo root, build and push (after ECR exists):

```bash
./scripts/docker_push_lambda_auth.sh <tag>
```

Then set `auth_lambda_image_tag` (or `TF_VAR_auth_lambda_image_tag`) to the same tag and `terraform apply`.
