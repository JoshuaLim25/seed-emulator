#!/bin/sh

container_id="$(docker ps -a | grep multi-traffic-generator | awk '{print $1}')"
docker exec -it ${container_id} /bin/zsh
