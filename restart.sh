#!/bin/bash
docker-compose down
docker container prune
docker-compose -f docker-compose.dev.yml up --build -d