FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/* \
 && useradd --create-home --uid 10001 lodgeflow
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p /app/media /app/staticfiles && chown -R lodgeflow:lodgeflow /app
USER lodgeflow
CMD ["gunicorn","lodgeflow.wsgi:application","--bind","0.0.0.0:8000","--workers","3","--threads","2","--timeout","60","--access-logfile","-"]
