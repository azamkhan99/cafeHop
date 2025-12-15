import json
import jwt
import os
import time

SECRET = os.environ.get("JWT_SECRET", "supersecret")  # store in Lambda env variable

def lambda_handler(event, context):
    body = json.loads(event.get("body", "{}"))
    password = body.get("password", "")

    # Only allow if password matches your private password
    if password != "coffee":
        return {
            "statusCode": 401,
            "body": json.dumps({"error": "Unauthorized"})
        }

    # Generate JWT valid for 5 minutes
    payload = {
        "user": "trusted",
        "exp": int(time.time()) + 300
    }
    token = jwt.encode(payload, SECRET, algorithm="HS256")

    return {
        "statusCode": 200,
        "headers": {"Access-Control-Allow-Origin": "https://azamkhan99.github.io"},
        "body": json.dumps({"token": token})
    }

