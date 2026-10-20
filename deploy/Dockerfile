FROM mcr.microsoft.com/playwright/python:v1.64.0-noble@sha256:684df257a1fa0ef3fa288239819984008f560e8f8db5b635ee9e2a50cbcd2e23
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HOME=/tmp XDG_CONFIG_HOME=/tmp/config XDG_CACHE_HOME=/tmp/cache
WORKDIR /app
COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt && useradd --uid 10001 --create-home chickadee && mkdir /results && chown 10001:10001 /results
COPY chickadee ./chickadee
COPY schemas/result.schema.json ./schemas/result.schema.json
COPY profiles ./profiles
USER 10001:10001
ENTRYPOINT ["python", "-m", "chickadee"]
