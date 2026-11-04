FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# UID 1000 matches typical host bind-mount ownership for ./data writes.
RUN useradd --create-home --uid 1000 appuser

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY app ./app
# Sample data is bind-mounted at runtime via compose; keep a copy in the image
# so `docker run` without a mount still has placeholders.
COPY data ./data

RUN mkdir -p /app/data/output && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
