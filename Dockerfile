# syntax=docker/dockerfile:1
# -----------------------------------------------------------------------
# SeagentHub — AWS Lambda Web Adapter container image
#
# The Lambda Web Adapter sidecar (/opt/extensions/lambda-adapter) intercepts
# Lambda invocations and forwards them as plain HTTP requests to the FastMCP
# server running on PORT 8080, then streams the response back to the caller.
# -----------------------------------------------------------------------

FROM public.ecr.aws/docker/library/python:3.12-slim

# Inject the Lambda Web Adapter binary from its public ECR image
COPY --from=public.ecr.aws/awsguru/aws-lambda-adapter:0.8.4 \
     /lambda-adapter /opt/extensions/lambda-adapter

WORKDIR /app

# Install Python dependencies first (layer-cache friendly)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source and prompt/template assets
COPY src/       ./src/
COPY templates/ ./templates/
COPY prompts/   ./prompts/

# Make src importable without a package install step
ENV PYTHONPATH=/app

# -----------------------------------------------------------------------
# Lambda Web Adapter settings
# AWS_LWA_PORT          — port the adapter forwards HTTP traffic to
# AWS_LWA_READINESS_CHECK_PROTOCOL=tcp — check port open, not HTTP 200
#   (FastMCP's /mcp path requires POST; a GET returns 405, not 200)
# AWS_LWA_ASYNC_INIT=true — start accepting traffic before init completes,
#   avoiding the 10 s cold-start timeout during LangGraph graph compilation
# -----------------------------------------------------------------------
ENV PORT=8080
ENV AWS_LWA_PORT=8080
ENV AWS_LWA_READINESS_CHECK_PROTOCOL=tcp
ENV AWS_LWA_ASYNC_INIT=true
ENV PYTHONUNBUFFERED=1

EXPOSE 8080

CMD ["python", "-m", "src.main", "--transport=streamable-http", "--port=8080"]
