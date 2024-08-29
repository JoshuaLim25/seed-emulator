#!/bin/env sh

CONTAINER_ID=$(docker ps -a | grep iperf-generator | awk '{print $1}')
docker cp $CONTAINER_ID:root/iperf3_generator.log ./logs/
