#!/bin/bash

sudo rm -rf data/certbot
docker rm -f $(docker ps -a -q)
docker rmi $(docker images -q)
./init-letsencrypt.sh