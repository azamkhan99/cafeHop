import json
import jwt
import os
import time

SECRET = os.environ.get("JWT_SECRET", "supersecret")  # store in Lambda env variable

# CORS: API Gateway HTTP API cors_configuration handles preflight; these headers on responses
ALLOWED_ORIGINS = ("https://azamkhan99.github.io", "http://127.0.0.1:3000")


def _cors_headers(event):
    origin = (event.get("headers") or {}).get("origin") or (event.get("headers") or {}).get("Origin")
    allow_origin = origin if origin in ALLOWED_ORIGINS else ALLOWED_ORIGINS[0]
    return {
        "Access-Control-Allow-Origin": allow_origin,
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "content-type, authorization",
    }


def lambda_handler(event, context):
    headers = _cors_headers(event)
    body = json.loads(event.get("body", "{}"))
    password = body.get("password", "")

    # Only allow if password matches your private password
    if password != "coffee":
        return {
            "statusCode": 401,
            "headers": headers,
            "body": json.dumps({"error": "Unauthorized"}),
        }

    # Generate JWT valid for 5 minutes
    payload = {
        "user": "trusted",
        "exp": int(time.time()) + 300,
    }
    token = jwt.encode(payload, SECRET, algorithm="HS256")

    return {
        "statusCode": 200,
        "headers": headers,
        "body": json.dumps({"token": token}),
    }
