#!/usr/bin/env bash

set -euo pipefail

watchfile="/logs/iperf3_generator.log"
pattern='Done.'
container_id=$(docker ps -a --filter "name=iperf-generator" --format "{{.ID}}")
logfile="$HOME/research-projects/iperf3-logs/$(date +'%Y-%m-%d-%H:%M')-iperf3-generator.log"

if [ -z "$container_id" ]; then
    echo "No container found with the name containing 'iperf-generator'"
    exit 1
fi

echo "Waiting for log completion..."
function cleanup_tail() {
    echo "Attempting to clean up tail process with PID $tail_pid"
    if ps -p "${tail_pid}" > /dev/null; then
        echo "Tail process is still running, trying to kill it."
        if kill "${tail_pid}" 2>/dev/null; then
            echo "Tail process killed successfully."
        fi
    else
            echo "Failed to kill tail process."
    fi
}

trap cleanup_tail EXIT

docker exec ${container_id} tail -f -n0 "${watchfile}" &
tail_pid=$!

while read -r line; do
    echo "${line}"
    if [[ "${line}" =~ "${pattern}" ]]; then
        echo "iperf3 test completed, copying file..."
        cleanup_tail
        wait "$tail_pid" 2>/dev/null || true
        sleep 1
        if docker cp ${container_id}:${watchfile} $logfile; then
            echo "Successfully copied logfile, exiting now..."
            exit 0
        else
            echo "failed to copy file"
            exit 42
        fi
    fi
done < <(docker exec ${container_id} tail -f -n0 "${watchfile}")

# Bad ending
echo "Script interrupted. iperf3 test may not have completed."
cleanup_tail
exit 42
