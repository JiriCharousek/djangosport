FROM python:3.11-slim

# Instalace systémových závislostí
RUN apt-get update && apt-get install -y libpq-dev gcc && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instalace Python závislostí
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kopírování projektu
COPY . .

# Příprava statických souborů
RUN python manage.py collectstatic --noinput
EXPOSE 8000

# Příkaz, který spustí migrace a pak Gunicorn
CMD sh -c "python manage.py migrate && gunicorn --bind 0.0.0.0:8000 agenda.wsgi:application"
# Spuštění přes Gunicorn (změňte 'muj_projekt' na název vaší složky se settings.py)
#CMD ["gunicorn", "--bind", "0.0.0.0:8000", "agenda.wsgi:application"]
