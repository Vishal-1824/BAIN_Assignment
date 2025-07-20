FROM python:3.11-slim-bullseye

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

# By default, run Streamlit on container start
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0"]