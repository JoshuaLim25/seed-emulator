#!/usr/bin/env bash

initial_size=10   # starting size of networks/ASNs
max_size=1000     # maximum size to test
increment=10      # amount to increase per iteration

for ((size=$initial_size; size<=$max_size; size+=$increment))
do
    echo "Running experiment with network size: $size"

    # run the Python script with the current size
    python3 iperf-generator.py $size

    cd output
    docker compose build && docker compose up -d

    sleep 120

    docker cp "$container_id:root/iperf3_generator.log" "$HOME/research-projects/iperf3-logs/logs_$size.txt"

    # TODO: analyze logs (this can be another script or inline, idk)
    # analyze.sh && python3 analyze_logs.py ./logs_$size.txt

    docker compose down

    # TODO: check for stopping condition (e.g., based on logs / system resources)
    # if <failure_condition>
    # then
    #     echo "System is straining or breaking at size: $size"
    #     break
    # fi

    # maybe sleep bw iterations
    sleep 20000
    echo "IM AWAKE :)"
done
