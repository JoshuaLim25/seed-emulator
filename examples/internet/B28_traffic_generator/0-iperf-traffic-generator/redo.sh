#!/usr/bin/env bash

set -euo pipefail

# NOTE: could just cp it in the beginning
pattern='iperf Done.'
container_id=$(docker ps -a --filter "name=iperf-generator" --format "{{.ID}}")
# container_log_dir="/logs"
# container_log="${container_log_dir}/traffic_generator.log"
container_log="/root/iperf3_generator.log"
host_log_dir="$HOME/research-projects/iperf3-logs"
watchfile="${host_log_dir}/iperf3_generator.log"
host_log_file="${host_log_dir}/$(date +'%Y-%m-%d-%H:%M')-iperf3_generator.log"

mkdir -p "$host_log_dir"

trap teardown EXIT INT TERM

function setup () {
    touch "$watchfile"
    cd output && docker compose up --remove-orphans --abort-on-container-failure
}

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

function teardown() {
    # NOTE: think about what other cleanup tasks you have to do
    # TODO: make sure that docker containers are all being cleaned up
    docker compose down && echo "All cleaned up"
    killall tail
    pkill -f "tail -f" || echo "No tail process to kill."
    touch "$watchfile"
}

read -p "Please enter the number of hosts per AS: " num_hosts
num_hosts=${num_hosts:-5}
read -p "Please enter the number of ASes: " as_count
as_count=${as_count:-5}
read -p "Provide a custom path to your logfiles (default is $HOME/logs-cont/): " host_volume_loc
host_volume_loc=${host_volume_loc:-$HOME/research-projects/iperf3-logs/iperf3_generator.log}  # Set default if no input is given

# python3 iperf-traffic-generator.py -n "$num_hosts" -a "$as_count" -v "$host_volume_loc"
python3 iperf_improved.py -n "$num_hosts" -a "$as_count" -v # "$host_volume_loc"
echo $num_hosts
echo $as_count
echo $host_volume_loc

# setup && tail -f -n0 $logfile &
# tail_pid=$!

# WARN: bad, there's a better way for sure
# ${host_volume_loc+default_log_dir}
#
# if [[ -z ${host_volume_loc} ]]; then    # it's unset
#     echo "No arg given"
#     python3 iperf-traffic-generator.py -n "$num_hosts" -a "$as_count" -v
# else
#     echo "An arg was given"
#     python3 iperf-traffic-generator.py -n "$num_hosts" -a "$as_count" -v "$host_volume_loc"
# fi


####
# Start tailing the shared log in the background
# tail -f -n0 "$host_shared_log" | while IFS= read -r line; do
#     echo "${line}"
#     if [[ $line =~ $pattern ]]; then
#         cp "$host_shared_log" "$host_log_file"
#         break
#     fi
# done &

# tail_pid=$!  # Capture the PID of the tail process
# wait $tail_pid  # Wait for the tail process to complete

# ( tail -f -n0 "${host_shared_log}" & ) | grep -q "$pattern"
####
# tail -f -n0 $host_shared_log 2>&1 > /dev/null | while read line
#     if [[ $line =~ $pattern ]]; then
#         cp "$host_shared_log" "$host_log_file"
#         break
#     fi
# done 

# while read -r line; do
#     echo "$line"
#     if [[ $line =~ $pattern ]]; then
#         cp "$host_shared_log" "$host_log_file"
#         break
#     fi
# done < <(tail -f -n0 $host_shared_log)

tail -f -n0 "${watchfile}" &
tail_pid=$!
setup

while read -r line; do
    echo "${line}"
    if [[ "${line}" =~ $pattern ]]; then
        echo "iperf3 test completed, copying file..."
        cleanup_tail
        wait "$tail_pid" 2>/dev/null || true
        sleep 1
        if cp "$host_shared_log" "$host_log_file"
            echo "Successfully copied logfile, exiting now..."
            teardown
            exit 0
        else
            echo "failed to copy file"
            exit 42
        fi
    fi
done < <(tail -f -n0 "${watchfile}")


echo "loop ended, exiting..."

# Bad ending
echo "Script interrupted. iperf3 test may not have completed."
teardown
exit 42
