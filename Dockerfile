FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

WORKDIR /app

RUN mkdir /data

COPY src ./src
COPY pyproject.toml .

EXPOSE 6379

CMD ["python", "src/pyredis/cli.py", "--host", "0.0.0.0", "--port", "6379", "--dir", "/data"]