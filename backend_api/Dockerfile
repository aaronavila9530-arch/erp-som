FROM python:3.11

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# -------------------------------
# Dependencias del sistema
# -------------------------------
RUN apt-get update && apt-get install -y \
    libreoffice-calc \
    libreoffice-writer \
    fonts-dejavu \
    fonts-liberation \
    fonts-freefont-ttf \
    && rm -rf /var/lib/apt/lists/*

# -------------------------------
# Directorio de trabajo
# -------------------------------
WORKDIR /app

# -------------------------------
# Dependencias Python
# -------------------------------
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# -------------------------------
# Código (CLAVE)
# -------------------------------
COPY . .

# -------------------------------
# Puerto
# -------------------------------
EXPOSE 8000

# -------------------------------
# Arranque
# -------------------------------
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
