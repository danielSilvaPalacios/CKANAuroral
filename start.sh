#!/bin/bash
docker network create auroral_network
docker-compose -f docker-compose.dev.yml up --build -d