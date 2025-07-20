FROM python:3.13-slim-bullseye

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

ENTRYPOINT ["/bin/bash", "/app/entrypoint.sh"]

