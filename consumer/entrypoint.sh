#!/usr/bin/env bash

uvicorn consumer:app --port "${CONSUMER_PORT}" --host 0.0.0.0 --reload