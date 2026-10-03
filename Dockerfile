# ---- Stage 1: build the package into a wheel ----
FROM python:3.12-slim AS builder

WORKDIR /build

RUN pip install --no-cache-dir build

COPY pyproject.toml README.md ./
COPY src ./src

RUN python -m build --wheel --outdir /dist


# ---- Stage 2: small runtime image ----
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Run as a non-root user
RUN useradd --create-home --uid 1000 pyredis \
    && mkdir /data \
    && chown pyredis:pyredis /data

COPY --from=builder /dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl && rm /tmp/*.whl

USER pyredis
WORKDIR /data

EXPOSE 6379

CMD ["pyredis", "--host", "0.0.0.0", "--port", "6379", "--dir", "/data"]