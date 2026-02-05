FROM python:3.11

# -------------------------------
# Variables de entorno
# -------------------------------
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# -------------------------------
# Dependencias del sistema (PDF)
# -------------------------------
RUN apt-get update && apt-get install -y \
    libreoffice-core \
    libreoffice-calc \
    fonts-dejavu \
    fonts-liberation \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# -------------------------------
# Directorio de trabajo
# -------------------------------
WORKDIR /app

# -------------------------------
# Dependencias Python
# -------------------------------
COPY backend_api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# -------------------------------
# Código
# -------------------------------
COPY backend_api/ .

# -------------------------------
# Puerto
# -------------------------------
EXPOSE 8000

# -------------------------------
# Ejecutar FastAPI
# -------------------------------
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
