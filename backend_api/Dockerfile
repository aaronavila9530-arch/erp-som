FROM python:3.11-slim

# -------------------------------
# Variables de entorno
# -------------------------------
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# -------------------------------
# Instalar dependencias del sistema
# -------------------------------
RUN apt-get update && apt-get install -y \
    libreoffice \
    libreoffice-writer \
    fonts-dejavu \
    fonts-liberation \
    fonts-freefont-ttf \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# -------------------------------
# Directorio de trabajo
# -------------------------------
WORKDIR /app

# -------------------------------
# Instalar dependencias Python
# -------------------------------
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# -------------------------------
# Copiar el código
# -------------------------------
COPY . .

# -------------------------------
# Puerto FastAPI
# -------------------------------
EXPOSE 8000

# -------------------------------
# Ejecutar la app
# -------------------------------
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
