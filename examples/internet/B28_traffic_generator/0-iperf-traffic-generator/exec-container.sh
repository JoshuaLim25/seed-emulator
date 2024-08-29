#!/bin/sh

# container_id="$(docker ps -a | grep iperf-generator | awk '{print $1}')"
container_id=$(docker ps -a --filter "name=iperf-generator" --format "{{.ID}}")
docker exec -it ${container_id} /bin/zsh
