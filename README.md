# BAIN Assignment

## Assignment Overview
- Kafka Broker Service
- Kafka Consumer Service
- Kafka Producer Service
- Postgres Database Service (for persistent database)
- NLP Interpreter for SQL Query 
- Data Visualization Service (for data visualization)
- API Authentication and Authorization via JWT
- Streamlit App for Application UI

## Technologies Used
- Kafka
- Postgres
- Python | FASTAPI
- Docker | Docker Compose
- Streamlit

## Pre-requisites
- Docker

## Setup the .env file
- Update the `.env` file with your Postgres database credentials.
- Make sure to set the `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD` variables.
- Update the ports if necessary. (Make sure the ports are not in use by other services)

## Start the BAIN Assignment Project
- Command to build the images
```bash

docker compose -f docker-compose.yml build --no-cache
```

- Command to start the services
```bash

docker compose -f docker-compose.yml up -d
```

You can now access the services at the following URLs:
(Suppose the ports are set to following values in the `.env` file)
```ini
KUI_PORT=8080
PRODUCER_PORT=8001
CONSUMER_PORT=8002
GEN_AI_PORT=8003
STREAMLIT_PORT=8501
POSTGRES_PORT=5432
PGADMIN_PORT=8081
```
- Kafka Broker UI: `localhost:8080`
- Producer Service: `localhost:8001/docs`
- Consumer Service: `localhost:8002/docs`
- GEN AI Service: `localhost:8003/docs`
- Streamlit App: `localhost:8501`
- PGAdmin: `localhost:8081`