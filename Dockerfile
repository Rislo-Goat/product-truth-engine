# JARVIS Ecommerce OS — image API/worker
FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
# Port FIXE 8000, aligné avec EXPOSE et le port cible par défaut du domaine Railway.
# (Évite le 502 quand Railway route le domaine vers 8000 mais injecte un PORT différent.)
CMD ["uvicorn", "jarvis_os.main:app", "--host", "0.0.0.0", "--port", "8000"]
