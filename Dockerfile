# Usar Python 3.11 slim
FROM python:3.11-slim

# Variables de entorno para Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Directorio de trabajo
WORKDIR /app

# Copiar requirements primero (para cache de layers)
COPY requirements.txt .

# Instalar dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fuente
COPY . .

# Exponer puerto (Railway lo asigna dinámicamente via PORT)
EXPOSE 8000

# Comando para ejecutar (usando gunicorn para producción)
CMD gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 120 app:app
