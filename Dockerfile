FROM --platform=linux/amd64 python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL -o global-bundle.pem \
    https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.core.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
