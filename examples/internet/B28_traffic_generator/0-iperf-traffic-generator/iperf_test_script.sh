#!/usr/bin/env bash
set -euo pipefail

pattern='iperf Done.'
host_log_dir="$HOME/research-projects/iperf3-logs"
watch_file="${host_log_dir}/iperf3_generator.log"
host_log_file="${host_log_dir}/$(date +'%Y-%m-%d-%H:%M')-iperf3_generator.log"

mkdir -p "$host_log_dir"

cleanup() {
    echo "Performing cleanup..."
    cd "/home/josh/research-projects/seed-emulator/examples/internet/B28_traffic_generator/0-iperf-traffic-generator/output/"
    docker compose down || true
    pkill -f "tail -f ${watch_file}" || true
    echo "Cleanup completed"
}

trap cleanup EXIT INT TERM

# user input
read -p "Please enter the number of hosts per AS (default: 5): " num_hosts
num_hosts=${num_hosts:-5}
read -p "Please enter the number of ASes (default: 5): " as_count
as_count=${as_count:-5}
# NOTE: didn't ask `-v` this time around

main() {
    # wipe out the existing watchfile, if one exists
    # NOTE: switched from touch / rm in the setup / cleanup fns
    # what if one doesn't exist?
    : > "$watch_file"

    python3 iperf_improved.py -n "$num_hosts" -a "$as_count" -v

    # start the setup process in the background
    (cd output && docker compose up --remove-orphans) &
    docker_pid=$!

    echo "Waiting for iperf test to complete..."

    timeout 100 tail -f "$watch_file" | while read -r line; do
        echo "$line"
        if [[ "$line" =~ $pattern ]]; then
            echo "iperf3 test completed, copying log file..."
            if cp "$watch_file" "$host_log_file"; then
                echo "Successfully copied logfile to: $host_log_file"
                cleanup
                exit 0
            else
                echo "Failed to copy log file"
                exit 1
            fi
        fi
    done
}

if main; then
    echo "Script completed successfully"
    exit 0
else
    echo "Script failed or timed out"
    exit 1
fi
