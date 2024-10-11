#!/usr/bin/env bash

set -o pipefail nounset errexit

function setup () {
    cd output && docker compose up
    # || true
}

function teardown() {
    docker compose down
}

pattern="Starting traffic generator"

read -p "Please enter the number of hosts per AS: " num_hosts
read -p "Please enter the number of ASes: " as_count
echo "Provide a custom path to your logfiles (default is $HOME/research-projects/iperf3-logs): "
read host_volume_loc
default_log="$HOME/research-projects/iperf3-logs/"

if [[ -z ${host_volume_loc+default_log} ]]; then
    python3 iperf-traffic-generator.py -n "$num_hosts" -a "$as_count" -v "$host_volume_loc"
else
    python3 iperf-traffic-generator.py -n "$num_hosts" -a "$as_count" -v "$default_log"
fi

setup | {
    while IFS= read -r line; do
        if [[ "${line}" =~ "${pattern}" ]]; then
            echo "Pattern found, watching logs..."
            . ./watchlog.sh
            break
        fi
    done
}


trap teardown EXIT

### NOTES

# INFO: think about watch command - https://phoenixnap.com/kb/linux-watch-command

# Surround loop with {} if you need vars after loop's done
# Is b/c the loop runs in a subshell, and after it ends vars go poof
