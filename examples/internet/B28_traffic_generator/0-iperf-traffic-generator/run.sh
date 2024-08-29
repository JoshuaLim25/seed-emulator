#!/usr/bin/env bash

# Exit on error, unset var, pipe fail
set -o pipefail nounset errexit

function setup () {
    cd output && docker compose build && docker compose up
}

python3 iperf-traffic-generator.py && setup
