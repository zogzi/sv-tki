# syntax=docker/dockerfile:1
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml ./
COPY src ./src
COPY data ./data
RUN --mount=type=secret,id=proxy_ca \
    if [ -f /run/secrets/proxy_ca ]; then export PIP_CERT=/run/secrets/proxy_ca; fi; \
    pip install --no-cache-dir -e . && chmod -R a+rX /app/src /app/data /app/pyproject.toml && useradd --uid 10001 --create-home bot && mkdir runtime && chown bot:bot runtime
USER bot
CMD ["python", "-m", "svetki.bot"]
