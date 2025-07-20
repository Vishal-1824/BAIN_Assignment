FROM python:3.12-slim-bullseye

WORKDIR /home/app

COPY . .

RUN pip install -r requirements.txt

ENTRYPOINT ["/bin/bash", "/home/app/entrypoint.sh"]