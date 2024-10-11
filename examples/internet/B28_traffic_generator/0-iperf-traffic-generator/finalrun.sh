#!/usr/bin/env bash

set -o pipefail nounset errexit

initial_size=10   # starting size of networks/ASNs
max_size=1000     # maximum size to test
increment=10      # amount to increase per iteration

script="iperf-generator.py"


function setup () {
    cd output && docker compose up || true
    docker compose down
}

for ((size=$initial_size; size<=$max_size; size+=$increment))
do
    echo "Running experiment with network size: $size"

    # run the Python script with the current size
    python3 $script $size && setup

    # don't think i need this
    # the amount of time traffic generator takes
    sleep 120
    # or this
    docker cp "$container_id:root/iperf3_generator.log" "$HOME/research-projects/iperf3-logs/logs_$size.txt"

    # Extract logs from container, and move them to
    # "$HOME/research-projects/iperf3-logs/"
    # NOTE: You need to run this after checking stdout for the right line to appear
    # See this post: https://stackoverflow.com/questions/17545750/read-content-from-stdout-in-realtime 
    mkfifo run_file
    python3 $script $size && setup > run_file &

    while read -r line; do
        ./watchlog.sh
    done < run_file

    # TODO: analyze logs (this can be another script or inline, idk)
    # analyze.sh && python3 analyze_logs.py ./logs_$size.txt

    # NOTE: you should port the cleanup steps from the run script
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

# or


for i in $(seq 1 100); do
    echo "Starting run $i"
    ./run_iperf_test.sh
    sleep 5  # Optional: add a small delay between runs
done
