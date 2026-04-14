# AWS Lambda container image (auth). Build from repo root:
#   docker build -f services/auth/Dockerfile -t <account>.dkr.ecr.<region>.amazonaws.com/<repo>:<tag> .
FROM public.ecr.aws/lambda/python:3.12

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock /tmp/dep/
WORKDIR /tmp/dep
RUN uv export --frozen --only-group lambda-auth -o /tmp/req.txt \
    && uv pip install --system --no-cache -r /tmp/req.txt \
    && rm -rf /tmp/dep /tmp/req.txt

WORKDIR /var/task
COPY services/auth/lambda_function.py /var/task/

CMD ["lambda_function.lambda_handler"]
