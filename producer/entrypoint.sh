#!/usr/bin/env bash

uvicorn producer:app --port "${PRODUCER_PORT}" --host 0.0.0.0 --reload