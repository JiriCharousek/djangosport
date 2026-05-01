FROM python:3.11-slim

# Instalace systémových závislostí
RUN apt-get update && apt-get install -y libpq-dev gcc python3-dev musl-dev && rm -rf /var/lib/apt/lists/*

# Nastavení pracovního adresáře
WORKDIR /app

# Vytvoření složky pro databázi (DŮLEŽITÉ pro Persistent Storage)
RUN mkdir -p /app/database

# Instalace Python závislostí
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kopírování celého projektu (včetně tvého data.json a skriptů)
COPY . .

# Příprava statických souborů
RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "core.wsgi:application"]