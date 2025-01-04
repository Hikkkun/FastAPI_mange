#!/bin/bash

sudo rm -rf data/certbot
docker rmi --force certbot/certbot nginx serverapi_fastapi
./init-letsencrypt.sh