FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# -------------------------------
# LibreOffice + fuentes
# -------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice \
    libreoffice-calc \
    fonts-dejavu \
    fonts-liberation \
    fonts-freefont-ttf \
    && rm -rf /var/lib/apt/lists/*

# -------------------------------
# Python deps
# -------------------------------
COPY backend_api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# -------------------------------
# Código
# -------------------------------
COPY backend_api /app

# -------------------------------
# Run FastAPI
# -------------------------------
CMD ["bash", "-lc", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
