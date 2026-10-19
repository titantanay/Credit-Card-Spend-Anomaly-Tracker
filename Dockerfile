# Local risk-monitoring dashboard image.
# Analytical data is mounted at runtime (see docker-compose.yml).
# Ollama is not bundled — use host Ollama or fallback narration.
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DUCKDB_PATH=/app/database/spend_monitor.duckdb \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY config.py .
COPY ai_narration ./ai_narration
COPY kpi ./kpi
COPY dashboard ./dashboard

RUN mkdir -p /app/database /app/data/raw /app/data/processed

EXPOSE 8501

CMD ["streamlit", "run", "dashboard/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
