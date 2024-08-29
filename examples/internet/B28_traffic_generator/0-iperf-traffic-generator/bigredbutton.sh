#!/usr/bin/env bash

docker network rm -f $(docker network ls -q)
yes | docker network prune
docker rm -f $(docker ps -a -q)
